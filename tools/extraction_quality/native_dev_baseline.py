"""EX-01: two bounded native DEV passes; private captures, no quality scoring.

Run: python -m tools.extraction_quality.native_dev_baseline run --output <fresh-private-dir>
Verify: python -m tools.extraction_quality.native_dev_baseline verify --output <private-dir>
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import math
import platform
import subprocess
import sys
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from pydantic import TypeAdapter

from doclens_ai.eda import corpus_v2 as corpus
from doclens_ai.extraction.fidelity_gold import fingerprint
from doclens_ai.extraction.limits import ExtractionLimits
from doclens_ai.extraction.models import ExtractionResult
from tools.extraction_campaign.run import environment, run_one
from tools.extraction_quality import readiness_release
from tools.extraction_quality.readiness_io import ROOT, atomic, confined, private_root

VERSION = "extraction-native-dev-baseline-1"
RELEASE = ROOT / "evaluation-output/extraction-readiness-continuation-20261023-v2"
RELEASE_FINGERPRINT = "f480f4fad5b46eaf037b67d7ca77db2e37f93f1aa0172405fd7f493d44489b55"
EXPECTED = {"registered": 217, "dev": 215, "sealed_candidate": 2, "eligible": 199}
POLICY = {
    "wall_seconds_per_document": 120,
    "cpu_seconds": 90,
    "os_commit_bytes": 3 * 1024**3,
    "process_tree_rss_bytes": 2 * 1024**3,
    "native_output_bytes": 256 * 1024**2,
    "scratch_bytes": 512 * 1024**2,
}
CODE = (
    "tools/extraction_quality/native_dev_baseline.py",
    "tools/extraction_quality/readiness_release.py",
    "tools/extraction_quality/readiness_io.py",
    "tools/extraction_campaign/run.py",
    "tools/extraction_campaign/worker.py",
    "tools/extraction_campaign/resources.py",
    "tools/extraction_campaign/protocol.py",
    "tools/extraction_campaign/evidence.py",
    "src/doclens_ai/extraction/parsers.py",
    "src/doclens_ai/extraction/models.py",
    "src/doclens_ai/extraction/limits.py",
    "src/doclens_ai/extraction/fidelity_gold.py",
    "src/doclens_ai/eda/corpus_v2.py",
)
ADAPTER = TypeAdapter(ExtractionResult)


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT).decode("utf-8").strip()


def fresh_private(path: Path) -> None:
    """Reject public, linked, tracked, existing and frozen destinations before writing."""
    corpus.no_links(path)
    resolved = path.resolve()
    base = (ROOT / "evaluation-output").resolve()
    if resolved == base or not resolved.is_relative_to(base) or path.exists():
        raise ValueError("fresh private evaluation-output subdirectory required")
    if any((p / "RELEASE.json").exists() for p in (path, *path.parents)):
        raise ValueError("frozen destination rejected")
    relative = path.relative_to(ROOT).as_posix()
    ignored = subprocess.run(
        ["git", "check-ignore", "--quiet", "--", relative], cwd=ROOT, check=False
    )
    tracked = git("ls-files", "--", relative)
    if ignored.returncode != 0 or tracked:
        raise ValueError("ignored and untracked private destination required")


def admission(population: list[dict], expected: dict = EXPECTED) -> tuple[list[dict], list[dict]]:
    """Use the frozen matrix's scorer admission rule; never discover originals by glob."""
    ids, hashes, registered, admitted = set(), set(), [], []
    for row in population:
        key, sha = row["id"], row["sha256"]
        asset = corpus.Asset.model_validate(row["source_reference"])
        if key in ids or sha in hashes:
            raise ValueError("duplicate registered identity")
        ids.add(key)
        hashes.add(sha)
        if (
            (sha, row["format"]) != (asset.sha256, asset.format)
            or row.get("bytes", asset.size_bytes) != asset.size_bytes
            or asset.format not in {"pdf", "docx", "xlsx"}
        ):
            raise ValueError("source identity/size/format mismatch")
        if row["split"] not in {"dev", "sealed_candidate"}:
            raise ValueError("unexpected TEST/QA partition")
        if type(row["reserved_qa_family"]) is not bool:
            raise ValueError("explicit QA eligibility required")
        right = row["rights"]["local_evaluation"]
        if right is not None and type(right) is not bool:
            raise ValueError("explicit evaluation rights required")
        reasons = []
        if row["split"] != "dev":
            reasons.append("SEALED_CANDIDATE")
        if row["reserved_qa_family"]:
            reasons.append("RESERVED_QA_FAMILY")
        if right is not True:
            reasons.append("EVALUATION_RIGHTS_DENIED_OR_UNKNOWN")
        item = {
            "id": "nd-" + fingerprint([key, sha])[:24],
            "sha256": sha,
            "size_bytes": asset.size_bytes,
            "format": asset.format,
            "language": row["language"],
            "family": "nf-" + fingerprint(row["family"])[:24],
            "split": row["split"],
            "eligible": not reasons,
            "exclusion_reasons": reasons,
        }
        registered.append(item)
        if not reasons:
            admitted.append({"metadata": item, "asset": asset.model_dump(mode="json")})
    counts = {
        "registered": len(registered),
        "dev": sum(r["split"] == "dev" for r in registered),
        "sealed_candidate": sum(r["split"] == "sealed_candidate" for r in registered),
        "eligible": len(admitted),
    }
    if counts != expected or len({r["id"] for r in registered}) != len(registered):
        raise ValueError(f"population/eligibility reconciliation failed: {counts}")
    return sorted(registered, key=lambda r: r["id"]), sorted(
        admitted, key=lambda r: r["metadata"]["id"]
    )


