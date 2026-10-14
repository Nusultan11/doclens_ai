"""Offline, metadata-only extraction fidelity measurement; no production defaults."""

from __future__ import annotations

import argparse
import contextlib
import csv
import hashlib
import importlib.metadata
import io
import json
import logging
import math
import re
import sys
import time
import zipfile
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

from doclens_ai.chunking.core import chunk_document
from doclens_ai.chunking.models import ChunkingConfig, ChunkingStrategy
from doclens_ai.extraction.fidelity_gold import (
    FidelityRecord,
    GoldError,
    Locator,
    fingerprint,
    load_gold,
)
from doclens_ai.extraction.models import (
    DocumentFormat,
    ErrorCategory,
    ExtractionResult,
    ExtractionStatus,
    SourceLocation,
    TableBlock,
    TextBlock,
)
from doclens_ai.extraction.parsers import ExtractionLimits, extract_file

VERSION = "1.0"
PRIORITIES = {
    "c1-0041",
    "c1-0044",
    "c1-0045",
    "c1-0006",
    "c1-0007",
    "c1-0067",
    "c1-0071",
    "c1-0081",
}
_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_METRICS = (
    "required_text_recall",
    "reading_order",
    "table_cells",
    "table_relationships",
    "stored_values",
    "formulas",
    "cached_values",
    "displayed_values",
    "provenance",
)


def normalize(text: str) -> str:
    """Collapse whitespace only; never lowercase, round numbers or execute formulas."""
    return " ".join(text.split())


@dataclass(frozen=True)
class Observation:
    text: str
    source: SourceLocation
    ordinal: int
    row_span: int = 1
    column_span: int = 1
    structured_cell: bool = False


def _observations(result: ExtractionResult) -> list[Observation]:
    observations: list[Observation] = []
    for block in result.blocks:
        if isinstance(block, TextBlock):
            observations.append(Observation(block.text, block.source, len(observations)))
        elif isinstance(block, TableBlock):
            for row in block.rows:
                for cell in row.cells:
                    observations.append(
                        Observation(
                            cell.text,
                            cell.source,
                            len(observations),
                            cell.row_span,
                            cell.column_span,
                            True,
                        )
                    )
    for sheet in result.sheets:
        from openpyxl.utils.cell import range_boundaries

        merge_spans = {}
        for merged in sheet.merged_ranges:
            min_col, min_row, max_col, max_row = range_boundaries(merged)
            merge_spans[(min_row - 1, min_col - 1)] = (max_row - min_row + 1, max_col - min_col + 1)
        for cell in sheet.cells:
            # Search fields separately, never manufacture a cross-field anchor.
            # Value and cached_value often carry the same value: not two occurrences.
            row_span, column_span = merge_spans.get((cell.row_index, cell.column_index), (1, 1))
            for value in dict.fromkeys((cell.value, cell.formula, cell.cached_value)):
                if value is not None:
                    observations.append(
                        Observation(
                            value,
                            cell.source,
                            len(observations),
                            row_span,
                            column_span,
                            structured_cell=True,
                        )
                    )
    return observations


def _located(source: SourceLocation, expected: Locator) -> bool:
    if expected.region != "body":
        return False  # The frozen contract has no ancillary-region output.
    return all(
        value is None or getattr(source, key, None) == value
        for key, value in expected.model_dump().items()
        if key not in {"region", "part_index"}
    )


def _metric(passed: int, total: int, unsupported: int = 0) -> dict[str, object]:
    return {
        "status": "EVALUATED" if total else "NOT_EVALUATED",
        "passed": passed,
        "evaluated": total,
        "unsupported": unsupported,
        "score": passed / total if total else None,
    }


