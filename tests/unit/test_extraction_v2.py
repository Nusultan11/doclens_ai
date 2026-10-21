"""Offline evaluation accounting, literal metrics, fault paths and source support."""

from __future__ import annotations

import copy
import csv
import json

import pytest

from doclens_ai.eda import corpus_v2 as corpus
from tests.unit.test_corpus_v2 import manifest, sample
from tests.unit.test_pdf_cell_recovery import bind, reference
from tools.extraction_quality import comparison_v2 as comparison
from tools.extraction_quality import extraction_v2 as runner
from tools.extraction_quality import ocr_diagnostics_v2 as ocr
from tools.extraction_quality import source_alignment_v2 as alignment
from tools.pdf_ocr_candidate import benchmark as bounded


def test_exact_numeric_tokens_never_drop_signs_zeros_units_or_decimal_separators():
    assert runner.exact_positions("-001,25 %", "001,25") == []
    assert runner.exact_positions("-001,25 %", "-001,25 %") == [0]
    assert runner.exact_positions("120 20.1 020", "20") == []
    assert runner.exact_positions("001.25", "001,25") == []
    assert runner.exact_positions("Not payable", "payable") == [4]


def test_empty_denominators_are_unknown():
    score = ocr.score("", "extra", language="en", evidence_class="synthetic")
    assert score["cer"] is None and score["wer"] is None
    assert comparison.prf(0, 0, 0)["f1"] is None
    assert comparison.prf(0, 0, 1)["f1"] == 0


def test_legacy_scorer_denominators_are_evaluated_not_total():
    report = runner.summarize(
        [
            {
                "status": "success",
                "eligible": True,
                "runtime": None,
                "legacy_expected": {"required_text_recall": 5},
                "legacy_scores": {
                    "metrics": {
                        "required_text_recall": {"passed": 2, "evaluated": 3, "unsupported": 0},
                    }
                },
            }
        ]
    )
    metric = report["legacy_attested_metrics"]["required_text_recall"]
    assert metric == {
        "passed": 2,
        "total": 3,
        "unsupported": 0,
        "expected_total": 5,
        "unobserved": 2,
    }


def test_ocr_multilingual_character_and_numeric_errors():
    reference_text = "Ә Ғ Қ Ң Ө Ұ Ү Һ І -001,25 %"
    score = ocr.score(
        reference_text,
        reference_text.replace("Ә", "А").replace("-001,25", "001,25"),
        language="kk",
        evidence_class="synthetic",
        anchors=("-001,25 %",),
    )
    assert score["character_errors"] == 2
    assert score["word_errors"] == 2
    assert score["numeric_missing_or_changed"] == 1
    assert score["numeric_added_or_duplicated"] == 1
    assert score["anchors_recovered"] == 0
    assert score["kazakh_reference_character_counts"]["Ә"] == 1
    assert score["source_alignment"] == "NOT_EVALUATED"
    same = ocr.score(
        "Добрый день 002", "Добрый день 002 002", language="ru", evidence_class="synthetic"
    )
    assert same["numeric_added_or_duplicated"] == 1
    with pytest.raises(ValueError):
        ocr.score("a", "a", language="unknown", evidence_class="synthetic")
    with pytest.raises(ValueError):
        ocr.edit_distance("x" * 10_000, "x" * 10_000)


@pytest.mark.parametrize(
    "text,images,suspicious,route",
    [
        ("", 1, 0, "likely_scanned_requires_render_inspection"),
        ("", 0, 1, "encoding_risk_requires_inspection"),
        ("\ufffd", 0, 0, "encoding_risk_requires_inspection"),
        ("native " * 10, 1, 0, "mixed_resources_requires_region_inspection"),
        ("", 0, 0, "low_text_unknown"),
    ],
)
def test_scan_diagnosis_is_explicitly_provisional(text, images, suspicious, route):
    result = ocr.signals(text, images=images, fonts=1, suspicious_fonts=suspicious)
    assert result["route"] == route
    assert result["classification_verified"] is False
    assert result["ocr_selected"] is False


