from __future__ import annotations

import math
import re
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from importlib.metadata import version
from pathlib import Path
from typing import Literal, Protocol

from doclens_ai.retrieval_baseline.runner import file_sha256

MODEL_ID = "intfloat/multilingual-e5-small"
MODEL_REVISION = "614241f622f53c4eeff9890bdc4f31cfecc418b3"
MODEL_FILE_HASHES = {
    "config.json": "69137736cab8b8903a07fe8afaafdda25aac55415a12a55d1bffa9f581abf959",
    "tokenizer_config.json": "a1d6bc8734a6f635dc158508bef000f8e2e5a759c7d92f984b2c86e5ff53425b",
    "special_tokens_map.json": "d05497f1da52c5e09554c0cd874037a083e1dc1b9cfd48034d1c717f1afc07a7",
    "model.safetensors": "1a55775f53449dac10a2bcbc312469fac40b96d53198c407081a831f81c98477",
    "tokenizer.json": "0b44a9d7b51c3c62626640cda0e2c2f70fdacdc25bbbd68038369d14ebdf4c39",
}
InputKind = Literal["query", "passage"]
Vector = tuple[float, ...]


class DenseError(ValueError):
    """Sanitized dense experiment failure; no input text in diagnostic messages."""


@dataclass(frozen=True, slots=True)
class EmbeddingConfig:
    model_id: str = MODEL_ID
    revision: str = MODEL_REVISION
    batch_size: int = 2
    max_tokens: int = 512
    cpu_threads: int = 4
    device: str = "cpu"

    def __post_init__(self) -> None:
        if (
            self.model_id != MODEL_ID
            or not isinstance(self.revision, str)
            or not re.fullmatch(r"[0-9a-f]{40}", self.revision)
        ):
            raise DenseError("invalid pinned embedding model identity")
        if self.revision != MODEL_REVISION or self.device != "cpu":
            raise DenseError("v1 requires the frozen model revision and CPU")
        if type(self.batch_size) is not int or not 1 <= self.batch_size <= 8:
            raise DenseError("batch_size must be an integer between 1 and 8")
        if self.max_tokens != 512 or type(self.max_tokens) is not int:
            raise DenseError("v1 max_tokens must be 512 including prefix/special tokens")
        if type(self.cpu_threads) is not int or not 1 <= self.cpu_threads <= 8:
            raise DenseError("cpu_threads must be an integer between 1 and 8")

    def to_dict(self) -> dict[str, object]:
        return {
            **asdict(self),
            "query_prefix": "query: ",
            "passage_prefix": "passage: ",
            "pooling": "attention-mask mean",
            "normalization": "L2",
            "truncation": "right",
            "dtype": "float32",
            "seed": 0,
            "attention": "eager",
            "deterministic_algorithms": True,
            "interop_threads": 1,
            "padding": "longest in batch",
        }


@dataclass(frozen=True, slots=True)
class EmbeddingBatch:
    vectors: tuple[Vector, ...]
    token_counts: tuple[int, ...]
    truncated_count: int


class Embedder(Protocol):
    dimensions: int
    metadata: dict[str, object]
    load_ms: float

    def encode(self, texts: Sequence[str], *, kind: InputKind) -> EmbeddingBatch: ...


def format_input(text: str, kind: InputKind) -> str:
    if kind not in ("query", "passage") or not isinstance(text, str):
        raise DenseError("invalid embedding input kind or text type")
    return kind + ": " + text


def validate_vectors(
    vectors: Sequence[Sequence[float]], *, count: int, dimensions: int | None = None
) -> tuple[Vector, ...]:
    if len(vectors) != count or count < 0:
        raise DenseError("embedding count mismatch")
    validated = []
    for vector in vectors:
        if dimensions is None:
            dimensions = len(vector)
        if not dimensions or len(vector) != dimensions:
            raise DenseError("embedding dimension mismatch")
        if any(
            isinstance(value, bool)
            or not isinstance(value, int | float)
            or not math.isfinite(value)
            for value in vector
        ):
            raise DenseError("non-finite or nonnumeric embedding")
        norm = math.sqrt(sum(value * value for value in vector))
        if not math.isclose(norm, 1.0, rel_tol=1e-4, abs_tol=1e-4):
            raise DenseError("embedding must be nonzero and L2-normalized")
        validated.append(tuple(float(value) for value in vector))
    return tuple(validated)


