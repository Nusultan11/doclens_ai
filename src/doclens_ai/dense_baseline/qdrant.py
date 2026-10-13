from __future__ import annotations

import math
import re
from collections.abc import Sequence
from dataclasses import dataclass
from functools import wraps
from urllib.parse import urlparse
from uuid import UUID, uuid5

import httpx

from doclens_ai.chunking.models import Chunk
from doclens_ai.dense_baseline.embeddings import DenseError, Vector, validate_vectors

QDRANT_VERSION = "1.15.4"
QDRANT_IMAGE = (
    "qdrant/qdrant@sha256:6ac4807063bbecddca0250bfbcff52acf18c22263b904d12919349e6d0a408f1"
)
POINT_NAMESPACE = UUID("61c341ab-89a9-509a-afad-ef86bc6d57f8")


def point_id(chunk: Chunk) -> str:
    return str(uuid5(POINT_NAMESPACE, chunk.source_sha256 + ":" + chunk.chunk_id))


def point_payload(chunk: Chunk) -> dict[str, object]:
    return {
        "chunk_id": chunk.chunk_id,
        "source_sha256": chunk.source_sha256,
        "format": chunk.document_format.value,
        "ordinal": chunk.ordinal,
        "chunking_fingerprint": chunk.config_fingerprint,
    }


@dataclass(frozen=True, slots=True)
class DenseHit:
    chunk_id: str
    score: float


def _protocol_guard(method):
    @wraps(method)
    def guarded(*args, **kwargs):
        try:
            return method(*args, **kwargs)
        except (KeyError, TypeError, AttributeError, OverflowError):
            raise DenseError("malformed Qdrant response or vector data") from None

    return guarded


