"""One incremental readiness release from frozen evidence. Never a QG certification.

Run: python -m tools.extraction_quality.readiness_release prepare --output <private-dir>
Then annotate admitted Office sources, freeze, verify, or score literal oracle fields.
"""

from __future__ import annotations

import argparse
import copy
import json
import time
import zipfile
from collections import Counter
from pathlib import Path

from pydantic import TypeAdapter

from doclens_ai.eda import corpus_v2 as corpus
from doclens_ai.extraction.fidelity_eval import _observations, _read_sources, score_record
from doclens_ai.extraction.fidelity_gold import fingerprint, load_gold
from doclens_ai.extraction.models import ExtractionResult
from tools.extraction_quality import office_readiness_oracle as oracle
from tools.extraction_quality.readiness_io import (
    ROOT,
    VERSION,
    atomic,
    atomic_bytes,
    cached,
    confined,
    private_root,
)

INVENTORY = "evaluation-output/dataset-readiness-inventory-20261021/run-1.json"
ISOLATION = "evaluation-output/dataset-readiness-closure-20261022/isolation-1.json"
OFFICE = "docs/eda/extraction_corpus_v2_manifest.json"
CONTROLS = "evaluation-output/extraction-v2-20261021/control-manifest-final.json"
ELIGIBILITY = "evaluation-output/qg00-annotation-rights-20261021/eligibility-v2.json"
REFERENCE = "local-evaluation/pdf-dev-reference-20261022-v1"
PDF_NATIVE = "evaluation-output/pdf-native-dev-diagnostic-20261022/run-1/diagnostic.json"
PDF_PROBE = "evaluation-output/pdf-table-source-only-probe-20261022/evaluation.json"
GOLD = "local-evaluation/extraction_fidelity_v1_expanded_approved.jsonl"
STABILIZED = "evaluation-output/stabilization-complete-20261021"


def read(relative: str):
    return corpus.read_json(confined(ROOT, relative), max_bytes=256 * 1024**2)


def rights(existing: dict, admission: dict | None = None) -> dict:
    result = {
        "local_evaluation": existing.get("local_evaluation"),
        "new_annotation": None,
        "training": None,
        "redistribution": None,
        "cloud": None,
        "basis": existing.get("references", []),
        "decision_kind": "reused_existing_scope",
    }
    if admission is not None and admission["disposition"] == "admit":
        if admission["annotation_use"] is not True or admission["adaptation_granted"] is not True:
            raise ValueError("annotation admission has no grant")
        result.update(
            new_annotation=True,
            basis=[ELIGIBILITY, *admission["evidence_refs"]],
            annotation_scope=admission["scope"],
        )
    result["annotation_disposition"] = "ADMIT" if result["new_annotation"] is True else "QUARANTINE"
    return result


def join_population(inventory: dict, isolation: dict, eligibility: dict) -> list[dict]:
    decisions = {c["document_id"]: c for c in eligibility["candidates"]}
    guards = {
        r["sample_id"].removeprefix("e2-")
        if r["sample_id"].startswith("e2-c1-")
        else r["sample_id"]: r
        for r in isolation["rows"]
    }
    rows, seen = [], set()
    for source in inventory["population"]:
        key = source["id"]
        if key in seen or key not in guards:
            raise ValueError("duplicate source or missing isolation record")
        seen.add(key)
        guard = guards[key]
        if guard["source_sha256"] != source["sha256"] or guard["family_id"] != source["family"]:
            raise ValueError("source/family binding mismatch")
        decision = decisions.get(key)
        if decision and decision["source_sha256"] != source["sha256"]:
            raise ValueError("rights source mismatch")
        row = copy.deepcopy(source)
        row.update(
            rights=rights(source["rights"], decision),
            declared_language=source["language"],
            verified_language=["unknown"],
            exposure="legacy_development_exposed",
            split="dev",
            reserved_qa_family=not guard["development_eligible_against_test_families"],
            isolation_evidence=ISOLATION,
            difficulty=source["metadata"],
            gold_origin="historical_single_reviewer_attestation"
            if source["gold"]["extraction"]
            else "NO_EXTRACTION_GOLD",
            independent_gold=False,
            failure_classes=[*source["warnings"], *([source["error"]] if source["error"] else [])],
        )
        rows.append(row)
    if set(guards) != seen:
        raise ValueError("hidden source exclusion")
    return rows


