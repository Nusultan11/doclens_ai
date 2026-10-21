"""Public synthetic review drafts; no real Gold text or source names."""

from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from doclens_ai.extraction.docx_footnote_candidate import FootnoteLimits, extract_footnotes
from doclens_ai.extraction.fidelity_gold import FidelityRecord, GoldError
from tests.unit.test_docx_footnote_candidate import note, package
from tools.docx_footnote_candidate import locator_review_packet as tool


@pytest.fixture
def tmp_path() -> Iterator[Path]:
    """Exercise real output guards independently of pytest's global basetemp."""
    root = tool.ROOT / "evaluation-output"
    root.mkdir(exist_ok=True)
    with TemporaryDirectory(prefix="docx-locator-test-", dir=root) as directory:
        yield Path(directory)


def record(path: Path, *, text: str = "Synthetic note 007.50") -> FidelityRecord:
    return FidelityRecord.model_validate_json(
        json.dumps(
            {
                "schema_version": "1.0",
                "dataset_revision": "corpus-v1-fidelity-v1",
                "dataset_kind": "synthetic",
                "review_basis": "synthetic_fixture",
                "document_id": "c1-0001",
                "source_sha256": tool.existing.sha(path),
                "source_size_bytes": path.stat().st_size,
                "document_format": "docx",
                "review_status": "reviewed",
                "reviewer_count": 1,
                "reviewed_on": "2026-01-01",
                "anchors": [
                    {
                        "anchor_id": "a1",
                        "text": text,
                        "source": {"region": "footnote", "part_index": 0},
                    }
                ],
                "order_pairs": [],
                "table_cells": [],
                "table_relationships": [],
                "cells": [],
            }
        )
    )


def capture(path: Path, *, limits: FootnoteLimits | None = None) -> dict:
    a = extract_footnotes(path, limits=limits).to_dict()
    return {
        "ancillary": a,
        "address_checks": tool.existing.verify_ancillary(path, {"ancillary": a}),
    }


@pytest.mark.parametrize("moved", [False, True])
def test_actual_part_identity_never_becomes_reviewed_mapping(tmp_path, moved):
    path = package(tmp_path, moved=moved)
    packet = tool.make_packet(record(path), capture(path))
    assert packet["review_status"] == "draft"
    assert packet["reviewed_locator_fidelity"] == "NOT_EVALUATED"
    assert packet["production_authorization"] is False
    review = packet["anchor_reviews"][0]
    assert review["text_diagnostic"] == "SINGLE_TEXT_CANDIDATE"
    assert review["legacy_gold_locator"]["part_index"] == 0
    assert review["mapping"]["state"] == "UNRESOLVED"
    assert all(value is None for key, value in review["mapping"].items() if key != "state")
    hint = review["text_hints"][0]
    assert hint["note_id"] == "7" and hint["note_element_index"] == 0
    assert hint["part_uri"] == ("/notes/actual.xml" if moved else "/word/footnotes.xml")
    assert hint["paragraph_child_index"] == 0 and hint["reference_ordinals"] == (0,)
    assert tool.make_packet(record(path), capture(path)) == packet


def test_duplicate_text_and_multiple_references_preserve_ambiguity(tmp_path):
    path = package(tmp_path, notes=note("7") + note("8"), references=("7", "8", "7"))
    packet = tool.make_packet(record(path), capture(path))
    observation = packet["candidate_observation"]
    assert len(observation["notes"]) == 2 and len(observation["references"]) == 3
    assert observation["notes"][0]["reference_ordinals"] == (0, 2)
    review = packet["anchor_reviews"][0]
    assert review["text_diagnostic"] == "AMBIGUOUS_TEXT_MATCH"
    assert [hint["note_id"] for hint in review["text_hints"]] == ["7", "8"]
    assert review["mapping"]["selected_note_identity"] is None
    safe = json.dumps(tool.aggregate([packet]))
    assert "Synthetic" not in safe and "word/" not in safe and "note_id" not in safe


def test_repeated_text_in_one_paragraph_is_also_ambiguous(tmp_path):
    path = package(tmp_path, notes=note(text="Synthetic note 007.50 Synthetic note 007.50"))
    review = tool.make_packet(record(path), capture(path))["anchor_reviews"][0]
    assert review["text_diagnostic"] == "AMBIGUOUS_TEXT_MATCH"
    assert review["text_hints"][0]["occurrences"] == 2


def test_normal_zero_id_and_unsupported_content_remain_distinct(tmp_path):
    path = package(tmp_path, notes=note("0", extra="<w:tbl/>"), references=("0",))
    packet = tool.make_packet(record(path), capture(path))
    assert packet["candidate_status"] == "needs_review"
    assert packet["candidate_observation"]["notes"][0]["note_id"] == "0"
    assert packet["anchor_reviews"][0]["text_hints"][0]["complete"] is False
    assert tool.aggregate([packet])["documents"][0]["incomplete_notes"] == 1