def verified_cohort(release: Path) -> tuple[list[dict], list[dict]]:
    verified = readiness_release.verify(release)
    if verified["fingerprint"] != RELEASE_FINGERPRINT:
        raise ValueError("unexpected frozen readiness release")
    matrix = corpus.read_json(release / "effective-matrix.json", max_bytes=256 * 1024**2)
    # Reuse rights receipts, exact/normalized/template/translation family components,
    # reserved-QA checks and parent bindings, in addition to archive integrity.
    readiness_release.validate_continuation(release, matrix)
    registered, cohort = admission(matrix["population"])
    for row in matrix["population"]:
        corpus.asset_path(ROOT, corpus.Asset.model_validate(row["source_reference"]))
    return registered, cohort


def configuration() -> dict:
    """Freeze implementation, dependencies and native defaults before either pass."""
    env = environment(Path(sys.executable))
    return {
        "version": VERSION,
        "release_fingerprint": RELEASE_FINGERPRINT,
        "policy": POLICY,
        "limits": asdict(ExtractionLimits()),
        "code_sha256": {p: corpus.sha256(ROOT / p) for p in CODE},
        "python_sha256": corpus.sha256(Path(sys.executable)),
        "python": env["python"],
        "packages": env["packages"],
        "git": {
            "branch": git("branch", "--show-current"),
            "head": git("rev-parse", "HEAD"),
            "status": git("status", "--short"),
            "diff_sha256": fingerprint(git("diff", "--binary", "HEAD")),
        },
        "concurrency": 1,
        "seed": "not_applicable_no_random_sampling",
        "rss_scope": "sampled actual worker plus descendants; excludes venv launcher and parent",
        "rss_sampling_seconds": 0.05,
        "rss_limitations": "brief peaks may be missed; Windows commit limit is separate from RSS",
        "time_scope": "fresh child startup/imports, source checks, parsing, serialization, cleanup",
        "cache_scope": "fresh process per document; OS filesystem caches not reset",
    }


def structural(value: dict) -> dict:
    """Count only emitted structure; no guessed relationships, pages or quality scores."""
    blocks, sheets = value["blocks"], value["sheets"]
    tables = [b for b in blocks if b["kind"] == "table"]
    cells = [c for t in tables for r in t["rows"] for c in r["cells"]]
    spreadsheet = [c for s in sheets for c in s["cells"]]
    return {
        "text_blocks": sum(b["kind"] == "text" for b in blocks),
        "tables": len(tables),
        "table_cells": len(cells),
        "spanned_table_cells": sum(c["row_span"] > 1 or c["column_span"] > 1 for c in cells),
        "sheets": len(sheets),
        "spreadsheet_cells": len(spreadsheet),
        "formula_cells": sum(c["has_formula"] for c in spreadsheet),
        "formula_cached_value_null": sum(
            c["has_formula"] and c["cached_value"] is None for c in spreadsheet
        ),
        "merged_ranges": sum(len(s["merged_ranges"]) for s in sheets),
        "spreadsheet_tables": sum(len(s["tables"]) for s in sheets),
        "note_references": len(value["note_references"]),
        "page_locators": sum(b["source"]["page_number"] is not None for b in blocks),
        "xml_locators": sum(b["source"]["xml_path"] is not None for b in blocks),
        "cell_locators": sum(c["source"]["cell_coordinate"] is not None for c in spreadsheet),
    }