def pdf_items(inventory: list, native: dict, probe: dict) -> list[dict]:
    findings = {f["item_id"]: f for d in native["documents"] for f in d["findings"]}
    correspondences = {}
    for document in probe["documents"]:
        for finding in document["cell_findings"]:
            key = finding.get("reference_item_id")
            if key:
                correspondences.setdefault(key, []).append(finding)
    output, seen = [], set()
    for entry in inventory:
        original = entry["original_proposal"]
        key = entry["item_id"]
        if key in seen or original["item_id"] != key:
            raise ValueError("duplicate or mismatched PDF proposal")
        seen.add(key)
        output.append(
            {
                "item_id": key,
                "source_id": original["source_id"],
                "source_sha256": original["source_sha256"],
                "original_proposal": original,
                "field_admission": entry["field_admission"],
                "native_observation": findings.get(key),
                "source_only_observations": correspondences.get(key, []),
                "observation_tier": "AUTOMATIC_SOURCE_OBSERVATION",
                "suspected_blank": original["kind"] == "cell"
                and original.get("proposed_text") == "",
                "requires_review": [
                    "literal_and_signs",
                    "geometry_and_spans",
                    "header_value_unit_period",
                    "blank_visibility",
                ]
                if original["kind"] == "cell"
                else ["source_semantics"],
                "assisted_decision": None,
                "correction": None,
                "reviewer": None,
                "independent_gold": False,
                "state": "UNRESOLVED",
            }
        )
    return output


def historical_assertions() -> dict:
    """Diagnose saved native observations without changing or reauditing Gold."""
    gold = load_gold(ROOT / GOLD, _read_sources(ROOT / "docs/eda/corpus_v1_manifest.csv"))
    result = []
    for record in gold:
        path = f"{STABILIZED}/pipeline-1/extractions/{record.document_id}.json"
        capture = TypeAdapter(ExtractionResult).validate_python(read(path))
        observations = _observations(capture)
        # Reuse scorer semantics for per-assertion checks; retain each denominator.
        for group in ("anchors", "order_pairs", "table_cells", "table_relationships", "cells"):
            for index, assertion in enumerate(getattr(record, group)):
                selected = record.model_copy(update={group: (assertion,)})
                scores = score_record(selected, capture)["metrics"]
                keys = {
                    "anchors": ("required_text_recall", "provenance"),
                    "order_pairs": ("reading_order",),
                    "table_cells": ("table_cells",),
                    "table_relationships": ("table_relationships",),
                    "cells": ("stored_values", "formulas", "cached_values", "displayed_values"),
                }[group]
                metrics = {k: scores[k] for k in keys}
                failed = any(m["passed"] < m["evaluated"] for m in metrics.values())
                unsupported = any(m["unsupported"] for m in metrics.values())
                classification = "OBSERVATION_MATCH"
                if unsupported:
                    classification = "UNSUPPORTED_DISPLAY_OR_LOCATOR"
                if failed:
                    if group == "anchors":
                        # Capture absence cannot prove absence in the original.
                        present = any(assertion.text in o.text for o in observations)
                        classification = (
                            "LOCATOR_OR_PARSER_MISMATCH" if present else "LOSS_OR_SOURCE_AMBIGUITY"
                        )
                    elif record.document_format == "pdf" and group != "cells":
                        classification = "UNSUPPORTED_NATIVE_TABLE_OR_ORDER"
                    else:
                        classification = "PARSER_OR_LOCATOR_REVIEW_REQUIRED"
                result.append(
                    {
                        "assertion_id": f"{record.document_id}/{group}/{index}",
                        "source_id": record.document_id,
                        "source_sha256": record.source_sha256,
                        "group": group,
                        "assertion": assertion.model_dump(mode="json"),
                        "metrics": metrics,
                        "classification": classification,
                        "capture": path,
                        "capture_sha256": corpus.sha256(ROOT / path),
                        "needs_review": failed or unsupported,
                        "source_reinspection": "OUTSTANDING" if failed or unsupported else None,
                        "reviewer": None,
                    }
                )
    return {
        "scope": "saved_capture_diagnosis_not_new_gold_audit",
        "records": len(gold),
        "assertions": result,
    }


