"""Frozen paired offline ruled-table benchmark. No production or Gold writes."""

from __future__ import annotations

import argparse
import contextlib
import csv
import io
import json
import logging
import platform
import subprocess
import sys
from collections import Counter
from dataclasses import asdict
from pathlib import Path

import pypdf

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
    SourceLocation,
    TableBlock,
    TableCell,
    TableRow,
    TextBlock,
    WarningCode,
    WarningSeverity,
)
from doclens_ai.extraction.parsers import ExtractionLimits, extract_file
from doclens_ai.extraction.pdf_table_candidate import TableLimits, extract_tables, supplement
from tools.docx_footnote_candidate.benchmark import GUARDS, monitor, sha
from tools.docx_footnote_candidate.locator_review_packet import (
    fresh_output,
    require_unoptimized,
    write_json,
)

ROOT = Path(__file__).resolve().parents[2]
PINS = (
    "src/doclens_ai/extraction/parsers.py",
    "src/doclens_ai/extraction/models.py",
    "src/doclens_ai/extraction/fidelity_gold.py",
    "src/doclens_ai/extraction/fidelity_eval.py",
    "tools/docx_footnote_candidate/benchmark.py",
    "tools/docx_footnote_candidate/locator_review_packet.py",
    "src/doclens_ai/extraction/pdf_table_candidate.py",
    "tools/pdf_table_candidate/benchmark.py",
    "tests/unit/test_pdf_table_candidate.py",
)
METRICS = (
    "required_text_recall",
    "provenance",
    "reading_order",
    "table_cells",
    "table_relationships",
)


def restore(raw: dict) -> ExtractionResult:
    blocks = []
    for b in raw["blocks"]:
        if b["kind"] == "text":
            blocks.append(TextBlock(b["order"], b["text"], SourceLocation(**b["source"])))
        elif b["kind"] == "table":
            rows = tuple(
                TableRow(
                    r["row_index"],
                    tuple(
                        TableCell(
                            c["row_index"],
                            c["column_index"],
                            c["text"],
                            SourceLocation(**c["source"]),
                            c["row_span"],
                            c["column_span"],
                        )
                        for c in r["cells"]
                    ),
                )
                for r in b["rows"]
            )
            blocks.append(
                TableBlock(
                    b["order"],
                    b["table_index"],
                    rows,
                    SourceLocation(**b["source"]),
                    b["name"],
                    b["reference"],
                )
            )
        else:
            raise ValueError("Unknown block")
    result = ExtractionResult(
        raw["schema_version"],
        DocumentFormat(raw["document_format"]),
        ExtractionStatus(raw["status"]),
        raw["source_sha256"],
        raw["source_size_bytes"],
        tuple(blocks),
        (),
        tuple(
            ExtractionWarning(
                WarningCode(w["code"]),
                WarningSeverity(w["severity"]),
                w["count"],
                SourceLocation(**w["source"]) if w["source"] else None,
            )
            for w in raw["warnings"]
        ),
        ErrorCategory(raw["error_category"]) if raw["error_category"] else None,
    )
    if result.to_dict() != raw:
        raise ValueError("Lossy PDF capture rejected")
    return result


def freeze(manifest: Path, corpus: Path, gold: Path, baseline: Path):
    require_unoptimized()
    sources = _read_sources(manifest)
    paths = verify_corpus(corpus, sources, ExtractionLimits())
    records = tuple(
        r
        for r in load_gold(gold, sources)
        if r.document_format == "pdf" and (r.table_cells or r.table_relationships)
    )
    if not records:
        raise ValueError("Missing reviewed cohort")
    with manifest.open(encoding="utf-8", newline="") as f:
        if any(
            not row.get(k)
            for row in csv.DictReader(f)
            for k in ("license", "license_url", "license_basis_url")
        ):
            raise ValueError("Missing license provenance")
    historic = json.loads(baseline.read_text())
    if (
        historic["manifest"] != sha(manifest)
        or historic["gold"] != sha(gold)
        or historic["source_map"] != fingerprint(sources)
    ):
        raise ValueError("Historical identity mismatch")
    if {d["id"]: tuple(d["source"]) for d in historic["documents"]} != {
        r.document_id: sources[r.document_id] for r in records
    }:
        raise ValueError("Historical cohort mismatch")
    return (
        {
            "version": "ml23-v1",
            "manifest": sha(manifest),
            "gold": sha(gold),
            "source_map": fingerprint(sources),
            "head": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            "baseline_preflight": sha(baseline),
            "cohort": {r.document_id: sources[r.document_id] for r in records},
            "code": {n: sha(ROOT / n) for n in PINS},
            "limits": asdict(TableLimits()),
            "guards": GUARDS,
            "pypdf": pypdf.__version__,
            "python": platform.python_version(),
            "pypdf_code": {
                name: sha(Path(pypdf.__file__).parent / name)
                for name in (
                    "_page.py",
                    "_reader.py",
                    "generic/_data_structures.py",
                    "generic/_base.py",
                )
            },
            "platform": {"system": platform.system(), "machine": platform.machine()},
            "decision": {
                "min_cell_gain": 1,
                "min_relation_gain": 1,
                "zero_losses": True,
                "production_authorization": False,
            },
        },
        paths,
        records,
        historic,
    )


