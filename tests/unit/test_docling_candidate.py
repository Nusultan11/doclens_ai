from __future__ import annotations

import importlib.metadata
import socket
import sys
from dataclasses import replace
from types import SimpleNamespace as NS

import pytest

from doclens_ai.extraction import docling_candidate as candidate
from doclens_ai.extraction.fidelity_gold import fingerprint
from doclens_ai.extraction.models import ErrorCategory, ExtractionStatus, TableBlock, TextBlock


@pytest.fixture
def config(tmp_path):
    return candidate.CandidateConfig(tmp_path / "models", "a" * 64)


def text(reference="text/0", value="narrative", page=1):
    return NS(self_ref=reference, label="text", text=value, prov=[NS(page_no=page)])


def cell(row=0, column=0, row_span=1, col_span=1, value="cell"):
    return NS(
        start_row_offset_idx=row,
        start_col_offset_idx=column,
        end_row_offset_idx=row + row_span,
        end_col_offset_idx=column + col_span,
        row_span=row_span,
        col_span=col_span,
        text=value,
    )


def table(cells=None, rows=2, columns=3, reference="table/0", page=1):
    return NS(
        self_ref=reference,
        label="table",
        prov=[NS(page_no=page)],
        data=NS(
            num_rows=rows,
            num_cols=columns,
            table_cells=cells if cells is not None else [cell(col_span=2), cell(1, 2)],
        ),
    )


def document(*items):
    return NS(pages={1: NS(), 2: NS()}, iterate_items=lambda **_: iter((i, 0) for i in items))


def normalize(config, *items):
    return candidate.normalize_document(
        document(*items), source_sha256="b" * 64, source_size_bytes=100, config=config
    )


def fake_converter(doc, status="success"):
    return NS(convert=lambda *_args, **_kwargs: NS(status=status, document=doc))


def pdf(tmp_path):
    path = tmp_path / "synthetic.pdf"
    path.write_bytes(b"%PDF-synthetic-only")
    return path


def test_grid_spans_sparse_no_fabricated_cells(config):
    result = normalize(config, table())
    assert result.status == ExtractionStatus.SUCCESS
    block = result.blocks[0]
    assert isinstance(block, TableBlock)
    assert len(block.rows) == 2
    assert sum(len(r.cells) for r in block.rows) == 2
    merged = block.rows[0].cells[0]
    assert (merged.row_index, merged.column_index, merged.row_span, merged.column_span) == (
        0,
        0,
        1,
        2,
    )
    assert merged.source.page_number == 1
    assert merged.source.block_index == 0
    assert merged.source.table_index == 0
    assert (merged.source.row_index, merged.source.column_index) == (0, 0)
    assert block.rows[1].cells[0].column_index == 2


def test_order_identity_dedup_equal_text_and_page_provenance(config):
    first = text(value="repeat")
    result = normalize(
        config,
        first,
        table(),
        first,
        text("text/1", "repeat"),
        text("text/2", "later", 2),
        table(reference="table/1", page=2),
    )
    assert [b.order for b in result.blocks] == [0, 1, 2, 3, 4]
    assert isinstance(result.blocks[1], TableBlock)
    assert [b.text for b in result.blocks if isinstance(b, TextBlock)] == [
        "repeat",
        "repeat",
        "later",
    ]
    assert result.blocks[3].source.page_number == 2
    assert result.blocks[3].source.block_index == 1
    assert result.blocks[4].table_index == 0  # Page-local, never Gold-dependent.
    assert (
        normalize(config, first, table()).to_dict() == normalize(config, first, table()).to_dict()
    )


@pytest.mark.parametrize(
    "fault", ["overlap", "span", "bounds", "negative", "bool", "text", "rich", "empty"]
)
def test_malformed_table_rejected(config, fault):
    item = table()
    if fault == "overlap":
        item.data.table_cells.append(cell())
    elif fault == "span":
        item.data.table_cells[0].col_span = 1
    elif fault == "bounds":
        item.data.table_cells[0].end_col_offset_idx = 9
    elif fault == "negative":
        item.data.table_cells[0].start_row_offset_idx = -1
    elif fault == "bool":
        item.data.table_cells[0].row_span = True
    elif fault == "text":
        item.data.table_cells[0].text = None
    elif fault == "rich":
        item.data.table_cells[0].ref = NS()
    else:
        item.data.table_cells = []
    with pytest.raises(candidate.CandidateError):
        normalize(config, item)


