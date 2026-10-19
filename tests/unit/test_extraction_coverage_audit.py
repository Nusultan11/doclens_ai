"""Synthetic metadata/Gold/captures only; no real corpus or model runtime."""

from __future__ import annotations

import json
import sys
import zipfile
from dataclasses import replace

import pytest

from doclens_ai.extraction.fidelity_gold import FidelityRecord, fingerprint
from doclens_ai.extraction.models import (
    DocumentFormat,
    ExtractionResult,
    ExtractionStatus,
    SourceLocation,
    SpreadsheetCell,
    SpreadsheetSheet,
    TextBlock,
)
from tools.extraction_quality import coverage_audit as audit


def fixture(fmt="pdf", number=1, *, region="body", text="Synthetic evidence 007.50"):
    identity = f"c1-{number:04d}"
    locator = {"region": region}
    if fmt == "pdf":
        locator["page_number"] = 1
    elif fmt == "docx":
        locator["block_index" if region == "body" else "part_index"] = 0
    else:
        locator.update(sheet_index=0, cell_coordinate="A1")
    data = {
        "schema_version": "1.0",
        "dataset_revision": "corpus-v1-fidelity-v1",
        "dataset_kind": "synthetic",
        "review_basis": "synthetic_fixture",
        "document_id": identity,
        "source_sha256": "a" * 64,
        "source_size_bytes": 100,
        "document_format": fmt,
        "review_status": "reviewed",
        "reviewer_count": 1,
        "reviewed_on": "2026-01-01",
        "anchors": [{"anchor_id": "a1", "text": text, "source": locator}],
        "order_pairs": [],
        "table_cells": [],
        "table_relationships": [],
        "cells": [],
    }
    record = FidelityRecord.model_validate_json(json.dumps(data))
    source = SourceLocation(
        **{k: v for k, v in locator.items() if k not in ("region", "part_index")}
    )
    result = ExtractionResult("1.0", DocumentFormat(fmt), ExtractionStatus.SUCCESS, "a" * 64, 100)
    if fmt == "xlsx":
        cell = SpreadsheetCell("A1", 0, 0, text, None, None, "s", source)
        result = replace(
            result, sheets=(SpreadsheetSheet(0, "Synthetic sheet", "visible", (cell,), (), ()),)
        )
    else:
        result = replace(result, blocks=(TextBlock(0, text, source),))
    row = {
        "document_id": identity,
        "format": fmt,
        "status": "success",
        "sha256": str(number),
        "features": {},
        "language": "en",
    }
    return row, record, result


def test_empty_labels_are_not_perfect():
    report = audit.build_audit([], [], {})
    metric = report["reviewed"]["metrics"]["required_text_recall"]
    assert metric["label_total"] == metric["evaluated"] == 0
    assert metric["score"] is None and metric["status"] == "NOT_EVALUATED"


def test_overlapping_categories_do_not_inflate_population():
    row, record, result = fixture("docx")
    row["features"] = {"body": True, "tables": True, "footnotes": True}
    report = audit.build_audit([row], [record], {record.document_id: result})
    assert report["corpus_documents"] == report["reviewed"]["labels"]["anchors"] == 1
    for name in (
        "format.docx",
        "docx.body",
        "docx.tables",
        "docx.footnotes",
        "language_metadata.en",
    ):
        assert report["scenarios"][name]["documents"] == 1
    assert "must not be summed" in report["overlap_rule"]


def test_missing_metadata_stays_unknown_and_does_not_leak():
    row, record, result = fixture()
    row.update(language="PRIVATE VALUE", original_name="PRIVATE FILE", family=None)
    report = audit.build_audit([row], [record], {record.document_id: result})
    assert report["scenarios"]["pdf.scanned"]["unknown_documents"] == 1
    assert report["scenarios"]["pdf.scanned"]["documents"] == 0
    assert report["scenarios"]["language_metadata.UNKNOWN"]["documents"] == 1
    assert "PRIVATE" not in json.dumps(report)


def test_duplicate_and_declared_family_risks_are_separate():
    rows = [fixture(number=n)[0] for n in (1, 2, 3)]
    rows[0].update(family="private-family", split="dev", source_page="private-url")
    rows[1].update(family="private-family", split="test", source_page="private-url", sha256="1")
    risk = audit.family_risks(rows)
    assert (
        risk["exact_hash"]
        == risk["declared_family"]
        == risk["shared_source_page_risk"]
        == {"groups": 1, "documents": 2}
    )
    assert risk["declared_family_split_crossings"] == 1
    assert risk["family_unknown_documents"] == 1
    assert "private" not in json.dumps(risk)


@pytest.mark.parametrize("observed", [False, True])
def test_failures_stay_in_label_and_document_denominators(observed):
    row, record, result = fixture()
    row["status"] = "failed"
    result = replace(result, status=ExtractionStatus.FAILED, blocks=())
    report = audit.build_audit([row], [record], {record.document_id: result if observed else None})
    metric = report["reviewed"]["metrics"]["required_text_recall"]
    assert metric["label_total"] == 1 and metric["passed"] == 0
    assert metric["evaluated"] == int(observed)
    assert metric["unknown"] == int(not observed)
    assert report["scenarios"]["status.failed"]["documents"] == 1


