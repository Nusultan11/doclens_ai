"""Read-only coverage of frozen metadata/labels/captures; never runs extraction.

Scenario rows overlap and cannot be summed. Unknown captures retain label totals.
No document names, text, URLs, family names or annotation values are exported.
"""

from __future__ import annotations

import argparse
import contextlib
import csv
import hashlib
import io
import json
import logging
import re
import subprocess
import time
import warnings
import zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET

from doclens_ai.extraction.fidelity_eval import (
    _observations,
    _read_sources,
    normalize,
    score_record,
    verify_corpus,
)
from doclens_ai.extraction.fidelity_gold import fingerprint, load_gold
from doclens_ai.extraction.models import WarningCode
from doclens_ai.extraction.parsers import ExtractionLimits
from tools.pdf_ocr_candidate.benchmark import restore

VERSION = "coverage-v1"
MAX_JSON = 32 * 1024 * 1024
MAX_XML = 16 * 1024 * 1024
MAX_XML_TOTAL = 64 * 1024 * 1024
MAX_SECONDS = 120
FORMATS = ("pdf", "docx", "xlsx")
FEATURES = {
    "pdf": ("native_text_proxy", "low_native_proxy", "scanned", "mixed", "layout"),
    "docx": ("body", "tables", "footnotes", "endnotes", "ancillary"),
    "xlsx": ("formulas", "formula_cache", "missing_formula_cache", "merged", "sparse_proxy"),
}
METRICS = (
    "required_text_recall",
    "provenance",
    "reading_order",
    "table_cells",
    "table_relationships",
    "stored_values",
    "formulas",
    "cached_values",
    "displayed_values",
)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path):
    if path.is_symlink() or path.stat().st_size > MAX_JSON:
        raise ValueError("Evidence resource bound")
    return json.loads(path.read_text(encoding="utf-8"))


def office_features(path: Path, fmt: str) -> dict[str, bool | None]:
    """Bounded element inventory only; no formula/macro/link execution or text export."""
    unknown = dict.fromkeys(FEATURES[fmt])
    try:
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            if len(entries) > 20_000 or len({e.filename for e in entries}) != len(entries):
                return unknown
            selected = [
                e
                for e in entries
                if (fmt == "docx" and e.filename.startswith("word/"))
                or (fmt == "xlsx" and e.filename.startswith("xl/worksheets/"))
                if e.filename.endswith(".xml")
            ]
            if not selected or sum(e.file_size for e in selected) > MAX_XML_TOTAL:
                return unknown
            counts = Counter()
            for entry in selected:
                if (
                    entry.file_size > MAX_XML
                    or entry.flag_bits & 1
                    or entry.file_size / max(1, entry.compress_size) > 200
                ):
                    return unknown
                data = archive.read(entry)
                if re.search(rb"<!\s*(?:DOCTYPE|ENTITY)\b", data.replace(b"\x00", b""), re.I):
                    return unknown
                root = ET.fromstring(data)
                if fmt == "docx":
                    ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
                    if entry.filename == "word/document.xml":
                        counts["body"] += len(root.findall(f"./{ns}body/{ns}p"))
                        counts["tables"] += len(root.findall(f".//{ns}tbl"))
                    for tag in ("footnote", "endnote"):
                        counts[tag + "s"] += sum(
                            n.get(ns + "type")
                            not in ("separator", "continuationSeparator", "continuationNotice")
                            for n in root.iter(ns + tag)
                        )
                    if re.fullmatch(r"word/(?:header|footer)\d+\.xml", entry.filename):
                        counts["ancillary"] += 1
                    counts["ancillary"] += len(root.findall(f".//{ns}comment"))
                else:
                    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
                    cells = root.findall(f".//{ns}sheetData/{ns}row/{ns}c")
                    for cell in cells:
                        if cell.find(ns + "f") is not None:
                            counts["formulas"] += 1
                            cache = cell.find(ns + "v")
                            counts[
                                "formula_cache"
                                if cache is not None and cache.text
                                else "missing_formula_cache"
                            ] += 1
                    counts["merged"] += len(root.findall(f".//{ns}mergeCell"))
                    dimension = root.find(ns + "dimension")
                    if dimension is not None:
                        from openpyxl.utils.cell import range_boundaries

                        x1, y1, x2, y2 = range_boundaries(dimension.get("ref", "A1"))
                        if None not in (x1, y1, x2, y2):
                            area = (x2 - x1 + 1) * (y2 - y1 + 1)
                            counts["sparse_proxy"] += area >= 1000 and len(cells) / area < 0.01
            if fmt == "docx":
                counts["ancillary"] += counts["footnotes"] + counts["endnotes"]
            return {k: counts[k] > 0 for k in FEATURES[fmt]}
    except (OSError, ValueError, KeyError, ET.ParseError, zipfile.BadZipFile):
        return unknown


