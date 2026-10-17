"""Optional offline Docling 2.55.1 experiment. Never used by production routing.

API references: docling-project/docling tag v2.55.1 (pipeline_options,
document_converter), docling-core tag v2.48.2 (document, TableCell).
PDF block_index retains the baseline page slot (page_number - 1), not a
Docling item index. Table indices are page-local recognition order. Bounding
boxes, semantic roles, furniture, pictures and rich/multipage tables cannot
be fully represented by the frozen contract; no synthetic cells are filled.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.metadata
import io
import json
import logging
import math
import multiprocessing
import os
import queue
import socket
import time
import warnings
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from doclens_ai.extraction.models import (
    DocumentFormat,
    ErrorCategory,
    ExtractionResult,
    ExtractionStatus,
    ExtractionWarning,
    SourceLocation,
    TableBlock,
    TableCell,
    TableRow,
    TextBlock,
    WarningCode,
    WarningSeverity,
)

VERSION = "1.0"
PDF_IDS = frozenset({"c1-0041", "c1-0044", "c1-0045", "c1-0050"})
GOLD_FINGERPRINT = "896ce2c0e99b74683a8b15869c7ab72b94a27dd06fce66896db4ec8652c75b6c"
MANIFEST_SHA256 = "c3a91af4bf789400f23821a30c6468040334bdd65135460b96dc21bb64d335c0"
MODEL_REVISIONS = {
    "layout": "8f39ad3c0b4c58e9c2d2c84a38465abf757272d8",
    "table": "fc0f2d45e2218ea24bce5045f58a389aed16dc23",
}
MODEL_FILES = (
    "ds4sd--docling-layout-heron/config.json",
    "ds4sd--docling-layout-heron/preprocessor_config.json",
    "ds4sd--docling-layout-heron/model.safetensors",
    "ds4sd--docling-models/model_artifacts/tableformer/fast/tm_config.json",
    "ds4sd--docling-models/model_artifacts/tableformer/fast/tableformer_fast.safetensors",
)


@dataclass(frozen=True)
class BenchmarkProfile:
    gold_sha256: str
    gold_fingerprint: str
    reviewed_ids: frozenset[str]
    primary_ids: frozenset[str]
    control_ids: frozenset[str]

    @property
    def pdf_ids(self) -> frozenset[str]:
        return self.primary_ids | self.control_ids


_LEGACY_REVIEWED_IDS = PDF_IDS | frozenset(
    {"c1-0006", "c1-0007", "c1-0008", "c1-0062", "c1-0067", "c1-0071", "c1-0081"}
)
_FRESH_PDF_IDS = frozenset(
    {"c1-0031", "c1-0032", "c1-0033", "c1-0035", "c1-0040", "c1-0043", "c1-0048", "c1-0049"}
)
PROFILES = {
    "legacy-v1": BenchmarkProfile(
        "30cfdcf31f1036f1e6f813fad34266fa347b5368ee140be7304eb942f0e0d353",
        GOLD_FINGERPRINT,
        _LEGACY_REVIEWED_IDS,
        PDF_IDS,
        frozenset(),
    ),
    "expanded-v1": BenchmarkProfile(
        "f372f54d65916b57994ee62ce1fc00fdc536bcdd459b384c6d6e11e9f114bfaf",
        "50b37582e35382055515a16a2163f83a31ae8dcdd74e80729c499c04e65b815e",
        _LEGACY_REVIEWED_IDS | _FRESH_PDF_IDS,
        _FRESH_PDF_IDS,
        PDF_IDS,
    ),
}


@dataclass(frozen=True)
class CandidateConfig:
    artifacts: Path
    artifact_fingerprint: str
    timeout_seconds: float = 180
    max_process_bytes: int = 2 * 1024**3
    max_file_bytes: int = 50 * 1024**2
    max_pages: int = 200
    max_blocks: int = 100_000
    max_cells: int = 100_000
    max_characters: int = 5_000_000

    def __post_init__(self) -> None:
        if not math.isfinite(self.timeout_seconds):
            raise ValueError("Invalid candidate timeout")
        if len(self.artifact_fingerprint) != 64 or any(
            c not in "0123456789abcdef" for c in self.artifact_fingerprint
        ):
            raise ValueError("Invalid artifact pin")
        if any(
            value <= 0
            for value in (
                self.timeout_seconds,
                self.max_process_bytes,
                self.max_file_bytes,
                self.max_pages,
                self.max_blocks,
                self.max_cells,
                self.max_characters,
            )
        ):
            raise ValueError("Invalid candidate bounds")


class CandidateError(ValueError):
    """Content-free failure: never include Docling exceptions or document text."""


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def artifact_inventory(root: Path) -> dict[str, str]:
    """Hash the required local weight/config files, rejecting symlink ancestors."""
    result = {}
    for name in MODEL_FILES:
        path = root / name
        if any(p.is_symlink() for p in (path, *path.parents)) or not path.is_file():
            raise CandidateError("Local model artifacts unavailable")
        result[name] = _digest(path)
    return result


@contextlib.contextmanager
def _private_offline():
    """Block Python network use and third-party output in the isolated child.

    Not a hostile-input OS sandbox: run trusted frozen sources only. Native
    extensions are not firewalled by this guard. No converter/plugin uses a
    remote service; model loading is explicitly local and HF offline.
    """
    keys = ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_HUB_DISABLE_TELEMETRY")
    previous = {key: os.environ.get(key) for key in keys}
    old_connect, old_connect_ex = socket.socket.connect, socket.socket.connect_ex
    old_disable = logging.root.manager.disable

    def deny(*_args, **_kwargs):
        raise CandidateError("Network forbidden in candidate")

    try:
        os.environ.update(dict.fromkeys(keys, "1"))
        socket.socket.connect = deny
        socket.socket.connect_ex = deny
        logging.disable(logging.CRITICAL)
        with (
            warnings.catch_warnings(),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            warnings.simplefilter("ignore")
            yield
    finally:
        socket.socket.connect, socket.socket.connect_ex = old_connect, old_connect_ex
        logging.disable(old_disable)
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _converter(config: CandidateConfig):
    from doclens_ai.extraction.fidelity_gold import fingerprint

    if fingerprint(artifact_inventory(config.artifacts)) != config.artifact_fingerprint:
        raise CandidateError("Model artifact pin mismatch")
    for package, version in (("docling", "2.55.1"), ("docling-core", "2.48.2")):
        if importlib.metadata.version(package) != version:
            raise CandidateError("Unsupported Docling API version")
    from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
    from docling.document_converter import DocumentConverter, PdfFormatOption

    options = PdfPipelineOptions(
        artifacts_path=config.artifacts.resolve(),
        do_ocr=False,
        do_table_structure=True,
        enable_remote_services=False,
        allow_external_plugins=False,
        do_code_enrichment=False,
        do_formula_enrichment=False,
        do_picture_description=False,
        do_picture_classification=False,
        document_timeout=config.timeout_seconds,
        accelerator_options=AcceleratorOptions(device=AcceleratorDevice.CPU, num_threads=2),
    )
    options.table_structure_options.mode = TableFormerMode.FAST
    options.table_structure_options.do_cell_matching = True
    return DocumentConverter(
        allowed_formats=[InputFormat.PDF],
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)},
    )


def _integer(value: Any, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise CandidateError("Malformed candidate grid/provenance")
    return value


def normalize_document(
    document: Any,
    *,
    source_sha256: str,
    source_size_bytes: int,
    config: CandidateConfig,
) -> ExtractionResult:
    """Adapt ordered native items, not Markdown/dataframe exports or Gold text."""
    blocks: list[TextBlock | TableBlock] = []
    seen: set[str] = set()
    table_indices: Counter[int] = Counter()
    chars = cells = pictures = 0
    pages = document.pages
    if len(pages) > config.max_pages:
        raise CandidateError("Candidate page limit exceeded")
    # Native picture children use the same identity, provenance and safety gates.
    # Pictures themselves still require review; recovering text does not extract drawings.
    for item, _level in document.iterate_items(with_groups=False, traverse_pictures=True):
        reference = item.self_ref
        if not isinstance(reference, str) or not reference:
            raise CandidateError("Missing item identity")
        if reference in seen:
            continue  # Identity deduplication only; repeated equal text is not discarded.
        seen.add(reference)
        if len(seen) > config.max_blocks:
            raise CandidateError("Candidate block limit exceeded")
        label = getattr(item.label, "value", item.label)
        if label == "picture":
            pictures += 1
            continue
        provenance = item.prov
        if len(provenance) > 1 and label not in {"table", "document_index"}:
            if not isinstance(getattr(item, "text", None), str):
                raise CandidateError("Unsupported body item")
            cursor = 0
            for prov in provenance:
                start, end = (_integer(v) for v in prov.charspan)
                page = _integer(prov.page_no, 1)
                if page not in pages or not cursor <= start <= end <= len(item.text):
                    raise CandidateError("Invalid text provenance spans")
                if item.text[cursor:start].strip():
                    raise CandidateError("Unlocated text in provenance spans")
                blocks.append(
                    TextBlock(
                        len(blocks),
                        item.text[start:end],
                        SourceLocation(page_number=page, block_index=page - 1),
                    )
                )
                cursor = end
                if len(blocks) > config.max_blocks:
                    raise CandidateError("Candidate block limit exceeded")
            if item.text[cursor:].strip():
                raise CandidateError("Unlocated text in provenance spans")
            chars += len(item.text)
            if chars > config.max_characters:
                raise CandidateError("Candidate content limit exceeded")
            continue
        if len(provenance) != 1:
            raise CandidateError("Multipage or missing item provenance unsupported")
        page = _integer(provenance[0].page_no, 1)
        if page not in pages:
            raise CandidateError("Unknown provenance page")
        source = SourceLocation(page_number=page, block_index=page - 1)
        if label in {"table", "document_index"}:
            data = item.data
            if not data.table_cells:
                raise CandidateError("Empty recognized table")
            nrows, ncols = _integer(data.num_rows, 1), _integer(data.num_cols, 1)
            if nrows * ncols > config.max_cells:
                raise CandidateError("Candidate grid limit exceeded")
            rows: dict[int, list[TableCell]] = defaultdict(list)
            occupied: set[tuple[int, int]] = set()
            table_index = table_indices[page]
            table_indices[page] += 1
            for cell in data.table_cells:
                if hasattr(cell, "ref"):
                    raise CandidateError("Rich table cells unsupported")
                r, c = _integer(cell.start_row_offset_idx), _integer(cell.start_col_offset_idx)
                re, ce = _integer(cell.end_row_offset_idx, 1), _integer(cell.end_col_offset_idx, 1)
                rs, cs = _integer(cell.row_span, 1), _integer(cell.col_span, 1)
                if re > nrows or ce > ncols or (re - r, ce - c) != (rs, cs):
                    raise CandidateError("Inconsistent table spans")
                locations = {(i, j) for i in range(r, re) for j in range(c, ce)}
                if occupied.intersection(locations):
                    raise CandidateError("Overlapping logical cells")
                occupied.update(locations)
                if not isinstance(cell.text, str):
                    raise CandidateError("Malformed cell text")
                chars += len(cell.text)
                cells += 1
                if cells > config.max_cells or chars > config.max_characters:
                    raise CandidateError("Candidate content limit exceeded")
                rows[r].append(
                    TableCell(
                        r,
                        c,
                        cell.text,
                        SourceLocation(
                            page_number=page,
                            block_index=page - 1,
                            table_index=table_index,
                            row_index=r,
                            column_index=c,
                        ),
                        rs,
                        cs,
                    )
                )
            blocks.append(
                TableBlock(
                    len(blocks),
                    table_index,
                    tuple(
                        TableRow(r, tuple(sorted(row, key=lambda cell: cell.column_index)))
                        for r, row in sorted(rows.items())
                    ),
                    SourceLocation(page_number=page, block_index=page - 1, table_index=table_index),
                )
            )
        else:
            if not isinstance(getattr(item, "text", None), str):
                raise CandidateError("Unsupported body item")
            chars += len(item.text)
            if chars > config.max_characters:
                raise CandidateError("Candidate content limit exceeded")
            blocks.append(TextBlock(len(blocks), item.text, source))
    notices = []
    if pictures:
        notices.append(
            ExtractionWarning(WarningCode.DRAWINGS_NOT_EXTRACTED, WarningSeverity.REVIEW, pictures)
        )
    if not chars:
        notices.append(ExtractionWarning(WarningCode.INSUFFICIENT_TEXT, WarningSeverity.REVIEW))
    return ExtractionResult(
        "1.0",
        DocumentFormat.PDF,
        ExtractionStatus.NEEDS_REVIEW if notices else ExtractionStatus.SUCCESS,
        source_sha256,
        source_size_bytes,
        blocks=tuple(blocks),
        warnings=tuple(notices),
    )


def extract_candidate(
    path: Path,
    config: CandidateConfig,
    *,
    converter: Any | None = None,
    diagnostics: dict | None = None,
) -> ExtractionResult:
    """File-isolated optional candidate; errors contain no private input details."""
    digest = size = None
    category = ErrorCategory.EXTRACTION_FAILED
    phase = "input_validation"
    try:
        if path.is_symlink():
            category = ErrorCategory.SYMLINK_NOT_ALLOWED
            raise CandidateError("Source symlink")
        size = path.stat().st_size
        if not 0 < size <= config.max_file_bytes:
            category = ErrorCategory.LIMIT_EXCEEDED if size else ErrorCategory.EMPTY_FILE
            raise CandidateError("Source size rejected")
        digest = _digest(path)
        if path.suffix.lower() != ".pdf":
            category = ErrorCategory.UNSUPPORTED_FORMAT
            raise CandidateError("PDF required")
        with _private_offline():
            phase = "model_initialization"
            active = converter if converter is not None else _converter(config)
            phase = "conversion"
            conversion = active.convert(
                path,
                raises_on_error=False,
                max_num_pages=config.max_pages,
                max_file_size=config.max_file_bytes,
            )
            if getattr(conversion.status, "value", conversion.status) != "success":
                raise CandidateError("Incomplete conversion")
            phase = "normalization"
            result = normalize_document(
                conversion.document, source_sha256=digest, source_size_bytes=size, config=config
            )
        phase = "source_integrity"
        if _digest(path) != digest or path.stat().st_size != size:
            raise CandidateError("Source changed during conversion")
        return result
    except (ImportError, importlib.metadata.PackageNotFoundError):
        category = ErrorCategory.MISSING_DEPENDENCY
    except OSError:
        category = ErrorCategory.FILE_UNREADABLE
    except Exception as exc:
        if diagnostics is not None:
            messages = {
                "Multipage or missing item provenance unsupported": "unsupported_provenance",
                "Overlapping logical cells": "overlapping_grid",
                "Inconsistent table spans": "inconsistent_spans",
                "Empty recognized table": "empty_table",
                "Unsupported body item": "unsupported_body_item",
                "Rich table cells unsupported": "rich_cells",
            }
            diagnostics["reason"] = (
                messages.get(str(exc), "candidate_rejected")
                if isinstance(exc, CandidateError)
                else "candidate_rejected"
            )
        pass  # Isolation: never print third-party validation inputs or private exception text.
    if diagnostics is not None:
        diagnostics["failure_phase"] = phase
    return ExtractionResult(
        "1.0", DocumentFormat.PDF, ExtractionStatus.FAILED, digest, size, error_category=category
    )


def _worker(channel, path: Path, config: CandidateConfig, record, include_metadata=False) -> None:
    """Return only metadata across IPC; no extraction payload is persisted."""
    from doclens_ai.extraction.fidelity_eval import _observations, normalize, score_record
    from doclens_ai.extraction.fidelity_gold import fingerprint
    from doclens_ai.extraction.parsers import extract_file

    try:
        with _private_offline():
            outcomes = {}
            diagnostics = {}
            for name, call in (
                ("baseline", lambda: extract_file(path)),
                ("docling", lambda: extract_candidate(path, config, diagnostics=diagnostics)),
            ):
                started = time.perf_counter()
                result = call()
                elapsed = (time.perf_counter() - started) * 1000
                outcomes[name] = {
                    "status": result.status.value,
                    "error_category": (
                        result.error_category.value if result.error_category else None
                    ),
                    "scores": score_record(record, result)
                    if result.status != ExtractionStatus.FAILED
                    else None,
                    "extraction_fingerprint": fingerprint(result.to_dict()),
                    "latency_ms": elapsed,
                }
                if include_metadata:
                    counts: Counter[str] = Counter()
                    for warning in result.warnings:
                        counts[str(getattr(warning.code, "value", warning.code))] += warning.count
                    outcomes[name]["warning_counts"] = dict(sorted(counts.items()))
                    outcomes[name]["eligible_by_status"] = result.status == ExtractionStatus.SUCCESS
                    hits = None
                    if result.status != ExtractionStatus.FAILED:
                        fields = [normalize(item.text) for item in _observations(result)]
                        hits = {
                            anchor.anchor_id: any(
                                normalize(anchor.text) in field for field in fields
                            )
                            for anchor in record.anchors
                        }
                        if (
                            sum(hits.values())
                            != outcomes[name]["scores"]["metrics"]["required_text_recall"]["passed"]
                        ):
                            raise CandidateError("Anchor observation mismatch")
                    outcomes[name]["required_anchor_hits"] = hits
                if name == "docling" and diagnostics:
                    outcomes[name]["diagnostics"] = diagnostics
                channel.put({name: outcomes[name]})
            channel.put({"complete": True})
    except Exception:
        channel.put({"blocked": "worker_failure"})


def _isolated(path: Path, config: CandidateConfig, record, *, include_metadata=False) -> dict:
    import psutil  # Experimental environment only; normal unit tests use fakes.

    context = multiprocessing.get_context("spawn")
    channel = context.Queue()
    args = (channel, path, config, record)
    if include_metadata:
        args += (True,)
    child = context.Process(target=_worker, args=args)
    started = time.perf_counter()
    peak = 0
    result = {"blocked": "worker_failure"}
    child.start()
    try:
        while True:
            try:
                info = psutil.Process(child.pid).memory_info()
                peak = max(peak, getattr(info, "peak_wset", info.rss))
            except psutil.NoSuchProcess:
                pass
            if peak > config.max_process_bytes:
                result["blocked"] = "memory_limit"
                break
            if time.perf_counter() - started > config.timeout_seconds:
                result["blocked"] = "timeout"
                break
            try:
                message = channel.get(timeout=0.05)
                if message.get("complete"):
                    result.pop("blocked", None)
                    break
                result.update(message)
            except queue.Empty:
                if not child.is_alive():
                    # Final drain handles process-exit/queue-feeder timing.
                    try:
                        message = channel.get(timeout=1)
                        if message.get("complete"):
                            result.pop("blocked", None)
                        else:
                            result.update(message)
                    except queue.Empty:
                        pass
                    break
    finally:
        if child.is_alive():
            child.terminate()
        child.join(timeout=5)
        if child.is_alive():
            child.kill()
            child.join()
        channel.close()
    result["peak_process_bytes"] = peak or None
    result["wall_ms"] = (time.perf_counter() - started) * 1000
    return result


def evaluate_candidate(
    corpus: Path,
    manifest: Path,
    gold: Path,
    output: Path,
    config: CandidateConfig,
    *,
    profile: str = "legacy-v1",
) -> dict:
    from doclens_ai.evaluation.gold import _load_jsonl
    from doclens_ai.extraction.fidelity_eval import _read_sources, verify_corpus
    from doclens_ai.extraction.fidelity_gold import fingerprint, load_gold
    from doclens_ai.extraction.parsers import ExtractionLimits

    if profile not in PROFILES:
        raise CandidateError("Unknown frozen benchmark profile")
    selected = PROFILES[profile]
    if output.exists() or corpus.resolve() in output.resolve().parents:
        raise CandidateError("New output outside corpus required")
    # Full integrity audit MUST precede subset selection or model initialization.
    if _digest(manifest) != MANIFEST_SHA256:
        raise CandidateError("Manifest pin mismatch")
    sources = _read_sources(manifest)
    matched = verify_corpus(corpus, sources, ExtractionLimits())
    if len(matched) != 90:
        raise CandidateError("Frozen ninety-source corpus required")
    gold_bytes_sha256 = _digest(gold)
    if gold_bytes_sha256 != selected.gold_sha256:
        raise CandidateError("Gold byte pin mismatch")
    _load_jsonl(gold, kind="Fidelity Gold")  # Reject duplicate keys before Pydantic loading.
    records = load_gold(gold, sources)
    if (
        len(records) != len(selected.reviewed_ids)
        or {r.document_id for r in records} != selected.reviewed_ids
        or {r.document_id for r in records if r.document_format == "pdf"} != selected.pdf_ids
        or fingerprint([r.model_dump(mode="json") for r in records]) != selected.gold_fingerprint
    ):
        raise CandidateError("Gold pin mismatch")
    inventory = artifact_inventory(config.artifacts)
    if fingerprint(inventory) != config.artifact_fingerprint:
        raise CandidateError("Artifact pin mismatch")
    versions = {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()}
    documents = []
    runtime = []
    for record in records:
        if record.document_id not in selected.pdf_ids:
            continue
        if profile == "legacy-v1":
            outcome = _isolated(matched[record.document_id], config, record)
        else:
            outcome = _isolated(matched[record.document_id], config, record, include_metadata=True)
        runtime.append(
            {
                "document_id": record.document_id,
                "peak_process_bytes": outcome.pop("peak_process_bytes"),
                "wall_ms": outcome.pop("wall_ms"),
            }
        )
        for name in ("baseline", "docling"):
            if name in outcome:
                runtime[-1][name + "_latency_ms"] = outcome[name].pop("latency_ms")
        document = {"document_id": record.document_id, **outcome}
        if profile == "expanded-v1":
            document["population"] = (
                "fresh" if record.document_id in selected.primary_ids else "control"
            )
            document["label_counts"] = {
                name: len(getattr(record, name))
                for name in (
                    "anchors",
                    "order_pairs",
                    "table_cells",
                    "table_relationships",
                    "cells",
                )
            }
        documents.append(document)
    if verify_corpus(corpus, sources, ExtractionLimits()) != matched:
        raise CandidateError("Corpus changed")
    if fingerprint(artifact_inventory(config.artifacts)) != config.artifact_fingerprint:
        raise CandidateError("Models changed")
    if _digest(gold) != gold_bytes_sha256 or _digest(manifest) != MANIFEST_SHA256:
        raise CandidateError("Frozen labels or manifest changed")
    settings = asdict(config)
    settings.pop("artifacts")  # No local path is serialized.
    report = {
        "version": VERSION,
        "candidate_sha256": _digest(Path(__file__)),
        "manifest_sha256": MANIFEST_SHA256,
        "gold_fingerprint": selected.gold_fingerprint,
        "gold_bytes_sha256": gold_bytes_sha256,
        "code_sha256": {
            name: _digest(Path(__file__).with_name(name))
            for name in ("parsers.py", "models.py", "fidelity_eval.py", "fidelity_gold.py")
        },
        "table_mode": "fast",
        "model_revisions": MODEL_REVISIONS,
        "model_files": inventory,
        "environment": versions,
        "configuration": settings,
        "limitations": [
            "furniture_outside_body_iteration",
            "pictures_not_represented",
            "multipage_tables_and_rich_cells_fail_closed",
            "text_split_by_native_provenance_charspans_whitespace_gaps_only",
            "no_bounding_box_or_region_field",
            "page_slot_block_index",
            "page_local_table_index",
            "sampled_memory_guard_not_hard_os_sandbox",
        ],
        "documents": documents,
    }
    if profile == "expanded-v1":
        report["benchmark_profile"] = profile
        report["population"] = {
            "reviewed_documents": len(selected.reviewed_ids),
            "evaluated_pdf_ids": sorted(selected.pdf_ids),
            "fresh_pdf_ids": sorted(selected.primary_ids),
            "control_pdf_ids": sorted(selected.control_ids),
        }
    report["deterministic_fingerprint"] = fingerprint(report)
    report["runtime"] = runtime
    output.mkdir(parents=True)
    (output / "metrics.json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    return report


def _execution_complete(report: dict, profile: str) -> bool:
    if len(report["documents"]) != len(PROFILES[profile].pdf_ids):
        return False
    for doc in report["documents"]:
        if profile == "expanded-v1" and "baseline" not in doc:
            return False
        if profile == "expanded-v1" and doc.get("blocked") in {"timeout", "memory_limit"}:
            # A monitored limit after baseline observation is a measured failed attempt,
            # not missing infrastructure. Keep missing candidate scores null and retain
            # its full Gold denominators; never silently drop the document.
            continue
        if (
            "blocked" in doc
            or "docling" not in doc
            or doc["docling"]["error_category"] == "missing_dependency"
            or doc["docling"].get("diagnostics", {}).get("failure_phase") == "model_initialization"
        ):
            return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("corpus", "manifest", "gold", "output-dir", "artifacts"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--artifact-fingerprint", required=True)
    parser.add_argument("--timeout-seconds", type=float, default=180)
    parser.add_argument("--max-process-mib", type=int, default=2048)
    parser.add_argument("--profile", choices=tuple(PROFILES), default="legacy-v1")
    args = parser.parse_args()
    try:
        report = evaluate_candidate(
            args.corpus,
            args.manifest,
            args.gold,
            args.output_dir,
            CandidateConfig(
                args.artifacts,
                args.artifact_fingerprint,
                args.timeout_seconds,
                args.max_process_mib * 1024**2,
            ),
            profile=args.profile,
        )
    except Exception:
        print("BLOCKED: candidate preflight rejected; inspect local inputs privately")
        return 1
    complete = _execution_complete(report, args.profile)
    print(
        json.dumps(
            {
                "status": "evaluated" if complete else "blocked",
                "documents": len(report["documents"]),
                "deterministic_fingerprint": report["deterministic_fingerprint"],
            }
        )
    )
    return 0 if complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