def capture_record(directory: Path, metadata: dict, receipt: dict) -> dict:
    """An absent/crashed worker is a failed observation, never a fabricated ExtractionResult."""
    record = {
        **metadata,
        "status": "failed",
        "failure": receipt["status"],
        "attempted": receipt["attempted_inference"],
        "capture": None,
        "runtime": receipt,
    }
    native = directory / "native.json"
    value = None
    if native.is_file():
        record["raw_capture_sha256"] = corpus.sha256(native)
        try:
            value = corpus.read_json(native, max_bytes=POLICY["native_output_bytes"])
            parsed = ADAPTER.validate_python(value)
            if parsed.to_dict() != value:
                raise ValueError("incomplete or lossy ExtractionResult capture")
        except (OSError, ValueError, TypeError, KeyError):
            value = None
            record["failure"] = "invalid_capture"
    if value is not None:
        if (value["source_sha256"], value["source_size_bytes"], value["document_format"]) != (
            metadata["sha256"],
            metadata["size_bytes"],
            metadata["format"],
        ):
            raise ValueError("capture source identity drift")
        record["capture"] = {
            "schema_version": value["schema_version"],
            "byte_sha256": corpus.sha256(native),
            "content_sha256": fingerprint(value),
            "structure_sha256": fingerprint(
                {k: value[k] for k in ("blocks", "sheets", "note_references")}
            ),
            "status": value["status"],
            "warnings": value["warnings"],
            "error_category": value["error_category"],
            "structure": structural(value),
        }
        if receipt["status"] == "completed":
            record.update(status=value["status"], failure=value["error_category"])
    elif receipt["status"] == "completed" and record["failure"] != "invalid_capture":
        record["failure"] = "missing_capture"
    if receipt["status"] == "completed":
        try:
            result = corpus.read_json(
                directory / "result.json", max_bytes=POLICY["native_output_bytes"]
            )
            if result["native_status"] != record["status"] or not record["attempted"]:
                raise ValueError("incomplete worker output")
        except (OSError, ValueError, KeyError, TypeError):
            record.update(status="failed", failure="incomplete_worker_output")
    elif receipt.get("error_type") == "MemoryError":
        record["failure"] = "memory_limit"
    record["deterministic_sha256"] = fingerprint(
        {k: v for k, v in record.items() if k not in {"runtime", "deterministic_sha256"}}
    )
    return record


def run_pass(cohort: list[dict], config: dict, output: Path, *, executor=run_one) -> dict:
    fresh_private(output)
    output.mkdir(parents=True)
    rows = []
    atomic(output / "STARTED.json", {"expected": len(cohort), "configuration": fingerprint(config)})
    for index, source in enumerate(cohort, 1):
        metadata = source["metadata"]
        path = corpus.asset_path(ROOT, corpus.Asset.model_validate(source["asset"]))
        directory = output / metadata["id"]
        job = {
            "candidate": "native",
            "configuration": {},
            "policy": config["policy"],
            "environment": config["packages"],
            "source_path": str(path.resolve()),
            "source_sha256": metadata["sha256"],
            "source_size_bytes": metadata["size_bytes"],
            "document_id": metadata["id"],
        }
        receipt = executor(Path(sys.executable), job, directory)
        corpus.asset_path(ROOT, corpus.Asset.model_validate(source["asset"]))
        row = capture_record(directory, metadata, receipt)
        atomic(directory / "observation.json", row)
        rows.append(row)
        if index % 10 == 0 or index == len(cohort):
            print(
                json.dumps({"pass": output.name, "accounted": index, "expected": len(cohort)}),
                flush=True,
            )
    result = {"version": VERSION, "configuration": fingerprint(config), "rows": rows}
    atomic(output / "manifest.json", result)
    atomic(output / "summary.json", summarize(result))
    return result


def percentile(values: list[float | int], fraction: float) -> float | int | None:
    return sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)] if values else None


