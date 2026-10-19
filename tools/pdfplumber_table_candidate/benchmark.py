"""Frozen offline pdfplumber comparison, reusing unchanged ML-23 scoring contracts."""

from __future__ import annotations

import argparse
import contextlib
import importlib.metadata as md
import io
import json
import logging
import sys
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from doclens_ai.extraction.parsers import extract_file
from doclens_ai.extraction.pdfplumber_table_candidate import (
    SETTINGS,
    TEXT_SETTINGS,
    Limits,
    extract_tables,
    supplement,
)
from tools.pdf_table_candidate import benchmark as base

AREA = Path("evaluation-output/pdfplumber-table-v1-20261019")
PINS = (
    "src/doclens_ai/extraction/pdfplumber_table_candidate.py",
    "tools/pdfplumber_table_candidate/benchmark.py",
    "tests/unit/test_pdfplumber_table_candidate.py",
)


def runtime_identity() -> dict:
    """Verify installed distribution bytes against the preflight, excluding bytecode."""
    frozen = json.loads((AREA / "runtime-packages.json").read_text())
    for name, record in frozen.items():
        dist = md.distribution(name)
        if dist.version != record["version"] or any(
            base.sha(Path(dist.locate_file(n))) != digest for n, digest in record["files"].items()
        ):
            raise ValueError("Runtime drift")
    wheels = json.loads((AREA / "wheel-manifest.json").read_text())
    if any(base.sha(AREA / "wheels" / n) != digest for n, digest in wheels.items()):
        raise ValueError("Wheel drift")
    return {
        "packages": base.sha(AREA / "runtime-packages.json"),
        "wheels": base.sha(AREA / "wheel-manifest.json"),
        "triage": base.sha(AREA / "source-only-triage.json"),
    }


def freeze():
    frozen, paths, records, historic = base.freeze(
        Path("docs/eda/corpus_v1_manifest.csv"),
        Path("local-corpus"),
        Path("local-evaluation/extraction_fidelity_v1_expanded_approved.jsonl"),
        Path("evaluation-output/pdf-table-v1-20261019/baseline-preflight.json"),
    )
    frozen.update(
        version="ml24-v1",
        limits=asdict(Limits()),
        table_settings=dict(SETTINGS),
        text_settings=dict(TEXT_SETTINGS),
        runtime=runtime_identity(),
    )
    frozen["code"].update(
        {p: base.sha(base.ROOT / p) for p in (*PINS, "tools/pdf_table_candidate/benchmark.py")}
    )
    frozen["resolved_table_settings"] = asdict(
        __import__("pdfplumber.table", fromlist=["TableSettings"]).TableSettings.resolve(
            dict(SETTINGS)
        )
    )
    return frozen, paths, records, historic


def worker(source: Path, output: Path) -> int:
    previous = logging.root.manager.disable
    try:
        base.require_unoptimized()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            logging.disable(logging.CRITICAL)
            before = extract_file(source)
            geometry = extract_tables(source)
            combined = supplement(before, geometry)
            after = extract_file(source)
        base.write_json(
            output / "result.json",
            {
                "baseline": before.to_dict(),
                "candidate": combined.to_dict(),
                "geometry": geometry.to_dict(),
                "baseline_after": base.fingerprint(after.to_dict()),
            },
        )
        return 0
    except Exception:
        return 2
    finally:
        logging.disable(previous)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", type=Path)
    parser.add_argument("--preregister", action="store_true")
    parser.add_argument("--registration", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        base.require_unoptimized()
        base.fresh_output(
            args.output / "boundary" if args.worker else args.output, Path("local-corpus")
        )
        if args.worker:
            if not args.output.is_dir() or {p.name for p in args.output.iterdir()} != {
                "resources.jsonl"
            }:
                raise ValueError("Worker output rejected")
            return worker(args.worker, args.output)
        frozen, paths, records, historic = freeze()
        if not args.preregister and (
            args.registration is None
            or json.loads(args.registration.read_text()) != json.loads(json.dumps(frozen))
        ):
            raise ValueError("Frozen configuration drift")
        args.output.mkdir(parents=True)
        base.write_json(args.output / "registration.json", frozen)
        if args.preregister:
            print(json.dumps({"status": "FROZEN", "fingerprint": base.fingerprint(frozen)}))
            return 0
        docs = []
        resources = []
        old = {d["id"]: d for d in historic["documents"]}
        for record in records:
            stage = args.output / record.document_id
            stage.mkdir()
            runtime = base.monitor(
                [
                    sys.executable,
                    "-B",
                    str(Path(__file__).resolve()),
                    "--worker",
                    str(paths[record.document_id]),
                    "--output",
                    str(stage),
                ],
                stage,
            )
            resources.append({"document_id": record.document_id, **runtime})
            capture = stage / "result.json"
            raw = (
                json.loads(capture.read_text())
                if capture.exists() and not runtime["failure"]
                else None
            )
            summary = base.summarize(record, raw)
            summary["baseline_frozen"] = (
                raw is not None
                and base.fingerprint(raw["baseline"])
                == old[record.document_id]["baseline_fingerprint"]
                and summary["baseline_scores"] == old[record.document_id]["scores"]
            )
            docs.append({"document_id": record.document_id, **summary})
        after, *_ = freeze()
        if frozen != after:
            raise ValueError("Post-run drift")
        integrity = all(d["baseline_frozen"] for d in docs) and all(
            r["cleanup"] and not r["failure"] for r in resources
        )
        quality = {
            "registration_fingerprint": base.fingerprint(frozen),
            "documents": docs,
            "baseline": base.totals(docs, "baseline"),
            "candidate": base.totals(docs, "candidate"),
            "candidate_verdict": base.decision(docs),
            "status_counts": dict(Counter(d["status"] for d in docs)),
            "production_authorization": False,
            "qg01": "NOT_EVALUATED",
        }
        report = {
            "status": "PASS" if integrity else "FIX",
            "quality": quality,
            "deterministic_fingerprint": base.fingerprint(quality),
            "runtime": resources,
        }
        base.write_json(args.output / "metrics.json", report)
        base.write_json(
            args.output / "artifact-manifest.json",
            {
                p.relative_to(args.output).as_posix(): base.sha(p)
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
                    "metrics": quality["candidate"],
                }
            )
        )
        return 0 if integrity else 1
    except Exception as exc:
        # Fixed diagnostic, with exception class only: no source/exception payload.
        print("BLOCKED: frozen offline comparator rejected (" + type(exc).__name__ + ")")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