def score_record(record: FidelityRecord, result: ExtractionResult) -> dict[str, object]:
    """Score reviewed expectations against unchanged structured output in memory."""
    if (
        record.source_sha256 != result.source_sha256
        or record.source_size_bytes != result.source_size_bytes
        or record.document_format != result.document_format
    ):
        raise GoldError("Gold extraction identity mismatch")
    observations = _observations(result)
    found: dict[str, tuple[Observation, int]] = {}
    matched_text = 0
    for anchor in record.anchors:
        needle = normalize(anchor.text)
        # Global recall: text can be present in the wrong location. Provenance is separate.
        global_present = any(needle in normalize(item.text) for item in observations)
        matched_text += int(global_present)
        matches: list[tuple[Observation, int]] = []
        for item in observations:
            if not _located(item.source, anchor.source):
                continue
            text = normalize(item.text)
            start = 0
            while (position := text.find(needle, start)) >= 0:
                matches.append((item, position))
                start = position + len(needle)
        if len(matches) >= anchor.occurrence:
            found[anchor.anchor_id] = matches[anchor.occurrence - 1]
    order_passed = sum(
        pair.before in found
        and pair.after in found
        and (found[pair.before][0].ordinal, found[pair.before][1])
        < (found[pair.after][0].ordinal, found[pair.after][1])
        for pair in record.order_pairs
    )
    table_passed = sum(
        check.anchor_id in found
        and found[check.anchor_id][0].structured_cell
        and (found[check.anchor_id][0].row_span, found[check.anchor_id][0].column_span)
        == (check.row_span, check.column_span)
        for check in record.table_cells
    )
    relation_passed = 0
    for pair in record.table_relationships:
        if pair.left not in found or pair.right not in found:
            continue
        left, right = found[pair.left][0], found[pair.right][0]
        key = "row_index" if pair.relationship == "same_row" else "column_index"
        scope = ("sheet_index", "table_index", "page_number")
        relation_passed += int(
            left.structured_cell
            and right.structured_cell
            and getattr(left.source, key) is not None
            and getattr(left.source, key) == getattr(right.source, key)
            and all(getattr(left.source, k) == getattr(right.source, k) for k in scope)
        )
    cells = [cell for sheet in result.sheets for cell in sheet.cells]
    cell_matches = [
        [cell for cell in cells if _located(cell.source, check.source)] for check in record.cells
    ]
    metrics = {
        "required_text_recall": _metric(matched_text, len(record.anchors)),
        "reading_order": _metric(order_passed, len(record.order_pairs)),
        "table_cells": _metric(table_passed, len(record.table_cells)),
        "table_relationships": _metric(relation_passed, len(record.table_relationships)),
        "provenance": _metric(
            len(found) + sum(len(items) == 1 for items in cell_matches),
            len(record.anchors) + len(record.cells),
        ),
        # Display is not present in ExtractionResult. Null does not mean wrong display.
        "displayed_values": _metric(0, 0, sum(check.check_display for check in record.cells)),
    }
    for metric, field in (
        ("stored_values", "value"),
        ("formulas", "formula"),
        ("cached_values", "cached_value"),
    ):
        passed = sum(
            len(items) == 1 and getattr(items[0], field) == getattr(check, field)
            for check, items in zip(record.cells, cell_matches, strict=True)
        )
        metrics[metric] = _metric(passed, len(record.cells))
    return {
        "metrics": metrics,
        "missing_evidence_count": len(record.anchors) - matched_text,
    }


def _read_sources(manifest: Path) -> dict[str, tuple[str, int, str]]:
    try:
        with manifest.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        sources = {}
        for row in rows:
            identity, digest, fmt = row["document_id"], row["sha256"], row["format"]
            size = int(row["size_bytes"])
            if (
                not re.fullmatch(r"c1-[0-9]{4}", identity)
                or not re.fullmatch(r"[0-9a-f]{64}", digest)
                or fmt not in {"pdf", "docx", "xlsx"}
                or size <= 0
                or identity in sources
            ):
                raise ValueError
            sources[identity] = (digest, size, fmt)
        if (
            not sources
            or len(sources) > 90
            or len({s[0] for s in sources.values()}) != len(sources)
        ):
            raise ValueError
        return sources
    except Exception:
        raise ValueError("Invalid frozen corpus manifest") from None


def _digest_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(data)
    return digest.hexdigest()