@pytest.mark.parametrize("fault", ["missing", "multipage", "unknown", "invalid"])
def test_provenance_not_guessed(config, fault):
    item = text()
    if fault == "missing":
        item.prov = []
    elif fault == "multipage":
        item.prov.append(NS(page_no=2))
    elif fault == "unknown":
        item.prov[0].page_no = 3
    else:
        item.prov[0].page_no = 0
    with pytest.raises((candidate.CandidateError, AttributeError)):
        normalize(config, item)


def test_native_multipage_text_charspans_preserved(config):
    item = text(value="page one page two")
    item.prov = [NS(page_no=1, charspan=(0, 8)), NS(page_no=2, charspan=(9, 17))]
    result = normalize(config, item)
    assert [(b.text, b.source.page_number) for b in result.blocks] == [
        ("page one", 1),
        ("page two", 2),
    ]
    item.prov[1].charspan = (10, 17)  # A missing non-whitespace character is not silently lost.
    with pytest.raises(candidate.CandidateError):
        normalize(config, item)


@pytest.mark.parametrize("limit", ["max_blocks", "max_cells", "max_characters", "max_pages"])
def test_normalization_limits(config, limit):
    active = replace(config, **{limit: 1})
    with pytest.raises(candidate.CandidateError):
        normalize(active, text(), table())


def test_empty_and_unrepresented_pictures_require_review(config):
    empty = normalize(config)
    assert empty.status == ExtractionStatus.NEEDS_REVIEW
    assert empty.warnings[0].code == "insufficient_text"
    picture = NS(self_ref="picture/0", label="picture")
    result = normalize(config, text(), picture)
    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert result.warnings[0].code == "drawings_not_extracted"
    assert len(result.blocks) == 1


def test_missing_optional_dependency_without_docling(config, tmp_path, monkeypatch):
    def missing(_config):
        raise ImportError("SECRET dependency detail")

    monkeypatch.setattr(candidate, "_converter", missing)
    result = candidate.extract_candidate(pdf(tmp_path), config)
    assert result.status == ExtractionStatus.FAILED
    assert result.error_category == ErrorCategory.MISSING_DEPENDENCY
    assert "SECRET" not in str(result.to_dict())


def test_failure_isolation_and_no_exception_content(config, tmp_path, capsys):
    path = pdf(tmp_path)
    broken = NS(convert=lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("SECRET")))
    failed = candidate.extract_candidate(path, config, converter=broken)
    succeeding = candidate.extract_candidate(
        path, config, converter=fake_converter(document(text()))
    )
    assert failed.status == ExtractionStatus.FAILED
    assert succeeding.status == ExtractionStatus.SUCCESS
    assert failed.source_sha256 == succeeding.source_sha256
    assert "SECRET" not in str(failed.to_dict())
    assert capsys.readouterr() == ("", "")


def test_partial_conversion_fails_not_silent_success(config, tmp_path):
    result = candidate.extract_candidate(
        pdf(tmp_path), config, converter=fake_converter(document(text()), "partial_success")
    )
    assert result.status == ExtractionStatus.FAILED
    assert not result.blocks


def test_source_mutation_and_file_size_gate(config, tmp_path):
    path = pdf(tmp_path)
    bounded = candidate.extract_candidate(
        path, replace(config, max_file_bytes=1), converter=fake_converter(document(text()))
    )
    assert bounded.error_category == ErrorCategory.LIMIT_EXCEEDED

    def mutate(*_args, **_kwargs):
        path.write_bytes(b"changed")
        return NS(status="success", document=document(text()))

    assert (
        candidate.extract_candidate(path, config, converter=NS(convert=mutate)).status == "failed"
    )


def test_offline_guard_restores_state(monkeypatch, capsys):
    monkeypatch.setenv("HF_HUB_OFFLINE", "prior")
    previous = socket.socket.connect
    with candidate._private_offline():
        import os

        assert os.environ["HF_HUB_OFFLINE"] == "1"
        print("SECRET")
        with socket.socket() as s, pytest.raises(candidate.CandidateError):
            s.connect(("127.0.0.1", 9))
    assert socket.socket.connect is previous
    assert os.environ["HF_HUB_OFFLINE"] == "prior"
    assert capsys.readouterr() == ("", "")