def test_partial_observations_do_not_hide_unknown_labels():
    a, b = fixture(), fixture("docx", 2)
    report = audit.build_audit([a[0], b[0]], [a[1], b[1]], {a[1].document_id: a[2]})
    metric = report["reviewed"]["metrics"]["required_text_recall"]
    assert (metric["passed"], metric["evaluated"], metric["label_total"], metric["unknown"]) == (
        1,
        1,
        2,
        1,
    )
    assert metric["status"] == "PARTIALLY_EVALUATED"
    assert metric["score"] is None


def test_mixed_formats_have_unique_denominators_and_stable_output():
    fixtures = [fixture(fmt, n) for n, fmt in enumerate(("pdf", "docx", "xlsx"), 1)]
    rows = [f[0] for f in fixtures]
    records = [f[1] for f in fixtures]
    results = {f[1].document_id: f[2] for f in fixtures}
    one = audit.build_audit(rows, records, results)
    two = audit.build_audit(list(reversed(rows)), list(reversed(records)), results)
    assert one == two
    assert one["reviewed"]["metrics"]["required_text_recall"]["passed"] == 3
    assert sum(one["scenarios"]["format." + f]["documents"] for f in audit.FORMATS) == 3
    assert "Synthetic evidence" not in json.dumps(one)


@pytest.mark.parametrize("status", ["needs_review", "failed"])
def test_capture_cannot_silently_promote_status(status):
    row, record, result = fixture()
    row["status"] = status
    with pytest.raises(ValueError, match="no automatic promotion"):
        audit.build_audit([row], [record], {record.document_id: result})


def test_unknown_ids_and_formats_are_rejected():
    row, record, result = fixture()
    with pytest.raises(ValueError):
        audit.build_audit([row, row], [record], {})
    with pytest.raises(ValueError):
        audit.build_audit([], [record], {})
    with pytest.raises(ValueError):
        audit.build_audit([{**row, "format": "docx"}], [record], {})


def test_numeric_and_ancillary_facets_select_labels_not_whole_documents():
    row, record, result = fixture("docx", region="footnote")
    report = audit.build_audit([row], [record], {record.document_id: result})
    assert report["anchor_facets"]["footnote"]["labels"]["anchors"] == 1
    assert report["anchor_facets"]["body"]["reviewed_documents"] == 0
    assert (
        report["anchor_facets"]["numeric_bearing"]["metrics"]["required_text_recall"]["passed"] == 1
    )
    assert report["anchor_facets"]["footnote"]["metrics"]["provenance"]["passed"] == 0
    assert report["semantic_units_dates_ids"] == "NOT_EVALUATED_NO_TYPED_LABELS"


def test_office_inventory_independent_of_names_and_values(tmp_path):
    path = tmp_path / "opaque.zip"
    xml = '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p/><w:tbl/></w:body></w:document>'
    notes = (
        '<w:footnotes xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:footnote w:id="-1" w:type="separator"/>'
        '<w:footnote w:id="0"><w:p/></w:footnote></w:footnotes>'
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", xml)
        archive.writestr("word/footnotes.xml", notes)
    flags = audit.office_features(path, "docx")
    assert flags == {
        "body": True,
        "tables": True,
        "footnotes": True,
        "endnotes": False,
        "ancillary": True,
    }


def test_xlsx_formulas_cache_merged_and_sparse_are_structural(tmp_path):
    path = tmp_path / "opaque.zip"
    xml = (
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<dimension ref="A1:A10000"/><sheetData><row r="1">'
        '<c r="A1"><f>1+1</f><v>2</v></c><c r="B1"><f>2+2</f></c>'
        '</row></sheetData><mergeCells><mergeCell ref="A2:B2"/></mergeCells></worksheet>'
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("xl/worksheets/sheet1.xml", xml)
    assert all(audit.office_features(path, "xlsx").values())


@pytest.mark.parametrize(
    "bad",
    [b"bad XML", b'<!DOCTYPE x [<!ENTITY a "secret">]><x/>', "<!DOCTYPE x><x/>".encode("utf-16")],
)
def test_malformed_or_entity_xml_is_unknown(tmp_path, bad):
    path = tmp_path / "opaque.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", bad)
    assert set(audit.office_features(path, "docx").values()) == {None}


def test_archive_bounds_are_not_silent_absence(tmp_path, monkeypatch):
    path = tmp_path / "opaque.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", "<document/>")
    monkeypatch.setattr(audit, "MAX_XML", 1)
    assert all(v is None for v in audit.office_features(path, "docx").values())


def test_frozen_pair_ignores_only_runtime_and_checks_both_hashes(tmp_path):
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    frozen = {"quality": {"population": {"documents": 1}}}
    for p, latency in ((a, 1), (b, 2)):
        p.write_text(
            json.dumps(
                {
                    **frozen,
                    "runtime": latency,
                    "deterministic_fingerprint": fingerprint(frozen["quality"]),
                }
            )
        )
    assert audit.same_pair([a, b])["quality"] == frozen["quality"]
    bad = json.loads(b.read_text())
    bad["quality"]["population"]["documents"] = 2
    b.write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="fingerprint"):
        audit.same_pair([a, b])