def worker(source: Path, output: Path) -> int:
    previous = logging.root.manager.disable
    try:
        require_unoptimized()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            logging.disable(logging.CRITICAL)
            before = extract_file(source)
            evidence = extract_tables(source)
            combined = supplement(before, evidence)
            after = extract_file(source)
        write_json(
            output / "result.json",
            {
                "baseline": before.to_dict(),
                "candidate": combined.to_dict(),
                "geometry": evidence.to_dict(),
                "baseline_after": fingerprint(after.to_dict()),
            },
        )
        return 0
    except Exception:
        return 2
    finally:
        logging.disable(previous)


def summarize(record, raw: dict | None) -> dict:
    labels = {
        "anchors": len(record.anchors),
        "provenance": len(record.anchors),
        "order": len(record.order_pairs),
        "cells": len(record.table_cells),
        "relations": len(record.table_relationships),
        "numeric": sum(any("0" <= c <= "9" for c in a.text) for a in record.anchors),
    }
    if raw is None:
        return {
            "labels": labels,
            "baseline_scores": None,
            "candidate_scores": None,
            "status": "failed",
            "lost": None,
            "recovered": None,
            "numeric_before": None,
            "numeric_after": None,
            "native_preserved": False,
        }
    before = restore(raw["baseline"])
    after = restore(raw["candidate"])
    evidence = raw["geometry"]
    good = evidence["status"] != "failed"
    native_unchanged = (
        fingerprint(raw["baseline"]) == raw["baseline_after"]
        and after.blocks[: len(before.blocks)] == before.blocks
        and after.warnings == before.warnings
    )
    hits = []
    for result in (before, after):
        obs = _observations(result)
        hits.append(
            {
                a.anchor_id: any(normalize(a.text) in normalize(o.text) for o in obs)
                for a in record.anchors
            }
        )
    numeric = [a.anchor_id for a in record.anchors if any("0" <= c <= "9" for c in a.text)]
    return {
        "labels": labels,
        "baseline_scores": score_record(record, before),
        "candidate_scores": score_record(record, after) if good else None,
        "baseline_status": before.status.value,
        "status": after.status.value,
        "geometry_status": evidence["status"],
        "native_preserved": native_unchanged,
        "lost": [a for a in hits[0] if hits[0][a] and not hits[1][a]],
        "recovered": [a for a in hits[0] if not hits[0][a] and hits[1][a]],
        "numeric_before": sum(hits[0][a] for a in numeric),
        "numeric_after": sum(hits[1][a] for a in numeric) if good else None,
        "pages": len(evidence["pages"]),
        "tables": len(evidence["grids"]),
        "emitted_cells": sum(len(g["cells"]) for g in evidence["grids"]),
        "page_issues": dict(
            sorted(Counter(issue for p in evidence["pages"] for issue in p["issues"]).items())
        ),
        "document_issues": evidence["issues"],
        "cell_hits": {
            a.anchor_id: any(
                normalize(a.text) in normalize(c.text)
                for b in after.blocks
                if isinstance(b, TableBlock)
                for r in b.rows
                for c in r.cells
            )
            for a in record.anchors
            if a.anchor_id in {x.anchor_id for x in record.table_cells}
        },
        "semantic_header_roles": "NOT_EVALUATED",
    }


def totals(documents, stage):
    keys = {
        "required_text_recall": "anchors",
        "provenance": "provenance",
        "reading_order": "order",
        "table_cells": "cells",
        "table_relationships": "relations",
    }
    result = {}
    for metric, label in keys.items():
        observations = [
            d[stage + "_scores"]["metrics"][metric]
            for d in documents
            if d[stage + "_scores"] is not None
        ]
        result[metric] = {
            "passed": sum(m["passed"] for m in observations),
            "evaluated": sum(m["evaluated"] for m in observations),
            "label_total": sum(d["labels"][label] for d in documents),
            "unknown_documents": sum(d[stage + "_scores"] is None for d in documents),
        }
    return result


