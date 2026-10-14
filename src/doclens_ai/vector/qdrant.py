from __future__ import annotations

import math
import re
from collections.abc import Sequence
from dataclasses import dataclass
from urllib.parse import urlparse
from uuid import UUID, uuid5

import httpx

from doclens_ai.dense_baseline.embeddings import DenseError, Vector, validate_vectors
from doclens_ai.dense_baseline.qdrant import QDRANT_IMAGE, QDRANT_VERSION

__all__ = [
    "QDRANT_IMAGE",
    "QDRANT_VERSION",
    "ProductionQdrant",
    "VectorPoint",
    "VectorFailure",
    "point_id",
]


class VectorFailure(RuntimeError):
    def __init__(self, code: str, *, retryable: bool) -> None:
        super().__init__(code)
        self.code = code
        self.retryable = retryable


def point_id(index_revision_id: UUID, chunk_id: UUID, chunk_identity: str) -> str:
    return str(uuid5(index_revision_id, str(chunk_id) + ":" + chunk_identity))


@dataclass(frozen=True, slots=True)
class VectorPoint:
    id: str
    vector: Vector
    payload: dict[str, str]


@dataclass(frozen=True, slots=True)
class SearchHit:
    id: str
    score: float
    payload: dict[str, str]


class ProductionQdrant:
    """Persistent collection, lease-revision-scoped points; never delete/recreate on close."""

    def __init__(
        self,
        url: str,
        collection: str,
        *,
        dimensions: int = 384,
        batch_size: int = 64,
        timeout_seconds: float = 15,
        api_key: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        parsed = urlparse(url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
        ):
            raise VectorFailure("invalid_qdrant_configuration", retryable=False)
        if not re.fullmatch(r"[a-z][a-z0-9_]{2,127}", collection):
            raise VectorFailure("invalid_collection_identity", retryable=False)
        if type(dimensions) is not int or not 1 <= dimensions <= 8192:
            raise VectorFailure("invalid_vector_dimension", retryable=False)
        if type(batch_size) is not int or not 1 <= batch_size <= 256:
            raise VectorFailure("invalid_upsert_batch", retryable=False)
        if not math.isfinite(timeout_seconds) or not 0 < timeout_seconds <= 60:
            raise VectorFailure("invalid_qdrant_timeout", retryable=False)
        self.collection, self.dimensions, self.batch_size = collection, dimensions, batch_size
        self._owned = client is None
        self._client = client or httpx.AsyncClient(
            base_url=url.rstrip("/"),
            timeout=timeout_seconds,
            trust_env=False,
            headers={"api-key": api_key} if api_key else None,
        )

    @property
    def path(self) -> str:
        return "/collections/" + self.collection

    async def _request(self, method: str, path: str, *, allowed_statuses=(), **kwargs):
        try:
            response = await self._client.request(method, path, **kwargs)
            if response.status_code in allowed_statuses:
                return None
            if response.status_code in {400, 401, 403, 422}:
                raise VectorFailure("qdrant_request_rejected", retryable=False)
            response.raise_for_status()
            body = response.json()
            if not isinstance(body, dict) or body.get("status", "ok") != "ok":
                raise VectorFailure("qdrant_invalid_response", retryable=True)
            return body
        except (httpx.HTTPError, ValueError):
            raise VectorFailure("qdrant_unavailable", retryable=True) from None

    async def _collection_details(self) -> None:
        try:
            body = await self._request("GET", self.path)
            vectors = body["result"]["config"]["params"]["vectors"]
            if vectors.get("size") != self.dimensions or vectors.get("distance") != "Cosine":
                raise VectorFailure("qdrant_collection_mismatch", retryable=False)
        except (KeyError, AttributeError, TypeError):
            raise VectorFailure("qdrant_collection_mismatch", retryable=False) from None

    async def ensure_collection(self) -> None:
        # Version and collection are validated on every attempt, including crash/reclaim.
        root = await self._request("GET", "/")
        if root.get("version") != QDRANT_VERSION:
            raise VectorFailure("qdrant_version_mismatch", retryable=False)
        existing = await self._request("GET", self.path, allowed_statuses=(404,))
        if existing is None:
            # A racing creator may win. Re-read and validate; never recreate an existing index.
            created = await self._request(
                "PUT",
                self.path,
                allowed_statuses=(400, 409),
                json={"vectors": {"size": self.dimensions, "distance": "Cosine"}},
            )
            if created is not None and created.get("result") is not True:
                raise VectorFailure("qdrant_collection_unacknowledged", retryable=True)
        await self._collection_details()

    def _expected(self, revision_id: UUID, points: Sequence[VectorPoint]):
        if not points or len({p.id for p in points}) != len(points):
            raise VectorFailure("invalid_candidate_points", retryable=False)
        try:
            validate_vectors(
                [p.vector for p in points], count=len(points), dimensions=self.dimensions
            )
            for point in points:
                UUID(point.id)
                if point.payload.get("index_revision_id") != str(revision_id):
                    raise DenseError("candidate scope mismatch")
                for key in (
                    "workspace_id",
                    "document_id",
                    "document_version_id",
                    "processing_run_id",
                    "index_revision_id",
                    "chunk_id",
                ):
                    UUID(point.payload[key])
                if not re.fullmatch(r"[0-9a-f]{40}", point.payload["embedding_revision"]):
                    raise DenseError("embedding revision mismatch")
                if not re.fullmatch(
                    r"[0-9a-f]{64}", point.payload["embedding_configuration_fingerprint"]
                ):
                    raise DenseError("embedding configuration mismatch")
                if set(point.payload) != {
                    "workspace_id",
                    "document_id",
                    "document_version_id",
                    "processing_run_id",
                    "index_revision_id",
                    "chunk_id",
                    "embedding_revision",
                    "embedding_configuration_fingerprint",
                }:
                    raise DenseError("unexpected payload fields")
        except (DenseError, ValueError, TypeError, KeyError, AttributeError):
            raise VectorFailure("invalid_candidate_points", retryable=False) from None
        return {p.id: p for p in points}

    async def upsert(self, revision_id: UUID, points: Sequence[VectorPoint]) -> None:
        self._expected(revision_id, points)
        for offset in range(0, len(points), self.batch_size):
            body = await self._request(
                "PUT",
                self.path + "/points",
                params={"wait": "true"},
                json={
                    "points": [
                        {"id": p.id, "vector": p.vector, "payload": p.payload}
                        for p in points[offset : offset + self.batch_size]
                    ]
                },
            )
            result = body.get("result")
            if not isinstance(result, dict) or result.get("status") != "completed":
                raise VectorFailure("qdrant_upsert_unacknowledged", retryable=True)

    async def verify(self, revision_id: UUID, points: Sequence[VectorPoint]) -> int:
        expected = self._expected(revision_id, points)
        await self._collection_details()
        scope = {"must": [{"key": "index_revision_id", "match": {"value": str(revision_id)}}]}
        try:
            count = (
                await self._request(
                    "POST", self.path + "/points/count", json={"exact": True, "filter": scope}
                )
            )["result"]["count"]
            if type(count) is not int or count != len(expected):
                raise VectorFailure("candidate_count_mismatch", retryable=False)
            seen, offsets, offset = set(), set(), None
            while True:
                body = {
                    "filter": scope,
                    "limit": self.batch_size,
                    "with_payload": True,
                    "with_vector": True,
                }
                if offset is not None:
                    body["offset"] = offset
                page = (await self._request("POST", self.path + "/points/scroll", json=body))[
                    "result"
                ]
                for point in page["points"]:
                    identity = str(point["id"])
                    if (
                        identity in seen
                        or identity not in expected
                        or point.get("payload") != expected[identity].payload
                    ):
                        raise VectorFailure("candidate_payload_mismatch", retryable=False)
                    vector = validate_vectors(
                        [point.get("vector", [])], count=1, dimensions=self.dimensions
                    )[0]
                    if any(
                        not math.isclose(a, b, rel_tol=1e-5, abs_tol=1e-6)
                        for a, b in zip(vector, expected[identity].vector, strict=True)
                    ):
                        raise VectorFailure("candidate_vector_mismatch", retryable=False)
                    seen.add(identity)
                offset = page.get("next_page_offset")
                if offset is None:
                    break
                if str(offset) in offsets or len(seen) > len(expected):
                    raise VectorFailure("candidate_pagination_mismatch", retryable=False)
                offsets.add(str(offset))
            if seen != expected.keys():
                raise VectorFailure("candidate_identity_mismatch", retryable=False)
            return count
        except (DenseError, KeyError, TypeError, ValueError, AttributeError):
            raise VectorFailure("candidate_verification_failed", retryable=False) from None

    async def search(
        self,
        vector: Vector,
        *,
        workspace_id: UUID,
        revision_ids: Sequence[UUID],
        document_ids: Sequence[UUID] = (),
        limit: int = 20,
    ) -> tuple[SearchHit, ...]:
        if (
            not isinstance(workspace_id, UUID)
            or not revision_ids
            or len(revision_ids) > 512
            or any(not isinstance(value, UUID) for value in (*revision_ids, *document_ids))
            or len(document_ids) > 50
            or type(limit) is not int
            or not 1 <= limit <= 20
        ):
            raise VectorFailure("invalid_search_scope", retryable=False)
        try:
            query = validate_vectors([vector], count=1, dimensions=self.dimensions)[0]
        except (DenseError, TypeError, ValueError):
            raise VectorFailure("invalid_query_vector", retryable=False) from None
        # Read-only: unlike indexing ensure_collection, search never creates a missing collection.
        root = await self._request("GET", "/")
        if root.get("version") != QDRANT_VERSION:
            raise VectorFailure("qdrant_version_mismatch", retryable=False)
        await self._collection_details()
        must = [
            {"key": "workspace_id", "match": {"value": str(workspace_id)}},
            {"key": "index_revision_id", "match": {"any": sorted({str(v) for v in revision_ids})}},
        ]
        if document_ids:
            must.append(
                {"key": "document_id", "match": {"any": sorted({str(v) for v in document_ids})}}
            )
        body = await self._request(
            "POST",
            self.path + "/points/query",
            json={
                "query": query,
                "filter": {"must": must},
                "limit": limit,
                "params": {"exact": True},
                "with_payload": True,
                "with_vector": False,
            },
        )
        try:
            points = body["result"]["points"]
            if not isinstance(points, list) or len(points) > limit:
                raise ValueError("invalid bounded search response")
            hits = {}
            for item in points:
                if not isinstance(item, dict):
                    raise ValueError("invalid search hit")
                score = item["score"]
                if (
                    isinstance(score, bool)
                    or not isinstance(score, int | float)
                    or not math.isfinite(score)
                    or not -1.00001 <= score <= 1.00001
                ):
                    raise ValueError("invalid cosine score")
                try:
                    identity = str(UUID(item["id"]))
                    payload = item["payload"]
                    required = {
                        "workspace_id",
                        "document_id",
                        "document_version_id",
                        "processing_run_id",
                        "index_revision_id",
                        "chunk_id",
                        "embedding_revision",
                        "embedding_configuration_fingerprint",
                    }
                    if not isinstance(payload, dict) or set(payload) != required:
                        continue
                    for key in required - {
                        "embedding_revision",
                        "embedding_configuration_fingerprint",
                    }:
                        if str(UUID(payload[key])) != payload[key]:
                            raise ValueError("invalid scope UUID")
                    if (
                        payload["workspace_id"] != str(workspace_id)
                        or UUID(payload["index_revision_id"]) not in revision_ids
                        or (document_ids and UUID(payload["document_id"]) not in document_ids)
                        or not re.fullmatch(r"[0-9a-f]{40}", payload["embedding_revision"])
                        or not re.fullmatch(
                            r"[0-9a-f]{64}", payload["embedding_configuration_fingerprint"]
                        )
                    ):
                        continue
                except (ValueError, TypeError, AttributeError, KeyError):
                    continue
                hit = SearchHit(identity, float(score), dict(payload))
                if identity not in hits or hit.score > hits[identity].score:
                    hits[identity] = hit
            return tuple(sorted(hits.values(), key=lambda hit: (-hit.score, hit.id)))
        except (ValueError, KeyError, TypeError, AttributeError):
            raise VectorFailure("invalid_search_response", retryable=False) from None

    async def close(self) -> None:
        if self._owned:
            await self._client.aclose()