def source_references() -> dict:
    result = {}
    for path, base in (
        (CONTROLS, "local-corpus"),
        (OFFICE, "evaluation-output/extraction-v2-20261021/office-discovery"),
    ):
        for sample in corpus.load(ROOT / path).samples:
            asset = sample.original
            if asset is None:
                raise ValueError("missing registered original")
            key = (
                sample.sample_id.removeprefix("e2-")
                if sample.sample_id.startswith("e2-c1-")
                else sample.sample_id
            )
            result[key] = {
                "path": base + "/" + asset.path,
                "sha256": asset.sha256,
                "size_bytes": asset.size_bytes,
                "format": asset.format,
            }
    return result


def prepare(output: Path) -> dict:
    private_root(output)
    inputs = [
        INVENTORY,
        ISOLATION,
        OFFICE,
        CONTROLS,
        ELIGIBILITY,
        GOLD,
        PDF_NATIVE,
        PDF_PROBE,
        REFERENCE + "/proposal-inventory.json",
        REFERENCE + "/artifact-manifest.json",
    ]
    pins = {p: corpus.sha256(confined(ROOT, p)) for p in inputs}
    code = {
        p.relative_to(ROOT).as_posix(): corpus.sha256(p)
        for p in (
            Path(__file__),
            Path(oracle.__file__),
            ROOT / "tools/extraction_quality/readiness_io.py",
        )
    }
    binding = {"inputs": pins, "code": code}

    def build():
        population = join_population(read(INVENTORY), read(ISOLATION), read(ELIGIBILITY))
        references = source_references()
        for row in population:
            if references[row["id"]]["sha256"] != row["sha256"]:
                raise ValueError("source registry mismatch")
            row["source_reference"] = references[row["id"]]
        items = pdf_items(
            read(REFERENCE + "/proposal-inventory.json"), read(PDF_NATIVE), read(PDF_PROBE)
        )
        if len(population) != 150 or len(items) != 1154:
            raise ValueError("frozen population mismatch")
        return {
            "version": VERSION,
            "binding": binding,
            "population": population,
            "pdf_items": items,
            "historical_assertions": historical_assertions(),
            "sources": references,
            "new_multilingual": [],
            "external_pilots": [],
            "new_sealed_families": [],
            "gates": {
                "QG-00": "NOT_EVALUATED",
                "QG-01": "NOT_EVALUATED",
                "independent_test": "TEST_NOT_READY",
                "five_model_evaluation": "BLOCKED",
            },
        }

    value, hit = cached(output, "incremental-ledger", binding, build)
    summary = summarize(value)
    atomic(output / "coverage.json", summary)
    return {"cache_hit": hit, **summary}


def summarize(value: dict) -> dict:
    rows, items = value["population"], value["pdf_items"]
    historical = value["historical_assertions"]["assertions"]
    return {
        "version": VERSION,
        "attempted_documents": len(rows),
        "formats": dict(Counter(r["format"] for r in rows)),
        "outcomes": dict(Counter(r["status"] for r in rows)),
        "partial_legacy_gold_documents": sum(r["gold"]["extraction"] for r in rows),
        "missing_legacy_gold_documents": sum(not r["gold"]["extraction"] for r in rows),
        "annotation_rights": dict(Counter(r["rights"]["annotation_disposition"] for r in rows)),
        "reserved_qa_family_sources": sum(r["reserved_qa_family"] for r in rows),
        "pdf_items": len(items),
        "pdf_cells": sum(i["original_proposal"]["kind"] == "cell" for i in items),
        "pdf_suspected_blanks": sum(i["suspected_blank"] for i in items),
        "pdf_pending_item_decisions": sum(i["assisted_decision"] is None for i in items),
        "historical_assertions": len(historical),
        "historical_outstanding": sum(i["needs_review"] for i in historical),
        "historical_classifications": dict(Counter(i["classification"] for i in historical)),
        "gates": value["gates"],
        "independent_new_gold": 0,
    }