def metric_totals(records, results) -> dict:
    counts = {name: [0, 0, 0, 0] for name in METRICS}
    labels = Counter()
    for record in records:
        labels.update(
            {
                "anchors": len(record.anchors),
                "order": len(record.order_pairs),
                "table_cells": len(record.table_cells),
                "relations": len(record.table_relationships),
                "value_checks": len(record.cells),
                "numeric_bearing_anchors": sum(
                    bool(re.search(r"[0-9]", a.text)) for a in record.anchors
                ),
            }
        )
        totals = {
            "required_text_recall": len(record.anchors),
            "provenance": len(record.anchors) + len(record.cells),
            "reading_order": len(record.order_pairs),
            "table_cells": len(record.table_cells),
            "table_relationships": len(record.table_relationships),
            **dict.fromkeys(("stored_values", "formulas", "cached_values"), len(record.cells)),
            "displayed_values": 0,
        }
        result = results.get(record.document_id)
        scored = score_record(record, result)["metrics"] if result is not None else {}
        for name in METRICS:
            counts[name][2] += totals[name]
            if name in scored:
                m = scored[name]
                counts[name][0] += m["passed"]
                counts[name][1] += m["evaluated"]
                counts[name][3] += m["unsupported"]
        if result is None:
            counts["displayed_values"][3] += sum(c.check_display for c in record.cells)
    return {
        "reviewed_documents": len(records),
        "labels": dict(sorted(labels.items())),
        "metrics": {
            name: {
                "passed": p,
                "evaluated": e,
                "label_total": total,
                "unknown": total - e,
                "unsupported": unsupported,
                "status": "NOT_EVALUATED"
                if not e
                else "PARTIALLY_EVALUATED"
                if e < total
                else "EVALUATED",
                "score": p / e if e and e == total else None,
            }
            for name, (p, e, total, unsupported) in counts.items()
        },
    }


def family_risks(rows: list[dict]) -> dict:
    def repeated(key):
        counts = Counter(r[key] for r in rows if r.get(key))
        return {
            "groups": sum(n > 1 for n in counts.values()),
            "documents": sum(n for n in counts.values() if n > 1),
        }

    families = {}
    for row in rows:
        if row.get("family"):
            families.setdefault(row["family"], set()).add(row.get("split", "UNKNOWN"))
    return {
        "exact_hash": repeated("sha256"),
        "shared_source_page_risk": repeated("source_page"),
        "declared_family": repeated("family"),
        "family_unknown_documents": sum(not r.get("family") for r in rows),
        "declared_family_split_crossings": sum(
            "dev" in s and "test" in s for s in families.values()
        )
        if families
        else None,
        "family_split_check": "DECLARATIONS_ONLY" if families else "NOT_EVALUATED",
        "near_duplicates": "NOT_EVALUATED",
        "independent_test": "NOT_ESTABLISHED",
    }