@pytest.mark.parametrize("missing", [False, True])
def test_empty_notes_or_no_gold_text_match_stays_unresolved(tmp_path, missing):
    path = package(tmp_path, notes="" if missing else None, references=() if missing else ("7",))
    packet = tool.make_packet(record(path, text="Unmatched synthetic label"), capture(path))
    review = packet["anchor_reviews"][0]
    assert review["text_diagnostic"] == "NO_TEXT_MATCH" and review["text_hints"] == []
    assert tool.aggregate([packet])["unresolved_mappings"] == 1
    assert packet["review_status"] == "draft"


@pytest.mark.parametrize("failure", ["relationship", "corrupt", "oversize", "absent_capture"])
def test_failures_keep_label_denominators_and_unknown_observations(tmp_path, failure):
    path = package(tmp_path)
    rec = record(path)
    if failure == "absent_capture":
        raw = None
    elif failure == "relationship":
        path = package(tmp_path, changes={"word/_rels/document.xml.rels": None})
        rec = record(path)
        raw = capture(path)
    elif failure == "corrupt":
        path.write_bytes(b"PRIVATE malformed ZIP")
        rec = record(path)
        raw = capture(path)
    else:
        raw = capture(path, limits=FootnoteLimits(max_file_bytes=1))
    packet = tool.make_packet(rec, raw)
    summary = tool.aggregate([packet])
    assert packet["candidate_status"] == "failed"
    assert summary["attempted_documents"] == summary["footnote_labels"] == 1
    assert summary["unresolved_mappings"] == 1 and summary["reviewed_mappings"] == 0
    assert summary["documents"][0]["observed_notes"] is None
    assert packet["anchor_reviews"][0]["text_diagnostic"] == "UNKNOWN"
    assert "PRIVATE" not in json.dumps(summary)


def test_hash_size_mismatch_never_gets_a_packet(tmp_path):
    path = package(tmp_path)
    rec = record(path)
    raw = capture(path)
    raw["ancillary"]["source_sha256"] = "0" * 64
    with pytest.raises(tool.PacketError, match="source mismatch"):
        tool.make_packet(rec, raw)
    assert tool.worker(path, tmp_path, "0" * 64, rec.source_size_bytes) == 2
    assert not (tmp_path / "result.json").exists()


@pytest.mark.parametrize("field,value", [("source_size_bytes", None), ("source_size_bytes", 1)])
def test_missing_or_differing_size_is_rejected(tmp_path, field, value):
    path = package(tmp_path)
    raw = capture(path)
    raw["ancillary"][field] = value
    with pytest.raises(tool.PacketError, match="source mismatch"):
        tool.make_packet(record(path), raw)


def frozen_inputs(tmp_path):
    corpus = tmp_path / "raw"
    corpus.mkdir()
    source = package(corpus)
    rec = record(source)
    manifest = tmp_path / "manifest.csv"
    fields = [
        "document_id",
        "sha256",
        "format",
        "size_bytes",
        "license",
        "license_url",
        "license_basis_url",
    ]
    with manifest.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerow(
            dict(
                zip(
                    fields,
                    [
                        rec.document_id,
                        rec.source_sha256,
                        "docx",
                        rec.source_size_bytes,
                        "Synthetic",
                        "https://example.invalid/license",
                        "https://example.invalid/source",
                    ],
                    strict=True,
                )
            )
        )
    gold = tmp_path / "gold.jsonl"
    gold.write_text(rec.model_dump_json() + "\n", encoding="utf-8")
    return manifest, corpus, gold, source


def test_preflight_uses_existing_strict_contracts_and_preserves_inputs(tmp_path):
    manifest, corpus, gold, source = frozen_inputs(tmp_path)
    before = {p: p.read_bytes() for p in (manifest, gold, source)}
    identity, paths, records = tool.preflight(manifest, corpus, gold, allow_synthetic=True)
    assert identity["manifest_documents"] == identity["reviewed_docx"] == 1
    assert paths == {"c1-0001": source} and len(records) == 1
    assert all(p.read_bytes() == data for p, data in before.items())
    with pytest.raises(GoldError):
        tool.preflight(manifest, corpus, gold)


@pytest.mark.parametrize("failure", ["missing", "extra", "changed", "suffix", "linked"])
def test_source_preflight_rejects_identity_and_link_failures(tmp_path, monkeypatch, failure):
    manifest, corpus, gold, source = frozen_inputs(tmp_path)
    if failure == "missing":
        source.unlink()
    elif failure == "extra":
        (corpus / "extra.docx").write_bytes(b"extra")
    elif failure == "changed":
        source.write_bytes(source.read_bytes() + b"changed")
    elif failure == "suffix":
        source.rename(source.with_suffix(".pdf"))
    else:
        original = Path.is_symlink
        monkeypatch.setattr(Path, "is_symlink", lambda self: self == source or original(self))
    with pytest.raises((ValueError, tool.PacketError)):
        tool.preflight(manifest, corpus, gold, allow_synthetic=True)