def test_pinned_artifacts_and_explicit_options_without_real_models(config, monkeypatch):
    for name in candidate.MODEL_FILES:
        path = config.artifacts / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"synthetic weight fixture, not loadable")
    pin = fingerprint(candidate.artifact_inventory(config.artifacts))
    active = replace(config, artifact_fingerprint=pin)
    monkeypatch.setattr(
        importlib.metadata,
        "version",
        lambda name: {"docling": "2.55.1", "docling-core": "2.48.2"}[name],
    )

    def options(**kwargs):
        return NS(**kwargs, table_structure_options=NS())

    modules = {
        "docling.datamodel.accelerator_options": NS(
            AcceleratorDevice=NS(CPU="cpu"), AcceleratorOptions=lambda **kw: NS(**kw)
        ),
        "docling.datamodel.base_models": NS(InputFormat=NS(PDF="pdf")),
        "docling.datamodel.pipeline_options": NS(
            PdfPipelineOptions=options, TableFormerMode=NS(FAST="fast")
        ),
        "docling.document_converter": NS(
            DocumentConverter=lambda **kw: NS(**kw), PdfFormatOption=lambda **kw: NS(**kw)
        ),
    }
    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)
    converter = candidate._converter(active)
    options = converter.format_options["pdf"].pipeline_options
    assert converter.allowed_formats == ["pdf"]
    assert (
        options.do_ocr is options.enable_remote_services is options.allow_external_plugins is False
    )
    assert options.do_table_structure is True
    assert options.do_code_enrichment is options.do_formula_enrichment is False
    assert options.do_picture_description is options.do_picture_classification is False
    assert options.table_structure_options.mode == "fast"
    assert options.table_structure_options.do_cell_matching is True
    assert options.artifacts_path == active.artifacts.resolve()
    assert options.accelerator_options.device == "cpu"
    (active.artifacts / candidate.MODEL_FILES[0]).write_bytes(b"tampered")
    with pytest.raises(candidate.CandidateError):
        candidate._converter(active)


def test_bad_pins_and_bounds(config):
    with pytest.raises(ValueError):
        replace(config, artifact_fingerprint="not a hash")
    with pytest.raises(ValueError):
        replace(config, timeout_seconds=0)
    for timeout in (float("nan"), float("inf")):
        with pytest.raises(ValueError):
            replace(config, timeout_seconds=timeout)


def test_diagnostic_allowlist_never_echoes_exception_text(config, tmp_path):
    def fail(*_args, **_kwargs):
        raise candidate.CandidateError("SECRET annotation from unsafe fake")

    diagnostics = {}
    result = candidate.extract_candidate(
        pdf(tmp_path), config, converter=NS(convert=fail), diagnostics=diagnostics
    )
    assert result.status == "failed"
    assert diagnostics == {"reason": "candidate_rejected", "failure_phase": "conversion"}
    assert "SECRET" not in str(diagnostics)


def test_normalized_tables_use_unchanged_fidelity_scorer(config):
    import json

    from doclens_ai.extraction.fidelity_eval import score_record
    from doclens_ai.extraction.fidelity_gold import FidelityRecord

    result = normalize(
        config, table(cells=[cell(value="alpha"), cell(0, 1, value="beta")], rows=1, columns=2)
    )
    record = FidelityRecord.model_validate_json(
        json.dumps(
            {
                "schema_version": "1.0",
                "dataset_revision": "corpus-v1-fidelity-v1",
                "dataset_kind": "synthetic",
                "document_id": "c1-0001",
                "source_sha256": "b" * 64,
                "source_size_bytes": 100,
                "document_format": "pdf",
                "review_status": "reviewed",
                "review_basis": "synthetic_fixture",
                "reviewer_count": 1,
                "reviewed_on": "2026-01-01",
                "anchors": [
                    {
                        "anchor_id": identity,
                        "text": value,
                        "source": {
                            "region": "body",
                            "page_number": 1,
                            "block_index": 0,
                            "table_index": 0,
                            "row_index": 0,
                            "column_index": column,
                        },
                    }
                    for identity, value, column in (("a1", "alpha", 0), ("a2", "beta", 1))
                ],
                "order_pairs": [{"before": "a1", "after": "a2"}],
                "table_cells": [{"anchor_id": "a1"}, {"anchor_id": "a2"}],
                "table_relationships": [{"left": "a1", "right": "a2", "relationship": "same_row"}],
                "cells": [],
            }
        )
    )
    scores = score_record(record, result)
    assert scores["missing_evidence_count"] == 0
    assert all(
        scores["metrics"][name]["score"] == 1
        for name in (
            "required_text_recall",
            "reading_order",
            "table_cells",
            "table_relationships",
            "provenance",
        )
    )


def test_file_gate_before_converter_and_unsupported_body(config, tmp_path):
    source = tmp_path / "not-pdf.docx"
    source.write_bytes(b"synthetic")
    assert candidate.extract_candidate(source, config).error_category == "unsupported_format"
    unsupported = NS(self_ref="form/0", label="form", prov=[NS(page_no=1)])
    with pytest.raises(candidate.CandidateError):
        normalize(config, unsupported)


