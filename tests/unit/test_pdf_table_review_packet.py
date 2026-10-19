"""Synthetic private packets only; never imports real annotations into fixtures."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest
from pypdf import PdfWriter

from doclens_ai.extraction.fidelity_gold import FidelityRecord
from tools.extraction_quality import pdf_table_review_packet as tool


def fixture(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / ".gitignore").write_text("evaluation-output/\nlocal-evaluation/\n")
    corpus = root / "raw"
    corpus.mkdir()
    source = corpus / "PRIVATE_SYNTHETIC_FILENAME.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=400)
    with source.open("wb") as stream:
        writer.write(stream)
    manifest = root / "manifest.csv"
    fields = [
        "document_id",
        "sha256",
        "size_bytes",
        "format",
        "license",
        "license_url",
        "license_basis_url",
    ]
    with manifest.open("w", newline="") as stream:
        csvwriter = csv.DictWriter(stream, fieldnames=fields)
        csvwriter.writeheader()
        csvwriter.writerow(
            {
                "document_id": "c1-0001",
                "sha256": tool.sha(source),
                "size_bytes": source.stat().st_size,
                "format": "pdf",
                "license": "SYNTHETIC_PRIVATE_RIGHTS",
                "license_url": "https://example.invalid/rights",
                "license_basis_url": "https://example.invalid/basis",
            }
        )
    record = {
        "schema_version": "1.0",
        "dataset_revision": "corpus-v1-fidelity-v1",
        "dataset_kind": "synthetic",
        "document_id": "c1-0001",
        "source_sha256": tool.sha(source),
        "source_size_bytes": source.stat().st_size,
        "document_format": "pdf",
        "review_status": "reviewed",
        "review_basis": "synthetic_fixture",
        "reviewer_count": 1,
        "reviewed_on": "2026-01-01",
        "anchors": [
            {
                "anchor_id": f"a{i + 1}",
                "text": f"SYNTHETIC_PRIVATE_LABEL_{i}",
                "source": {
                    "region": "body",
                    "page_number": 1,
                    "block_index": 0,
                    "table_index": 0,
                    "row_index": 0,
                    "column_index": i,
                },
            }
            for i in range(2)
        ],
        "table_cells": [
            {"anchor_id": "a1", "row_span": 2, "column_span": 1},
            {"anchor_id": "a2", "row_span": 1, "column_span": 1},
        ],
        "table_relationships": [{"left": "a1", "right": "a2", "relationship": "same_row"}],
        "order_pairs": [{"before": "a1", "after": "a2"}],
        "cells": [],
    }
    gold = root / "gold.jsonl"
    gold.write_text(json.dumps(record) + "\n", encoding="utf-8")
    expected = tool.Expected(tool.sha(manifest), tool.sha(gold), 1, 1, 1)
    return root, manifest, corpus, gold, expected, source


def generate(data, name="packet"):
    root, manifest, corpus, gold, expected, _ = data
    output = root / "evaluation-output" / name
    summary = tool.generate(
        manifest, corpus, gold, output, expected=expected, allow_synthetic=True, root=root
    )
    return output, summary


def hashes(path):
    return {p.relative_to(path).as_posix(): tool.sha(p) for p in path.rglob("*") if p.is_file()}


def test_independent_worksheet_and_literal_legacy_assertions(tmp_path):
    data = fixture(tmp_path)
    before = {p: p.read_bytes() for p in (data[1], data[3], data[5])}
    output, summary = generate(data)
    folder = output / "review/c1-0001"
    blind = json.loads((folder / "independent.json").read_text())
    legacy = json.loads((folder / "legacy-assertions.json").read_text())
    decisions = json.loads((folder / "adjudication.json").read_text())
    assert legacy["frozen_record"] == FidelityRecord.model_validate_json(
        data[3].read_text()
    ).model_dump(mode="json")
    assert blind["tables"] == [] and blind["cell_template"]["row_span"] is None
    assert all(v is None for v in blind["reviewer"].values())
    assert all(p["table_presence"] is None for p in blind["pages"])
    assert "SYNTHETIC_PRIVATE_LABEL" not in json.dumps(blind)
    assert "asserted_table_index" not in json.dumps(blind)
    assert decisions["state"] == "UNRESOLVED"
    assert len(decisions["assertion_decisions"]) == 6
    assert all(
        r["state"] == "UNRESOLVED" and r["reviewer_id"] is None
        for r in decisions["assertion_decisions"]
    )
    assert legacy["source_regions"][0]["independent_bbox"] is None
    assert (output / "sources/c1-0001.pdf").read_bytes() == before[data[5]]
    assert all(p.read_bytes() == value for p, value in before.items())
    assert summary["totals"]["cell_spans"] == 2
    assert summary["documents"][0]["legacy_spanning_cells"] == 1
    assert summary["independent_reviews_completed"] == 0
    assert summary["qg_01"] == "NOT_EVALUATED"
    assert (output / "COMPLETE.json").exists()


def test_deterministic_packets_and_hash_manifest(tmp_path):
    data = fixture(tmp_path)
    first, a = generate(data, "one")
    second, b = generate(data, "two")
    assert a == b and hashes(first) == hashes(second)
    manifest = json.loads((first / "artifact-manifest.json").read_text())
    assert all(tool.sha(first / name) == value for name, value in manifest.items())
    marker = json.loads((first / "COMPLETE.json").read_text())
    assert marker["artifact_manifest_sha256"] == tool.sha(first / "artifact-manifest.json")


def test_sanitized_aggregate(tmp_path):
    _, summary = generate(fixture(tmp_path))
    text = json.dumps(summary)
    for private in (
        "SYNTHETIC_PRIVATE_LABEL",
        "PRIVATE_SYNTHETIC_FILENAME",
        "SYNTHETIC_PRIVATE_RIGHTS",
        str(tmp_path),
        "https://",
        "row_index",
        "column_index",
    ):
        assert private not in text
    assert summary["selected_documents"] == summary["prepared_documents"] == 1
    assert summary["excluded_documents"] == 0
    assert summary["totals"]["same_row"] == 1


@pytest.mark.parametrize(
    "kind",
    [
        "manifest",
        "gold",
        "source",
        "missing_gold",
        "missing_source",
        "extra_source",
        "population",
        "rights",
        "page",
    ],
)
def test_missing_changed_inputs_fail_without_complete_packet(tmp_path, kind):
    data = list(fixture(tmp_path))
    if kind == "manifest":
        data[1].write_text("changed private input")
    elif kind == "gold":
        data[3].write_text("changed private label")
    elif kind == "source":
        data[5].write_bytes(b"changed private PDF")
    elif kind == "missing_gold":
        data[3].unlink()
    elif kind == "missing_source":
        data[5].unlink()
    elif kind == "extra_source":
        (data[2] / "extra.pdf").write_bytes(b"unexpected source")
    elif kind == "population":
        data[4] = replace(data[4], table_documents=2)
    elif kind == "rights":
        data[1].write_text(data[1].read_text().replace("SYNTHETIC_PRIVATE_RIGHTS", ""))
        data[4] = replace(data[4], manifest_sha256=tool.sha(data[1]))
    elif kind == "page":
        record = json.loads(data[3].read_text())
        for a in record["anchors"]:
            a["source"]["page_number"] = 2
        data[3].write_text(json.dumps(record) + "\n")
        data[4] = replace(data[4], gold_sha256=tool.sha(data[3]))
    with pytest.raises((ValueError, OSError)):
        generate(data)
    assert not (data[0] / "evaluation-output/packet/COMPLETE.json").exists()


def test_never_runs_extraction_scoring_or_models(tmp_path, monkeypatch):
    from doclens_ai.extraction import fidelity_eval, parsers

    def forbidden(*args, **kwargs):
        raise AssertionError("extraction/scoring forbidden")

    monkeypatch.setattr(parsers, "extract_file", forbidden)
    monkeypatch.setattr(fidelity_eval, "score_record", forbidden)
    monkeypatch.setattr(fidelity_eval, "_observations", forbidden)
    assert generate(fixture(tmp_path))[1]["execution"] == "PASS"


def test_existing_or_unignored_output_rejected(tmp_path):
    data = fixture(tmp_path)
    output, _ = generate(data)
    before = hashes(output)
    with pytest.raises(ValueError):
        generate(data)
    assert hashes(output) == before
    root, manifest, corpus, gold, expected, _ = data
    with pytest.raises(ValueError):
        tool.generate(
            manifest,
            corpus,
            gold,
            root / "public-packet",
            expected=expected,
            allow_synthetic=True,
            root=root,
        )


def test_input_drift_during_build_is_not_published(tmp_path, monkeypatch):
    data = fixture(tmp_path)
    real = tool.worksheets

    def drift(*args):
        value = real(*args)
        data[3].write_text("changed during build")
        return value

    monkeypatch.setattr(tool, "worksheets", drift)
    with pytest.raises(ValueError):
        generate(data)
    assert not (data[0] / "evaluation-output/packet/COMPLETE.json").exists()


def test_timeout_and_output_failure_do_not_publish_complete_packet(tmp_path, monkeypatch):
    data = fixture(tmp_path)
    monkeypatch.setattr(tool, "MAX_SECONDS", -1)
    with pytest.raises(ValueError, match="timeout"):
        generate(data)
    assert not (data[0] / "evaluation-output/packet/COMPLETE.json").exists()


def test_serialization_failure_never_publishes_complete_packet(tmp_path, monkeypatch):
    data = fixture(tmp_path)
    original = tool.write_json

    def fail(path, value):
        if path.name == "legacy-assertions.json":
            raise OSError("synthetic private write error")
        original(path, value)

    monkeypatch.setattr(tool, "write_json", fail)
    with pytest.raises(OSError):
        generate(data)
    assert not (data[0] / "evaluation-output/packet/COMPLETE.json").exists()


def test_synthetic_requires_explicit_opt_in_and_real_pins(tmp_path):
    root, manifest, corpus, gold, expected, _ = fixture(tmp_path)
    for kwargs in ({}, {"expected": expected}):
        with pytest.raises(ValueError):
            tool.generate(
                manifest, corpus, gold, root / "evaluation-output/rejected", root=root, **kwargs
            )


def test_linked_corpus_rejected(tmp_path, monkeypatch):
    data = fixture(tmp_path)
    original = Path.is_symlink
    monkeypatch.setattr(Path, "is_symlink", lambda path: path == data[5] or original(path))
    with pytest.raises(ValueError):
        generate(data)
    assert not (data[0] / "evaluation-output/packet/COMPLETE.json").exists()


def test_cli_missing_inputs_does_not_echo_private_paths(tmp_path):
    command = [
        sys.executable,
        "-B",
        str(Path(tool.__file__).resolve()),
        "--manifest",
        str(tmp_path / "PRIVATE_MISSING.csv"),
        "--corpus",
        str(tmp_path / "PRIVATE_RAW"),
        "--gold",
        str(tmp_path / "PRIVATE_GOLD"),
        "--output",
        str(tmp_path / "PRIVATE_PACKET"),
    ]
    run = subprocess.run(command, capture_output=True, text=True, timeout=10)
    assert run.returncode == 2 and run.stderr == ""
    assert "PRIVATE_" not in run.stdout and str(tmp_path) not in run.stdout
    assert run.stdout.startswith("BLOCKED:")
