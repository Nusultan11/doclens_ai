from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from types import MappingProxyType

_TOKEN = re.compile(r"[^\W_]+", re.UNICODE)


def tokenize(text: str) -> tuple[str, ...]:
    """Casefold, then keep Unicode alphanumeric runs; punctuation separates tokens."""
    return tuple(_TOKEN.findall(text.casefold()))


@dataclass(frozen=True, slots=True)
class BM25Config:
    k1: float = 1.5
    b: float = 0.75
    top_k: int = 10
    version: str = "1.0"

    def __post_init__(self) -> None:
        for name, value in (("k1", self.k1), ("b", self.b)):
            if isinstance(value, bool) or not isinstance(value, int | float):
                raise ValueError(f"{name} must be a finite number")
            if not math.isfinite(value):
                raise ValueError(f"{name} must be a finite number")
        if self.k1 <= 0 or not 0 <= self.b <= 1:
            raise ValueError("k1 must be positive and b must be between 0 and 1")
        if type(self.top_k) is not int or not 1 <= self.top_k <= 1_000:
            raise ValueError("top_k must be an integer between 1 and 1000")
        if self.version != "1.0":
            raise ValueError("unsupported BM25 version")

    def to_dict(self) -> dict[str, object]:
        return {
            **asdict(self),
            "tokenization": "unicode-alphanumeric-casefold-v1",
            "query_term_policy": "deduplicate",
            "idf": "log(1 + (N - df + 0.5) / (df + 0.5))",
            "document_unit": "chunk",
            "stopwords": False,
            "stemming": False,
        }


@dataclass(frozen=True, slots=True)
class BM25Document:
    stable_id: str
    text: str


@dataclass(frozen=True, slots=True)
class BM25Hit:
    stable_id: str
    score: float


class BM25Index:
    """Rank only text, using fixed configuration and stable-ID tie breaks."""

    def __init__(
        self, documents: Iterable[BM25Document], *, config: BM25Config | None = None
    ) -> None:
        self.config = config or BM25Config()
        unique: dict[str, str] = {}
        for document in documents:
            if not isinstance(document.stable_id, str) or not document.stable_id.strip():
                raise ValueError("document stable_id must be nonblank")
            if not isinstance(document.text, str):
                raise ValueError("document text must be a string")
            if document.stable_id in unique and unique[document.stable_id] != document.text:
                raise ValueError("conflicting content for one stable document ID")
            unique[document.stable_id] = document.text
        self._ids = tuple(sorted(unique))
        lengths: dict[str, int] = {}
        frequency: Counter[str] = Counter()
        postings: dict[str, list[tuple[str, int]]] = defaultdict(list)
        identities = []
        for stable_id in self._ids:
            text = unique[stable_id]
            terms = Counter(tokenize(text))
            lengths[stable_id] = sum(terms.values())
            frequency.update(terms.keys())
            for term, count in terms.items():
                postings[term].append((stable_id, count))
            identities.append(
                {"stable_id": stable_id, "text_sha256": hashlib.sha256(text.encode()).hexdigest()}
            )
        self.document_count = len(self._ids)
        self.average_length = sum(lengths.values()) / self.document_count if self._ids else 0.0
        self.document_lengths = MappingProxyType(lengths)
        self.document_frequency = MappingProxyType(dict(frequency))
        self._postings = postings
        self.fingerprint = hashlib.sha256(
            json.dumps(
                {"documents": identities, "configuration": self.config.to_dict()},
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()

    def search(self, query: str) -> tuple[BM25Hit, ...]:
        scores: dict[str, float] = defaultdict(float)
        if not self.document_count or not self.average_length:
            return ()
        for term in sorted(set(tokenize(query))):
            df = self.document_frequency.get(term, 0)
            if not df:
                continue
            idf = math.log1p((self.document_count - df + 0.5) / (df + 0.5))
            for stable_id, tf in self._postings[term]:
                norm = (
                    1
                    - self.config.b
                    + self.config.b * (self.document_lengths[stable_id] / self.average_length)
                )
                scores[stable_id] += idf * tf * (self.config.k1 + 1) / (tf + self.config.k1 * norm)
        ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
        return tuple(BM25Hit(stable_id, score) for stable_id, score in ranked[: self.config.top_k])
