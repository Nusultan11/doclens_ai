"""Offline Corpus v1/Gold readiness audit. Never export private validation inputs."""

from __future__ import annotations

import argparse
import contextlib
import csv
import hashlib
import importlib.metadata
import io
import json
import logging
import sys
import warnings
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

from doclens_ai.chunking.core import _build_source_units
from doclens_ai.evaluation.gold import (
    CORPUS_V1_DATASET_REVISION,
    SYNTHETIC_DATASET_REVISION,
    _load_jsonl,
    load_gold_jsonl,
)
from doclens_ai.extraction import fidelity_eval, fidelity_gold
from doclens_ai.extraction.models import ExtractionResult, TableBlock, TextBlock
from doclens_ai.extraction.parsers import ExtractionLimits, extract_file

ROOT = Path(__file__).resolve().parents[3]
OUTPUT_ROOT = ROOT / "evaluation-output"
FORMATS = ("pdf", "docx", "xlsx")
STATUSES = ("success", "needs_review", "failed", "not_evaluated")


@dataclass(frozen=True)
class FrozenContract:
    name: str
    per_format: int
    manifest_sha256: str
    extraction_gold_fingerprint: str
    retrieval_gold_fingerprint: str
    synthetic_fixture_only: bool = False


CORPUS_V1 = FrozenContract(
    "corpus-v1",
    30,
    "c3a91af4bf789400f23821a30c6468040334bdd65135460b96dc21bb64d335c0",
    "896ce2c0e99b74683a8b15869c7ab72b94a27dd06fce66896db4ec8652c75b6c",
    "d6167fcf93d5cbce122e4bc444b478b23a0f02f3556364f1e3be58ad02f1bc94",
)
LIMITATIONS = [
    "Human review metadata is an attestation, not independently verified review activity.",
    "Declared family splits are checked; near-duplicate/family completeness is NOT_EVALUATED.",
    "Semantic correctness, answerability and complete extraction fidelity are NOT_EVALUATED.",
    "PDF spatial/table units and DOCX ancillary locators require original-document human review.",
    "Current parser evidence resolution is not independent validation of human labels.",
    "No test labels are used for model selection or tuning; no retrieval quality is measured.",
    "Logical parser limits are not a hostile-file sandbox or hard CPU/RSS limits.",
]


def digest(path: Path) -> str | None:
    try:
        if path.is_symlink() or not path.is_file():
            return None
        with path.open("rb") as stream:
            return hashlib.file_digest(stream, "sha256").hexdigest()
    except OSError:
        return None


