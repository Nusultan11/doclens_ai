"""Frozen, isolated offline DOCX ancillary comparison. Private captures stay ignored."""

from __future__ import annotations

import argparse
import contextlib
import csv
import hashlib
import importlib.metadata
import io
import json
import logging
import os
import platform
import posixpath
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path
from urllib.parse import unquote
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from doclens_ai.extraction.docx_footnote_candidate import FootnoteLimits, W, extract_footnotes
from doclens_ai.extraction.fidelity_eval import (
    _observations,
    _read_sources,
    normalize,
    score_record,
    verify_corpus,
)
from doclens_ai.extraction.fidelity_gold import fingerprint, load_gold
from doclens_ai.extraction.models import (
    DocumentFormat,
    ErrorCategory,
    ExtractionResult,
    ExtractionStatus,
    ExtractionWarning,
    NoteReference,
    SourceLocation,
    TableBlock,
    TableCell,
    TableRow,
    TextBlock,
    WarningCode,
    WarningSeverity,
)
from doclens_ai.extraction.parsers import ExtractionLimits, extract_file

GUARDS = {
    "timeout_seconds": 20.0,
    "max_process_bytes": 512 * 1024**2,
    "max_capture_bytes": 64 * 1024**2,
    "sample_seconds": 0.02,
}
PRODUCTION = ("parsers.py", "models.py", "fidelity_gold.py", "fidelity_eval.py")


def restore_docx(raw: dict) -> ExtractionResult:
    """Restore the frozen DOCX union, including genuine structured table blocks."""
    if raw["document_format"] != "docx" or raw["sheets"]:
        raise ValueError("DOCX capture contract rejected")
    blocks = []
    for block in raw["blocks"]:
        source = _restore_location(block["source"])
        if block["kind"] == "text":
            blocks.append(TextBlock(block["order"], block["text"], source))
        elif block["kind"] == "table":
            rows = tuple(
                TableRow(
                    row["row_index"],
                    tuple(
                        TableCell(
                            cell["row_index"],
                            cell["column_index"],
                            cell["text"],
                            _restore_location(cell["source"]),
                            cell["row_span"],
                            cell["column_span"],
                        )
                        for cell in row["cells"]
                    ),
                )
                for row in block["rows"]
            )
            blocks.append(
                TableBlock(
                    block["order"],
                    block["table_index"],
                    rows,
                    source,
                    block["name"],
                    block["reference"],
                    tuple(block.get("header_row_indices", ())),
                )
            )
        else:
            raise ValueError("Unknown DOCX block")
    warnings = tuple(
        ExtractionWarning(
            WarningCode(w["code"]),
            WarningSeverity(w["severity"]),
            w["count"],
            _restore_location(w["source"]) if w["source"] is not None else None,
        )
        for w in raw["warnings"]
    )
    result = ExtractionResult(
        raw["schema_version"],
        DocumentFormat.DOCX,
        ExtractionStatus(raw["status"]),
        raw["source_sha256"],
        raw["source_size_bytes"],
        tuple(blocks),
        (),
        warnings,
        ErrorCategory(raw["error_category"]) if raw["error_category"] else None,
        tuple(
            NoteReference(_restore_location(ref["source"]), ref["target_part_uri"], ref["note_id"])
            for ref in raw.get("note_references", ())
        ),
    )
    restored = result.to_dict()
    if raw["schema_version"] == "1.0":
        # Old captures have no new optional fields. Compare the exact old shape;
        # reject unknown fields rather than silently dropping them.
        def old_shape(value, shape):
            if isinstance(shape, dict):
                return {key: old_shape(value[key], child) for key, child in shape.items()}
            if isinstance(shape, list):
                return [old_shape(v, s) for v, s in zip(value, shape, strict=True)]
            return value

        restored = old_shape(restored, raw)
    if restored != raw:
        raise ValueError("Lossy DOCX capture restoration rejected")
    return result


def _restore_location(raw: dict) -> SourceLocation:
    values = dict(raw)
    if values.get("xml_path") is not None:
        values["xml_path"] = tuple(values["xml_path"])
    return SourceLocation(**values)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024**2), b""):
            h.update(chunk)
    return h.hexdigest()