def build_audit(rows: list[dict], records, results: dict) -> dict:
    """Aggregate unique document membership; unknown captures never erase labels."""
    by_id = {r["document_id"]: r for r in rows}
    if (
        len(rows) > 90
        or len(by_id) != len(rows)
        or len({r.document_id for r in records}) != len(records)
    ):
        raise ValueError("Coverage identities rejected")
    for row in rows:
        if row["format"] not in FORMATS or row["status"] not in (
            "success",
            "needs_review",
            "failed",
            "UNKNOWN",
        ):
            raise ValueError("Coverage metadata rejected")
    for record in records:
        if (
            record.document_id not in by_id
            or by_id[record.document_id]["format"] != record.document_format
        ):
            raise ValueError("Coverage Gold linkage rejected")
    for identity, result in results.items():
        if identity not in by_id or (
            result is not None and result.status.value != by_id[identity]["status"]
        ):
            raise ValueError("Capture status mismatch; no automatic promotion")
    facets = {}
    for fmt in FORMATS:
        facets["format." + fmt] = {r["document_id"] for r in rows if r["format"] == fmt}
        for feature in FEATURES[fmt]:
            facets[fmt + "." + feature] = {
                r["document_id"]
                for r in rows
                if r["format"] == fmt and r.get("features", {}).get(feature) is True
            }
    for lang in ("en", "cy", "ru", "kk", "mixed", "UNKNOWN"):
        facets["language_metadata." + lang] = {
            r["document_id"]
            for r in rows
            if (
                r.get("language")
                if r.get("language") in ("en", "cy", "ru", "kk", "mixed")
                else "UNKNOWN"
            )
            == lang
        }
    for status in ("success", "needs_review", "failed", "UNKNOWN"):
        facets["status." + status] = {r["document_id"] for r in rows if r["status"] == status}
    for fmt in FORMATS:
        facets[fmt + ".reviewed_table_scope"] = {
            r.document_id for r in records if r.document_format == fmt and r.table_cells
        }
    scenarios = {}
    for name, ids in sorted(facets.items()):
        fmt, _, feature = name.partition(".")
        applicable = [r for r in rows if fmt not in FORMATS or r["format"] == fmt]
        unknown = (
            sum(r.get("features", {}).get(feature) is None for r in applicable)
            if feature in FEATURES.get(fmt, ())
            else 0
        )
        selected = [r for r in records if r.document_id in ids]
        scenarios[name] = {
            "documents": len(ids),
            "applicable_documents": len(applicable),
            "unknown_documents": unknown,
            "statuses": dict(sorted(Counter(by_id[i]["status"] for i in ids).items())),
            "warning_documents": dict(
                sorted(
                    Counter(
                        code
                        for i in ids
                        for code in by_id[i].get("warnings", {})
                        if code in {w.value for w in WarningCode}
                    ).items()
                )
            ),
            **metric_totals(selected, results),
        }
    # Anchor facets use label identities, not every label in a document containing a number.
    anchor_facets = {}
    for name in (
        "numeric_bearing",
        "body",
        "footnote",
        "endnote",
        "header",
        "footer",
        "comment",
        "drawing",
    ):
        views = []
        for record in records:
            anchors = [
                a
                for a in record.anchors
                if (
                    bool(re.search(r"[0-9]", a.text))
                    if name == "numeric_bearing"
                    else a.source.region == name
                )
            ]
            ids = {a.anchor_id for a in anchors}
            if ids:
                views.append(
                    record.model_copy(
                        update={
                            "anchors": anchors,
                            "cells": [],
                            "order_pairs": [
                                p for p in record.order_pairs if {p.before, p.after} <= ids
                            ],
                            "table_cells": [c for c in record.table_cells if c.anchor_id in ids],
                            "table_relationships": [
                                p for p in record.table_relationships if {p.left, p.right} <= ids
                            ],
                        }
                    )
                )
        anchor_facets[name] = metric_totals(views, results)
    return {
        "version": VERSION,
        "corpus_documents": len(rows),
        "reviewed": metric_totals(records, results),
        "scenarios": scenarios,
        "anchor_facets": anchor_facets,
        "family_risks": family_risks(rows),
        "overlap_rule": "Unique membership per row; scenario rows overlap and must not be summed.",
        "semantic_units_dates_ids": "NOT_EVALUATED_NO_TYPED_LABELS",
        "content_language": "UNKNOWN_NOT_INFERRED_FROM_PAGE_LOCALE",
        "production_authorization": False,
    }


def same_pair(paths: list[Path]) -> dict:
    reports = [read_json(p) for p in paths]
    if len(reports) != 2:
        raise ValueError("Two captured repetitions required")
    for report in reports:
        frozen = (
            report["quality"]
            if "quality" in report
            else {
                k: v for k, v in report.items() if k not in ("runtime", "deterministic_fingerprint")
            }
        )
        if fingerprint(frozen) != report["deterministic_fingerprint"]:
            raise ValueError("Frozen report fingerprint rejected")
    if reports[0]["deterministic_fingerprint"] != reports[1]["deterministic_fingerprint"]:
        raise ValueError("Repetition mismatch")
    return reports[0]