def verify_corpus(
    corpus: Path,
    sources: dict[str, tuple[str, int, str]],
    limits: ExtractionLimits,
) -> dict[str, Path]:
    """Match by bytes, not filenames; reject extras, symlinks and changed sources."""
    if corpus.is_symlink() or not corpus.is_dir():
        raise ValueError("Corpus directory rejected")
    by_digest = {value[0]: identity for identity, value in sources.items()}
    matched: dict[str, Path] = {}
    for path in corpus.rglob("*"):
        if path.is_symlink():
            raise ValueError("Corpus symlink rejected")
        if not path.is_file():
            continue
        if len(matched) >= limits.max_files or path.stat().st_size > limits.max_file_bytes:
            raise ValueError("Corpus resource bound exceeded")
        identity = by_digest.get(_digest_file(path))
        if identity is None or identity in matched:
            raise ValueError("Corpus missing, duplicated, extra or changed")
        _, size, fmt = sources[identity]
        if path.stat().st_size != size or path.suffix.lower() != "." + fmt:
            raise ValueError("Corpus size or format mismatch")
        matched[identity] = path
    if set(matched) != set(sources):
        raise ValueError("Corpus incomplete")
    return matched


def _office_inventory(path: Path, fmt: str) -> dict[str, int]:
    """Bounded structural observations of original OOXML, NOT reviewed labels."""
    counts: Counter[str] = Counter()
    with zipfile.ZipFile(path) as archive:
        for entry in archive.infolist():
            name = entry.filename
            relevant = (
                fmt == "docx"
                and name.startswith("word/")
                and name.endswith(".xml")
                and (
                    name == "word/document.xml"
                    or any(
                        name.startswith("word/" + prefix)
                        for prefix in ("header", "footer", "footnotes", "endnotes", "comments")
                    )
                )
            ) or (
                fmt == "xlsx"
                and name.startswith("xl/worksheets/")
                and name.endswith(".xml")
                and "/_rels/" not in name
            )
            if not relevant:
                continue
            data = archive.read(entry)
            if re.search(rb"<!\s*(?:doctype|entity)\b", data, re.I):
                raise ValueError("Unsafe XML")
            root = ET.fromstring(data)
            if fmt == "docx":
                if name == "word/document.xml":
                    counts["main_xml_text_characters"] += sum(
                        len(node.text or "") for node in root.iter(_W + "t")
                    )
                    counts["nested_tables"] += sum(
                        len(node.findall(".//" + _W + "tbl"))
                        for node in root.findall("./" + _W + "body/" + _W + "tbl")
                    )
                    body = root.find(_W + "body")
                    if body is not None:
                        counts["body_paragraphs"] = len(body.findall(_W + "p"))
                        counts["body_tables"] = len(body.findall(_W + "tbl"))
                else:
                    counts["ancillary_xml_text_characters"] += sum(
                        len(node.text or "") for node in root.iter(_W + "t")
                    )
            else:
                counts["stored_xml_cells"] += len(root.findall(".//" + _S + "c"))
                dimension = root.find(_S + "dimension")
                counts["maximum_row_dimension_sheets"] += int(
                    dimension is not None and "1048576" in dimension.get("ref", "")
                )
                for cell in root.findall(".//" + _S + "c"):
                    formula, value = cell.find(_S + "f"), cell.find(_S + "v")
                    if formula is not None:
                        counts["formula_xml_cells"] += 1
                        counts["formula_definitions_missing"] += int(not formula.text)
                        counts["formula_caches_missing"] += int(value is None or value.text is None)
                    counts["styled_stored_cells"] += int(cell.get("s", "0") != "0")
    return dict(sorted(counts.items()))


