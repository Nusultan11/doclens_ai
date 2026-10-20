"""Completed synthetic worksheet contracts; no real reviewer decisions are written."""

from __future__ import annotations

import copy
import json

import pytest

from doclens_ai.extraction.evidence_v2 import Scope
from tests.unit.test_ml28_evidence import fixture as evidence_fixture
from tests.unit.test_pdf_table_review_packet import fixture as packet_fixture
from tools.extraction_quality import pdf_review_validation as validation
from tools.extraction_quality import pdf_table_review_packet as packet


def completed(tmp_path):
    data = packet_fixture(tmp_path)
    _, paths, records, _ = packet.preflight(*data[1:4], data[4], allow_synthetic=True)
    record = records[0]
    pages = validation.original_pages(paths[record.document_id])
    draft, _, adjudication = packet.worksheets(record, pages)
    _, gold, _, _ = evidence_fixture()
    reviewer = draft["reviewer"]
    reviewer.update(
        id="fixture-author",
        reviewed_on="2026-01-01",
        kind="synthetic_fixture",
        independent_of_original_annotator=True,
        parser_outputs_seen=False,
        legacy_assertions_seen_before_draft=False,
        prior_exposure_description="fixture",
        viewer_tool="fixture",
        viewer_version="1",
        render_settings="native points",
        annotation_authorized=True,
        annotation_permission_reference="synthetic-public-fixture",
    )
    draft["state"] = "REVIEWED"
    draft["completion"].update(all_pages_inspected=True, all_tables_inventoried=True)
    draft["family_language"] = {
        "family_id": "fixture-family",
        "languages": ["en"],
        "split": "dev",
        "basis": "independently authored fixture",
    }
    draft["pages"][0].update(
        table_presence=True,
        regions=[
            {
                "region_id": "region-1",
                "table_id": "table-1",
                "bbox_pdf_user_space_points": [0.0, 0.0, 100.0, 100.0],
            }
        ],
    )
    table = copy.deepcopy(draft["table_template"])
    table.update(
        review_table_id="table-1",
        page_number=1,
        section_id="section-1",
        bbox_pdf_user_space_points=[0.0, 0.0, 100.0, 100.0],
        coordinate_basis="pdf_user_space_unrotated",
        row_count=3,
        column_count=2,
        structure_complete=True,
        merged_or_ambiguous=False,
        evidence_reference="fixture",
    )
    for cell in gold.tables[0].cells:
        raw = copy.deepcopy(draft["cell_template"])
        raw.update(
            review_cell_id=cell.cell_id,
            row=cell.row,
            column=cell.column,
            row_span=cell.row_span,
            column_span=cell.column_span,
            literal_text=cell.literal,
            bbox_pdf_user_space_points=list(cell.locator.bbox),
            header_role=cell.role,
            evidence_reference="fixture",
            uncertain=False,
        )
        raw["value_unit_period_links"] = [
            [r.right, r.kind]
            for r in gold.tables[0].relations
            if r.left == cell.cell_id and r.kind in {"unit", "period"}
        ]
        table["cells"].append(raw)
    for rel in gold.tables[0].relations:
        table["relationships"].append(
            {
                "left_review_cell_id": rel.left,
                "right_review_cell_id": rel.right,
                "relationship": rel.kind,
                "visual_basis": rel.evidence_note,
                "uncertain": False,
            }
        )
    draft["tables"] = [table]
    draft["text_anchors"] = [
        {
            "anchor_id": a.anchor_id,
            "literal": a.text,
            "occurrence": a.occurrence,
            "category": "text",
            "locator": {
                "page": 1,
                "bbox": [0.0, 0.0, 10.0, 10.0],
                "coordinate_basis": "pdf_user_space_unrotated",
            },
        }
        for a in record.anchors
    ]
    draft["order_pairs"] = [[p.before, p.after] for p in record.order_pairs]
    draft["completion"]["signed_review_fingerprint"] = validation.draft_fingerprint(draft)
    adjudication.update(
        state="ADJUDICATED",
        ready_for_separate_gold_revision=True,
        independent_draft_fingerprint_before_legacy_comparison=validation.draft_fingerprint(draft),
    )
    for item in adjudication["assertion_decisions"] + adjudication["source_region_decisions"]:
        item.update(
            state="RESOLVED",
            decision="confirm",
            reviewer_id="fixture-author",
            reviewed_on="2026-01-02",
            rationale="Synthetic oracle decision",
            original_page_evidence=[
                {
                    "source_sha256": record.source_sha256,
                    "page_number": 1,
                    "bbox_pdf_user_space_points": [0.0, 0.0, 10.0, 10.0],
                    "coordinate_basis": "pdf_user_space_unrotated",
                    "review_evidence_revision": "fixture-1",
                }
            ],
        )
        if "legacy_region_ref" in item:
            item["independent_region_ref"] = "region-1"
        else:
            kind, index = item["legacy_assertion_ref"].split(":")
            if kind == "anchor":
                item["independent_anchor_id"] = record.anchors[int(index)].anchor_id
            elif kind == "order":
                item["independent_order_index"] = int(index)
            elif kind == "cell_span":
                item.update(
                    decision="revise",
                    proposed_correction="synthetic alternate cell",
                    independent_cell_ref={"table_id": "table-1", "cell_id": "value"},
                )
            else:
                item.update(
                    decision="revise",
                    proposed_correction="synthetic alternate relation",
                    independent_relation_ref={"table_id": "table-1", "index": 0},
                )
    scope = Scope(
        workspace_id="fixture-workspace",
        document_id=record.document_id,
        version_id="fixture-version",
        raw_sha256=record.source_sha256,
    )
    return data, draft, adjudication, record, pages, scope