def bundle_profile(bundle: Path) -> tuple[Path, list[Path]]:
    """Final v2 registration owns runs 3/4; legacy initial attempts stay separate."""
    if (bundle / "registration-v2.json").exists():
        return bundle / "registration-v2.json", [bundle / f"run-{n}/metrics.json" for n in (3, 4)]
    return bundle / "registration.json", [bundle / f"run-{n}/metrics.json" for n in (1, 2)]


def artifact_profile(bundle: Path) -> Path:
    final = bundle / "artifact-manifest-final.json"
    return final if final.exists() else bundle / "artifact-manifest.json"


def paired_hits(record, before, after) -> dict:
    if before is None or after is None:
        return {"recovered": None, "lost": None}
    presence = []
    for result in (before, after):
        observations = _observations(result)
        presence.append(
            {
                a.anchor_id: any(normalize(a.text) in normalize(o.text) for o in observations)
                for a in record.anchors
            }
        )
    b, c = presence
    return {
        "recovered": [a for a in b if c[a] and not b[a]],
        "lost": [a for a in b if b[a] and not c[a]],
    }


def historical_summary(records, metrics: dict) -> dict:
    """Project fixed numeric fields; never forward arbitrary captured dictionaries."""
    expected = metric_totals(records, {})["metrics"]
    safe = {}
    for name in METRICS:
        m = metrics[name]
        values = [m[k] for k in ("passed", "evaluated", "unsupported")]
        if any(type(v) is not int or v < 0 for v in values):
            raise ValueError("Historical metric counters rejected")
        passed, evaluated, unsupported = values
        if passed > evaluated or evaluated != expected[name]["label_total"]:
            raise ValueError("Historical metric denominator rejected")
        safe[name] = {
            "passed": passed,
            "evaluated": evaluated,
            "unsupported": unsupported,
            "score": passed / evaluated if evaluated else None,
            "status": "EVALUATED" if evaluated else "NOT_EVALUATED",
        }
    return {
        "gold": {
            "reviewed_documents": len(records),
            "anchors": sum(len(r.anchors) for r in records),
            "fingerprint": fingerprint([r.model_dump(mode="json") for r in records]),
        },
        "metrics": safe,
    }