def test_layout_region_score_is_separate_from_reading_order():
    regions = [
        {"page": 1, "class": "Text", "bbox": [0, 0, 10, 10]},
        {"page": 1, "class": "Table", "bbox": [20, 0, 40, 20]},
    ]
    score = comparison.layout(regions, regions[::-1])
    assert score["f1"] == 1
    assert score["reading_order"] == "NOT_EVALUATED"
    assert comparison.layout(regions, None)["status"] == "NOT_EVALUATED"
    repeated = comparison.layout(regions, regions + [regions[0]])
    assert repeated["matched"] == 2 and repeated["predicted"] == 3
    assert comparison.iou([0, 0, 10, 10], [20, 20, 30, 30]) == 0
    with pytest.raises(ValueError):
        comparison.layout([regions[0] | {"bbox": [0, 0, 10, 10, 20]}], regions)


def test_cell_topology_numeric_and_merged_literals():
    cell = {
        "page": 1,
        "table_id": "t1",
        "cell_id": "c1",
        "row": 0,
        "column": 0,
        "row_span": 1,
        "column_span": 2,
        "literal": "+001.20 %",
    }
    assert comparison.table_cells([cell], [cell])["f1"] == 1
    altered = cell | {"literal": "001.20 %"}
    assert comparison.table_cells([cell], [altered])["f1"] == 0
    assert comparison.table_cells([cell], None)["status"] == "NOT_EVALUATED"
    with pytest.raises(ValueError, match="duplicate"):
        comparison.table_cells([cell], [cell, cell])
    with pytest.raises(ValueError, match="conflicting"):
        comparison.table_cells([cell], [cell, cell | {"cell_id": "c2"}])


def test_combined_guard_rejects_lost_evidence_and_retains_incomplete_outputs():
    before = {1: "-001,25 % Required clause", 2: "Another column"}
    after = before | {1: "001,25 % Required clause"}
    score = comparison.paired_text(
        ("-001,25 %", "Required clause"), before, after, expected_pages={1, 2}
    )
    assert score["experiment"] == "REJECT"
    assert score["lost_anchor_indices"] == [0]
    assert score["quality"] == "FAIL"
    incomplete = comparison.paired_text((), before, {1: before[1]}, expected_pages={1, 2})
    assert incomplete["execution"] == "BLOCKED"
    assert incomplete["experiment"] == "INCONCLUSIVE"


def test_native_worker_two_repetitions_preserve_fingerprints(tmp_path, monkeypatch):
    value = manifest(sample(tmp_path))
    path = tmp_path / "manifest.json"
    path.write_text(value.model_dump_json(), encoding="utf-8")
    monkeypatch.setattr(runner, "private_destination", lambda _: None)
    result = runner.evaluate(path, tmp_path, tmp_path / "results")
    assert result["execution"] == "PASS"
    assert result["deterministic_equal"] is True
    assert result["pins_unchanged"] is True
    assert result["integrity_unchanged"] is True
    assert result["summaries"][0]["states"] == {"needs_review": 1}
    assert result["summaries"][0]["peak_sampled_tree_rss_bytes"] > 0
    assert result["quality"] == "NOT_EVALUATED"
    assert "source.pdf" not in json.dumps(result)


@pytest.mark.parametrize("failure", ["timeout", "worker_failed", "output_limit"])
def test_worker_failure_stays_in_denominator(tmp_path, monkeypatch, failure):
    value = manifest(sample(tmp_path))
    path = tmp_path / "manifest.json"
    path.write_text(value.model_dump_json(), encoding="utf-8")
    monkeypatch.setattr(runner, "private_destination", lambda _: None)
    monkeypatch.setattr(
        bounded,
        "isolated",
        lambda *args, **kwargs: {
            "result": None,
            "failure": failure,
            "runtime": {"seconds": 0.01, "peak_tree_rss_bytes": 10},
        },
    )
    result = runner.evaluate(path, tmp_path, tmp_path / "results")
    assert result["execution"] == "BLOCKED"
    assert result["summaries"][0]["attempted"] == 1
    assert result["summaries"][0]["eligible"] == 1
    assert result["summaries"][0]["states"] == {"failed": 1}
    row = json.loads((tmp_path / "results/run-1/results.json").read_text())["rows"][0]
    assert row["failure"] == failure and row["legacy_scores"] is None