def _layout_experiment(path: Path, result: ExtractionResult) -> dict[str, object]:
    from pypdf import PdfReader

    try:
        reader = PdfReader(path, strict=False)
        if len(reader.pages) > 10:
            return {"status": "SKIPPED_PAGE_BOUND"}
        layout = []
        rotated_layout = []
        for page in reader.pages:
            content = page.get_contents()
            if content is not None and len(content.get_data()) > 10 * 1024 * 1024:
                return {"status": "SKIPPED_CONTENT_BOUND"}
            layout.append(page.extract_text(extraction_mode="layout") or "")
            rotated_layout.append(
                page.extract_text(extraction_mode="layout", layout_mode_strip_rotated=False) or ""
            )
            if max(sum(map(len, layout)), sum(map(len, rotated_layout))) > 5_000_000:
                return {"status": "SKIPPED_CHARACTER_BOUND"}
        plain = [block.text for block in result.blocks if isinstance(block, TextBlock)]
        return {
            "status": "OBSERVED_NOT_REVIEWED",
            "pages": len(layout),
            "layout_characters": sum(map(len, layout)),
            "plain_characters": sum(map(len, plain)),
            "normalized_equal_pages": sum(
                normalize(a) == normalize(b) for a, b in zip(plain, layout, strict=True)
            ),
            "layout_fingerprint": fingerprint(layout),
            "include_rotated_characters": sum(map(len, rotated_layout)),
            "include_rotated_fingerprint": fingerprint(rotated_layout),
            "include_rotated_non_whitespace_equal_pages": sum(
                "".join(a.split()) == "".join(b.split())
                for a, b in zip(plain, rotated_layout, strict=True)
            ),
            "non_whitespace_equal_pages": sum(
                "".join(a.split()) == "".join(b.split()) for a, b in zip(plain, layout, strict=True)
            ),
        }
    except Exception:
        return {"status": "EXPERIMENT_FAILED"}


def _summary(result: ExtractionResult) -> dict[str, object]:
    observations = _observations(result)
    text_blocks = [block for block in result.blocks if isinstance(block, TextBlock)]
    table_blocks = [block for block in result.blocks if isinstance(block, TableBlock)]
    cells = [cell for sheet in result.sheets for cell in sheet.cells]
    return {
        "status": result.status.value,
        "error_category": result.error_category.value if result.error_category else None,
        "format": result.document_format.value if result.document_format else None,
        "extraction_fingerprint": fingerprint(result.to_dict()),
        "text_blocks": len(text_blocks),
        "tables": len(table_blocks),
        "table_cells": sum(len(row.cells) for block in table_blocks for row in block.rows),
        "sheets": len(result.sheets),
        "cells": len(cells),
        "merged_ranges": sum(len(sheet.merged_ranges) for sheet in result.sheets),
        "sheet_tables": sum(len(sheet.tables) for sheet in result.sheets),
        "formula_definitions": sum(cell.formula is not None for cell in cells),
        "cached_values": sum(cell.cached_value is not None for cell in cells),
        "text_characters": sum(len(item.text) for item in text_blocks),
        "empty_text_blocks": sum(not normalize(item.text) for item in text_blocks),
        "warnings": {
            code: count
            for code, count in sorted(
                Counter(warning.code.value for warning in result.warnings).items()
            )
        },
        "warning_occurrences": dict(
            sorted(
                sum((Counter({w.code.value: w.count}) for w in result.warnings), Counter()).items()
            )
        ),
        "contract_locators": _metric(
            sum(
                item.source.page_number is not None
                or item.source.block_index is not None
                or (item.source.sheet_index is not None and item.source.cell_coordinate is not None)
                for item in observations
            ),
            len(observations),
        ),
    }


def _percentile(values: list[float], percentile: float) -> float | None:
    return (
        round(sorted(values)[max(0, math.ceil(len(values) * percentile) - 1)], 3)
        if values
        else None
    )


def _template(sources: dict[str, tuple[str, int, str]]) -> str:
    records = []
    for identity in sorted(PRIORITIES & sources.keys()):
        digest, size, fmt = sources[identity]
        records.append(
            {
                "schema_version": VERSION,
                "dataset_revision": "corpus-v1-fidelity-v1",
                "dataset_kind": "real",
                "document_id": identity,
                "source_sha256": digest,
                "source_size_bytes": size,
                "document_format": fmt,
                "review_status": "draft",
                "review_basis": "original_document",
                "reviewer_count": 0,
                "reviewed_on": None,
                "anchors": [],
                "order_pairs": [],
                "table_cells": [],
                "table_relationships": [],
                "cells": [],
            }
        )
    return "\n".join(json.dumps(record, sort_keys=True) for record in records) + "\n"


