"""Public synthetic documentary decisions; never real permissions or reviewer evidence."""

from __future__ import annotations

import copy
import csv
import json
from dataclasses import replace

import pytest

from doclens_ai.extraction.fidelity_gold import fingerprint
from tests.unit.test_pdf_review_workbench import fixture as workbench_fixture
from tools.extraction_quality import pdf_review_eligibility as rights
from tools.extraction_quality import pdf_review_validation as validation
from tools.extraction_quality import pdf_review_workbench as workbench
from tools.extraction_quality import pdf_table_review_packet as packet


def fixture(tmp_path):
    old, _ = workbench_fixture(tmp_path, cohort=True)
    with old.manifest.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    for row in rows:
        row.update(
            source_page_url=f"https://example.invalid/{row['document_id']}",
            download_url=f"https://example.invalid/{row['document_id']}.pdf",
        )
    with old.manifest.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=[*fields, "source_page_url", "download_url"])
        writer.writeheader()
        writer.writerows(rows)
    expected = replace(old.expected, manifest_sha256=packet.sha(old.manifest))
    _, paths, records, _ = packet.preflight(
        old.manifest, old.corpus, old.gold, expected, allow_synthetic=True
    )
    base = old.root / "evaluation-output/rights"
    base.mkdir()
    evidence = {}
    for key, text, url in (
        ("grant", "PUBLIC SYNTHETIC LICENSE FIXTURE", rights.OGL),
        ("intake", "PUBLIC SYNTHETIC OLD INTAKE", None),
        ("inspection", "PUBLIC SYNTHETIC DOCUMENT INSPECTION", None),
        ("offer", f"{rights.OGL} {rows[0]['download_url']}", rows[0]["source_page_url"]),
    ):
        target = base / f"{key}.txt"
        target.write_text(text, encoding="utf-8")
        evidence[key] = dict(
            path=target.name,
            sha256=packet.sha(target),
            url=url,
            locator="PUBLIC SYNTHETIC FIXTURE ONLY",
        )
    candidates = []
    for index, (row, record) in enumerate(zip(rows, records, strict=True)):
        candidates.append(
            dict(
                document_id=record.document_id,
                disposition="admit" if index == 0 else "blocked",
                reasons=[] if index == 0 else ["THIRD_PARTY_RIGHTS_UNRESOLVED"],
                source_sha256=record.source_sha256,
                source_size_bytes=record.source_size_bytes,
                source_page_url=row["source_page_url"],
                download_url=row["download_url"],
                publisher="PUBLIC SYNTHETIC PROVIDER",
                family_id="f-" + fingerprint(row["source_page_url"])[:24],
                pages=validation.original_pages(paths[record.document_id]),
                evidence_refs=["grant", "offer", "inspection"],
                document_inspection_ref="inspection",
                license_offer_ref="offer",
                license_url=rights.OGL,
                annotation_use=index == 0,
                adaptation_granted=True,
                third_party_rights="none_identified" if index == 0 else "unresolved",
                exclusions=[],
                sensitivity="public",
                scope="new_source_annotations_local_dev",
                attribution=rights.ATTRIBUTION,
                existing_annotation_reuse_authorized=False,
                annotation_provenance="Synthetic fixtures only; never independent Gold",
                rationale="PUBLIC SYNTHETIC DECISION",
            )
        )
    value = dict(
        version="pdf-review-eligibility-v1",
        revision="public-synthetic-v1",
        supersedes=evidence.pop("intake"),
        manifest_sha256=packet.sha(old.manifest),
        gold_sha256=packet.sha(old.gold),
        license_grant_ref="grant",
        evidence=evidence,
        candidates=candidates,
        split="dev",
        publicly_exposed=True,
        independent_gold="NOT_EVALUATED",
        decision_basis="documentary_analysis_not_reviewer_attestation",
    )
    path = base / "eligibility.json"
    packet.write_json(path, value)
    return old, expected, path, value


def build(data, name="authorized"):
    old, expected, path, _ = data
    output = old.root / f"evaluation-output/{name}"
    summary = packet.generate(
        old.manifest,
        old.corpus,
        old.gold,
        output,
        root=old.root,
        expected=expected,
        allow_synthetic=True,
        eligibility=path,
    )
    return output, summary