def summarize(run: dict) -> dict:
    rows = run["rows"]

    def aggregate(selected: list[dict]) -> dict:
        durations = [
            r["runtime"]["wall_seconds"]
            for r in selected
            if r["runtime"]["wall_seconds"] is not None
        ]
        rss = [
            r["runtime"]["peak_tree_rss_bytes"]
            for r in selected
            if r["runtime"]["peak_tree_rss_bytes"] is not None
        ]
        structures, warning_documents, warning_occurrences = Counter(), Counter(), Counter()
        for row in selected:
            if row["capture"]:
                structures.update(row["capture"]["structure"])
                warning_documents.update({w["code"] for w in row["capture"]["warnings"]})
                for warning in row["capture"]["warnings"]:
                    warning_occurrences[warning["code"]] += warning["count"]
        return {
            "accounted": len(selected),
            "attempted": sum(r["attempted"] for r in selected),
            "statuses": dict(Counter(r["status"] for r in selected)),
            "failures": dict(Counter(r["failure"] for r in selected if r["failure"])),
            "full_captures": sum(r["capture"] is not None for r in selected),
            "structure": dict(structures),
            "warning_documents": dict(warning_documents),
            "warning_occurrences": dict(warning_occurrences),
            "seconds_p50": percentile(durations, 0.5),
            "seconds_p95": percentile(durations, 0.95),
            "seconds_total": sum(durations),
            "runtime_observations": len(durations),
            "rss_observations": len(rss),
            "rss_bytes_p50": percentile(rss, 0.5),
            "rss_bytes_p95": percentile(rss, 0.95),
            "rss_bytes_max": max(rss) if rss else None,
        }

    return {
        "version": VERSION,
        **aggregate(rows),
        "by_format": {
            f: aggregate([r for r in rows if r["format"] == f])
            for f in sorted({r["format"] for r in rows})
        },
        "by_language": {
            lang: aggregate([r for r in rows if r["language"] == lang.split("+")])
            for lang in sorted({"+".join(r["language"]) for r in rows})
        },
        "by_family": {
            f: aggregate([r for r in rows if r["family"] == f])
            for f in sorted({r["family"] for r in rows})
        },
        "quality": "NOT_EVALUATED",
        "semantic_dimensions": "NOT_EVALUATED",
        "independent_gold": False,
    }


def compare(left: dict, right: dict, expected: set[str]) -> dict:
    """Compare independently of timings/RSS; reject incomplete or duplicate denominators."""
    indexed = []
    for run in (left, right):
        rows = {r["id"]: r for r in run["rows"]}
        if set(rows) != expected or len(rows) != len(run["rows"]):
            raise ValueError("incomplete or duplicate pass outputs")
        indexed.append(rows)
    mismatches = {}
    for key in sorted(expected):
        a, b = indexed[0][key], indexed[1][key]
        fields = sorted((set(a) | set(b)) - {"runtime"})
        changed = [f for f in fields if a.get(f) != b.get(f)]
        if changed:
            mismatches[key] = changed
    return {
        "configuration_agrees": left["configuration"] == right["configuration"],
        "compared": len(expected),
        "mismatches": mismatches,
        "reproducible": not mismatches and left["configuration"] == right["configuration"],
    }


def artifact_hashes(output: Path) -> dict:
    result = {}
    for path in sorted(output.rglob("*")):
        corpus.no_links(path)
        if path.is_file() and path != output / "COMPLETE.json":
            result[path.relative_to(output).as_posix()] = corpus.sha256(path)
    return result


def execute(release: Path, output: Path) -> dict:
    import psutil

    from tools.extraction_campaign.resources import windows_job_supported

    fresh_private(output)
    if not windows_job_supported():
        raise ValueError("existing Windows job controls required")
    registered, cohort = verified_cohort(release)
    config = configuration()
    private_root(output)
    atomic(
        output / "protocol.json",
        {
            "configuration": config,
            "registered": registered,
            "hypothesis": "same frozen native inputs/configuration produce identical full captures",
            "acceptance": "199 attempted per pass; all accounted; deterministic agreement",
            "quality_thresholds": "NOT_EVALUATED_technical_diagnostic_only",
            "stopping_rule": "source/eligibility/code drift stops completion; keep parser failures",
            "hardware": {
                "platform": platform.platform(),
                "machine": platform.machine(),
                "logical_cpu": psutil.cpu_count(),
                "physical_cpu": psutil.cpu_count(logical=False),
                "ram_total_bytes": psutil.virtual_memory().total,
            },
        },
    )
    passes = []
    for name in ("pass-1", "pass-2"):
        current_registered, current_cohort = verified_cohort(release)
        if (current_registered, current_cohort, configuration()) != (registered, cohort, config):
            raise ValueError("cohort/configuration drift")
        passes.append(run_pass(cohort, config, output / name))
    if verified_cohort(release) != (registered, cohort) or configuration() != config:
        raise ValueError("post-run source/configuration drift")
    expected = {r["metadata"]["id"] for r in cohort}
    comparison = compare(*passes, expected)
    atomic(output / "reproducibility.json", comparison)
    complete = {
        "version": VERSION,
        "configuration": fingerprint(config),
        "registered": fingerprint(registered),
        "artifacts": artifact_hashes(output),
        "reproducibility": comparison,
        "all_attempted": all(all(r["attempted"] for r in p["rows"]) for p in passes),
    }
    complete["fingerprint"] = fingerprint(complete)
    atomic(output / "COMPLETE.json", complete)
    return verify(output)


