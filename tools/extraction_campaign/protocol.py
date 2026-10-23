"""Freeze byte-bound diagnostic DEV inputs; never manufacture Gold or sealed splits."""

from __future__ import annotations

import argparse
import csv
import importlib.metadata
import json
import platform
import subprocess
import sys
from pathlib import Path

from doclens_ai.eda import corpus_v2
from doclens_ai.evaluation.gold import load_gold_jsonl
from doclens_ai.evaluation.rag_gold import load_rag_gold
from doclens_ai.extraction.fidelity_eval import _read_sources, verify_corpus
from doclens_ai.extraction.fidelity_gold import load_gold
from doclens_ai.extraction.parsers import ExtractionLimits
from tools.extraction_campaign.evidence import digest
from tools.extraction_quality.dataset_readiness import (
    held_out_sources,
    isolation_report,
    validate_reference,
)

ROOT = Path(__file__).resolve().parents[2]
GOLD = ROOT / "local-evaluation/extraction_fidelity_v1_expanded_approved.jsonl"
MANIFEST = ROOT / "docs/eda/corpus_v1_manifest.csv"
EXCLUDED_RIGHTS = {"c1-0045": "new_processing_permission_unresolved_in_20261021_inventory"}


def sha(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_new(path: Path, value) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, sort_keys=True, ensure_ascii=True, indent=2, allow_nan=False)
        stream.write("\n")


def hardware() -> dict:
    import psutil

    memory = psutil.virtual_memory()
    try:
        gpu = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,uuid,driver_version,memory.total,memory.free",
                "--format=csv,noheader",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        devices = gpu.stdout.strip().splitlines() if gpu.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        devices = None
    return {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "logical_cpu": psutil.cpu_count(),
        "physical_cpu": psutil.cpu_count(logical=False),
        "ram_total_bytes": memory.total,
        "ram_available_bytes": memory.available,
        "disk_free_bytes": psutil.disk_usage(str(ROOT)).free,
        "gpu_inventory": devices,
        "cuda_execution": "NOT_EVALUATED",
    }


def code_pins() -> dict:
    paths = sorted((ROOT / "tools/extraction_campaign").glob("*.py"))
    paths += [
        ROOT / p
        for p in (
            "src/doclens_ai/extraction/fidelity_gold.py",
            "src/doclens_ai/extraction/docling_candidate.py",
            "src/doclens_ai/extraction/parsers.py",
            "src/doclens_ai/extraction/limits.py",
            "src/doclens_ai/extraction/models.py",
            "src/doclens_ai/extraction/bounded.py",
            "tools/extraction_quality/dataset_readiness.py",
        )
    ]
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in paths}