def save(path: Path, value: dict) -> None:
    """Bound output before publication; never leave a successful partial capture."""
    temporary = path.with_suffix(".partial")
    count = 0
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as stream:
            for chunk in json.JSONEncoder(sort_keys=True, indent=2).iterencode(value):
                count += len(chunk.encode("utf-8"))
                if count > GUARDS["max_capture_bytes"] - 1:
                    raise ValueError("Capture limit")
                stream.write(chunk)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def worker(source: Path, output: Path) -> int:
    previous = logging.root.manager.disable
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            logging.disable(logging.CRITICAL)
            baseline = extract_file(source)
            ancillary = extract_footnotes(source)
            again = extract_file(source)
        effective = (
            "failed"
            if "failed" in (baseline.status.value, ancillary.status.value)
            else "needs_review"
            if "needs_review" in (baseline.status.value, ancillary.status.value)
            else "success"
        )
        save(
            output / "result.json",
            {
                "baseline": baseline.to_dict(),
                "ancillary": ancillary.to_dict(),
                "baseline_after_fingerprint": fingerprint(again.to_dict()),
                "effective_status": effective,
            },
        )
        return 0
    except Exception:
        return 2  # No exception details, source paths or private library diagnostics.
    finally:
        logging.disable(previous)


def monitor(command: list[str], output: Path, *, guards: dict | None = None) -> dict:
    """Sample one isolated process tree; memory guard precedes timeout."""
    import psutil

    limits = guards or GUARDS
    start = time.monotonic()
    peak, samples, failure = 0, 0, None
    tracked = {}
    with (output / "resources.jsonl").open("x", encoding="utf-8") as journal:
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            while process.poll() is None:
                elapsed = time.monotonic() - start
                try:
                    parent = psutil.Process(process.pid)
                    tree = [parent] + parent.children(recursive=True)
                    tracked.update({p.pid: p for p in tree})
                    rss = sum(p.memory_info().rss for p in tree if p.is_running())
                except psutil.NoSuchProcess:
                    rss = 0
                except psutil.AccessDenied:
                    rss = 0
                    failure = "resource_monitor_failed"
                peak = max(peak, rss)
                samples += 1
                journal.write(json.dumps({"elapsed": elapsed, "tree_rss": rss}) + "\n")
                if failure:
                    break
                if rss > limits["max_process_bytes"]:
                    failure = "memory_limit"
                elif elapsed >= limits["timeout_seconds"]:
                    failure = "timeout"
                elif (
                    sum(p.stat().st_size for p in output.iterdir() if p.is_file())
                    > limits["max_capture_bytes"]
                ):
                    failure = "output_limit"
                if failure:
                    break
                time.sleep(limits["sample_seconds"])
        finally:
            # This worker spawns no tools; clean tracked descendants defensively.
            for p in reversed(list(tracked.values())):
                try:
                    if p.is_running():
                        p.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)
            for p in tracked.values():
                try:
                    if p.is_running():
                        p.kill()
                        p.wait(timeout=2)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
    if not failure and process.returncode:
        failure = "worker_failed"
    if failure:
        (output / "result.json").unlink(missing_ok=True)
    (output / "result.partial").unlink(missing_ok=True)
    cleanup = process.poll() is not None and all(not p.is_running() for p in tracked.values())
    return {
        "seconds": time.monotonic() - start,
        "peak_tree_rss_bytes": peak,
        "samples": samples,
        "failure": failure,
        "cleanup": cleanup,
    }