def test_cli_private_failures_are_sanitized(tmp_path, monkeypatch, capsys):
    secret = str(tmp_path / "private-source-secret")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "audit",
            "--manifest",
            secret,
            "--corpus",
            secret,
            "--gold",
            secret,
            "--baseline-gold",
            secret,
            "--baseline",
            secret,
            secret,
            "--output",
            secret,
        ],
    )
    assert audit.main() == 2
    output = capsys.readouterr()
    assert "private-source" not in output.out + output.err
    assert "BLOCKED" in output.out


def test_final_profile_never_combines_initial_code_with_final_captures(tmp_path):
    (tmp_path / "registration.json").write_text("{}")
    path, pair = audit.bundle_profile(tmp_path)
    assert path.name == "registration.json"
    assert [p.parent.name for p in pair] == ["run-1", "run-2"]
    (tmp_path / "registration-v2.json").write_text("{}")
    path, pair = audit.bundle_profile(tmp_path)
    assert path.name == "registration-v2.json"
    assert [p.parent.name for p in pair] == ["run-3", "run-4"]


def test_missing_capture_is_not_zero_recovery_or_loss():
    _, record, result = fixture()
    assert audit.paired_hits(record, result, None) == {"recovered": None, "lost": None}
    empty = replace(result, blocks=())
    assert audit.paired_hits(record, empty, result) == {"recovered": ["a1"], "lost": []}
    assert audit.paired_hits(record, result, empty) == {"recovered": [], "lost": ["a1"]}


def test_final_artifact_manifest_takes_precedence(tmp_path):
    (tmp_path / "artifact-manifest.json").write_text("{}")
    assert audit.artifact_profile(tmp_path).name == "artifact-manifest.json"
    (tmp_path / "artifact-manifest-final.json").write_text("{}")
    assert audit.artifact_profile(tmp_path).name == "artifact-manifest-final.json"


def test_no_family_declarations_is_not_zero_verified_crossings():
    row, _, _ = fixture()
    risks = audit.family_risks([row])
    assert risks["declared_family_split_crossings"] is None
    assert risks["family_split_check"] == "NOT_EVALUATED"


def test_unsupported_warning_codes_are_counted_without_promoting_quality():
    row, record, result = fixture("docx")
    row["warnings"] = {"footnotes_not_extracted": 2, "PRIVATE UNKNOWN CODE": 1}
    row["status"] = "needs_review"
    result = replace(result, status=ExtractionStatus.NEEDS_REVIEW)
    report = audit.build_audit([row], [record], {record.document_id: result})
    scenario = report["scenarios"]["format.docx"]
    assert scenario["warning_documents"] == {"footnotes_not_extracted": 1}
    assert scenario["statuses"] == {"needs_review": 1}
    assert "PRIVATE UNKNOWN CODE" not in json.dumps(report)


def test_historical_summary_projects_only_validated_counters():
    from doclens_ai.extraction.fidelity_eval import score_record

    _, record, result = fixture()
    metrics = score_record(record, result)["metrics"]
    metrics["required_text_recall"]["private_payload"] = "DO NOT EXPORT THIS"
    safe = audit.historical_summary([record], metrics)
    assert "DO NOT EXPORT THIS" not in json.dumps(safe)
    assert safe["metrics"]["required_text_recall"]["passed"] == 1
    metrics["required_text_recall"]["evaluated"] = 0
    with pytest.raises(ValueError, match="denominator"):
        audit.historical_summary([record], metrics)


def test_requested_display_without_capture_is_unsupported():
    from doclens_ai.extraction.fidelity_gold import CellCheck

    _, record, _ = fixture("xlsx")
    source = record.anchors[0].source
    check = CellCheck(
        source=source,
        value=None,
        formula=None,
        cached_value=None,
        check_display=True,
        displayed_value="Synthetic display",
    )
    record = record.model_copy(update={"cells": [check]})
    metric = audit.metric_totals([record], {})["metrics"]["displayed_values"]
    assert metric["unsupported"] == 1
    assert metric["status"] == "NOT_EVALUATED" and metric["score"] is None


def test_git_boundary_diagnostics_do_not_echo_private_paths(tmp_path, monkeypatch, capsys):
    secret = str(tmp_path / "private-outside-repository")
    corpus = str(tmp_path / "separate-raw")
    real_run = audit.subprocess.run

    def checked_run(*args, **kwargs):
        assert kwargs["stdout"] is audit.subprocess.DEVNULL
        assert kwargs["stderr"] is audit.subprocess.DEVNULL
        return real_run(*args, **kwargs)

    monkeypatch.setattr(audit.subprocess, "run", checked_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "audit",
            "--manifest",
            secret,
            "--corpus",
            corpus,
            "--gold",
            secret,
            "--baseline-gold",
            secret,
            "--baseline",
            secret,
            secret,
            "--output",
            secret,
        ],
    )
    assert audit.main() == 2
    captured = capsys.readouterr()
    assert "private-outside" not in captured.out + captured.err
    assert captured.err == ""
