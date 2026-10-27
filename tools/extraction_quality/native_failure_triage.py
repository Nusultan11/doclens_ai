"""Diagnose EX-01's eight saved failures; never fix or relax native extraction.

python -m tools.extraction_quality.native_failure_triage run --output <fresh-private-dir>
Only unresolved saved failures may be replayed, with native defaults and bounded tracing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import traceback
import zipfile
from collections import Counter
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

from doclens_ai.eda import corpus_v2 as corpus
from doclens_ai.extraction import parsers
from doclens_ai.extraction.fidelity_gold import fingerprint
from doclens_ai.extraction.limits import ExtractionLimits
from tools.extraction_quality import native_dev_baseline as baseline
from tools.extraction_quality.readiness_io import ROOT, atomic
from tools.pdf_ocr_candidate import benchmark as bounded

VERSION = "native-failure-triage-1"
MODULE = "tools.extraction_quality.native_failure_triage"
BASELINE = ROOT / "evaluation-output/extraction-native-dev-baseline-20261027/run-1"
EXPECTED = {
    ("xlsx", "unsupported_format"): 5,
    ("xlsx", "limit_exceeded"): 2,
    ("docx", "extraction_failed"): 1,
}
TRACE_INTS = (
    "character_count",
    "stored_cell_count",
    "merged_range_count",
    "table_count",
    "total_characters",
    "grid_position_count",
    "sheet_index",
    "row_index",
)


def reconcile(left: dict, right: dict, registered: list[dict]) -> list[dict]:
    """Retain exactly the paired failed population, rejecting hidden denominator changes."""
    allowed = {r["id"]: r for r in registered}
    if len(allowed) != len(registered):
        raise ValueError("duplicate registration")
    failures = []
    for run in (left, right):
        rows = {r["id"]: r for r in run["rows"]}
        if len(rows) != len(run["rows"]):
            raise ValueError("duplicate pass identity")
        if set(rows) != {k for k, r in allowed.items() if r["eligible"]}:
            raise ValueError("missing, excluded or foreign pass identity")
        failed = {}
        for key, row in rows.items():
            if row["status"] != "failed":
                continue
            admission = allowed[key]
            if not admission["eligible"] or admission["split"] != "dev":
                raise ValueError("non-DEV or excluded failure")
            if any(row[k] != admission[k] for k in ("sha256", "format", "size_bytes")):
                raise ValueError("failed source drift")
            if (
                row["runtime"]["status"] != "completed"
                or not row["attempted"]
                or row["capture"] is None
                or row["capture"]["status"] != "failed"
                or row["capture"]["error_category"] != row["failure"]
            ):
                raise ValueError("operational failure or missing native failed capture")
            failed[key] = row
        failures.append(failed)
    if (
        set(failures[0]) != set(failures[1])
        or Counter((r["format"], r["failure"]) for r in failures[0].values()) != EXPECTED
    ):
        raise ValueError("eight-failure denominator/category mismatch")
    for key, row in failures[0].items():
        if {k: v for k, v in row.items() if k != "runtime"} != {
            k: v for k, v in failures[1][key].items() if k != "runtime"
        }:
            raise ValueError("failed captures differ between passes")
    return [failures[0][key] for key in sorted(failures[0])]


def package_evidence(path: Path, fmt: str) -> dict:
    """Read original ZIP/XML metadata without storing body text in the public summary."""
    limits = ExtractionLimits()
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        archive_limits = {
            "entries": len(entries),
            "total_uncompressed_bytes": sum(e.file_size for e in entries),
            "max_entry_bytes": max((e.file_size for e in entries), default=0),
            "max_compression_ratio": max(
                (e.file_size / e.compress_size for e in entries if e.compress_size), default=0
            ),
            "nonempty_zero_compressed_entries": sum(
                e.file_size > 0 and e.compress_size == 0 for e in entries
            ),
        }
        # Reuse the actual archive validator; its exceptions are evidence, not a reason to relax it.
        parsers._validate_office_archive(path, parsers.DocumentFormat(fmt), limits)
        result = {"archive": archive_limits, "archive_validation": "PASS"}
        if fmt == "xlsx":
            workbook = parsers._parse_xml(archive.read("xl/workbook.xml"))
            relationships = parsers._read_relationships(archive, "xl/_rels/workbook.xml.rels")
            sheets = []
            for index, sheet in enumerate(
                workbook.findall(f".//{{{parsers._SPREADSHEET_NS}}}sheet")
            ):
                rid = sheet.get(f"{{{parsers._OFFICE_REL_NS}}}id")
                target, kind = relationships[rid]
                part = parsers._resolve_relationship_target("xl/workbook.xml", target)
                sheet_root = parsers._parse_xml(archive.read(part))
                sheets.append(
                    {
                        "index": index,
                        "relationship_id": rid,
                        "part": part,
                        "relationship_type": kind,
                        "root_tag": sheet_root.tag,
                    }
                )
            result["sheets"] = sheets
        elif fmt == "docx":
            document = parsers._parse_xml(archive.read("word/document.xml"))
            ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
            sections = document.findall(f".//{ns}sectPr")
            result["docx_structure"] = {
                "sections": len(sections),
                "header_references": len(document.findall(f".//{ns}headerReference")),
                "footer_references": len(document.findall(f".//{ns}footerReference")),
                "body_tables": len(document.findall(f"./{ns}body/{ns}tbl")),
                "xml_part_sha256": hashlib.sha256(archive.read("word/document.xml")).hexdigest(),
                "non_element_body_nodes": [
                    {
                        "child_ordinal": i,
                        "node_type": type(node).__name__,
                        "tag_type": type(node.tag).__name__,
                        "supports_rsplit": hasattr(node.tag, "rsplit"),
                    }
                    for i, node in enumerate(parsers.Document(path).element.body)
                    if not isinstance(node.tag, str)
                ],
            }
        else:
            raise ValueError("only failed Office originals admitted")
    return result


def trace_extraction(source: Path, metadata: dict) -> dict:
    """Observe exceptions from the unchanged native entry point; never alter its result."""
    asset = corpus.Asset(
        path=source.relative_to(ROOT).as_posix(),
        sha256=metadata["sha256"],
        size_bytes=metadata["size_bytes"],
        format=metadata["format"],
    )
    corpus.asset_path(ROOT, asset)
    events: list[dict] = []
    parser_file = str(Path(parsers.__file__).resolve())

    def observe(frame: Any, event: str, arg: Any):
        if frame.f_code.co_filename != parser_file:
            return None
        frame.f_trace_lines = False
        if event == "exception" and len(events) < 64:
            kind, error, tb = arg
            events.append(
                {
                    "function": frame.f_code.co_name,
                    "line": frame.f_lineno,
                    "exception_type": kind.__name__,
                    "message": str(error)[:2000],
                    "numeric_locals": {
                        k: frame.f_locals[k]
                        for k in TRACE_INTS
                        if type(frame.f_locals.get(k)) is int
                    },
                    "source_locals": {
                        k: frame.f_locals[k]
                        for k in ("sheet_path", "relationship_type", "coordinate")
                        if isinstance(frame.f_locals.get(k), str)
                    },
                    "traceback": [
                        {"file": f.filename, "line": f.lineno, "function": f.name}
                        for f in traceback.extract_tb(tb, limit=32)
                    ],
                }
            )
        return observe

    previous = sys.gettrace()
    try:
        sys.settrace(observe)
        capture = parsers.extract_file(source).to_dict()
    finally:
        sys.settrace(previous)
    corpus.asset_path(ROOT, asset)
    return {
        "capture": capture,
        "capture_fingerprint": fingerprint(capture),
        "exception_events": events,
        "native_defaults": asdict(ExtractionLimits()),
    }


def diagnosis(row: dict, package: dict, replay: dict | None) -> dict:
    result = {
        "classification": "UNRESOLVED",
        "mechanism": "unresolved_native_failure",
        "confidence": "UNRESOLVED",
        "recommended_minimal_fix": "Establish the exact triggering path before changing behavior.",
    }
    if row["failure"] == "unsupported_format":
        unsupported = [
            s
            for s in package.get("sheets", [])
            if s["relationship_type"]
            in {f"{parsers._OFFICE_REL_NS}/chartsheet", f"{parsers._OFFICE_REL_NS}/dialogsheet"}
            and s["root_tag"]
            == f"{{{parsers._SPREADSHEET_NS}}}" + s["relationship_type"].rsplit("/", 1)[-1]
        ]
        if unsupported:
            kind = unsupported[0]["relationship_type"].rsplit("/", 1)[-1]
            result.update(
                classification="CONFIRMED",
                mechanism=f"whole_workbook_rejects_{kind}",
                confidence="direct_package_and_unique_native_branch",
                evidence={"unsupported_sheets": unsupported, "parser_function": "_extract_xlsx"},
                recommended_minimal_fix="Consider retaining supported worksheets with an "
                "explicit review warning for unsupported sheet kinds; preserve provenance "
                "and validate output/status policy before implementation.",
            )
    if replay is not None:
        if replay["capture_fingerprint"] != row["capture"]["content_sha256"]:
            raise ValueError("diagnostic replay does not reproduce frozen failed capture")
        events = replay["exception_events"]
        if row["failure"] == "limit_exceeded":
            hits = [
                e
                for e in events
                if e["function"] == "_extract_xlsx"
                and e["exception_type"] == "_ExtractionFailure"
                and e["numeric_locals"].get("character_count", 0)
                > ExtractionLimits().max_extracted_characters
            ]
            if hits:
                result.update(
                    classification="CONFIRMED",
                    mechanism="xlsx_character_budget",
                    confidence="exact_default_limit_exception_and_matching_capture",
                    evidence=hits[0],
                    recommended_minimal_fix="Preserve the safety guard. "
                    "First separate payload/formula and repeated-format character costs; "
                    "do not raise limits without controlled resource/quality evidence.",
                )
        elif row["failure"] == "extraction_failed" and events:
            hits = [
                e
                for e in events
                if e["exception_type"] != "_ExtractionFailure"
                and e["function"].startswith("_docx")
                or e["exception_type"] != "_ExtractionFailure"
                and e["function"] == "_extract_docx"
            ]
            if hits:
                first = hits[0]
                result.update(
                    classification="CONFIRMED",
                    mechanism=f"docx_{first['exception_type']}_{first['function']}",
                    confidence="direct_native_exception_and_matching_failed_capture",
                    evidence=first,
                    recommended_minimal_fix="Address the source construct "
                    "at the recorded failing call; preserve guards and add its precise "
                    "regression before changing error handling. The exception is confirmed; "
                    "deeper source-causal interpretation requires package evidence.",
                )
                comments = package.get("docx_structure", {}).get("non_element_body_nodes", [])
                if (
                    first["exception_type"] == "AttributeError"
                    and first["function"] == "_extract_docx"
                    and "has no attribute 'rsplit'" in first.get("message", "")
                    and any(
                        n["child_ordinal"] == 0
                        and n["node_type"] == "_Comment"
                        and n["supports_rsplit"] is False
                        for n in comments
                    )
                ):
                    result.update(
                        mechanism="docx_xml_comment_body_traversal",
                        confidence="original_comment_node_and_exact_native_exception",
                        evidence={"exception": first, "body_nodes": comments},
                        recommended_minimal_fix="Skip XML comment/non-element nodes before "
                        "body element tag operations; preserve real unknown-element warnings "
                        "and physical XML ordinals. Add a comment-before-paragraph regression.",
                    )
    return result


def verify_artifacts(output: Path) -> dict:
    corpus.no_links(output)
    if not output.resolve().is_relative_to(ROOT / "evaluation-output"):
        raise ValueError("private diagnostic evidence required")
    complete = corpus.read_json(output / "COMPLETE.json")
    if complete["fingerprint"] != fingerprint(
        {k: v for k, v in complete.items() if k != "fingerprint"}
    ) or complete["artifact_sha256"] != baseline.artifact_hashes(output):
        raise ValueError("diagnostic evidence drift")
    return complete


def refine(source: Path, output: Path) -> dict:
    """Refine source-causal evidence from sealed traces; zero extraction replays."""
    baseline.fresh_private(output)
    previous = verify_artifacts(source)
    rows = corpus.read_json(source / "ledger.json")["rows"]
    if (
        len(rows) != 8
        or len({r["id"] for r in rows}) != 8
        or Counter((r["format"], r["observed_failure"]) for r in rows) != EXPECTED
    ):
        raise ValueError("refinement denominator drift")
    native_complete = corpus.read_json(BASELINE / "COMPLETE.json")
    if baseline.artifact_hashes(BASELINE) != native_complete["artifacts"]:
        raise ValueError("previous native baseline artifacts changed")
    for row in rows:
        path = corpus.asset_path(ROOT, corpus.Asset.model_validate(row["source"]["asset"]))
        package = package_evidence(path, row["format"])
        replay_file = source / row["id"] / "result.json"
        replay = corpus.read_json(replay_file) if replay_file.exists() else None
        row["package"] = package
        row["diagnosis"] = diagnosis(
            {"failure": row["observed_failure"], "capture": row["paired_capture"]}, package, replay
        )
        row["baseline_evidence"] = []
        for n in (1, 2):
            directory = BASELINE / f"pass-{n}" / row["id"]
            row["baseline_evidence"].append(
                {
                    "pass": n,
                    "native_capture": str(directory / "native.json"),
                    "native_capture_sha256": corpus.sha256(directory / "native.json"),
                    "console_bytes": (directory / "console-private.txt").stat().st_size,
                    "console_sha256": corpus.sha256(directory / "console-private.txt"),
                    "worker_error_json_exists": (directory / "error.json").exists(),
                }
            )
    result = {
        "version": VERSION,
        "accounted": len(rows),
        "extraction_replays": 0,
        "origin": {
            "path": str(source),
            "fingerprint": previous["fingerprint"],
            "tool_sha256": previous["tool_sha256"],
        },
        "classifications": dict(Counter(r["diagnosis"]["classification"] for r in rows)),
        "mechanisms": dict(Counter(r["diagnosis"]["mechanism"] for r in rows)),
        "next_fix": "docx_xml_comment_body_traversal"
        if any(r["diagnosis"]["mechanism"] == "docx_xml_comment_body_traversal" for r in rows)
        else None,
        "tool_sha256": corpus.sha256(Path(__file__)),
        "native_baseline_artifacts_unchanged": True,
        "quality": "NOT_EVALUATED",
    }
    output.mkdir(parents=True)
    atomic(output / "ledger.json", {"version": VERSION, "rows": rows})
    result["artifact_sha256"] = baseline.artifact_hashes(output)
    result["fingerprint"] = fingerprint(result)
    atomic(output / "COMPLETE.json", result)
    verify_artifacts(output)
    return result


def run(output: Path) -> dict:
    baseline.fresh_private(output)
    code_sha256 = corpus.sha256(Path(__file__))
    verified = baseline.verify(BASELINE)
    if verified["execution"] != "PASS":
        raise ValueError("saved baseline verification failed")
    registered, cohort = baseline.verified_cohort(baseline.RELEASE)
    protocol = corpus.read_json(BASELINE / "protocol.json")
    if registered != protocol["registered"]:
        raise ValueError("baseline eligibility drift")
    config = protocol["configuration"]
    for path in (
        "src/doclens_ai/extraction/parsers.py",
        "src/doclens_ai/extraction/models.py",
        "src/doclens_ai/extraction/limits.py",
    ):
        if corpus.sha256(ROOT / path) != config["code_sha256"][path]:
            raise ValueError("native implementation drift")
    passes = [
        corpus.read_json(BASELINE / f"pass-{n}/manifest.json", max_bytes=256 * 1024**2)
        for n in (1, 2)
    ]
    failed = reconcile(*passes, registered)
    indexed = {r["metadata"]["id"]: r for r in cohort}
    output.mkdir(parents=True)
    rows = []
    for row in failed:
        source = indexed[row["id"]]
        path = corpus.asset_path(ROOT, corpus.Asset.model_validate(source["asset"]))
        package = package_evidence(path, row["format"])
        replay = None
        runtime = None
        if row["failure"] != "unsupported_format":
            directory = output / row["id"]
            directory.mkdir()
            atomic(
                directory / "request.json", {"source": str(path), "metadata": source["metadata"]}
            )
            limits = replace(
                bounded.Limits(),
                max_process_bytes=2 * 1024**3,
                max_scratch_bytes=32 * 1024**2,
                tool_timeout_seconds=90,
                poll_seconds=0.02,
            )
            try:
                runtime = bounded.command(
                    [sys.executable, "-B", "-m", MODULE, "worker", "--output", str(directory)],
                    directory,
                    limits,
                )
                replay = corpus.read_json(directory / "result.json")
            except bounded.BoundedFailure as error:
                runtime = {"failure": error.category}
        entry = {
            "id": row["id"],
            "format": row["format"],
            "observed_failure": row["failure"],
            "source": source,
            "paired_capture": row["capture"],
            "package": package,
            "diagnosis": diagnosis(row, package, replay),
            "replay_runtime": runtime,
        }
        if replay:
            entry["replay_fingerprint"] = replay["capture_fingerprint"]
        rows.append(entry)
        atomic(output / "ledger.json", {"version": VERSION, "rows": rows})
        print(
            json.dumps(
                {
                    "id": row["id"],
                    "classification": entry["diagnosis"]["classification"],
                    "mechanism": entry["diagnosis"]["mechanism"],
                }
            ),
            flush=True,
        )
    if baseline.verified_cohort(baseline.RELEASE) != (registered, cohort):
        raise ValueError("source/eligibility drift after diagnostics")
    if corpus.sha256(Path(__file__)) != code_sha256:
        raise ValueError("diagnostic implementation changed during execution")
    result = {
        "version": VERSION,
        "accounted": len(rows),
        "saved_baseline": verified,
        "mechanisms": dict(Counter(r["diagnosis"]["mechanism"] for r in rows)),
        "classifications": dict(Counter(r["diagnosis"]["classification"] for r in rows)),
        "quality": "NOT_EVALUATED",
        "parser_modified": False,
        "tool_sha256": code_sha256,
    }
    artifacts = {
        p.relative_to(output).as_posix(): corpus.sha256(p) for p in output.rglob("*") if p.is_file()
    }
    result["artifact_sha256"] = artifacts
    result["fingerprint"] = fingerprint(result)
    atomic(output / "COMPLETE.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("run", "worker", "refine"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--input", type=Path)
    args = parser.parse_args()
    output = args.output.absolute()
    if args.command == "worker":
        corpus.no_links(output)
        if not output.resolve().is_relative_to(ROOT / "evaluation-output"):
            raise ValueError("private diagnostic output required")
        request = corpus.read_json(output / "request.json")
        result = trace_extraction(Path(request["source"]), request["metadata"])
        atomic(output / "result.json", result)
        return 0
    if args.command == "refine":
        if args.input is None:
            parser.error("refine requires --input")
        result = refine(args.input.absolute(), output)
    else:
        result = run(output)
    print(json.dumps({k: v for k, v in result.items() if k != "artifact_sha256"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