def test_native_parser_rejection_is_a_measured_outcome_not_worker_failure(tmp_path, monkeypatch):
    from dataclasses import replace

    from doclens_ai.extraction.models import ErrorCategory, ExtractionStatus
    from doclens_ai.extraction.parsers import extract_file

    value = manifest(sample(tmp_path))
    path = tmp_path / "manifest.json"
    path.write_text(value.model_dump_json(), encoding="utf-8")
    rejected = replace(
        extract_file(tmp_path / "source.pdf"),
        status=ExtractionStatus.FAILED,
        error_category=ErrorCategory.CORRUPT_DOCUMENT,
        blocks=(),
        warnings=(),
    )
    monkeypatch.setattr(runner, "private_destination", lambda _: None)
    monkeypatch.setattr(
        bounded,
        "isolated",
        lambda *args, **kwargs: {
            "result": rejected.to_dict(),
            "failure": None,
            "runtime": {"seconds": 0.01, "peak_tree_rss_bytes": 10},
        },
    )
    result = runner.evaluate(path, tmp_path, tmp_path / "results")
    assert result["execution"] == "PASS"
    assert result["summaries"][0]["states"] == {"failed": 1}
    assert result["quality"] == "NOT_EVALUATED"


def test_recovery_compares_literal_against_source_without_changing_candidate(tmp_path):
    pytest.importorskip("pypdfium2")
    source, proposal, _ = reference(tmp_path)
    original = copy.deepcopy(proposal)
    result = alignment.verify(source, corpus.sha256(source), [proposal])
    assert result["summary"]["native_literal_available"] == 4
    assert result["summary"]["candidate_literal_conflicts"] == 2
    assert result["summary"]["independently_human_verified"] == 0
    assert proposal == original
    assert result["summary"]["quality"] == "NOT_EVALUATED"
    assert all("native_literal" not in c for c in result["sanitized_cells"])
    proposal["cells"][2]["literal_text"] = "-001.20"
    corrupted = alignment.verify(source, corpus.sha256(source), [bind(proposal)])
    assert "CANDIDATE_LITERAL_CONFLICT" in corrupted["cells"][2]["issues"]
    assert "CRITICAL_NUMERIC_CONFLICT" in corrupted["cells"][2]["issues"]
    assert corrupted["cells"][2]["native_literal"] == "+001.20"
    assert corrupted["summary"]["experiment"] == "REJECT"
    assert corrupted["summary"]["quality"] == "FAIL"


def test_global_duplicate_glyph_ownership_across_tables_is_never_accepted(tmp_path):
    pytest.importorskip("pypdfium2")
    source, proposal, _ = reference(tmp_path)
    second = copy.deepcopy(proposal)
    second["context"]["review_table_id"] = "second-table"
    result = alignment.verify(source, corpus.sha256(source), [proposal, bind(second)])
    assert result["summary"]["duplicate_glyphs"] > 0
    assert all("DUPLICATE_GLYPH_OWNERSHIP" in c["issues"] for c in result["cells"])


def test_missing_crossed_or_unbounded_glyphs_remain_needs_review(tmp_path):
    pytest.importorskip("pypdfium2")
    source, proposal, _ = reference(tmp_path, crossed=True)
    result = alignment.verify(source, corpus.sha256(source), [proposal])
    assert result["cells"][0]["status"] == "needs_review"
    assert result["cells"][0]["native_literal"] is None
    with pytest.raises(ValueError):
        alignment.verify(source, "0" * 64, [proposal])


def test_output_guard_requires_fresh_ignored_directory(tmp_path):
    with pytest.raises(ValueError):
        runner.private_destination(runner.ROOT / "docs" / "public-result")
    with pytest.raises(ValueError):
        runner.private_destination(tmp_path)