def evaluate(
    corpus: Path,
    manifest: Path,
    output: Path,
    *,
    gold: Path | None = None,
    template: Path | None = None,
    experiments: bool = False,
    allow_synthetic: bool = False,
    measure_latency: bool = True,
    limits: ExtractionLimits | None = None,
) -> dict[str, object]:
    """Validate first, contain failures, export only allowlisted metadata."""
    limits = limits or ExtractionLimits()
    sources = _read_sources(manifest)
    matched = verify_corpus(corpus, sources, limits)
    if output.exists() or corpus.resolve() in output.resolve().parents:
        raise ValueError("Output must be new and outside corpus")
    if template is not None:
        if (
            template.exists()
            or template.parent.name != "local-evaluation"
            or corpus.resolve() in template.resolve().parents
        ):
            raise ValueError("Template must be new and private under local-evaluation")
    records = load_gold(gold, sources, allow_synthetic=allow_synthetic) if gold else ()
    by_id = {record.document_id: record for record in records}
    config = ChunkingConfig(strategy=ChunkingStrategy.STRUCTURE_AWARE)
    metrics = {name: [0, 0, 0] for name in _METRICS}
    documents, latency = [], {fmt: [] for fmt in ("pdf", "docx", "xlsx")}
    missing = 0
    # Silence third-party logs/warnings and stdout which may contain input details.
    import warnings

    old_disable = logging.root.manager.disable
    try:
        logging.disable(logging.CRITICAL)
        for identity in sorted(matched):
            path = matched[identity]
            start = time.perf_counter()
            with (
                warnings.catch_warnings(),
                contextlib.redirect_stdout(io.StringIO()),
                contextlib.redirect_stderr(io.StringIO()),
            ):
                warnings.simplefilter("ignore")
                try:
                    result = extract_file(path, limits=limits)
                except Exception:
                    digest, size, fmt = sources[identity]
                    result = ExtractionResult(
                        schema_version="1.0",
                        document_format=DocumentFormat(fmt),
                        status=ExtractionStatus.FAILED,
                        source_sha256=digest,
                        source_size_bytes=size,
                        error_category=ErrorCategory.EXTRACTION_FAILED,
                    )
            elapsed = (time.perf_counter() - start) * 1000
            # A source mutation after the initial audit must fail closed.
            digest, size, fmt = sources[identity]
            if _digest_file(path) != digest or path.stat().st_size != size:
                raise ValueError("Corpus changed during evaluation")
            if result.source_sha256 not in {None, digest} or result.document_format != fmt:
                raise ValueError("Extraction identity mismatch")
            summary = _summary(result)
            outcome = chunk_document(result, document_id=identity, config=config)
            summary["chunking"] = {
                "status": outcome.status.value,
                "reason": outcome.reason.value if outcome.reason else None,
                "chunks": len(outcome.chunks),
                "fingerprint": outcome.deterministic_fingerprint(),
                "source_characters": outcome.normalized_source_characters,
                "covered_characters": outcome.covered_source_characters,
            }
            summary["document_id"] = identity
            if experiments and identity in PRIORITIES and result.status != "failed":
                with (
                    warnings.catch_warnings(),
                    contextlib.redirect_stdout(io.StringIO()),
                    contextlib.redirect_stderr(io.StringIO()),
                ):
                    warnings.simplefilter("ignore")
                    try:
                        summary["experiment"] = (
                            _layout_experiment(path, result)
                            if fmt == "pdf"
                            else {
                                "status": "OBSERVED_NOT_REVIEWED",
                                "inventory": _office_inventory(path, fmt),
                            }
                        )
                    except Exception:
                        summary["experiment"] = {"status": "EXPERIMENT_FAILED"}
            if identity in by_id:
                scored = score_record(by_id[identity], result)
                missing += scored["missing_evidence_count"]
                for name, score in scored["metrics"].items():
                    for i, field in enumerate(("passed", "evaluated", "unsupported")):
                        metrics[name][i] += score[field]
            if measure_latency:
                latency[fmt].append(elapsed)
            documents.append(summary)
    finally:
        logging.disable(old_disable)
    identity = {
        "schema_version": VERSION,
        "python_version": sys.version.split()[0],
        "source_snapshot": fingerprint(sources),
        "manifest_sha256": _digest_file(manifest),
        "parser_sha256": _digest_file(Path(__file__).with_name("parsers.py")),
        "extraction_models_sha256": _digest_file(Path(__file__).with_name("models.py")),
        "chunking_core_sha256": _digest_file(Path(__file__).parents[1] / "chunking/core.py"),
        "evaluator_sha256": _digest_file(Path(__file__)),
        "gold_contract_sha256": _digest_file(Path(__file__).with_name("fidelity_gold.py")),
        "dependencies": {
            name: importlib.metadata.version(name)
            for name in ("pypdf", "python-docx", "openpyxl", "pydantic")
        },
        "extraction_limits": asdict(limits),
        "chunking_config": asdict(config),
        "chunking_config_fingerprint": config.fingerprint(),
        "pdf_experiment": "pypdf_layout_strip_rotated_true_and_false_max10pages_10MiBstream_5Mchars"
        if experiments
        else "disabled",
    }
    aggregate = {
        fmt: {
            "documents": sum(doc["format"] == fmt for doc in documents),
            "statuses": {
                status: sum(doc["format"] == fmt and doc["status"] == status for doc in documents)
                for status in ("success", "needs_review", "failed")
            },
        }
        for fmt in ("pdf", "docx", "xlsx")
    }
    report = {
        "identity": identity,
        "automated_by_format": aggregate,
        "documents": documents,
        "gold": {
            "kind": records[0].dataset_kind if records else None,
            "reviewed_documents": len(records),
            "fingerprint": fingerprint([r.model_dump(mode="json") for r in records])
            if records
            else None,
            "anchors": sum(len(r.anchors) for r in records),
            "reviewed_by_format": {
                fmt: sum(r.document_format == fmt for r in records) for fmt in aggregate
            },
        },
        "reviewed_fidelity": {
            "metrics": {name: _metric(*values) for name, values in metrics.items()},
            "missing_evidence_count": missing if records else None,
        },
    }
    report["deterministic_fingerprint"] = fingerprint(report)
    report["runtime"] = {
        fmt: {
            "observations": len(values),
            "p50_ms": _percentile(values, 0.50),
            "p95_ms": _percentile(values, 0.95),
        }
        for fmt, values in latency.items()
    }
    output.mkdir(parents=True)
    (output / "metrics.json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    if template is not None:
        template.parent.mkdir(parents=True, exist_ok=True)
        with template.open("x", encoding="utf-8") as stream:
            stream.write(_template(sources))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--gold", type=Path)
    parser.add_argument("--annotation-template", type=Path)
    parser.add_argument("--experiments", action="store_true")
    parser.add_argument("--allow-synthetic", action="store_true")
    parser.add_argument("--omit-runtime", action="store_true")
    args = parser.parse_args()
    try:
        report = evaluate(
            args.corpus,
            args.manifest,
            args.output_dir,
            gold=args.gold,
            template=args.annotation_template,
            experiments=args.experiments,
            allow_synthetic=args.allow_synthetic,
            measure_latency=not args.omit_runtime,
        )
    except (ValueError, GoldError, OSError):
        print("Fidelity evaluation rejected; inspect private inputs locally.")
        return 1
    print(
        json.dumps(
            {
                "documents": len(report["documents"]),
                "reviewed_documents": report["gold"]["reviewed_documents"],
                "deterministic_fingerprint": report["deterministic_fingerprint"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