def verify_ancillary(source: Path, captured: dict) -> dict:
    """Independently resolve emitted XML addresses on the immutable package.

    No Gold text or Gold part_index participates in these address checks.
    """
    a = captured["ancillary"]
    if a["status"] == "failed":
        return {"status": "NOT_EVALUATED", "notes": 0, "references": 0, "paragraphs": 0}
    assert sha(source) == a["source_sha256"]
    if a["footnote_part_uri"] is None:
        assert not a["notes"] and not a["references"]
        return {"status": "EVALUATED", "notes": 0, "references": 0, "paragraphs": 0}
    with ZipFile(source) as z:
        package = ET.fromstring(z.read("_rels/.rels"))
        office = [r for r in package if r.get("Type", "").endswith("/officeDocument")]
        assert len(office) == 1 and office[0].get("TargetMode", "Internal") == "Internal"
        main_name = posixpath.normpath(unquote(office[0].get("Target")).lstrip("/"))
        assert "/" + main_name == a["main_part_uri"]
        rel_name = posixpath.join(
            posixpath.dirname(main_name), "_rels", posixpath.basename(main_name) + ".rels"
        )
        relations = ET.fromstring(z.read(rel_name))
        relation = [r for r in relations if r.get("Id") == a["footnote_relationship_id"]]
        assert len(relation) == 1 and relation[0].get("Type", "").endswith("/footnotes")
        assert relation[0].get("TargetMode", "Internal") == "Internal"
        target = unquote(relation[0].get("Target"))
        note_name = posixpath.normpath(
            target.lstrip("/")
            if target.startswith("/")
            else posixpath.join(posixpath.dirname(main_name), target)
        )
        assert "/" + note_name == a["footnote_part_uri"]
        main = ET.fromstring(z.read(a["main_part_uri"].lstrip("/")))
        body = main.find(W + "body")
        part = ET.fromstring(z.read(a["footnote_part_uri"].lstrip("/")))
        assert len(list(body.iter(W + "footnoteReference"))) == len(a["references"])
        for ref in a["references"]:
            node = body
            for index in ref["body_xml_path"]:
                node = node[index]
            assert node.tag == W + "footnoteReference" and node.get(W + "id") == ref["note_id"]
            assert ref["body_child_index"] == ref["body_xml_path"][0]
            if ref["paragraph_xml_path"] is not None:
                node = body
                for index in ref["paragraph_xml_path"]:
                    node = node[index]
                assert node.tag == W + "p"
                prefix = ref["paragraph_xml_path"]
                assert ref["body_xml_path"][: len(prefix)] == prefix
            index = ref["baseline_block_index"]
            expected = sum(
                c.tag in (W + "p", W + "tbl") for c in list(body)[: ref["body_child_index"]]
            )
            assert (
                index == expected
                if body[ref["body_child_index"]].tag in (W + "p", W + "tbl")
                else index is None
            )
        paragraphs = 0
        for note in a["notes"]:
            node = part[note["note_element_index"]]
            assert node.tag == W + "footnote" and node.get(W + "id") == note["note_id"]
            assert note["part_uri"] == a["footnote_part_uri"] and note["gold_part_index"] is None
            expected = [
                r["ordinal"] for r in a["references"] if int(r["note_id"]) == int(note["note_id"])
            ]
            assert tuple(note["reference_ordinals"]) == tuple(expected)
            for p in note["paragraphs"]:
                xml_p = node[p["child_index"]]
                assert xml_p.tag == W + "p"
                if p["complete"]:
                    controls = {
                        W + "tab": "\t",
                        W + "br": "\n",
                        W + "cr": "\n",
                        W + "softHyphen": "\u00ad",
                        W + "noBreakHyphen": "\u2011",
                    }
                    properties = {
                        id(n)
                        for prop in xml_p.iter()
                        if prop.tag in (W + "pPr", W + "rPr")
                        for n in prop.iter()
                    }
                    text = "".join(
                        (n.text or "") if n.tag == W + "t" else controls.get(n.tag, "")
                        for n in xml_p.iter()
                        if id(n) not in properties
                    )
                    assert text == p["text"]
                paragraphs += 1
    return {
        "status": "EVALUATED",
        "notes": len(a["notes"]),
        "references": len(a["references"]),
        "paragraphs": paragraphs,
    }


