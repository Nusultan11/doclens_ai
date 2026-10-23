"""Private, source-bound readiness artifacts; no parser or network execution."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from doclens_ai.eda import corpus_v2 as corpus
from doclens_ai.extraction.fidelity_gold import fingerprint

ROOT = Path(__file__).resolve().parents[2]
VERSION = "extraction-readiness-20261023-v1"


def confined(root: Path, relative: str) -> Path:
    corpus.no_links(root)
    part = Path(relative)
    if part.is_absolute() or part.drive or ".." in part.parts or ":" in relative:
        raise ValueError("unsafe artifact path")
    path = root / part
    corpus.no_links(path)
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("artifact escapes root")
    return path


def private_root(path: Path) -> None:
    corpus.no_links(path)
    if not path.resolve().is_relative_to(ROOT / "evaluation-output"):
        raise ValueError("private evaluation-output destination required")
    path.mkdir(parents=True, exist_ok=True)


def atomic(path: Path, value: Any) -> None:
    corpus.no_links(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    corpus.no_links(temporary)
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def cached(root: Path, name: str, binding: dict, build) -> tuple[dict, bool]:
    """An incomplete write never becomes a cache hit; changed bindings are rejected."""
    path = confined(root, name + ".json")
    receipt = confined(root, name + ".checkpoint.json")
    key = fingerprint({"version": VERSION, "binding": binding})
    if receipt.exists():
        state = corpus.read_json(receipt)
        if state["key"] != key or corpus.sha256(path) != state["sha256"]:
            raise ValueError("checkpoint binding or output drift")
        return corpus.read_json(path, max_bytes=256 * 1024**2), True
    value = build()
    atomic(path, value)
    atomic(receipt, {"key": key, "sha256": corpus.sha256(path)})
    return value, False