@contextlib.contextmanager
def quiet_inputs():
    """Contain third-party messages and exception excerpts; restore process logging."""
    previous = logging.root.manager.disable
    try:
        logging.disable(logging.CRITICAL)
        with (
            warnings.catch_warnings(),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            warnings.simplefilter("ignore")
            yield
    finally:
        logging.disable(previous)


def code_identity() -> dict:
    files = {
        "gate": Path(__file__),
        "fidelity_evaluator_and_corpus_validator": Path(fidelity_eval.__file__),
        "fidelity_gold_validator": Path(fidelity_gold.__file__),
        "retrieval_gold_validator": ROOT / "src/doclens_ai/evaluation/gold.py",
        "extraction_parser": ROOT / "src/doclens_ai/extraction/parsers.py",
        "extraction_models": ROOT / "src/doclens_ai/extraction/models.py",
        "retrieval_source_unit_builder": ROOT / "src/doclens_ai/chunking/core.py",
    }
    return {
        "python": sys.version.split()[0],
        "code_sha256": {
            key: hashlib.sha256(p.read_text(encoding="utf-8").encode()).hexdigest()
            for key, p in files.items()
        },
        "dependencies": {
            name: importlib.metadata.version(name)
            for name in ("pypdf", "python-docx", "openpyxl", "pydantic")
        },
        "extraction_limits": asdict(ExtractionLimits()),
    }


def _inventory(corpus: Path, sources: dict) -> dict:
    """Diagnostic counters only; verify_corpus remains the acceptance boundary.

    Unknown bytes cannot safely be called an extra rather than a changed source.
    Filenames are deliberately not used to guess source identities.
    """
    by_hash = {value[0]: value for value in sources.values()}
    counts: Counter = Counter()
    hashes: Counter = Counter()
    matched = set()
    for path in corpus.rglob("*"):
        if path.is_symlink():
            counts["symlinks"] += 1
        elif path.is_file():
            counts["files"] += 1
            checksum = (
                digest(path) if path.stat().st_size <= ExtractionLimits().max_file_bytes else None
            )
            hashes[checksum] += 1
            expected = by_hash.get(checksum)
            if expected is None:
                counts["unexpected_or_changed_files"] += 1
            elif (path.stat().st_size, path.suffix.lower()) != (expected[1], "." + expected[2]):
                counts["size_or_extension_mismatches"] += 1
            else:
                matched.add(checksum)
    return {
        key: counts[key]
        for key in (
            "files",
            "symlinks",
            "unexpected_or_changed_files",
            "size_or_extension_mismatches",
        )
    } | {
        "verified_source_identities": len(matched),
        "missing_or_changed_source_identities": len(sources) - len(matched),
        "duplicate_file_hashes": sum(n - 1 for h, n in hashes.items() if h and n > 1),
    }


def resolve_unit(result: ExtractionResult, locator: dict, *, start=None, end=None) -> str:
    """Check supported source-unit geometry/bounds, NOT semantic text correctness.

    Unsupported baseline units are NOT_EVALUATED, never invented or invalidated
    merely because the baseline cannot reconstruct them.
    """
    from openpyxl.utils.cell import range_boundaries

    if result.status == "failed":
        return "not_evaluated"
    if result.document_format != "pdf" and locator.get("region", "body") != "body":
        return "not_evaluated"
    fields: list[str] = []
    if result.document_format == "pdf":
        blocks = [b for b in result.blocks if b.source.page_number == locator["page_number"]]
        if not blocks:
            return "invalid"
        if locator.get("region", "body") != "body":
            return "not_evaluated"
        if any(
            locator.get(key) is not None for key in ("table_index", "row_index", "column_index")
        ):
            return "not_evaluated"
        if locator.get("block_index") is not None and not any(
            b.source.block_index == locator["block_index"] for b in blocks
        ):
            return "not_evaluated"  # No independent PDF layout block inventory.
        fields = [b.text for b in blocks if isinstance(b, TextBlock)]
    elif result.document_format == "docx":
        blocks = [b for b in result.blocks if b.source.block_index == locator["block_index"]]
        if len(blocks) != 1:
            return "invalid"
        block = blocks[0]
        if locator.get("table_index") is not None:
            if not isinstance(block, TableBlock) or block.table_index != locator["table_index"]:
                return "invalid"
            cells = [
                c
                for row in block.rows
                for c in row.cells
                if all(
                    locator.get(key) is None or getattr(c, key) == locator[key]
                    for key in ("row_index", "column_index")
                )
            ]
            if not cells:
                return "invalid"
            fields = [c.text for c in cells]
        elif isinstance(block, TextBlock):
            if locator.get("row_index") is not None or locator.get("column_index") is not None:
                return "invalid"
            fields = [block.text]
        else:
            return "not_evaluated"
    else:
        sheets = [s for s in result.sheets if s.index == locator["sheet_index"]]
        if len(sheets) != 1:
            return "invalid"
        sheet = sheets[0]
        if locator.get("sheet_name") is not None and locator["sheet_name"] != sheet.name:
            return "invalid"
        table = None
        if locator.get("table_index") is not None:
            if locator["table_index"] >= len(sheet.tables):
                return "invalid"
            table = sheet.tables[locator["table_index"]]
        reference = locator.get("cell_coordinate") or (table.reference if table else None)
        if reference is None:
            return "invalid"
        x1, y1, x2, y2 = range_boundaries(reference)
        if not (1 <= x1 <= x2 <= 16384 and 1 <= y1 <= y2 <= 1048576):
            return "invalid"
        if any(
            locator.get(k) is not None and locator[k] != value
            for k, value in (("row_index", y1 - 1), ("column_index", x1 - 1))
        ):
            return "invalid"
        if table:
            a, b, c, d = range_boundaries(table.reference)
            if not (a <= x1 <= x2 <= c and b <= y1 <= y2 <= d):
                return "invalid"
        cells = [
            c for c in sheet.cells if x1 <= c.column_index + 1 <= x2 and y1 <= c.row_index + 1 <= y2
        ]
        if not cells:
            return "invalid"
        fields = [v for c in cells for v in (c.value, c.formula, c.cached_value) if v is not None]
    if start is not None and not any(end <= len(fidelity_eval.normalize(text)) for text in fields):
        return "invalid"
    return "verified"


def _empty_units() -> dict:
    return {key: 0 for key in ("verified", "invalid", "not_evaluated")}


def resolve_retrieval_unit(result: ExtractionResult, anchor) -> str:
    state = resolve_unit(result, anchor.locator.to_dict())
    if state != "verified":
        return state
    # Retrieval spans index the EXISTING normalized chunk source unit, not raw
    # extraction fields. Tables/cells include the contract's metadata prefixes.
    units = [
        u
        for u in _build_source_units(result)
        if all(getattr(u.source, key) == value for key, value in anchor.locator.to_dict().items())
    ]
    if not units:
        return "not_evaluated"
    if anchor.source_start is not None and not any(anchor.source_end <= len(u.text) for u in units):
        return "invalid"
    return "verified"


def _audit(
    corpus: Path,
    manifest: Path,
    extraction_gold: Path,
    retrieval_gold: Path,
    contract: FrozenContract,
) -> dict:
    inputs = {
        "manifest": manifest,
        "extraction_gold": extraction_gold,
        "retrieval_gold": retrieval_gold,
    }
    before = {key: digest(path) for key, path in inputs.items()}
    findings: Counter = Counter()
    blocked: Counter = Counter()
    expected = contract.per_format * len(FORMATS)
    statuses = {fmt: {s: 0 for s in STATUSES} for fmt in FORMATS}
    for fmt in FORMATS:
        statuses[fmt]["not_evaluated"] = contract.per_format
    report = {
        "schema_version": "3.0",
        "contract": asdict(contract),
        "identity": code_identity(),
        "inputs_sha256": before,
        "corpus": {
            "expected_documents": expected,
            "manifest_rows": None,
            "source_fingerprint": None,
            "integrity": "NOT_EVALUATED",
            "duplicate_identities": None,
            "duplicate_manifest_hashes": None,
            "inclusion_denominator": expected,
        },
        "extraction": {
            "by_format": statuses,
            "audited": 0,
            "eligible_by_status": 0,
            "excluded_by_status": 0,
            "failures": 0,
            "needs_review": 0,
            "not_evaluated": expected,
            "eligibility_rule": "success only; not an ingestion guarantee",
        },
        "extraction_gold": {
            "status": "NOT_EVALUATED",
            "fingerprint": None,
            "source_units": _empty_units(),
            "relationships": _empty_units(),
        },
        "retrieval_gold": {
            "status": "NOT_EVALUATED",
            "fingerprint": None,
            "source_units": _empty_units(),
        },
        "unverified_properties": LIMITATIONS,
    }
    for key, checksum in before.items():
        if checksum is None:
            blocked[key + "_unavailable"] += 1
    if not corpus.is_dir() or corpus.is_symlink():
        blocked["corpus_unavailable"] += 1
    sources, matched, fidelity, retrieval = {}, {}, (), None
    if before["manifest"]:
        try:
            with manifest.open(encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
            report["corpus"].update(
                manifest_rows=len(rows),
                duplicate_identities=len(rows) - len({r.get("document_id") for r in rows}),
                duplicate_manifest_hashes=len(rows) - len({r.get("sha256") for r in rows}),
            )
            sources = fidelity_eval._read_sources(manifest)
            report["corpus"]["source_fingerprint"] = fidelity_gold.fingerprint(sources)
            if before["manifest"] != contract.manifest_sha256:
                findings["manifest_snapshot_changed"] += 1
            if Counter(value[2] for value in sources.values()) != {
                fmt: contract.per_format for fmt in FORMATS
            }:
                findings["corpus_composition_mismatch"] += 1
            mime = {
                "pdf": "application/pdf",
                "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            }
            if any("content_type" in r and r["content_type"] != mime[r["format"]] for r in rows):
                findings["manifest_mime_mismatch"] += 1
        except Exception:
            findings["manifest_invalid"] += 1
    if sources:
        sources_by_hash = {source[0]: source for source in sources.values()}
        if before["extraction_gold"]:
            try:
                # Reuse the retrieval loader's duplicate-key guard as well:
                # Pydantic's JSON entry point alone accepts duplicate JSON keys.
                if extraction_gold.stat().st_size > 20 * 1024 * 1024:
                    raise ValueError
                _load_jsonl(extraction_gold, kind="Gold")
                fidelity = fidelity_gold.load_gold(
                    extraction_gold, sources, allow_synthetic=contract.synthetic_fixture_only
                )
                section = report["extraction_gold"]
                fp = fidelity_gold.fingerprint([r.model_dump(mode="json") for r in fidelity])
                section.update(
                    status="VALID",
                    fingerprint=fp,
                    documents=len(fidelity),
                    unreviewed_corpus_documents=expected - len(fidelity),
                    reviewed_by_format={
                        fmt: sum(r.document_format == fmt for r in fidelity) for fmt in FORMATS
                    },
                    anchors=sum(len(r.anchors) for r in fidelity),
                    order_pairs=sum(len(r.order_pairs) for r in fidelity),
                    table_cells=sum(len(r.table_cells) for r in fidelity),
                    table_relationships=sum(len(r.table_relationships) for r in fidelity),
                    value_checks=sum(len(r.cells) for r in fidelity),
                    pdf_sources_with_table_labels=sum(
                        r.document_format == "pdf" and bool(r.table_cells or r.table_relationships)
                        for r in fidelity
                    ),
                    declared_reviewer_counts=dict(
                        sorted(Counter(r.reviewer_count for r in fidelity).items())
                    ),
                    split_check="NOT_APPLICABLE_NO_SPLIT_IN_FIDELITY_SCHEMA",
                    human_review="DECLARED_NOT_INDEPENDENTLY_VERIFIED",
                )
                section["source_units"]["not_evaluated"] = (
                    section["anchors"] + section["value_checks"]
                )
                section["relationships"]["not_evaluated"] = section["table_relationships"]
                if fp != contract.extraction_gold_fingerprint:
                    findings["extraction_gold_snapshot_changed"] += 1
                    section["status"] = "SNAPSHOT_MISMATCH"
            except Exception:
                fidelity = ()
                findings["extraction_gold_invalid"] += 1
                section = report["extraction_gold"]
                section["status"] = "INVALID"
        if before["retrieval_gold"]:
            try:
                if retrieval_gold.stat().st_size > 20 * 1024 * 1024:
                    raise ValueError
                retrieval = load_gold_jsonl(retrieval_gold, corpus_manifest_path=manifest)
                expected_revision = (
                    SYNTHETIC_DATASET_REVISION
                    if contract.synthetic_fixture_only
                    else CORPUS_V1_DATASET_REVISION
                )
                if retrieval.dataset_revision != expected_revision:
                    raise ValueError
                if any(
                    e.source_document_sha256 not in {s[0] for s in sources.values()}
                    for e in retrieval.examples
                ):
                    raise ValueError
                section = report["retrieval_gold"]
                examples = retrieval.examples
                source_splits: dict[str, set[str]] = {}
                for example in examples:
                    for checksum in {
                        example.source_document_sha256,
                        *(a.document_sha256 for a in example.evidence),
                    }:
                        source_splits.setdefault(checksum, set()).add(example.split.value)
                crossings = sum(len(splits) > 1 for splits in source_splits.values())
                section.update(
                    status="VALID",
                    fingerprint=retrieval.fingerprint,
                    questions=len(examples),
                    source_documents=len(source_splits),
                    unreviewed_corpus_documents=expected - len(source_splits),
                    by_format={
                        fmt: {
                            "source_documents": len(
                                {
                                    e.source_document_sha256
                                    for e in examples
                                    if sources_by_hash[e.source_document_sha256][2] == fmt
                                }
                            ),
                            "questions": sum(
                                sources_by_hash[e.source_document_sha256][2] == fmt
                                for e in examples
                            ),
                            "evidence_anchors": sum(
                                a.document_format == fmt for e in examples for a in e.evidence
                            ),
                        }
                        for fmt in FORMATS
                    },
                    families=len({e.document_family_id for e in examples}),
                    splits={s: sum(e.split == s for e in examples) for s in ("dev", "test")},
                    review_statuses=dict(
                        sorted(Counter(e.review_status.value for e in examples).items())
                    ),
                    answerable=sum(e.answerable for e in examples),
                    unanswerable=sum(not e.answerable for e in examples),
                    evidence_anchors=sum(len(e.evidence) for e in examples),
                    source_split_crossings=crossings,
                    declared_family_split_check="VALID",
                    human_review="DECLARED_NOT_INDEPENDENTLY_VERIFIED",
                )
                if crossings:
                    findings["source_split_leakage"] += crossings
                if retrieval.fingerprint != contract.retrieval_gold_fingerprint:
                    findings["retrieval_gold_snapshot_changed"] += 1
                    section["status"] = "SNAPSHOT_MISMATCH"
                section["source_units"]["not_evaluated"] = section["evidence_anchors"]
            except Exception:
                retrieval = None
                findings["retrieval_gold_invalid"] += 1
                report["retrieval_gold"]["status"] = "INVALID"
        if not blocked.get("corpus_unavailable"):
            try:
                report["corpus"]["inventory"] = _inventory(corpus, sources)
                matched = fidelity_eval.verify_corpus(corpus, sources, ExtractionLimits())
                report["corpus"]["integrity"] = "VERIFIED"
            except Exception:
                findings["corpus_integrity_failed"] += 1
                report["corpus"]["integrity"] = "INVALID"
    results: dict[str, ExtractionResult] = {}
    if matched and not any(
        findings.get(key) for key in ("manifest_snapshot_changed", "corpus_composition_mismatch")
    ):
        for key in ("extraction_gold", "retrieval_gold"):
            report[key]["source_units"] = _empty_units()
        report["extraction_gold"]["relationships"] = _empty_units()
        statuses = {fmt: {s: 0 for s in STATUSES} for fmt in FORMATS}
        fidelity_by_id = {r.document_id: r for r in fidelity}
        evidence_metrics: dict[str, list[int]] = {}
        missing = 0
        for identity in sorted(matched):
            path, (checksum, size, fmt) = matched[identity], sources[identity]
            try:
                result = extract_file(path)
                if (result.source_sha256, result.source_size_bytes, result.document_format) != (
                    checksum,
                    size,
                    fmt,
                ):
                    raise ValueError
            except Exception:
                findings["extraction_execution_failed"] += 1
                statuses[fmt]["failed"] += 1
                continue
            results[identity] = result
            statuses[fmt][result.status.value] += 1
            if result.status == "failed":
                findings["extraction_failed"] += 1
            if identity in fidelity_by_id:
                try:
                    scored = fidelity_eval.score_record(fidelity_by_id[identity], result)
                    missing += scored["missing_evidence_count"]
                    for key, metric in scored["metrics"].items():
                        counts = evidence_metrics.setdefault(key, [0, 0, 0])
                        for i, field in enumerate(("passed", "evaluated", "unsupported")):
                            counts[i] += metric[field]
                except Exception:
                    findings["fidelity_scoring_failed"] += 1
        report["extraction"].update(
            by_format=statuses,
            audited=len(matched),
            eligible_by_status=sum(x["success"] for x in statuses.values()),
            excluded_by_status=sum(x["failed"] + x["needs_review"] for x in statuses.values()),
            failures=sum(x["failed"] for x in statuses.values()),
            needs_review=sum(x["needs_review"] for x in statuses.values()),
            not_evaluated=0,
        )
        if fidelity:
            report["extraction_gold"]["baseline_parser_evidence"] = {
                "metrics": {
                    key: fidelity_eval._metric(*counts)
                    for key, counts in sorted(evidence_metrics.items())
                },
                "missing_required_anchors": missing,
            }
        for record in fidelity:
            result = results.get(record.document_id)
            locations = {}
            for anchor in record.anchors:
                locations[anchor.anchor_id] = (
                    resolve_unit(result, anchor.source.model_dump()) if result else "not_evaluated"
                )
                report["extraction_gold"]["source_units"][locations[anchor.anchor_id]] += 1
            for cell in record.cells:
                state = (
                    resolve_unit(result, cell.source.model_dump()) if result else "not_evaluated"
                )
                report["extraction_gold"]["source_units"][state] += 1
            for pair in record.table_relationships:
                states = (locations[pair.left], locations[pair.right])
                state = (
                    "invalid"
                    if "invalid" in states
                    else ("not_evaluated" if "not_evaluated" in states else "verified")
                )
                report["extraction_gold"]["relationships"][state] += 1
        if retrieval:
            by_hash = {s[0]: results.get(identity) for identity, s in sources.items()}
            for example in retrieval.examples:
                for anchor in example.evidence:
                    result = by_hash.get(anchor.document_sha256)
                    if result and result.document_format != anchor.document_format:
                        state = "invalid"
                    else:
                        state = (
                            resolve_retrieval_unit(result, anchor) if result else "not_evaluated"
                        )
                    report["retrieval_gold"]["source_units"][state] += 1
        try:
            fidelity_eval.verify_corpus(corpus, sources, ExtractionLimits())
        except Exception:
            findings["corpus_changed_during_audit"] += 1
    for key in ("extraction_gold", "retrieval_gold"):
        if report[key]["source_units"]["invalid"]:
            findings[key + "_invalid_source_units"] += report[key]["source_units"]["invalid"]
    for key, path in inputs.items():
        if digest(path) != before[key]:
            findings[key + "_changed_during_audit"] += 1
    if code_identity() != report["identity"]:
        findings["code_or_environment_changed_during_audit"] += 1
    report["findings"] = dict(sorted(findings.items()))
    report["blockers"] = dict(sorted(blocked.items()))
    report["decision"] = "BLOCKED" if blocked else "FIX" if findings else "PASS"
    report["readiness_scope"] = (
        "frozen paired benchmark inputs only; NOT production/fidelity approval"
    )
    report["deterministic_fingerprint"] = fidelity_gold.fingerprint(report)
    return report


def audit(
    corpus: Path,
    manifest: Path,
    extraction_gold: Path,
    retrieval_gold: Path,
    *,
    contract: FrozenContract | None = None,
) -> dict:
    """Read-only audit. Custom contracts exist for explicit unit fixtures, not CLI bypasses."""
    with quiet_inputs():
        return _audit(corpus, manifest, extraction_gold, retrieval_gold, contract or CORPUS_V1)


def write_reports(report: dict, output: Path, *, protected: tuple[Path, ...] = ()) -> None:
    root, target = OUTPUT_ROOT.resolve(), output.resolve()
    if (
        OUTPUT_ROOT.is_symlink()
        or output.is_symlink()
        or target == root
        or not target.is_relative_to(root)
        or target.exists()
        or any(target == p.resolve() or target.is_relative_to(p.resolve()) for p in protected)
    ):
        raise ValueError("Output must be a new directory under evaluation-output")
    target.mkdir(parents=True)
    payload = json.dumps(report, sort_keys=True, indent=2, ensure_ascii=True) + "\n"
    (target / "metrics.json").write_text(payload, encoding="utf-8", newline="\n")
    rows = [
        "# Data Quality & Gold Readiness Gate v3",
        "",
        "Decision: " + report["decision"],
        "",
        "Fingerprint: " + report["deterministic_fingerprint"],
        "",
        "All counts retain the frozen corpus denominator.",
        "",
        "| Format | Denominator | Eligible/success | Needs review | Failed | Not evaluated |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
        *(
            f"| {fmt} | {sum(counts.values())} | {counts['success']} | {counts['needs_review']} | "
            f"{counts['failed']} | {counts['not_evaluated']} |"
            for fmt, counts in report["extraction"]["by_format"].items()
        ),
        "",
        "## Gold and integrity checks",
        "",
        "Corpus integrity: " + report["corpus"]["integrity"],
        "",
        "| Gold | Status | Reviewed | Unreviewed | Units verified/invalid/NE |",
        "| --- | --- | ---: | ---: | --- |",
        *(
            f"| {key} | {report[key]['status']} | "
            f"{report[key].get('documents', report[key].get('source_documents', 'NE'))} | "
            f"{report[key].get('unreviewed_corpus_documents', 'NOT_EVALUATED')} | "
            f"{report[key]['source_units']['verified']}/{report[key]['source_units']['invalid']}/"
            f"{report[key]['source_units']['not_evaluated']} |"
            for key in ("extraction_gold", "retrieval_gold")
        ),
        "",
        *(
            f"{key} fingerprint: {report[key]['fingerprint']}"
            for key in ("extraction_gold", "retrieval_gold")
        ),
        "",
        "Findings: " + json.dumps(report["findings"], sort_keys=True),
        "Blockers: " + json.dumps(report["blockers"], sort_keys=True),
        "",
        "## Unverified properties",
        "",
        *("- " + text for text in report["unverified_properties"]),
        "",
    ]
    (target / "aggregate.md").write_text("\n".join(rows), encoding="utf-8", newline="\n")


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        # argparse normally echoes unrecognized arguments (possibly private paths).
        self.exit(2, "Invalid audit arguments; use --help.\n")


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=Path("local-corpus"))
    parser.add_argument("--manifest", type=Path, default=Path("docs/eda/corpus_v1_manifest.csv"))
    parser.add_argument(
        "--extraction-gold",
        type=Path,
        default=Path("local-evaluation/extraction_fidelity_v1_controls_reviewed.jsonl"),
    )
    parser.add_argument(
        "--retrieval-gold", type=Path, default=Path("local-evaluation/retrieval_gold_v1.jsonl")
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = audit(args.corpus, args.manifest, args.extraction_gold, args.retrieval_gold)
        write_reports(
            report,
            args.output_dir,
            protected=(args.corpus, args.manifest, args.extraction_gold, args.retrieval_gold),
        )
    except Exception:
        print("BLOCKED: audit execution/output unavailable; no private diagnostics exported.")
        return 2
    print(
        json.dumps(
            {"decision": report["decision"], "fingerprint": report["deterministic_fingerprint"]},
            sort_keys=True,
        )
    )
    return {"PASS": 0, "FIX": 1, "BLOCKED": 2}[report["decision"]]


if __name__ == "__main__":
    raise SystemExit(main())