def test_hint_budget_and_timeout_never_adjudicate(tmp_path, monkeypatch):
    path = package(tmp_path, notes=note("7") + note("8"), references=("7", "8"))
    monkeypatch.setattr(tool, "MAX_HINTS", 1)
    packet = tool.make_packet(record(path), capture(path))
    review = packet["anchor_reviews"][0]
    assert review["text_hints_truncated"] and review["text_diagnostic"] == "UNKNOWN"
    assert review["mapping"]["state"] == "UNRESOLVED"
    monkeypatch.setattr(tool, "BUILD_SECONDS", 0)
    with pytest.raises(tool.PacketError, match="timeout"):
        tool.make_packet(record(path), capture(path))


def test_atomic_write_failure_and_budget_do_not_publish(tmp_path, monkeypatch):
    output = tmp_path / "review.json"

    def fail(*args):
        raise OSError("PRIVATE PATH")

    monkeypatch.setattr(tool.os, "replace", fail)
    with pytest.raises(OSError):
        tool.write_json(output, {"private": "synthetic"})
    assert not output.exists() and not output.with_suffix(".partial").exists()
    monkeypatch.setitem(tool.existing.GUARDS, "max_capture_bytes", 1)
    with pytest.raises(tool.PacketError, match="Output limit"):
        tool.write_json(output, {"a": 1})
    assert not output.exists() and not output.with_suffix(".partial").exists()


def test_existing_outputs_and_partials_never_overwritten(tmp_path):
    path = tmp_path / "packet.json"
    path.write_text("existing", encoding="utf-8")
    with pytest.raises(tool.PacketError):
        tool.write_json(path, {})
    assert path.read_text() == "existing"
    path.unlink()
    partial = path.with_suffix(".partial")
    partial.write_text("other owner", encoding="utf-8")
    with pytest.raises(tool.PacketError):
        tool.write_json(path, {})
    assert partial.read_text() == "other owner"


def test_fresh_output_rejects_existing_raw_and_unignored_paths(tmp_path):
    tool.fresh_output(tmp_path / "fresh", tmp_path / "raw")
    for path, corpus in (
        (tmp_path, tmp_path / "raw"),
        (tmp_path / "raw/new", tmp_path / "raw"),
        (tool.ROOT / "docs/eda/unignored", tmp_path / "raw"),
    ):
        with pytest.raises(tool.PacketError):
            tool.fresh_output(path, corpus)
    with TemporaryDirectory() as outside:
        with pytest.raises(tool.PacketError):
            tool.fresh_output(Path(outside) / "fresh", tmp_path / "raw")


def test_internal_worker_allows_parent_journal_without_accepting_old_capture(tmp_path, monkeypatch):
    stage = tmp_path / "stage"
    stage.mkdir()
    (stage / "resources.jsonl").write_text("", encoding="utf-8")
    calls = []
    monkeypatch.setattr(tool, "worker", lambda *args: calls.append(args) or 0)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "packet",
            "--worker",
            "synthetic.docx",
            "--expected-sha",
            "0" * 64,
            "--expected-size",
            "1",
            "--output",
            str(stage),
        ],
    )
    assert tool.main() == 0 and len(calls) == 1
    (stage / "result.json").write_text("{}", encoding="utf-8")
    assert tool.main() == 2 and len(calls) == 1


def test_cli_failure_never_echoes_private_exception(monkeypatch, capsys):
    def fail(*args):
        raise ValueError("PRIVATE source text and path")

    monkeypatch.setattr(tool, "generate", fail)
    monkeypatch.setattr(sys, "argv", ["packet", "--output", "unignored"])
    assert tool.main() == 2
    assert (
        capsys.readouterr().out
        == "BLOCKED: local review packet input, resource or output boundary rejected\n"
    )


def test_no_footnote_labels_is_not_a_perfect_fidelity_score(tmp_path):
    path = package(tmp_path)
    data = record(path).model_dump(mode="json")
    data["anchors"][0]["source"] = {"region": "body", "block_index": 0}
    packet = tool.make_packet(FidelityRecord.model_validate_json(json.dumps(data)), capture(path))
    assert packet["anchor_reviews"] == []
    summary = tool.aggregate([packet])
    assert summary["footnote_labels"] == summary["reviewed_mappings"] == 0
    assert summary["reviewed_locator_fidelity"] == "NOT_EVALUATED"


