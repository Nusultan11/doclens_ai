"""Offline native-PDF diagnostic against a pinned, exposed development reference.

No parser changes, cell reconstruction, semantic scoring or Gold promotion.
All captures and item findings require a fresh ignored output directory.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import platform
import re
import subprocess
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from pydantic import TypeAdapter

from doclens_ai.eda import corpus_v2 as corpus
from doclens_ai.extraction import models, parsers
from doclens_ai.extraction.fidelity_gold import fingerprint
from tools.extraction_quality import pdf_dev_reference as reference
from tools.extraction_quality.extraction_v2 import exact_positions
from tools.extraction_quality.pdf_table_review_packet import fresh_output, write_json
from tools.pdf_ocr_candidate import benchmark as bounded

ROOT = Path(__file__).resolve().parents[2]
REFERENCE_FINGERPRINT = "64fa75b779854918fc50df38bc3e3cb3bf0069c8cb6c76e775bf6c35f8e1c9dc"
VERSION = "pdf-native-dev-diagnostic-1.0"
VALIDATION_PATHS = (
    "package",
    "manifest",
    "corpus",
    "gold",
    "eligibility",
    "plan",
    "reference_manifest",
    "office_manifest",
    "retrieval_gold",
    "answer_gold",
    "confirmation",
)


def validation_args(config: Path) -> argparse.Namespace:
    value = corpus.read_json(config)
    if set(value) != {*VALIDATION_PATHS, "plan_sha256"} or any(
        not isinstance(v, str) or not v for v in value.values()
    ):
        raise ValueError("Validation configuration rejected")
    return argparse.Namespace(
        **{k: Path(v) if k in VALIDATION_PATHS else v for k, v in value.items()}
    )


def literal_observation(literal: str, blocks: list, multiplicity: int, *, symbol=False) -> dict:
    """Page-text evidence only. Repeated references never acquire a unique binding."""
    raw, exact, soft = [], [], []
    compact = "".join(literal.split())
    pattern = (
        (r"(?<![\w+−.,/:\-])" + r"\s*".join(re.escape(c) for c in compact) + r"(?![\w.,/:\-])")
        if compact
        else None
    )
    for block in blocks:
        if literal:
            block_positions = []
            start = 0
            while (start := block.text.find(literal, start)) >= 0:
                raw.append((block.source, start, start + len(literal)))
                block_positions.append(start)
                start += 1
            positions = block_positions if symbol else exact_positions(block.text, literal)
            exact.extend((asdict(block.source), p, p + len(literal)) for p in positions)
        if pattern and not symbol:
            soft.extend(
                (asdict(block.source), m.start(), m.end()) for m in re.finditer(pattern, block.text)
            )
    if not literal:
        state, cause = "EMPTY_CELL_NOT_TEXT_SCORABLE", "empty_cell_case"
    elif not blocks:
        state, cause = "NO_PAGE_OUTPUT", "unknown_cause"
    elif exact:
        unique = len(exact) == 1 and multiplicity == 1
        state = "PAGE_EXACT_UNIQUE" if unique else "PAGE_EXACT_AMBIGUOUS"
        cause = None if unique else "ambiguous_match"
    elif raw:
        state, cause = "SUBSTRING_ONLY_AMBIGUOUS", "ambiguous_match"
    elif soft:
        state, cause = "WHITESPACE_FRAGMENTATION", "fragmentation"
    else:
        state = "MISSING_TEXT"
        available = set("".join(b.text for b in blocks))
        cause = "omission" if set(compact) - available else "unknown_cause"
    return dict(
        literal_state=state,
        literal_cause=cause,
        raw_substring_occurrences=len(raw),
        exact_occurrences=len(exact),
        whitespace_equivalent_occurrences=len(soft),
        reference_multiplicity=multiplicity,
        candidate_evidence_fingerprint=fingerprint(dict(exact=exact, whitespace=soft)),
        # Offsets refer only to the extracted string, not original PDF glyph offsets.
        unique_page_match=(
            dict(native_source=exact[0][0], extracted_text_range=list(exact[0][1:]))
            if state == "PAGE_EXACT_UNIQUE"
            else None
        ),
        verified_cell_binding=False,
    )


def assess_document(
    doc: dict,
    result: models.ExtractionResult | None,
    failure: str | None,
    grid_item_ids: dict[str, str],
) -> dict:
    if result is not None and (
        result.source_sha256 != doc["source_sha256"]
        or result.source_size_bytes != doc["source_size_bytes"]
        or result.document_format != models.DocumentFormat.PDF
    ):
        raise ValueError("Native capture source binding rejected")
    blocks = [b for b in result.blocks if isinstance(b, models.TextBlock)] if result else []
    tables = [b for b in result.blocks if isinstance(b, models.TableBlock)] if result else []
    native_cells = sum(len(row.cells) for t in tables for row in t.rows)
    expected_page = doc["pages"][0]["page_number"]
    page_blocks = [b for b in blocks if b.source.page_number == expected_page]
    topology = "MISSING_NATIVE_TOPOLOGY" if not tables else "NATIVE_TOPOLOGY_UNMAPPED"
    unavailable = (
        failure is not None or result is None or result.status == models.ExtractionStatus.FAILED
    )
    if unavailable:
        page_blocks = []
        topology = "CAPTURE_UNAVAILABLE"
    findings = []
    for kind, values, field in (
        ("cell", doc["cells"], "literal_text"),
        ("text_anchor", doc["text_anchors"], "literal_text"),
        ("printed_symbol", doc["printed_symbols"], "printed_symbol"),
    ):
        repeated = Counter(v[field] for v in values)
        for item in values:
            observation = literal_observation(
                item[field], page_blocks, repeated[item[field]], symbol=kind == "printed_symbol"
            )
            findings.append(
                dict(
                    source_id=doc["document_id"],
                    item_id=item["item_id"],
                    kind=kind,
                    **observation,
                    page_locator_available=bool(page_blocks),
                    source_glyph_locator_support="UNAVAILABLE",
                    bbox_locator_support="UNAVAILABLE",
                    topology_support=topology if kind != "text_anchor" else "NOT_APPLICABLE",
                    limitations=["locator_limitation"]
                    + (["missing_topology"] if kind != "text_anchor" and not tables else []),
                )
            )
    for grid in doc["logical_grids"]:
        findings.append(
            dict(
                source_id=doc["document_id"],
                item_id=grid_item_ids[grid["table_id"]],
                table_id=grid["table_id"],
                kind="logical_grid",
                topology_support=topology,
                verified_cell_binding=False,
                page_locator_available=bool(page_blocks),
                bbox_locator_support="UNAVAILABLE",
                limitations=["missing_topology", "locator_limitation"]
                if not tables
                else ["locator_limitation"],
            )
        )
    identities = [(f["kind"], f["item_id"]) for f in findings]
    if len(set(identities)) != len(identities):
        raise ValueError("Duplicate reference field identity")
    summary = summarize(findings)
    return dict(
        source_id=doc["document_id"],
        source_sha256=doc["source_sha256"],
        status=result.status.value if result else "failed",
        failure=failure,
        error_category=result.error_category.value if result and result.error_category else None,
        warnings=[asdict(w) for w in result.warnings] if result else [],
        extraction_fingerprint=fingerprint(result.to_dict()) if result else None,
        native_text_blocks=len(blocks),
        native_tables=len(tables),
        native_cells=native_cells,
        native_locators=[asdict(b.source) for b in blocks],
        native_bbox_support=False,
        verified_cell_fidelity="NOT_EVALUATED",
        summary=summary,
        findings=findings,
    )


def summarize(findings: list[dict]) -> dict:
    return {
        kind: dict(
            total=len(rows),
            literal_states=dict(
                sorted(Counter(r["literal_state"] for r in rows if "literal_state" in r).items())
            ),
            literal_causes=dict(
                sorted(Counter(r["literal_cause"] for r in rows if r.get("literal_cause")).items())
            ),
            page_locator_available=sum(r["page_locator_available"] for r in rows),
            verified_cell_bindings=0,
            topology_support=dict(sorted(Counter(r["topology_support"] for r in rows).items())),
        )
        for kind in ("cell", "text_anchor", "printed_symbol", "logical_grid")
        if (rows := [r for r in findings if r["kind"] == kind])
    }


def run(snapshot: Path, config: Path, output: Path) -> dict:
    args = validation_args(config)
    fresh_output(output, args.corpus, root=ROOT)
    if not output.resolve().is_relative_to(ROOT / "evaluation-output"):
        raise ValueError("Private diagnostic output required")
    validation = reference.validate_snapshot(snapshot, args)
    if validation["snapshot_fingerprint"] != REFERENCE_FINGERPRINT:
        raise ValueError("Frozen dev reference fingerprint rejected")
    frozen = corpus.read_json(snapshot / "reference.json")
    inventory = corpus.read_json(snapshot / "proposal-inventory.json")
    grid_item_ids = {
        i["original_proposal"]["table_id"]: i["item_id"]
        for i in inventory
        if i["original_proposal"]["kind"] == "table"
    }
    parser_limits = parsers.ExtractionLimits()
    limits = bounded.Limits(
        max_pages=parser_limits.max_pdf_pages,
        max_process_bytes=1024**3,
        timeout_seconds=60,
        max_scratch_bytes=16 * 1024**2,
    )
    pins = dict(
        method=VERSION,
        reference_fingerprint=REFERENCE_FINGERPRINT,
        git_head=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        code={
            p.relative_to(ROOT).as_posix(): corpus.sha256(p)
            for p in (
                Path(__file__),
                Path(parsers.__file__),
                Path(models.__file__),
                Path(reference.__file__),
                Path(bounded.__file__),
                ROOT / "tools/extraction_quality/extraction_v2.py",
            )
        },
        parser_limits=asdict(parser_limits),
        worker_budgets=asdict(limits),
        python=platform.python_version(),
        platform=platform.platform(),
        machine=platform.machine(),
        processor=platform.processor(),
        cpu_count=os.cpu_count(),
        packages={n: importlib.metadata.version(n) for n in ("pypdf", "pydantic", "psutil")},
        concurrency=1,
        seeds="NOT_APPLICABLE",
        gpu="NOT_USED",
        models="NONE",
        hypothesis="Native page text may retain literals without cell topology or bbox provenance",
        quality_thresholds="NOT_EVALUATED_NO_PROMOTION",
        cache="OS cache not reset",
        runtime_scope=(
            "fresh spawned worker startup plus native extraction; "
            "20ms sampled process-tree RSS bytes; not OS sandbox"
        ),
        unresolved_dimensions=frozen["unresolved_dimensions"],
    )
    output.mkdir(parents=True)
    write_json(output / "pins.json", pins)  # Freeze protocol before the first extraction.
    documents, runtime = [], []
    for doc in frozen["documents"]:
        source = snapshot / "sources" / (doc["document_id"] + ".pdf")
        if corpus.sha256(source) != doc["source_sha256"]:
            raise ValueError("Source drift before extraction")
        capture = bounded.isolated(
            source,
            bounded.Runtime("", "", ""),
            limits,
            output / doc["document_id"],
            candidate=False,
        )
        raw = capture.get("result")
        result = TypeAdapter(models.ExtractionResult).validate_python(raw) if raw else None
        documents.append(assess_document(doc, result, capture["failure"], grid_item_ids))
        runtime.append(dict(source_id=doc["document_id"], **capture["runtime"]))
    if reference.validate_snapshot(snapshot, args) != validation:
        raise ValueError("Reference changed during extraction")
    if any(corpus.sha256(ROOT / name) != digest for name, digest in pins["code"].items()):
        raise ValueError("Diagnostic/parser code changed during extraction")
    all_findings = [f for d in documents for f in d["findings"]]
    expected = dict(cell=536, text_anchor=62, printed_symbol=115, logical_grid=6)
    expected_ids = {i["item_id"] for i in inventory if i["field_admission"] == "PARTIAL_DEV_FIELDS"}
    if (
        Counter(f["kind"] for f in all_findings) != expected
        or len(documents) != 2
        or {f["item_id"] for f in all_findings} != expected_ids
    ):
        raise ValueError("Diagnostic population mismatch")
    report = dict(
        method=VERSION,
        engineering_execution="PASS",
        extraction_quality_gate="NOT_EVALUATED",
        independent_gold=False,
        reference_validation=validation,
        pin_fingerprint=fingerprint(pins),
        documents=documents,
        aggregate=summarize(all_findings),
        original_proposal_ids=1154,
        admitted_field_items=719,
        unresolved_only_proposals=435,
        unresolved_dimensions=frozen["unresolved_dimensions"],
    )
    report["evidence_fingerprint"] = fingerprint(report)
    write_json(output / "diagnostic.json", report)
    write_json(output / "runtime.json", dict(documents=runtime, scope=pins["runtime_scope"]))
    manifest = {
        p.relative_to(output).as_posix(): corpus.sha256(p)
        for p in sorted(output.rglob("*"))
        if p.is_file()
    }
    write_json(
        output / "COMPLETE.json",
        dict(files=manifest, evidence_fingerprint=report["evidence_fingerprint"]),
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("snapshot", "validation-config", "output"):
        parser.add_argument("--" + key, type=Path, required=True)
    args = parser.parse_args()
    try:
        value = run(args.snapshot, args.validation_config, args.output)
        print(
            json.dumps(
                {
                    k: value[k]
                    for k in (
                        "engineering_execution",
                        "extraction_quality_gate",
                        "evidence_fingerprint",
                        "aggregate",
                    )
                },
                sort_keys=True,
            )
        )
        return 0
    except Exception:
        print("BLOCKED: reference, source, capture, population or private output rejected")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