def decision(documents):
    if any(not d["native_preserved"] or d["status"] == "failed" or d["lost"] for d in documents):
        return "REJECT"
    for d in documents:
        if d["baseline_scores"] is None or d["candidate_scores"] is None:
            return "INCONCLUSIVE"
        if any(
            d["candidate_scores"]["metrics"][m]["passed"]
            < d["baseline_scores"]["metrics"][m]["passed"]
            for m in METRICS
        ):
            return "REJECT"
        if d["numeric_after"] < d["numeric_before"]:
            return "REJECT"
    b, c = totals(documents, "baseline"), totals(documents, "candidate")
    return (
        "PROMOTE"
        if c["table_cells"]["passed"] - b["table_cells"]["passed"] >= 1
        and c["table_relationships"]["passed"] - b["table_relationships"]["passed"] >= 1
        else "REJECT"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", type=Path)
    parser.add_argument("--preregister", action="store_true")
    parser.add_argument("--registration", type=Path)
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
        default=Path("evaluation-output/pdf-table-v1-20261019/baseline-preflight.json"),
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        require_unoptimized()
        if args.worker:
            fresh_output(args.output / "boundary", args.corpus)
            if not args.output.is_dir() or {p.name for p in args.output.iterdir()} != {
                "resources.jsonl"
            }:
                raise ValueError("Worker output rejected")
            return worker(args.worker, args.output)
        fresh_output(args.output, args.corpus)
        frozen, paths, records, historical = freeze(
            args.manifest, args.corpus, args.gold, args.baseline
        )
        args.output.mkdir(parents=True)
        if args.preregister:
            write_json(args.output / "registration.json", frozen)
            print(json.dumps({"status": "FROZEN", "fingerprint": fingerprint(frozen)}))
            return 0
        if json.loads(args.registration.read_text()) != json.loads(json.dumps(frozen)):
            raise ValueError("Frozen configuration drift")
        write_json(args.output / "registration.json", frozen)
        docs = []
        resources = []
        old = {d["id"]: d for d in historical["documents"]}
        for r in records:
            stage = args.output / r.document_id
            stage.mkdir()
            runtime = monitor(
                [
                    sys.executable,
                    "-B",
                    str(Path(__file__).resolve()),
                    "--worker",
                    str(paths[r.document_id]),
                    "--output",
                    str(stage),
                ],
                stage,
            )
            resources.append({"document_id": r.document_id, **runtime})
            raw = (
                json.loads((stage / "result.json").read_text())
                if (stage / "result.json").exists() and not runtime["failure"]
                else None
            )
            d = summarize(r, raw)
            d["baseline_frozen"] = (
                raw is not None
                and fingerprint(raw["baseline"]) == old[r.document_id]["baseline_fingerprint"]
                and d["baseline_scores"] == old[r.document_id]["scores"]
            )
            docs.append({"document_id": r.document_id, **d})
        current, _, _, _ = freeze(args.manifest, args.corpus, args.gold, args.baseline)
        if current != frozen:
            raise ValueError("Post-run drift")
        integrity = all(d["baseline_frozen"] for d in docs) and all(r["cleanup"] for r in resources)
        quality = {
            "registration_fingerprint": fingerprint(frozen),
            "documents": docs,
            "baseline": totals(docs, "baseline"),
            "candidate": totals(docs, "candidate"),
            "candidate_verdict": decision(docs),
            "production_authorization": False,
            "qg01": "NOT_EVALUATED",
            "status_counts": dict(Counter(d["status"] for d in docs)),
        }
        report = {
            "status": "PASS" if integrity else "FIX",
            "quality": quality,
            "deterministic_fingerprint": fingerprint(quality),
            "runtime": resources,
        }
        write_json(args.output / "metrics.json", report)
        write_json(
            args.output / "artifact-manifest.json",
            {
                p.relative_to(args.output).as_posix(): sha(p)
                for p in sorted(args.output.rglob("*"))
                if p.is_file()
            },
        )
        print(
            json.dumps(
                {
                    "status": report["status"],
                    "candidate": quality["candidate_verdict"],
                    "fingerprint": report["deterministic_fingerprint"],
                    "baseline": quality["baseline"],
                    "tables": quality["candidate"],
                }
            )
        )
        return 0 if integrity else 1
    except Exception:
        print("BLOCKED: frozen PDF table experiment input, resource or output boundary rejected")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