@pytest.mark.parametrize("failure", ["timeout", "memory_limit", "worker_failed"])
def test_generate_resource_failures_keep_full_attempted_population(tmp_path, monkeypatch, failure):
    path = package(tmp_path)
    rec = record(path)
    monkeypatch.setattr(tool, "preflight", lambda *args: ({}, {rec.document_id: path}, (rec,)))
    monkeypatch.setattr(
        tool.existing,
        "monitor",
        lambda *args: {
            "failure": failure,
            "cleanup": True,
            "seconds": 0.1,
            "peak_tree_rss_bytes": 1,
            "samples": 1,
        },
    )
    output = tmp_path / "fresh"
    report = tool.generate(tmp_path / "manifest", tmp_path / "raw", tmp_path / "gold", output)
    assert report["status"] == "FIX" and report["quality"] == "NOT_EVALUATED"
    summary = report["deterministic"]["summary"]
    assert summary["attempted_documents"] == summary["footnote_labels"] == 1
    assert summary["candidate_status_counts"] == {"failed": 1}
    assert summary["unresolved_mappings"] == 1
    assert summary["documents"][0]["observed_notes"] is None
    packet = json.loads((output / rec.document_id / "review-draft.json").read_text())
    assert packet["review_status"] == "draft" and packet["candidate_observation"] is None
    assert (output / "artifact-manifest.json").is_file()


@pytest.mark.parametrize("mode", ["normal", "-O", "PYTHONOPTIMIZE=1"])
@pytest.mark.parametrize("entry", ["parent_api", "parent_cli", "worker_api", "worker_cli"])
def test_subprocess_optimization_boundary(tmp_path, mode, entry):
    """Real interpreter flags; child assertions cannot establish test success."""
    script = r"""
import json,sys
from pathlib import Path
from tests.unit.test_docx_footnote_candidate import package
from tests.unit.test_docx_footnote_locator_review_packet import record
from tools.docx_footnote_candidate import locator_review_packet as p
stage=Path(sys.argv[1]); entry=sys.argv[2]
source=package(stage); rec=record(source); output=stage/'output'
def inputs(*args):
    (stage/'preflight-called').write_text('called')
    return {},{rec.document_id:source},(rec,)
p.preflight=inputs
verify=p.existing.verify_ancillary
def checked(*args):
    (stage/'verification-called').write_text('called')
    return verify(*args)
p.existing.verify_ancillary=checked
if entry.startswith('worker'):
    output.mkdir()
    (output/'resources.jsonl').write_text('')
if entry.endswith('cli'):
    sys.argv=['packet','--output',str(output)]
    if entry.startswith('worker'):
        sys.argv+=['--worker',str(source),'--expected-sha',rec.source_sha256,
                   '--expected-size',str(rec.source_size_bytes)]
    raise SystemExit(p.main())
if entry=='worker_api':
    raise SystemExit(p.worker(source,output,rec.source_sha256,rec.source_size_bytes))
try:
    result=p.generate(stage/'manifest',stage/'raw',stage/'gold',output)
except p.PacketError as exc:
    print(str(exc))
    raise SystemExit(2)
print(result['status'])
raise SystemExit(0 if result['status']=='PASS' else 1)
"""
    env = os.environ.copy()
    env.pop("PYTHONOPTIMIZE", None)
    env["PYTHONPATH"] = os.pathsep.join(
        (str(tool.ROOT / "src"), str(tool.ROOT / ".venv/Lib/site-packages"), str(tool.ROOT))
    )
    if mode == "PYTHONOPTIMIZE=1":
        env["PYTHONOPTIMIZE"] = "1"
    command = [sys.executable, "-B"] + (["-O"] if mode == "-O" else [])
    result = subprocess.run(
        command + ["-c", script, str(tmp_path), entry],
        env=env,
        cwd=tool.ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.stderr == ""
    output = tmp_path / "output"
    if mode == "normal":
        assert result.returncode == 0
        capture_path = (
            output / "result.json" if entry.startswith("worker") else output / "c1-0001/result.json"
        )
        assert json.loads(capture_path.read_text())["address_checks"]["status"] == "EVALUATED"
        if entry.startswith("parent"):
            assert json.loads((output / "summary.json").read_text())["status"] == "PASS"
    else:
        assert result.returncode == 2
        expected = (
            "BLOCKED: local review packet input, resource or output boundary rejected\n"
            if entry.endswith("cli")
            else "Optimized Python execution rejected\n"
            if entry == "parent_api"
            else ""
        )
        assert result.stdout == expected
        assert not (tmp_path / "preflight-called").exists()
        assert not (tmp_path / "verification-called").exists()
        assert not list(tmp_path.rglob("result.json"))
        assert not list(tmp_path.rglob("review-draft.json"))
        assert not list(tmp_path.rglob("summary.json"))
        if entry.startswith("parent"):
            assert not output.exists()