class QdrantIndex:
    """Own a new offline collection only; never overwrite/recreate an existing one."""

    def __init__(
        self, url: str, collection: str, *, dimensions: int, client: httpx.Client | None = None
    ) -> None:
        parsed = urlparse(url)
        if (
            parsed.scheme != "http"
            or parsed.hostname not in {"127.0.0.1", "localhost", "qdrant"}
            or parsed.username
            or parsed.password
            or parsed.path not in ("", "/")
            or parsed.query
            or parsed.fragment
        ):
            raise DenseError("Qdrant URL must identify a disposable local test server")
        if not re.fullmatch(r"dense_v1_[a-z0-9_]{3,100}", collection):
            raise DenseError("collection must use an isolated dense_v1_ name")
        if type(dimensions) is not int or dimensions <= 0:
            raise DenseError("invalid Qdrant vector dimensions")
        self.collection = collection
        self.dimensions = dimensions
        self._client = client or httpx.Client(base_url=url.rstrip("/"), timeout=30, trust_env=False)
        self._owned_client = client is None
        self._created = False
        self._verified = False
        self._expected: dict[str, dict[str, object]] = {}
        self._expected_vectors: dict[str, Vector] = {}
        self.server_version: str | None = None
        self.configuration = {
            "vectors": {"size": dimensions, "distance": "Cosine"},
            "hnsw_config": {"m": 0},
            "optimizers_config": {"indexing_threshold": 0},
        }

    def _request(self, method: str, path: str, *, allow_missing: bool = False, **kwargs):
        try:
            response = self._client.request(method, path, **kwargs)
            if allow_missing and response.status_code == 404:
                return None
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise DenseError("invalid Qdrant response")
            if payload.get("status", "ok") != "ok":
                raise DenseError("Qdrant operation failed")
            return payload
        except (httpx.HTTPError, ValueError):
            raise DenseError("Qdrant unavailable or invalid response") from None

    @property
    def _path(self) -> str:
        return "/collections/" + self.collection

    @_protocol_guard
    def create(self) -> None:
        root = self._request("GET", "/")
        self.server_version = root.get("version")
        if self.server_version != QDRANT_VERSION:
            raise DenseError("Qdrant server version differs from frozen v1")
        if self._request("GET", self._path, allow_missing=True) is not None:
            raise DenseError("refusing to modify an existing collection")
        if self._request("PUT", self._path, json=self.configuration).get("result") is not True:
            raise DenseError("Qdrant collection creation incomplete")
        self._created = True

    @_protocol_guard
    def upsert(self, chunks: Sequence[Chunk], vectors: Sequence[Vector]) -> None:
        if not self._created:
            raise DenseError("collection has not been created by this experiment")
        validated = validate_vectors(vectors, count=len(chunks), dimensions=self.dimensions)
        expected = {point_id(chunk): point_payload(chunk) for chunk in chunks}
        if len(expected) != len(chunks):
            raise DenseError("duplicate source/chunk point identities")
        self._verified = False
        self._expected = expected
        self._expected_vectors = {
            point_id(chunk): vector for chunk, vector in zip(chunks, validated, strict=True)
        }
        points = [
            {"id": point_id(chunk), "vector": vector, "payload": point_payload(chunk)}
            for chunk, vector in zip(chunks, validated, strict=True)
        ]
        for offset in range(0, len(points), 64):
            result = self._request(
                "PUT",
                self._path + "/points",
                params={"wait": "true"},
                json={"points": points[offset : offset + 64]},
            )
            if result.get("result", {}).get("status") != "completed":
                raise DenseError("Qdrant point upsert incomplete")

    @_protocol_guard
    def verify(self) -> int:
        self._verified = False
        details = self._request("GET", self._path)["result"]
        actual_vectors = details["config"]["params"]["vectors"]
        if (
            actual_vectors.get("size") != self.dimensions
            or actual_vectors.get("distance") != "Cosine"
        ):
            raise DenseError("Qdrant collection vector configuration mismatch")
        count = self._request("POST", self._path + "/points/count", json={"exact": True})["result"][
            "count"
        ]
        if count != len(self._expected):
            raise DenseError("incomplete or unexpected Qdrant point count")
        seen: set[str] = set()
        offsets: set[str] = set()
        offset = None
        while True:
            body = {"limit": 64, "with_payload": True, "with_vector": True}
            if offset is not None:
                body["offset"] = offset
            page = self._request("POST", self._path + "/points/scroll", json=body)["result"]
            for point in page["points"]:
                identity = str(point.get("id"))
                if (
                    identity in seen
                    or identity not in self._expected
                    or point.get("payload") != self._expected[identity]
                ):
                    raise DenseError("Qdrant point identity or metadata mismatch")
                vector = validate_vectors(
                    [point.get("vector", [])], count=1, dimensions=self.dimensions
                )[0]
                if any(
                    not math.isclose(actual, expected, rel_tol=1e-5, abs_tol=1e-6)
                    for actual, expected in zip(
                        vector, self._expected_vectors[identity], strict=True
                    )
                ):
                    raise DenseError("Qdrant stored vector differs from original embedding")
                seen.add(identity)
            offset = page.get("next_page_offset")
            if offset is None:
                break
            if str(offset) in offsets:
                raise DenseError("Qdrant scroll pagination cycle")
            offsets.add(str(offset))
        if seen != self._expected.keys():
            raise DenseError("Qdrant stored identities differ from complete corpus")
        self._verified = True
        return count

    @_protocol_guard
    def search(self, vector: Vector) -> tuple[DenseHit, ...]:
        if not self._verified:
            raise DenseError("Qdrant index must be verified before retrieval")
        validate_vectors([vector], count=1, dimensions=self.dimensions)
        if not self._expected:
            return ()
        # Fetch the small full score pool so ties at rank 10 cannot hide candidate identities.
        result = self._request(
            "POST",
            self._path + "/points/query",
            json={
                "query": vector,
                "limit": len(self._expected),
                "params": {"exact": True},
                "with_payload": True,
                "with_vector": False,
            },
        )["result"]
        hits = []
        seen: set[str] = set()
        for point in result["points"]:
            identity = str(point.get("id"))
            if (
                identity in seen
                or identity not in self._expected
                or point.get("payload") != self._expected[identity]
            ):
                raise DenseError("retrieved point identity or metadata mismatch")
            score = point.get("score")
            if type(score) not in (int, float) or not math.isfinite(score):
                raise DenseError("retrieved score is invalid")
            seen.add(identity)
            hits.append(DenseHit(str(self._expected[identity]["chunk_id"]), float(score)))
        if seen != self._expected.keys():
            raise DenseError("incomplete Qdrant exact-search score pool")
        return tuple(sorted(hits, key=lambda hit: (-hit.score, hit.chunk_id))[:10])

    def close(self) -> None:
        try:
            if self._created:
                self._request("DELETE", self._path)
                self._created = False
        finally:
            if self._owned_client:
                self._client.close()