def _load_local(model_dir: Path, config: EmbeddingConfig):
    # Lazy imports keep optional ML frameworks out of normal backend/module startup.
    import torch
    from transformers import AutoModel, AutoTokenizer

    torch.manual_seed(0)
    torch.set_num_threads(config.cpu_threads)
    if torch.get_num_interop_threads() != 1:
        torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    tokenizer = AutoTokenizer.from_pretrained(
        model_dir, local_files_only=True, trust_remote_code=False, use_fast=True
    )
    tokenizer.truncation_side = "right"
    model = (
        AutoModel.from_pretrained(
            model_dir,
            local_files_only=True,
            trust_remote_code=False,
            use_safetensors=True,
            attn_implementation="eager",
        )
        .to("cpu")
        .float()
        .eval()
    )
    return torch, tokenizer, model


class E5Embedder:
    def __init__(self, model_dir: Path, *, config: EmbeddingConfig | None = None) -> None:
        self.config = config or EmbeddingConfig()
        start = time.perf_counter()
        try:
            for name, sha in MODEL_FILE_HASHES.items():
                path = model_dir / name
                if path.is_symlink() or file_sha256(path) != sha:
                    raise DenseError("local model/tokenizer bytes differ from pinned revision")
            self._torch, self._tokenizer, self._model = _load_local(model_dir, self.config)
            self.dimensions = self._model.config.hidden_size
            if type(self.dimensions) is not int or self.dimensions <= 0:
                raise DenseError("invalid model output dimensions")
            self.metadata = {
                "configuration": self.config.to_dict(),
                "dimensions": self.dimensions,
                "tokenizer_class": type(self._tokenizer).__name__,
                "tokenizer_identity": dict(MODEL_FILE_HASHES),
                "libraries": {
                    name: version(name)
                    for name in (
                        "torch",
                        "transformers",
                        "huggingface-hub",
                        "tokenizers",
                        "safetensors",
                        "numpy",
                    )
                },
            }
        except Exception as exc:
            if isinstance(exc, DenseError):
                raise
            raise DenseError("local model load failed") from None
        self.load_ms = (time.perf_counter() - start) * 1000

    def encode(self, texts: Sequence[str], *, kind: InputKind) -> EmbeddingBatch:
        vectors = []
        lengths = []
        try:
            for offset in range(0, len(texts), self.config.batch_size):
                batch = [
                    format_input(text, kind)
                    for text in texts[offset : offset + self.config.batch_size]
                ]
                raw = self._tokenizer(batch, truncation=False, padding=False, verbose=False)
                lengths.extend(len(ids) for ids in raw["input_ids"])
                tokens = self._tokenizer(
                    batch,
                    max_length=self.config.max_tokens,
                    padding=True,
                    truncation=True,
                    return_tensors="pt",
                    verbose=False,
                )
                with self._torch.inference_mode():
                    hidden = self._model(**tokens).last_hidden_state
                    mask = tokens["attention_mask"]
                    masked = hidden.masked_fill(~mask[..., None].bool(), 0.0)
                    pooled = masked.sum(dim=1) / mask.sum(dim=1)[..., None]
                    normalized = self._torch.nn.functional.normalize(pooled, p=2, dim=1)
                    vectors.extend(normalized.tolist())
            result = validate_vectors(vectors, count=len(texts), dimensions=self.dimensions)
        except Exception:
            raise DenseError("embedding inference or vector validation failed") from None
        return EmbeddingBatch(
            result, tuple(lengths), sum(length > self.config.max_tokens for length in lengths)
        )