def test_runner_audits_whole_corpus_before_selection_and_writes_metadata(
    config,
    tmp_path,
    monkeypatch,
):
    import json

    from doclens_ai.extraction import fidelity_eval, fidelity_gold

    calls = []
    identities = sorted(candidate.PDF_IDS) + [f"c1-{n:04d}" for n in range(1, 8)]
    records = [
        NS(document_id=i, model_dump=lambda i=i, **_: {"document_id": i}) for i in identities
    ]
    monkeypatch.setattr(
        candidate, "GOLD_FINGERPRINT", fingerprint([r.model_dump() for r in records])
    )
    monkeypatch.setattr(candidate, "_digest", lambda _: candidate.MANIFEST_SHA256)
    monkeypatch.setattr(fidelity_eval, "_read_sources", lambda _: {})
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    matches = {f"c1-{n:04d}": corpus / "SECRET-source.pdf" for n in range(1, 91)}

    def verify(*_args):
        calls.append("full_integrity")
        return matches

    monkeypatch.setattr(fidelity_eval, "verify_corpus", verify)
    monkeypatch.setattr(fidelity_gold, "load_gold", lambda *_: records)
    inventory = {"public-model": "a" * 64}
    monkeypatch.setattr(candidate, "artifact_inventory", lambda _: inventory)
    active = replace(config, artifact_fingerprint=fingerprint(inventory))

    def isolated(*_args):
        calls.append("candidate")
        return {
            "peak_process_bytes": None,
            "wall_ms": 1.0,
            "baseline": {"status": "success", "scores": None, "latency_ms": 0.1},
            "docling": {"status": "failed", "scores": None, "latency_ms": 0.2},
        }

    monkeypatch.setattr(candidate, "_isolated", isolated)
    output = tmp_path / "new-output"
    report = candidate.evaluate_candidate(
        corpus, tmp_path / "manifest", tmp_path / "gold", output, active
    )
    assert calls == ["full_integrity", *("candidate" for _ in range(4)), "full_integrity"]
    serialized = (output / "metrics.json").read_text()
    assert "SECRET" not in serialized
    assert str(config.artifacts) not in serialized
    assert len(report["documents"]) == 4
    assert json.loads(serialized) == report
    for d in report["documents"]:
        assert "latency_ms" not in d["docling"]
        assert d["docling"]["scores"] is None  # No fabricated zero quality for failures.
    stable = {k: v for k, v in report.items() if k not in {"runtime", "deterministic_fingerprint"}}
    assert report["deterministic_fingerprint"] == fingerprint(stable)
    with pytest.raises(candidate.CandidateError):
        candidate.evaluate_candidate(
            corpus, tmp_path / "manifest", tmp_path / "gold", output, active
        )


@pytest.mark.parametrize("stop", ["complete", "memory", "timeout"])
def test_isolated_monitor_preserves_baseline_and_cleans_own_child(config, monkeypatch, stop):
    import queue

    messages = [
        {"baseline": {"status": "success"}},
        {"docling": {"status": "success"}},
        {"complete": True},
    ]
    closed = []

    def get(**_):
        if messages:
            return messages.pop(0)
        raise queue.Empty

    channel = NS(get=get, close=lambda: closed.append("queue"))
    alive = [True]
    child = NS(
        pid=1,
        start=lambda: None,
        is_alive=lambda: alive[0],
        terminate=lambda: alive.__setitem__(0, False),
        join=lambda **_: None,
    )
    context = NS(Queue=lambda: channel, Process=lambda **_: child)
    monkeypatch.setattr(candidate.multiprocessing, "get_context", lambda _: context)
    peaks = iter([1, 20] if stop == "memory" else [1] * 10)
    fake_psutil = NS(
        Process=lambda _: NS(memory_info=lambda: NS(rss=next(peaks))),
        NoSuchProcess=ProcessLookupError,
    )
    monkeypatch.setitem(sys.modules, "psutil", fake_psutil)
    clock = iter([0, 0, 2, 3] if stop == "timeout" else range(10))
    monkeypatch.setattr(candidate.time, "perf_counter", lambda: next(clock))
    active = replace(config, max_process_bytes=10, timeout_seconds=1 if stop == "timeout" else 100)
    outcome = candidate._isolated(config.artifacts, active, None)
    assert outcome["baseline"]["status"] == "success"
    assert closed == ["queue"] and alive == [False]
    if stop == "complete":
        assert "blocked" not in outcome
        assert outcome["docling"]["status"] == "success"
    else:
        assert outcome["blocked"] == ("memory_limit" if stop == "memory" else "timeout")
        assert "docling" not in outcome