def prepare(output: Path) -> dict:
    if output.exists() or not output.resolve().is_relative_to(ROOT / "evaluation-output"):
        raise ValueError("fresh_private_output_required")
    sources = _read_sources(MANIFEST)
    paths = verify_corpus(ROOT / "local-corpus", sources, ExtractionLimits())
    records = load_gold(GOLD, sources)
    reference_path = ROOT / "evaluation-output/extraction-v2-20261021/control-manifest-final.json"
    office_path = ROOT / "docs/eda/extraction_corpus_v2_manifest.json"
    reference, office = corpus_v2.load(reference_path), corpus_v2.load(office_path)
    validate_reference(reference, MANIFEST)
    retrieval_path = ROOT / "local-evaluation/retrieval_gold_v1.jsonl"
    answers_path = ROOT / "local-evaluation/rag_gold_v1_approved.jsonl"
    # Metadata-only reuse of the existing cross-collection family exclusion guard.
    retrieval = load_gold_jsonl(retrieval_path, corpus_manifest_path=MANIFEST)
    answers = load_rag_gold(answers_path, manifest_path=MANIFEST)
    isolation = isolation_report(reference, office, held_out_sources(retrieval, answers))
    eligible = set(isolation["eligible_ids"])
    families = {s.source_record_id: s.family_id for s in reference.samples}
    with MANIFEST.open(encoding="utf-8", newline="") as stream:
        manifest = {r["document_id"]: r for r in csv.DictReader(stream)}
    selected, excluded = [], []
    from pypdf import PdfReader

    for record in records:
        identity = record.document_id
        if record.document_format != "pdf":
            continue
        reason = EXCLUDED_RIGHTS.get(identity)
        if "e2-" + identity not in eligible:
            reason = "reserved_test_family"
        if reason:
            excluded.append({"document_id": identity, "reason": reason})
            continue
        path = paths[identity]
        reader = PdfReader(path)
        pages = []
        for number, page in enumerate(reader.pages, 1):
            pages.append(
                {
                    "page_number": number,
                    "mediabox": [float(n) for n in page.mediabox],
                    "rotation": int(page.get("/Rotate", 0)),
                    "physical_page_id": digest({"source": record.source_sha256, "page": number}),
                }
            )
        selected.append(
            {
                "document_id": identity,
                "sha256": record.source_sha256,
                "size_bytes": record.source_size_bytes,
                "family_id": families[identity],
                "split": "dev_exposed",
                "language": manifest[identity]["document_language"],
                "language_basis": "historical_manifest_not_fresh_human_language_review",
                "local_evaluation": "historically_admitted_local_only",
                "license": manifest[identity]["license"],
                "new_annotation_permission": "not_inferred",
                "pages": pages,
                "gold": {
                    "class": "historical_partial_single_reviewer_attestation",
                    "anchors": len(record.anchors),
                    "order_pairs": len(record.order_pairs),
                    "numeric_anchors": sum(
                        any(c.isdigit() for c in a.text) for a in record.anchors
                    ),
                    "table_span_assertions": len(record.table_cells),
                    "table_relation_assertions": len(record.table_relationships),
                },
            }
        )
    if not 2 <= len(selected) <= 12:
        raise ValueError("diagnostic_cohort_size")
    input_paths = [
        MANIFEST,
        GOLD,
        reference_path,
        office_path,
        retrieval_path,
        answers_path,
        ROOT / "docs/eda/dataset_readiness_inventory_20261021.md",
    ]
    protocol = {
        "version": "extraction-research-20261023-v1",
        "git_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "sources": selected,
        "excluded": excluded,
        "input_sha256": {p.relative_to(ROOT).as_posix(): sha(p) for p in input_paths},
        "code_sha256": code_pins(),
        "hardware": hardware(),
        "environment": {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()},
        "family_split": {
            "development": "all_selected_exposed",
            "validation": [],
            "sealed_test": [],
            "independent_split_validity": "NOT_EVALUATED",
            "family_completeness": "unreviewed",
            "qa_test_families_excluded": True,
        },
        "metrics": {
            "exact_anchors": "whitespace_only_and_numeric_token_boundaries",
            "numbers": "exact_numeric_bearing_reviewed_anchors_not_all_source_numbers",
            "page": "exact_original_one_based_page_presence",
            "order": "historical_reviewed_pairs_with_native_order_not_spatial_sort",
            "CER_WER_GriTS_TEDS_layout_AP_formula_accuracy": "NOT_EVALUATED_missing_valid_gold",
            "table_cells_geometry_relations": "native_observations_retained_not_independent_gold",
            "p50_p95": "nearest_rank_completed_runs_only_full_attempt_counts_separate",
        },
        "critical_regressions": [
            "baseline_present_anchor_loss",
            "numeric_anchor_loss",
            "page_or_order_regression",
            "fabricated_relationship_or_geometry",
        ],
        "policy": {
            "max_configurations": 3,
            "repetitions": 2,
            "concurrency": 1,
            "wall_seconds_per_document": 600,
            "process_tree_rss_bytes": 3 * 1024**3,
            "os_commit_bytes": 4 * 1024**3,
            "cpu_seconds": 1200,
            "scratch_bytes": 256 * 1024**2,
            "native_output_bytes": 128 * 1024**2,
            "minimum_available_ram_bytes": 4 * 1024**3,
            "oom_modifications_max": 1,
            "quality_thresholds": "TBD_no_QG_claim",
            "critical_loss_gate": "any_measured_new_critical_loss_REJECT_frozen_config",
            "stop": "R3_only_after_R2_DEV_recovery_no_sealed_tuning",
            "cloud_transfer": False,
            "production_promotion": False,
            "inference_network": "deny_external_allow_only_explicit_owned_loopback",
        },
        "candidate_order": [
            "docling",
            "marker2",
            "ppstructurev3",
            "paddleocr_vl_1_6",
            "mineru25pro",
        ],
        "candidate_freeze": "Pin environment, config and model hashes before inference",
        "limitations": [
            "no_real_RU_KK_gold",
            "no_independent_whole_document_gold",
            "no_sealed_test",
            "difficulty_labels_not_invented",
            "no_expansion_without_gold",
        ],
    }
    protocol["fingerprint"] = digest(protocol)
    output.mkdir(parents=True)
    write_new(output / "protocol.json", protocol)
    write_new(
        output / "private-paths.json",
        {s["document_id"]: str(paths[s["document_id"]]) for s in selected},
    )
    print(
        json.dumps(
            {
                "sources": len(selected),
                "pages": sum(len(s["pages"]) for s in selected),
                "anchors": sum(s["gold"]["anchors"] for s in selected),
                "excluded": excluded,
                "fingerprint": protocol["fingerprint"],
            }
        )
    )
    return protocol


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.output)


if __name__ == "__main__":
    sys.exit(main())