def validate_continuation(output: Path, effective: dict) -> None:
    """Bind rights changes and partitions to the frozen parent; no legal attestation."""
    proof_path = output / "parent-proof.json"
    if not proof_path.exists():
        return  # Historical v1 layout remains readable.
    proof = corpus.read_json(proof_path)
    parent = confined(ROOT, proof["parent_root"])
    if corpus.sha256(parent / "RELEASE.json") != proof["manifest_sha256"]:
        raise ValueError("parent release identity mismatch")
    verify(parent, code_snapshot=output / "parent-code")
    previous = {
        r["id"]: r
        for r in corpus.read_json(parent / "effective-matrix.json", max_bytes=256 * 1024**2)[
            "population"
        ]
    }
    decisions = corpus.read_json(output / "rights-decisions-v2.json")["decisions"]
    indexed = {}
    for decision in decisions:
        key = decision["source_id"]
        if (
            key in indexed
            or decision["reviewer"] is not None
            or decision["human_reviewed"] is not False
        ):
            raise ValueError("duplicate rights identity or spoofed review")
        indexed[key] = decision
    rows = effective["population"]
    if not set(previous).issubset({r["id"] for r in rows}):
        raise ValueError("parent source omitted")
    hashes = set()
    samples = []
    for row in rows:
        key = row["id"]
        if row["sha256"] in hashes:
            raise ValueError("duplicate original bytes counted twice")
        hashes.add(row["sha256"])
        ref = row["source_reference"]
        corpus.asset_path(ROOT, corpus.Asset.model_validate(ref))
        if ref["sha256"] != row["sha256"]:
            raise ValueError("original source drift")
        old = previous.get(key)
        if old and (row["sha256"], ref) != (old["sha256"], old["source_reference"]):
            raise ValueError("frozen parent source rewritten")
        if row.get("independent_gold") is not False:
            raise ValueError("unreviewed release cannot promote independent Gold")
        if row["split"] not in {"dev", "sealed_candidate"}:
            raise ValueError("approved test requires authentic independent review")
        if row["split"] == "sealed_candidate" and old:
            raise ValueError("development source cannot become new sealed candidate")
        samples.append(
            corpus.Sample(
                sample_id=key if key.startswith("e2-") else "e2-" + key,
                dataset="readiness-release",
                release="20261023-v2",
                revision="v2",
                source_record_id=key,
                cohort="pilot",
                disposition="admitted",
                reasons=(),
                original=corpus.Asset.model_validate(ref),
                rights=corpus.Rights(
                    dataset_license=None,
                    original_license=None,
                    local_evaluation=row["rights"].get("local_evaluation"),
                    annotation_use=row["rights"].get("new_annotation"),
                    redistribution=row["rights"].get("redistribution"),
                    references=("source-specific-rights-ledger",),
                    sensitivity="public",
                ),
                languages=("unknown",),
                document_type=row["format"],
                difficulty=("unreviewed",),
                family_id=row["family"],
                related_families=tuple(row.get("related_families", [])),
                near_duplicate_group=row.get("near_duplicate_group"),
                normalized_text_sha256=row.get("normalized_text_sha256"),
                family_review="unknown",
                split="dev",
                publicly_exposed=False,
            )
        )
        for scope in ("local_evaluation", "new_annotation", "training", "redistribution", "cloud"):
            if row["rights"].get(scope) is not True or (old and old["rights"].get(scope) is True):
                continue
            decision = indexed.get(key)
            if (
                decision is None
                or decision["source_sha256"] != row["sha256"]
                or decision["disposition"] != "ADMIT"
                or decision["scopes"].get(scope) is not True
                or decision["grants"].get(scope) is not True
                or decision["basis_kind"]
                not in {
                    "source_document_OGL_grant",
                    "publisher_page_OGL_grant",
                    "official_statistics_reuse",
                    "publisher_CC_license",
                }
                or not decision["evidence"]
            ):
                raise ValueError("illegal rights promotion")
            for evidence in decision["evidence"]:
                if corpus.sha256(confined(ROOT, evidence["path"])) != evidence["sha256"]:
                    raise ValueError("rights evidence drift")
    components = corpus.family_components(tuple(samples))
    families = {}
    reserved_sha = set(read(ISOLATION)["reserved_source_sha256"])
    reserved_components = {
        components[s.sample_id] for s in samples if s.original.sha256 in reserved_sha
    }
    for row, sample in zip(rows, samples, strict=True):
        component = components[sample.sample_id]
        families.setdefault(component, set()).add(row["split"])
        if bool(row.get("reserved_qa_family")) != (component in reserved_components):
            raise ValueError("QA family admission mismatch")
    if any(len(splits) > 1 for splits in families.values()):
        raise ValueError("family crosses development/candidate partition")