def summarize(record, captured: dict | None) -> dict:
    labels = {
        "anchors": len(record.anchors),
        "provenance": len(record.anchors) + len(record.cells),
        "order": len(record.order_pairs),
        "table_cells": len(record.table_cells),
        "relations": len(record.table_relationships),
        "value_checks": len(record.cells),
        "footnotes": sum(a.source.region == "footnote" for a in record.anchors),
        "numeric_bearing": sum(any("0" <= c <= "9" for c in a.text) for a in record.anchors),
    }
    provenance = {
        "status": "NOT_EVALUATED",
        "passed": None,
        "evaluated": 0,
        "label_total": labels["footnotes"],
        "reason": "part_index_convention_unspecified",
    }
    if captured is None:
        return {
            "reviewed_denominators": labels,
            "baseline_scores": None,
            "frozen_candidate_scores": None,
            "footnote_text": {
                "passed": None,
                "evaluated": 0,
                "label_total": labels["footnotes"],
            },
            "reviewed_footnote_provenance": provenance,
            "numeric_bearing": {
                "passed": None,
                "evaluated": 0,
                "label_total": labels["numeric_bearing"],
            },
            "supplemented_numeric_bearing": {
                "passed": None,
                "evaluated": 0,
                "label_total": labels["numeric_bearing"],
            },
            "recovered": None,
            "lost": None,
            "status": "failed",
            "regressions": True,
        }
    base = restore_docx(captured["baseline"])
    a = captured["ancillary"]
    before = score_record(record, base)
    present, recovered, numeric, supplemented_numeric = [], [], [], []
    for anchor in record.anchors:
        native = any(normalize(anchor.text) in normalize(o.text) for o in _observations(base))
        hit = False
        if anchor.source.region == "footnote":
            hit = a["status"] != "failed" and any(
                n["complete"]
                and n["reference_ordinals"]
                and any(
                    p["complete"] and normalize(anchor.text) in normalize(p["text"])
                    for p in n["paragraphs"]
                )
                for n in a["notes"]
            )
            present.append(hit)
            if hit and not native:
                recovered.append(anchor.anchor_id)
        if any("0" <= c <= "9" for c in anchor.text):
            numeric.append(native)
            supplemented_numeric.append(native or hit)
    guard = fingerprint(captured["baseline"]) == captured["baseline_after_fingerprint"]
    return {
        "reviewed_denominators": labels,
        "baseline_scores": before,
        "frozen_candidate_scores": before,
        "footnote_text": {
            "passed": sum(present) if a["status"] != "failed" else None,
            "evaluated": len(present) if a["status"] != "failed" else 0,
            "label_total": len(present),
        },
        "reviewed_footnote_provenance": provenance,
        "numeric_bearing": {
            "passed": sum(numeric),
            "evaluated": len(numeric),
            "label_total": len(numeric),
        },
        "supplemented_numeric_bearing": {
            "passed": sum(supplemented_numeric) if a["status"] != "failed" else None,
            "evaluated": len(supplemented_numeric) if a["status"] != "failed" else 0,
            "label_total": len(supplemented_numeric),
        },
        "recovered": recovered,
        "lost": [] if guard else None,
        "native_result_identical": guard,
        "status": captured["effective_status"],
        "baseline_status": base.status.value,
        "ancillary_status": a["status"],
        "issues": a["issues"],
        "complete_notes": sum(n["complete"] for n in a["notes"]),
        "incomplete_notes": sum(not n["complete"] for n in a["notes"]),
        "regressions": not guard
        or a["status"] == "failed"
        or (base.status.value == "needs_review" and captured["effective_status"] == "success"),
    }