def verify(output: Path) -> dict:
    corpus.no_links(output)
    if not output.resolve().is_relative_to((ROOT / "evaluation-output").resolve()):
        raise ValueError("private output required")
    complete = corpus.read_json(output / "COMPLETE.json")
    if complete["fingerprint"] != fingerprint(
        {k: v for k, v in complete.items() if k != "fingerprint"}
    ) or complete["artifacts"] != artifact_hashes(output):
        raise ValueError("incomplete or modified baseline artifacts")
    protocol = corpus.read_json(output / "protocol.json")
    registered = protocol["registered"]
    expected = {r["id"] for r in registered if r["eligible"]}
    if len(registered) != EXPECTED["registered"] or len(expected) != EXPECTED["eligible"]:
        raise ValueError("completion cohort denominator drift")
    if complete["registered"] != fingerprint(registered) or complete[
        "configuration"
    ] != fingerprint(protocol["configuration"]):
        raise ValueError("completion protocol mismatch")
    passes = []
    for name in ("pass-1", "pass-2"):
        run = corpus.read_json(output / name / "manifest.json", max_bytes=256 * 1024**2)
        if run["configuration"] != complete["configuration"]:
            raise ValueError("pass configuration mismatch")
        for row in run["rows"]:
            metadata = next((r for r in registered if r["id"] == row["id"]), None)
            if metadata is None or not metadata["eligible"]:
                raise ValueError("unregistered output")
            directory = confined(output / name, row["id"])
            receipt = corpus.read_json(directory / "receipt.json")
            if row != capture_record(directory, metadata, receipt):
                raise ValueError("saved observation drift")
        if corpus.read_json(output / name / "summary.json") != summarize(run):
            raise ValueError("summary drift")
        passes.append(run)
    comparison = compare(*passes, expected)
    if comparison != complete["reproducibility"] or comparison != corpus.read_json(
        output / "reproducibility.json"
    ):
        raise ValueError("comparison drift")
    all_attempted = all(all(r["attempted"] for r in p["rows"]) for p in passes)
    if all_attempted != complete["all_attempted"]:
        raise ValueError("attempt accounting drift")
    captures_complete = all(
        all(
            r["capture"] is not None
            and r["runtime"]["status"] == "completed"
            and r["status"] == r["capture"]["status"]
            and r["failure"] == r["capture"]["error_category"]
            for r in p["rows"]
        )
        for p in passes
    )
    return {
        "execution": "PASS"
        if all_attempted and captures_complete and comparison["reproducible"]
        else "FIX",
        "accounted_per_pass": [len(p["rows"]) for p in passes],
        "attempted_per_pass": [sum(r["attempted"] for r in p["rows"]) for p in passes],
        "reproducibility": comparison,
        "fingerprint": complete["fingerprint"],
        "quality": "NOT_EVALUATED",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("run", "verify"))
    parser.add_argument("--release", type=Path, default=RELEASE)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = (
            execute(args.release.resolve(), args.output.absolute())
            if args.command == "run"
            else verify(args.output.absolute())
        )
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        importlib.metadata.PackageNotFoundError,
    ) as exc:
        # No paths, source content or library traceback in public console output.
        print(
            json.dumps(
                {
                    "execution": "BLOCKED",
                    "reason_type": type(exc).__name__,
                    "prerequisite": "valid frozen release, originals, private outputs and runtime",
                }
            )
        )
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0 if result["execution"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