def test_subset_build_resume_blinding_and_determinism(tmp_path):
    data = fixture(tmp_path)
    old, expected, path, _ = data
    first, a = build(data)
    second, b = build(data, "repeat")
    assert a == b
    assert {p.relative_to(first): packet.sha(p) for p in first.rglob("*") if p.is_file()} == {
        p.relative_to(second): packet.sha(p) for p in second.rglob("*") if p.is_file()
    }
    assert a["prepared_documents"] == 1 and a["excluded_documents"] == 1
    assert a["eligibility"]["blocked"] == 1
    assert not (first / "sources/c1-0002.pdf").exists()
    workspace = old.root / "evaluation-output/authorized-workspace"
    app = workbench.Workbench(
        old.manifest,
        old.corpus,
        old.gold,
        first,
        workspace,
        root=old.root,
        expected=expected,
        allow_synthetic=True,
        eligibility=path,
    )
    assert set(app.records) == {"c1-0001"}
    draft = app.view()["documents"]["c1-0001"]["draft"]
    assert draft["tables"] == [] and all(v is None for v in draft["reviewer"].values())
    with pytest.raises(ValueError):
        app.legacy("c1-0001")
    with pytest.raises(ValueError):
        app.pdf("c1-0002")
    with pytest.raises(ValueError):
        app.update(
            "freeze",
            dict(revision=app.view()["revision"], document_id="c1-0001", confirm_freeze=True),
        )
    resumed = workbench.Workbench(
        old.manifest,
        old.corpus,
        old.gold,
        first,
        workspace,
        resume=True,
        root=old.root,
        expected=expected,
        allow_synthetic=True,
        eligibility=path,
    )
    assert resumed.view() == app.view()
    summary, documents = validation.validate_workflow(
        old.manifest,
        old.corpus,
        old.gold,
        first / "review",
        app.scopes,
        "synthetic-check",
        expected=expected,
        allow_synthetic=True,
        eligibility=path,
    )
    assert summary["execution"] == "BLOCKED" and not documents
    assert summary["independent_reviews_completed"] == 0 and not summary["export_ready"]
    with pytest.raises(ValueError):
        workbench.Workbench(
            old.manifest,
            old.corpus,
            old.gold,
            first,
            workspace,
            resume=True,
            root=old.root,
            expected=expected,
            allow_synthetic=True,
        )


@pytest.mark.parametrize(
    "kind",
    [
        "null_authorization",
        "false_adaptation",
        "different_license",
        "third_party",
        "third_party_unsupported_grant",
        "exclusion",
        "sensitivity",
        "generic_link",
        "wrong_offer",
        "missing_inspection",
        "missing_grant",
        "missing_evidence",
        "evidence_drift",
        "wrong_sha",
        "wrong_size",
        "wrong_page",
        "wrong_family",
        "wrong_source_url",
        "duplicate",
        "hidden_candidate",
        "fabricated_gold",
        "reuse_legacy_annotations",
        "sealed_test",
        "no_eligible",
        "path_escape",
    ],
)
def test_unresolved_or_misbound_rights_fail_closed(tmp_path, kind):
    data = fixture(tmp_path)
    _, _, path, value = data
    candidate = value["candidates"][0]
    if kind == "null_authorization":
        candidate["annotation_use"] = None
    elif kind == "false_adaptation":
        candidate["adaptation_granted"] = False
    elif kind == "different_license":
        candidate["license_url"] = "https://example.invalid/restricted"
    elif kind == "third_party":
        candidate["third_party_rights"] = "unresolved"
    elif kind == "third_party_unsupported_grant":
        candidate["third_party_rights"] = "authorized"
    elif kind == "exclusion":
        candidate["exclusions"] = ["REPRODUCTION_REQUIRES_LICENSE"]
    elif kind == "sensitivity":
        candidate["sensitivity"] = "unresolved"
    elif kind == "generic_link":
        target = path.parent / "offer.txt"
        target.write_text(rights.OGL, encoding="utf-8")
        value["evidence"]["offer"]["sha256"] = packet.sha(target)
    elif kind == "wrong_offer":
        candidate["license_offer_ref"] = "grant"
    elif kind == "missing_inspection":
        candidate["document_inspection_ref"] = None
    elif kind == "missing_grant":
        value["license_grant_ref"] = "absent"
    elif kind == "missing_evidence":
        (path.parent / "inspection.txt").unlink()
    elif kind == "evidence_drift":
        (path.parent / "inspection.txt").write_text("changed")
    elif kind == "wrong_sha":
        candidate["source_sha256"] = "0" * 64
    elif kind == "wrong_size":
        candidate["source_size_bytes"] += 1
    elif kind == "wrong_page":
        candidate["pages"][0]["page_number"] = 2
    elif kind == "wrong_family":
        candidate["family_id"] = value["candidates"][1]["family_id"]
    elif kind == "wrong_source_url":
        candidate["source_page_url"] += "/unrelated"
    elif kind == "duplicate":
        value["candidates"].append(copy.deepcopy(candidate))
    elif kind == "hidden_candidate":
        value["candidates"].pop()
    elif kind == "fabricated_gold":
        value["independent_gold"] = "PASS"
    elif kind == "reuse_legacy_annotations":
        candidate["existing_annotation_reuse_authorized"] = True
    elif kind == "sealed_test":
        value["split"] = "test"
    elif kind == "no_eligible":
        candidate.update(disposition="blocked", reasons=["UNRESOLVED"])
    elif kind == "path_escape":
        value["evidence"]["inspection"]["path"] = "../inspection.txt"
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises((ValueError, OSError)):
        build(data)
    assert not (path.parent.parent / "authorized/COMPLETE.json").exists()


def test_rights_drift_prevents_resume(tmp_path):
    data = fixture(tmp_path)
    old, expected, path, value = data
    output, _ = build(data)
    value["revision"] = "different-decision"
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError):
        workbench.Workbench(
            old.manifest,
            old.corpus,
            old.gold,
            output,
            old.root / "evaluation-output/changed-workspace",
            root=old.root,
            expected=expected,
            allow_synthetic=True,
            eligibility=path,
        )


def test_duplicate_json_permission_key_rejected(tmp_path):
    data = fixture(tmp_path)
    path = data[2]
    text = path.read_text(encoding="utf-8")
    path.write_text(
        text.replace('"annotation_use": true', '"annotation_use": false, "annotation_use": true'),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate JSON key"):
        build(data)