def validate(parts, *, allow_synthetic=True):
    _, draft, adjudication, record, pages, scope = parts
    return validation.validate_document(
        draft, adjudication, record, pages, scope, "fixture-v2", allow_synthetic=allow_synthetic
    )


def resign(parts):
    parts[1]["completion"]["signed_review_fingerprint"] = validation.draft_fingerprint(parts[1])
    parts[2]["independent_draft_fingerprint_before_legacy_comparison"] = (
        validation.draft_fingerprint(parts[1])
    )


def test_completed_synthetic_workflow_is_deterministic_and_not_real_gold(tmp_path):
    parts = completed(tmp_path)
    result = validate(parts)
    assert validate(parts) == result and result.review.kind == "synthetic_fixture"
    assert len(result.tables[0].cells) == 5 and len(result.text_anchors) == 2
    with pytest.raises(packet.PacketError, match="Synthetic"):
        validate(parts, allow_synthetic=False)
    assert parts[0][3].read_bytes()  # legacy input remains untouched


@pytest.mark.parametrize(
    "case",
    [
        "unresolved",
        "missing",
        "duplicate",
        "draft_drift",
        "page_drift",
        "sha_drift",
        "bbox",
        "exposed",
        "machine",
        "uncertain",
        "disagreement",
        "signature",
        "future",
        "missing_family",
        "semantic_link",
        "span",
        "ambiguous",
        "unauthorized_annotation",
    ],
)
def test_incomplete_or_disputed_review_cannot_promote(tmp_path, case):
    parts = completed(tmp_path)
    _, draft, adjudication, _, _, _ = parts
    if case == "unresolved":
        adjudication["assertion_decisions"][0]["state"] = "UNRESOLVED"
    elif case == "missing":
        adjudication["assertion_decisions"].pop()
    elif case == "duplicate":
        adjudication["assertion_decisions"][-1] = adjudication["assertion_decisions"][0]
    elif case == "draft_drift":
        draft["tables"][0]["cells"][0]["literal_text"] = "changed after signing"
    elif case == "page_drift":
        draft["pages"][0]["rotation"] = 90
        resign(parts)
    elif case == "sha_drift":
        adjudication["assertion_decisions"][0]["original_page_evidence"][0]["source_sha256"] = (
            "0" * 64
        )
    elif case == "bbox":
        adjudication["assertion_decisions"][0]["original_page_evidence"][0][
            "bbox_pdf_user_space_points"
        ] = [0.0, 0.0, 5000.0, 5000.0]
    elif case == "exposed":
        draft["reviewer"]["parser_outputs_seen"] = True
        resign(parts)
    elif case == "machine":
        draft["reviewer"]["id"] = "Codex"
        resign(parts)
    elif case == "uncertain":
        draft["tables"][0]["cells"][0]["uncertain"] = True
        resign(parts)
    elif case == "disagreement":
        adjudication["reviewer_disagreements"] = [{"state": "UNRESOLVED"}]
    elif case == "signature":
        draft["completion"]["signed_review_fingerprint"] = "0" * 64
    elif case == "future":
        adjudication["assertion_decisions"][0]["reviewed_on"] = "2999-01-01"
    elif case == "missing_family":
        draft["family_language"]["basis"] = None
        resign(parts)
    elif case == "semantic_link":
        draft["tables"][0]["cells"][2]["value_unit_period_links"] = []
        resign(parts)
    elif case == "span":
        draft["tables"][0]["cells"][0]["column_span"] = 3
        resign(parts)
    elif case == "unauthorized_annotation":
        draft["reviewer"]["annotation_authorized"] = False
        resign(parts)
    else:
        draft["tables"][0]["merged_or_ambiguous"] = True
        resign(parts)
    with pytest.raises((ValueError, KeyError, TypeError)):
        validate(parts)