def freeze(output: Path) -> dict:
    private_root(output)
    if (output / "RELEASE.json").exists():
        raise ValueError("immutable release already exists; verify or create a new revision")
    path = output / "incremental-ledger.json"
    value = corpus.read_json(path, max_bytes=256 * 1024**2)
    for relative, digest in value["binding"]["inputs"].items():
        if corpus.sha256(confined(ROOT, relative)) != digest:
            raise ValueError("input drift")
    protected = dict(value["binding"]["inputs"])
    protected.update({r["path"]: r["sha256"] for r in value["sources"].values()})
    effective_path = output / "effective-matrix.json"
    effective = corpus.read_json(effective_path, max_bytes=256 * 1024**2)
    validate_continuation(output, effective)
    ids = [r["id"] for r in effective["population"]]
    if len(ids) != len(set(ids)) or not set(value["sources"]).issubset(ids):
        raise ValueError("release denominator mismatch")
    for row in effective["population"]:
        ref = row["source_reference"]
        if ref["sha256"] != row["sha256"]:
            raise ValueError("effective matrix source mismatch")
        protected[ref["path"]] = ref["sha256"]
    for relative, digest in read(ISOLATION)["inputs_sha256"].items():
        protected[relative.replace("\\", "/")] = digest
    for relative, digest in read(REFERENCE + "/artifact-manifest.json").items():
        protected[REFERENCE + "/" + relative] = digest
    protected[REFERENCE + "/COMPLETE.json"] = corpus.sha256(ROOT / REFERENCE / "COMPLETE.json")
    for relative, digest in protected.items():
        if corpus.sha256(confined(ROOT, relative)) != digest:
            raise ValueError("frozen source/Gold/reference drift")
    code_paths = [
        Path(__file__),
        Path(oracle.__file__),
        ROOT / "tools/extraction_quality/readiness_io.py",
        ROOT / "tools/extraction_quality/readiness_evaluator.py",
        ROOT / "docs/eda/readiness_predictions_v1_schema.json",
    ]
    code_paths += [
        ROOT / p
        for p in (
            "tools/extraction_quality/readiness_source_checks.py",
            "tools/extraction_quality/readiness_pdf_metrics.py",
            "tools/extraction_quality/comparison_v2.py",
            "tools/extraction_quality/extraction_v2.py",
            "tools/extraction_quality/pdf_cell_recovery.py",
            "src/doclens_ai/eda/corpus_v2.py",
            "src/doclens_ai/eda/dataset_adapters_v2.py",
            "src/doclens_ai/extraction/evidence_v2.py",
            "src/doclens_ai/extraction/fidelity_gold.py",
        )
        if (ROOT / p).is_file()
    ]
    final_code = {p.relative_to(ROOT).as_posix(): corpus.sha256(p) for p in code_paths}
    for relative, digest in final_code.items():
        destination = confined(output, "validation-code/" + relative)
        if destination.exists() and corpus.sha256(destination) != digest:
            raise ValueError("code archive changed; use a new release revision")
        if not destination.exists():
            atomic_bytes(destination, confined(ROOT, relative).read_bytes())
    files = {}
    for candidate in output.rglob("*"):
        corpus.no_links(candidate)
        if (
            candidate.is_file()
            and candidate.name != "RELEASE.json"
            and not candidate.name.endswith(".tmp")
        ):
            corpus.no_links(candidate)
            files[candidate.relative_to(output).as_posix()] = corpus.sha256(candidate)
    protected.update(final_code)
    release = {
        "version": VERSION,
        "artifact_sha256": files,
        "protected_sha256": protected,
        "gates": value["gates"],
        "datasheet": effective.get("datasheet", "docs/eda/extraction_data_readiness_20261023.md"),
        "tiers": [
            "HISTORICAL_ATTESTATION",
            "SOURCE_NATIVE_ORACLE",
            "ASSISTED_PROPOSAL",
            "AUTOMATIC_SOURCE_OBSERVATION",
        ],
        "independent_gold": False,
        "attempted_population": len(ids),
        "final_code_sha256": final_code,
        "code_archive": "validation-code",
    }
    if (output / "parent-proof.json").exists():
        parent_proof = corpus.read_json(output / "parent-proof.json")
        release["parent_release"] = {
            "root": parent_proof["parent_root"],
            "manifest_sha256": parent_proof["manifest_sha256"],
            "code_archive": "parent-code",
        }
        release["version"] = "extraction-readiness-20261023-v2"
    release["fingerprint"] = fingerprint(release)
    destination = output / "RELEASE.json"
    if destination.exists():
        if corpus.read_json(destination) != release:
            raise ValueError("immutable release exists with different artifacts")
    else:
        atomic(destination, release)
    return {
        "frozen_files": len(files),
        "protected_files": len(protected),
        "fingerprint": release["fingerprint"],
        "gates": release["gates"],
    }