def run(
    manifest: Path,
    corpus: Path,
    gold: Path,
    baseline_paths: list[Path],
    bundles: list[Path],
    baseline_gold: Path,
) -> dict:
    started = time.monotonic()
    sources = _read_sources(manifest)
    paths = verify_corpus(corpus, sources, ExtractionLimits())
    records = load_gold(gold, sources)
    baseline = same_pair(baseline_paths)
    old_records = load_gold(baseline_gold, sources)
    current = {r.document_id: r for r in records}
    if (
        fingerprint([r.model_dump(mode="json") for r in old_records])
        != baseline["gold"]["fingerprint"]
    ):
        raise ValueError("Historical Gold revision rejected")
    if any(current.get(r.document_id) != r for r in old_records):
        raise ValueError("Historical Gold is not an unchanged subset")
    identity = baseline["identity"]
    if identity["manifest_sha256"] != digest(manifest) or identity[
        "source_snapshot"
    ] != fingerprint(sources):
        raise ValueError("Baseline source identity rejected")
    code_names = {
        "parser_sha256": "parsers.py",
        "evaluator_sha256": "fidelity_eval.py",
        "extraction_models_sha256": "models.py",
        "gold_contract_sha256": "fidelity_gold.py",
    }
    for key, name in code_names.items():
        if digest(Path("src/doclens_ai/extraction") / name) != identity[key]:
            raise ValueError("Baseline code drift")
    documents = {d["document_id"]: d for d in baseline["documents"]}
    if set(documents) != set(sources) or len(documents) != len(baseline["documents"]):
        raise ValueError("Baseline population rejected")
    with manifest.open(encoding="utf-8", newline="") as stream:
        metadata = {r["document_id"]: r for r in csv.DictReader(stream)}
    rows = []
    for key, (_, _, fmt) in sorted(sources.items()):
        if time.monotonic() - started > MAX_SECONDS:
            raise ValueError("Audit time bound")
        meta, observed = metadata[key], documents[key]
        if (
            not meta.get("license")
            or not meta.get("license_url")
            or not meta.get("license_basis_url")
        ):
            raise ValueError("Missing license provenance")
        if observed["format"] != fmt:
            raise ValueError("Baseline format rejected")
        features = (
            office_features(paths[key], fmt)
            if fmt != "pdf"
            else {
                "native_text_proxy": observed["text_characters"] > 0,
                "low_native_proxy": observed["warnings"].get("insufficient_text", 0) > 0,
            }
        )
        rows.append(
            {
                "document_id": key,
                "format": fmt,
                "status": observed["status"],
                "sha256": meta["sha256"],
                "source_page": meta.get("source_page_url"),
                "language": meta.get("document_language") or "UNKNOWN",
                "features": features,
                "warnings": observed["warnings"],
            }
        )
    results = {}
    comparisons = []
    inputs = {
        "manifest": digest(manifest),
        "gold": digest(gold),
        "code": digest(Path(__file__)),
        "baseline_gold": digest(baseline_gold),
    }
    for i, path in enumerate(baseline_paths):
        inputs[f"baseline_{i}"] = digest(path)
    by_id = {r.document_id: r for r in records}
    shared_ocr = None
    for bundle_index, bundle in enumerate(bundles):
        file_manifest = read_json(artifact_profile(bundle))
        for relative, checksum in file_manifest.items():
            target = (bundle / relative).resolve()
            if not target.is_relative_to(bundle.resolve()) or digest(target) != checksum:
                raise ValueError("Captured artifact hash rejected")
        # Historical profile filenames differ between the unchanged historical experiment profiles.
        reg_path, candidates = bundle_profile(bundle)
        registration = read_json(reg_path)
        if registration["gold_bytes"] != digest(gold) or registration["manifest"] != digest(
            manifest
        ):
            raise ValueError("OCR input identity rejected")
        configuration = {k: registration[k] for k in ("code", "limits", "ocr", "pins")}
        if shared_ocr is not None and configuration != shared_ocr:
            raise ValueError("OCR configuration mismatch")
        shared_ocr = configuration
        for name, checksum in registration["code"].items():
            code_path = (
                Path("tools/pdf_ocr_candidate/benchmark.py")
                if name == "benchmark.py"
                else Path("src/doclens_ai/extraction") / name
            )
            if digest(code_path) != checksum:
                raise ValueError("OCR code drift")
        pair = same_pair(candidates)
        allowed_states = {
            "native",
            "blank_render",
            "ocr",
            "empty_ocr",
            "duplicate_ocr",
            "pixel_limit",
            "page_limit",
            "output_limit",
            "timeout",
            "memory_limit",
            "missing_runtime",
            "tool_failed",
            "missing_ocr",
            "invalid_ocr",
            "invalid_render",
        }
        if any(
            p["state"] not in allowed_states
            for d in pair["quality"]["documents"]
            for p in d["pages"]
        ):
            raise ValueError("Captured page state rejected")
        if pair["quality"]["registration_fingerprint"] != fingerprint(registration):
            raise ValueError("OCR registration rejected")
        if set(registration["cohort"]) != {d["document_id"] for d in pair["quality"]["documents"]}:
            raise ValueError("OCR cohort rejected")
        for d in pair["quality"]["documents"]:
            key = d["document_id"]
            if key in results or tuple(registration["cohort"][key]) != sources[key]:
                raise ValueError("Duplicate or mismatched evidence scope")
            stage_results = {}
            for stage in ("baseline", "candidate"):
                raw_pair = [read_json(p.parent / key / stage / "result.json") for p in candidates]
                if raw_pair[0]["result"] != raw_pair[1]["result"]:
                    raise ValueError("Captured extraction repetition mismatch")
                result = (
                    restore(raw_pair[0]["result"]) if raw_pair[0]["result"] is not None else None
                )
                stage_results[stage] = result
                if result is not None:
                    if (
                        score_record(by_id[key], result) != d[stage]["scores"]
                        or fingerprint(result.to_dict()) != d[stage]["extraction_fingerprint"]
                        or result.status.value != d[stage]["status"]
                    ):
                        raise ValueError("Captured score or status rejected")
                elif d[stage]["scores"] is not None:
                    raise ValueError("Missing capture cannot have scores")
                for captured in candidates:
                    journal_path = captured.parent / key / stage / "resources.jsonl"
                    if journal_path.stat().st_size > MAX_JSON:
                        raise ValueError("Resource journal bound")
                    journal = [json.loads(line) for line in journal_path.read_text().splitlines()]
                    run_report = read_json(captured)
                    runtime = next(
                        x[stage] for x in run_report["runtime"] if x["document_id"] == key
                    )
                    if (
                        not journal
                        or not runtime["cleanup"]
                        or max(x["tree_rss"] for x in journal) != runtime["peak_tree_rss_bytes"]
                        or max(x["disk"] for x in journal) != runtime["peak_sampled_disk_bytes"]
                        or any(
                            x["tree_rss"] > registration["limits"]["max_process_bytes"]
                            or x["elapsed"] > registration["limits"]["timeout_seconds"]
                            or x["disk"] > registration["limits"]["max_scratch_bytes"]
                            for x in journal
                        )
                    ):
                        raise ValueError("Captured resource boundary rejected")
            if d["baseline"]["extraction_fingerprint"] != documents[key]["extraction_fingerprint"]:
                raise ValueError("Baseline capture not comparable")
            results[key] = stage_results["baseline"]
            before, after = stage_results["baseline"], stage_results["candidate"]
            expected = paired_hits(by_id[key], before, after)
            if any(d["comparison"][k] != v for k, v in expected.items()):
                raise ValueError("Captured recovery/loss mismatch")
            if before is not None and after is not None:
                native = Counter((b.text, str(b.source)) for b in before.blocks)
                proposed = Counter((b.text, str(b.source)) for b in after.blocks)
                if native - proposed:
                    raise ValueError("Native block preservation rejected")
                if before.status.value != after.status.value:
                    raise ValueError("Status transition requires separate review")
        comparisons.append(
            {
                "documents": len(pair["quality"]["documents"]),
                "anchors": pair["quality"]["population"]["anchors"],
                "recovered": None
                if any(d["comparison"]["recovered"] is None for d in pair["quality"]["documents"])
                else sum(
                    len(d["comparison"]["recovered"] or []) for d in pair["quality"]["documents"]
                ),
                "lost": None
                if any(d["comparison"]["lost"] is None for d in pair["quality"]["documents"])
                else sum(len(d["comparison"]["lost"] or []) for d in pair["quality"]["documents"]),
                "pages": dict(
                    sorted(
                        Counter(
                            p["state"] for d in pair["quality"]["documents"] for p in d["pages"]
                        ).items()
                    )
                ),
                "quality_fingerprint": pair["deterministic_fingerprint"],
                "artifact_hashes": len(file_manifest),
            }
        )
        inputs[f"bundle_{bundle_index}"] = fingerprint(file_manifest)
    report = build_audit(rows, records, results)
    report.update(
        {
            "inputs": inputs,
            "ocr_comparisons": comparisons,
            "historical_baseline": {
                **historical_summary(old_records, baseline["reviewed_fidelity"]["metrics"]),
            },
        }
    )
    if (
        verify_corpus(corpus, sources, ExtractionLimits()) != paths
        or digest(gold) != inputs["gold"]
    ):
        raise ValueError("Inputs changed during audit")
    report["deterministic_fingerprint"] = fingerprint(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--baseline", nargs=2, type=Path, required=True)
    parser.add_argument("--baseline-gold", type=Path, required=True)
    parser.add_argument("--ocr-bundle", action="append", type=Path, default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if (
            args.output.exists()
            or args.output.resolve().is_relative_to(args.corpus.resolve())
            or any(p.is_symlink() for p in args.output.parents)
        ):
            raise ValueError("Output rejected")
        if subprocess.run(
            ["git", "check-ignore", "-q", str(args.output)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode:
            raise ValueError("Output must be ignored")
        with (
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
            warnings.catch_warnings(),
        ):
            warnings.simplefilter("ignore")
            previous = logging.root.manager.disable
            logging.disable(logging.CRITICAL)
            try:
                report = run(
                    args.manifest,
                    args.corpus,
                    args.gold,
                    args.baseline,
                    args.ocr_bundle,
                    args.baseline_gold,
                )
            finally:
                logging.disable(previous)
        args.output.mkdir(parents=True, exist_ok=False)
        (args.output / "metrics.json").write_text(
            json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
        print(json.dumps({"status": "PASS", "fingerprint": report["deterministic_fingerprint"]}))
        return 0
    except Exception:
        print("BLOCKED: coverage inputs, evidence or output boundary rejected")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