def freeze(manifest: Path, corpus: Path, gold: Path, baseline: Path) -> tuple[dict, dict, tuple]:
    sources = _read_sources(manifest)
    paths = verify_corpus(corpus, sources, ExtractionLimits())
    records = tuple(r for r in load_gold(gold, sources) if r.document_format == "docx")
    if not records:
        raise ValueError("Missing reviewed population")
    code = {
        n: sha(Path("src/doclens_ai/extraction") / n)
        for n in PRODUCTION + ("docx_footnote_candidate.py",)
    }
    code["benchmark.py"] = sha(Path(__file__))
    code["synthetic_tests.py"] = sha(Path("tests/unit/test_docx_footnote_candidate.py"))
    with manifest.open(encoding="utf-8", newline="") as stream:
        if any(
            not row.get(k)
            for row in csv.DictReader(stream)
            for k in ("license", "license_url", "license_basis_url")
        ):
            raise ValueError("Missing source license provenance")
    historical = json.loads(baseline.read_text())
    if historical["identity"]["manifest_sha256"] != sha(manifest):
        raise ValueError("Frozen manifest drift")
    for field, name in (
        ("parser_sha256", "parsers.py"),
        ("evaluator_sha256", "fidelity_eval.py"),
        ("gold_contract_sha256", "fidelity_gold.py"),
        ("extraction_models_sha256", "models.py"),
    ):
        if historical["identity"][field] != code[name]:
            raise ValueError("Production drift")
    registration = {
        "version": "ml21-v1",
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "manifest": sha(manifest),
        "gold": sha(gold),
        "baseline": sha(baseline),
        "source_map": fingerprint(sources),
        "cohort": {r.document_id: sources[r.document_id] for r in records},
        "code": code,
        "limits": asdict(FootnoteLimits()),
        "guards": GUARDS,
        "python": platform.python_version(),
        "packages": {
            name: importlib.metadata.version(name)
            for name in ("python-docx", "pypdf", "pydantic", "openpyxl", "psutil")
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "protocol": {
            "primary": "referenced_complete_paragraph_text_1_of_1",
            "zero_native_losses": True,
            "gold_part_index": "UNSPECIFIED",
            "production_authorization": False,
        },
    }
    return registration, paths, records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", type=Path)
    parser.add_argument("--manifest", type=Path, default=Path("docs/eda/corpus_v1_manifest.csv"))
    parser.add_argument("--corpus", type=Path, default=Path("local-corpus"))
    parser.add_argument(
        "--gold",
        type=Path,
        default=Path("local-evaluation/extraction_fidelity_v1_expanded_approved.jsonl"),
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=Path("evaluation-output/fidelity-controls-v1-approved-run1/metrics.json"),
    )
    parser.add_argument("--registration", type=Path)
    parser.add_argument("--preregister", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.worker:
            if (
                not args.output.is_dir()
                or args.output.resolve().is_relative_to(args.corpus.resolve())
                or any(p.is_symlink() for p in (args.output, *args.output.parents))
                or subprocess.run(
                    ["git", "check-ignore", "-q", str(args.output)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                ).returncode
            ):
                raise ValueError("Worker output boundary")
            return worker(args.worker, args.output)
        if (
            args.output.exists()
            or args.output.resolve().is_relative_to(args.corpus.resolve())
            or any(p.is_symlink() for p in args.output.parents)
            or subprocess.run(
                ["git", "check-ignore", "-q", str(args.output)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            ).returncode
        ):
            raise ValueError("Output boundary")
        registration, paths, records = freeze(args.manifest, args.corpus, args.gold, args.baseline)
        args.output.mkdir(parents=True)
        if args.preregister:
            save(args.output / "registration.json", registration)
            print(json.dumps({"status": "PREREGISTERED", "fingerprint": fingerprint(registration)}))
            return 0
        frozen = json.loads(args.registration.read_text())
        if frozen != json.loads(json.dumps(registration)):
            raise ValueError("Frozen protocol drift")
        documents, resources = [], []
        baseline = json.loads(args.baseline.read_text())
        old = {d["document_id"]: d for d in baseline["documents"]}
        for record in records:
            destination = args.output / record.document_id
            destination.mkdir()
            command = [
                sys.executable,
                "-B",
                str(Path(__file__).resolve()),
                "--worker",
                str(paths[record.document_id]),
                "--output",
                str(destination),
            ]
            runtime = monitor(command, destination)
            resources.append({"document_id": record.document_id, **runtime})
            raw = destination / "result.json"
            captured = (
                json.loads(raw.read_text()) if raw.exists() and not runtime["failure"] else None
            )
            summary = summarize(record, captured)
            if captured is not None:
                summary["ooxml_provenance"] = verify_ancillary(paths[record.document_id], captured)
                summary["frozen_baseline_identical"] = (
                    fingerprint(captured["baseline"])
                    == old[record.document_id]["extraction_fingerprint"]
                )
                summary["native_fingerprint"] = fingerprint(captured["baseline"])
                summary["ancillary_fingerprint"] = fingerprint(captured["ancillary"])
            documents.append({"document_id": record.document_id, **summary})
        fresh, _, _ = freeze(args.manifest, args.corpus, args.gold, args.baseline)
        if fresh != registration:
            raise ValueError("Input drift")
        critical = any(r["failure"] or not r["cleanup"] for r in resources) or any(
            d["regressions"] or not d.get("frozen_baseline_identical") for d in documents
        )
        verdict = "REJECT" if critical else "INCONCLUSIVE"
        quality = {
            "registration_fingerprint": fingerprint(registration),
            "documents": documents,
            "population": {
                "documents": len(records),
                "anchors": sum(len(r.anchors) for r in records),
                "provenance": sum(len(r.anchors) + len(r.cells) for r in records),
                "order": sum(len(r.order_pairs) for r in records),
                "table_cells": sum(len(r.table_cells) for r in records),
                "relations": sum(len(r.table_relationships) for r in records),
                "value_checks": sum(len(r.cells) for r in records),
                "footnote_anchors": sum(
                    a.source.region == "footnote" for r in records for a in r.anchors
                ),
            },
            "candidate_verdict": verdict,
            "production_authorization": False,
        }
        metrics = {
            "quality": quality,
            "deterministic_fingerprint": fingerprint(quality),
            "runtime": resources,
        }
        save(args.output / "metrics.json", metrics)
        artifacts = {
            p.relative_to(args.output).as_posix(): sha(p)
            for p in sorted(args.output.rglob("*"))
            if p.is_file()
        }
        save(args.output / "artifact-manifest.json", artifacts)
        passed = all(not r["failure"] and r["cleanup"] for r in resources) and all(
            not d["regressions"] and d.get("frozen_baseline_identical") for d in documents
        )
        print(
            json.dumps(
                {
                    "status": "PASS" if passed else "FIX",
                    "quality": verdict,
                    "fingerprint": metrics["deterministic_fingerprint"],
                }
            )
        )
        return 0 if passed else 1
    except Exception:
        print("BLOCKED: offline DOCX evidence, registration or resource boundary rejected")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