def test_full_population_validation_keeps_unresolved_explicit(tmp_path):
    data = packet_fixture(tmp_path)
    _, _, records, _ = packet.preflight(*data[1:4], data[4], allow_synthetic=True)
    r = records[0]
    scopes = {
        r.document_id: Scope(
            workspace_id="fixture",
            document_id=r.document_id,
            version_id="v1",
            raw_sha256=r.source_sha256,
        )
    }
    summary, documents = validation.validate_workflow(
        *data[1:4], data[0] / "missing-review", scopes, "v2", expected=data[4], allow_synthetic=True
    )
    assert documents == () and not summary["export_ready"]
    assert summary["qg_00"] == summary["qg_01"] == "NOT_EVALUATED"
    assert len(summary["discrepancies"]) == 1
    assert summary["totals"]["unresolved_assertions"] == 6


def test_completed_workflow_and_frozen_bytes(tmp_path):
    parts = completed(tmp_path)
    data, draft, adjudication, record, _, scope = parts
    review = data[0] / "review"
    folder = review / record.document_id
    folder.mkdir(parents=True)
    for name, value in (("independent.json", draft), ("adjudication.json", adjudication)):
        (folder / name).write_text(json.dumps(value), encoding="utf-8")
    before = [p.read_bytes() for p in (data[1], data[3], data[5])]
    first = validation.validate_workflow(
        *data[1:4],
        review,
        {record.document_id: scope},
        "v2",
        expected=data[4],
        allow_synthetic=True,
    )
    second = validation.validate_workflow(
        *data[1:4],
        review,
        {record.document_id: scope},
        "v2",
        expected=data[4],
        allow_synthetic=True,
    )
    assert first == second and first[0]["export_ready"] and len(first[1]) == 1
    assert before == [p.read_bytes() for p in (data[1], data[3], data[5])]


def test_sanitized_cli_refuses_export_and_does_not_echo_inputs(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.argv",
        [
            "validate",
            "--manifest",
            "private-path",
            "--corpus",
            "raw",
            "--gold",
            "private-gold",
            "--review-dir",
            "review",
            "--scopes",
            "scope",
            "--revision",
            "v2",
            "--output",
            str(tmp_path / "public-output"),
            "--export",
        ],
    )
    assert validation.main() == 2
    output = capsys.readouterr().out
    assert "BLOCKED" in output and "private" not in output.replace("private output", "")
    assert not (tmp_path / "public-output").exists()