def test_control_import_preserves_actual_non_target_language(tmp_path, monkeypatch):
    raw = tmp_path / "raw"
    raw.mkdir()
    value = sample(raw)
    row = {
        "document_id": "c1-0001",
        "format": "pdf",
        "document_language": "cy",
        "sha256": value.original.sha256,
        "size_bytes": value.original.size_bytes,
        "license": "public-fixture",
        "license_basis_url": "public-fixture-rights",
        "source_page_url": "public-fixture-parent",
    }
    legacy = tmp_path / "legacy.csv"
    with legacy.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    template = tmp_path / "template.json"
    template.write_text(manifest().model_dump_json(), encoding="utf-8")
    monkeypatch.setattr(runner, "private_destination", lambda _: None)
    output = tmp_path / "new-manifest.json"
    result = runner.prepare_controls(template, legacy, raw, output)
    assert result["legacy_controls"] == 1
    assert corpus.load(output).samples[0].languages == ("cy",)
    assert corpus.sha256(raw / "source.pdf") == value.original.sha256


@pytest.mark.parametrize("change", [{"page": 0}, {"page": True}, {"literal": None}])
def test_exact_cell_score_rejects_unknown_text_and_invalid_pages(change):
    cell = {
        "page": 1,
        "table_id": "t",
        "cell_id": "c",
        "row": 0,
        "column": 0,
        "row_span": 1,
        "column_span": 1,
        "literal": "",
    } | change
    with pytest.raises(ValueError):
        comparison.table_cells([cell], [cell])


def test_alignment_fingerprint_binds_candidate_and_source_evidence(tmp_path):
    source, proposal, _ = reference(tmp_path)
    a = alignment.verify(source, corpus.sha256(source), [proposal])
    changed = copy.deepcopy(proposal)
    changed["cells"][0]["literal_text"] = "Other wrong assignment"
    b = alignment.verify(source, corpus.sha256(source), [bind(changed)])
    assert a["sanitized_cells"] == b["sanitized_cells"]
    assert a["summary"]["deterministic_fingerprint"] != b["summary"]["deterministic_fingerprint"]


def test_ocr_cli_never_reads_unqualified_pdf(tmp_path, monkeypatch):
    import sys

    value = sample(tmp_path)
    value = value.model_copy(
        update={"rights": value.rights.model_copy(update={"local_evaluation": False})}
    )
    path = tmp_path / "manifest.json"
    path.write_text(manifest(value).model_dump_json(), encoding="utf-8")
    monkeypatch.setattr(ocr, "private_destination", lambda _: None)
    monkeypatch.setattr(ocr, "diagnose", lambda _: pytest.fail("unqualified source was read"))
    output = tmp_path / "diagnostics"
    monkeypatch.setattr(
        sys,
        "argv",
        ["ocr", "--manifest", str(path), "--root", str(tmp_path), "--output", str(output)],
    )
    assert ocr.main() == 2
    report = json.loads((output / "diagnostics.json").read_text())
    assert report["execution"] == "BLOCKED"
    assert report["rows"][0]["failure"] == "source_ineligible"


@pytest.mark.parametrize("fault", [None, "missing_run", "missing_row", "summary", "csv"])
def test_delivered_results_reject_incomplete_or_inconsistent_outputs(tmp_path, fault):
    from doclens_ai.extraction.fidelity_gold import fingerprint

    value = json.loads((runner.ROOT / "docs/eda/extraction_v2_results.json").read_text())
    cohort = value["native"]["controls"]
    if fault == "missing_run":
        cohort["runs"].pop()
    elif fault == "missing_row":
        cohort["runs"][0]["rows"].pop()
    elif fault == "summary":
        cohort["runs"][0]["summary"]["attempted"] += 1
    value["consolidated_fingerprint"] = fingerprint(
        {k: v for k, v in value.items() if k != "consolidated_fingerprint"}
    )
    path, csv_path = tmp_path / "results.json", tmp_path / "results.csv"
    path.write_text(json.dumps(value), encoding="utf-8")
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["metric_path", "value_json"])
        writer.writeheader()
        writer.writerows(runner.result_leaves(value))
    if fault == "csv":
        csv_path.write_text(csv_path.read_text(encoding="utf-8") + "extra,null\n", encoding="utf-8")
    if fault:
        with pytest.raises(ValueError):
            runner.verify_results(path, csv_path)
    else:
        assert runner.verify_results(path, csv_path)["documents"] == 150