def verify(output: Path, *, code_snapshot: Path | None = None) -> dict:
    private_root(output)
    release = corpus.read_json(output / "RELEASE.json")
    without = {k: v for k, v in release.items() if k != "fingerprint"}
    if fingerprint(without) != release["fingerprint"]:
        raise ValueError("release fingerprint mismatch")
    actual = set()
    for candidate in output.rglob("*"):
        corpus.no_links(candidate)
        if (
            candidate.is_file()
            and candidate.name != "RELEASE.json"
            and not candidate.name.endswith(".tmp")
        ):
            actual.add(candidate.relative_to(output).as_posix())
    if actual != set(release["artifact_sha256"]):
        raise ValueError("release artifact inventory drift")
    archive = code_snapshot
    if archive is None and release.get("code_archive"):
        archive = confined(output, release["code_archive"])
    for relative, digest in release["protected_sha256"].items():
        root = (
            archive
            if archive is not None and relative in release.get("final_code_sha256", {})
            else ROOT
        )
        if corpus.sha256(confined(root, relative)) != digest:
            raise ValueError("protected input drift")
    for relative, digest in release["artifact_sha256"].items():
        if corpus.sha256(confined(output, relative)) != digest:
            raise ValueError("release artifact drift")
    if release.get("parent_release"):
        parent = release["parent_release"]
        path = confined(ROOT, parent["root"])
        if corpus.sha256(path / "RELEASE.json") != parent["manifest_sha256"]:
            raise ValueError("parent manifest drift")
        verify(path, code_snapshot=confined(output, parent["code_archive"]))
    return {"integrity": "PASS", "gates": release["gates"], "fingerprint": release["fingerprint"]}


def verify_runtime(output: Path) -> dict:
    """Integrity may use historical archives; scoring must execute the pinned code."""
    result = verify(output)
    manifest = corpus.read_json(output / "RELEASE.json")
    for relative, digest in manifest.get("final_code_sha256", {}).items():
        if corpus.sha256(confined(ROOT, relative)) != digest:
            raise ValueError("active scoring code differs from frozen release")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "freeze", "verify"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--code-snapshot", type=Path)
    args = parser.parse_args()
    started = time.perf_counter()
    try:
        result = (
            verify(args.output, code_snapshot=args.code_snapshot)
            if args.mode == "verify"
            else {"prepare": prepare, "freeze": freeze}[args.mode](args.output)
        )
        print(json.dumps({**result, "seconds": time.perf_counter() - started}, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        print(json.dumps({"status": "BLOCKED", "reason": type(error).__name__}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
