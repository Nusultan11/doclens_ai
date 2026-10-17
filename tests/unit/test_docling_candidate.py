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


def picture_document(*children):
    """Model native preorder traversal, including captions visible in both modes."""
    caption = text("text/caption", "caption")
    nested = NS(self_ref="picture/inner", label="picture", children=list(children))
    picture = NS(self_ref="picture/outer", label="picture", children=[caption, nested])

    def iterate_items(*, with_groups, traverse_pictures):
        assert with_groups is False

        def visit(item, level=0):
            yield item, level
            for child in getattr(item, "children", []):
                if item.label != "picture" or traverse_pictures or child is caption:
                    yield from visit(child, level + 1)

        yield from visit(picture)
        yield caption, 0  # Repeated identity must not duplicate a caption.
        yield text("text/after", "after", 2), 0

    return NS(pages={1: NS(), 2: NS()}, iterate_items=iterate_items)


def normalize_picture(config, *children):
    return candidate.normalize_document(
        picture_document(*children),
        source_sha256="b" * 64,
        source_size_bytes=100,
        config=config,
    )


def test_picture_descendants_preserve_identity_order_locations_and_warnings(config):
    first = text("text/first", "same")
    split = text("text/split", "one two")
    split.prov = [NS(page_no=1, charspan=(0, 3)), NS(page_no=2, charspan=(4, 7))]
    result = normalize_picture(config, first, first, text("text/second", "same", 2), split)
    assert [
        (b.order, b.text, b.source.page_number, b.source.block_index) for b in result.blocks
    ] == [
        (0, "caption", 1, 0),
        (1, "same", 1, 0),
        (2, "same", 2, 1),
        (3, "one", 1, 0),
        (4, "two", 2, 1),
        (5, "after", 2, 1),
    ]
    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert [(w.code, w.count) for w in result.warnings] == [("drawings_not_extracted", 2)]
    assert (
        result.to_dict()
        == normalize_picture(config, first, first, text("text/second", "same", 2), split).to_dict()
    )


@pytest.mark.parametrize("fault", ["missing", "unknown", "ambiguous", "overlap", "gap"])
def test_picture_descendant_provenance_fails_closed(config, fault):
    child = text(value="one two")
    if fault == "missing":
        child.prov = []
    elif fault == "unknown":
        child.prov = [NS(page_no=3)]
    elif fault == "ambiguous":
        child.prov = [NS(page_no=1), NS(page_no=2)]
    elif fault == "overlap":
        child.prov = [NS(page_no=1, charspan=(0, 4)), NS(page_no=2, charspan=(3, 7))]
    else:
        child.prov = [NS(page_no=1, charspan=(0, 2)), NS(page_no=2, charspan=(4, 7))]
    with pytest.raises((candidate.CandidateError, AttributeError)):
        normalize_picture(config, child)


@pytest.mark.parametrize(
    "limit,bound",
    [("max_blocks", 4), ("max_cells", 1), ("max_characters", 12), ("max_pages", 1)],
)
def test_picture_descendants_obey_existing_limits(config, limit, bound):
    # Without children, caption + after use only 12 characters and four identities.
    with pytest.raises(candidate.CandidateError):
        normalize_picture(replace(config, **{limit: bound}), text(), table())


def test_invalid_picture_child_is_isolated_without_private_output(config, tmp_path, capsys):
    child = text(value="PRIVATE synthetic descendant")
    child.prov = []
    path = pdf(tmp_path)
    diagnostics = {}
    failed = candidate.extract_candidate(
        path, config, converter=fake_converter(picture_document(child)), diagnostics=diagnostics
    )
    recovered = candidate.extract_candidate(
        path, config, converter=fake_converter(picture_document(text()))
    )
    assert failed.status == ExtractionStatus.FAILED
    assert not failed.blocks
    assert diagnostics == {"reason": "unsupported_provenance", "failure_phase": "normalization"}
    assert "PRIVATE" not in str(failed.to_dict())
    assert recovered.status == ExtractionStatus.NEEDS_REVIEW
    assert capsys.readouterr() == ("", "")


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


@pytest.fixture
def frozen_runner(config, tmp_path, monkeypatch):
    """Synthetic bytes/labels only; no private corpus, models or approval claims."""
    import hashlib
    import json

    from doclens_ai.extraction import fidelity_eval, fidelity_gold

    corpus = tmp_path / "corpus"
    corpus.mkdir()
    rows = ["document_id,sha256,size_bytes,format"]
    sources = {}
    for n in range(1, 91):
        identity = f"c1-{n:04d}"
        fmt = "docx" if n <= 30 else "pdf" if n <= 60 else "xlsx"
        data = f"SECRET synthetic fixture {identity}".encode()
        path = corpus / f"SECRET-source-{n}.{fmt}"
        path.write_bytes(data)
        digest = hashlib.sha256(data).hexdigest()
        sources[identity] = digest, len(data), fmt
        rows.append(f"{identity},{digest},{len(data)},{fmt}")
    manifest = tmp_path / "manifest.csv"
    manifest.write_text("\n".join(rows) + "\n", encoding="utf-8")
    monkeypatch.setattr(candidate, "MANIFEST_SHA256", candidate._digest(manifest))
    gold_paths = {}
    for name, profile in candidate.PROFILES.items():
        records = []
        for identity in sorted(profile.reviewed_ids):
            digest, size, fmt = sources[identity]
            locator = {"region": "body"}
            if fmt == "pdf":
                locator["page_number"] = 1
            elif fmt == "docx":
                locator["block_index"] = 0
            else:
                locator.update(sheet_index=0, cell_coordinate="A1")
            records.append(
                {
                    "schema_version": "1.0",
                    "dataset_revision": "corpus-v1-fidelity-v1",
                    "dataset_kind": "synthetic",
                    "document_id": identity,
                    "source_sha256": digest,
                    "source_size_bytes": size,
                    "document_format": fmt,
                    "review_status": "reviewed",
                    "review_basis": "synthetic_fixture",
                    "reviewer_count": 1,
                    "reviewed_on": "2026-01-01",
                    "anchors": [{"anchor_id": "a1", "text": "SECRET synthetic", "source": locator}],
                    "order_pairs": [],
                    "table_cells": [],
                    "table_relationships": [],
                    "cells": [],
                }
            )
        path = tmp_path / f"{name}.jsonl"
        path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
        validated = fidelity_gold.load_gold(path, sources, allow_synthetic=True)
        monkeypatch.setitem(
            candidate.PROFILES,
            name,
            replace(
                profile,
                gold_sha256=candidate._digest(path),
                gold_fingerprint=fingerprint([r.model_dump(mode="json") for r in validated]),
            ),
        )
        gold_paths[name] = path
    original_load = fidelity_gold.load_gold
    monkeypatch.setattr(
        fidelity_gold,
        "load_gold",
        lambda path, sources: original_load(path, sources, allow_synthetic=True),
    )  # Explicit opt-in for synthetic fixtures only; production never enables it.
    calls = []
    original_verify = fidelity_eval.verify_corpus

    def verify(*args):
        calls.append("full_integrity")
        return original_verify(*args)

    monkeypatch.setattr(fidelity_eval, "verify_corpus", verify)
    inventory = {"public-model": "a" * 64}
    monkeypatch.setattr(candidate, "artifact_inventory", lambda _: inventory)
    active = replace(config, artifact_fingerprint=fingerprint(inventory))

    def isolated(_path, _config, record, **kwargs):
        calls.append((record.document_id, kwargs.get("include_metadata", False)))
        return {
            "peak_process_bytes": None,
            "wall_ms": 1.0,
            "baseline": {
                "status": "success",
                "error_category": None,
                "scores": None,
                "latency_ms": 0.1,
            },
            "docling": {
                "status": "failed",
                "error_category": "extraction_failed",
                "scores": None,
                "latency_ms": 0.2,
            },
        }

    monkeypatch.setattr(candidate, "_isolated", isolated)
    return NS(
        corpus=corpus,
        manifest=manifest,
        gold_paths=gold_paths,
        config=active,
        calls=calls,
        root=tmp_path,
    )


@pytest.mark.parametrize("profile,count", [("legacy-v1", 4), ("expanded-v1", 12)])
def test_runner_audits_whole_corpus_before_selection_and_writes_metadata(
    frozen_runner, profile, count
):
    import json

    f = frozen_runner
    output = f.root / "new-output"
    report = candidate.evaluate_candidate(
        f.corpus, f.manifest, f.gold_paths[profile], output, f.config, profile=profile
    )
    expected = candidate.PROFILES[profile]
    assert f.calls == [
        "full_integrity",
        *((i, profile == "expanded-v1") for i in sorted(expected.pdf_ids)),
        "full_integrity",
    ]
    assert {d["document_id"] for d in report["documents"]} == expected.pdf_ids
    assert len(report["documents"]) == count
    if profile == "expanded-v1":
        assert report["benchmark_profile"] == profile
        assert len(report["population"]["fresh_pdf_ids"]) == 8
        assert len(report["population"]["control_pdf_ids"]) == 4
        assert report["population"]["reviewed_documents"] == 19
        assert sum(d["label_counts"]["anchors"] for d in report["documents"]) == 12
        assert sum(d["population"] == "fresh" for d in report["documents"]) == 8
    else:
        assert "benchmark_profile" not in report and "population" not in report
        assert all("label_counts" not in d for d in report["documents"])
    serialized = (output / "metrics.json").read_text()
    assert "SECRET" not in serialized
    assert str(f.config.artifacts) not in serialized
    assert str(f.corpus) not in serialized
    assert json.loads(serialized) == report
    for d in report["documents"]:
        assert "latency_ms" not in d["docling"]
        assert d["docling"]["scores"] is None  # No fabricated zero quality for failures.
    stable = {k: v for k, v in report.items() if k not in {"runtime", "deterministic_fingerprint"}}
    assert report["deterministic_fingerprint"] == fingerprint(stable)
    with pytest.raises(candidate.CandidateError):
        candidate.evaluate_candidate(
            f.corpus, f.manifest, f.gold_paths[profile], output, f.config, profile=profile
        )


def test_default_and_explicit_legacy_reports_are_identical(frozen_runner):
    f = frozen_runner
    args = (f.corpus, f.manifest, f.gold_paths["legacy-v1"])
    implicit = candidate.evaluate_candidate(*args, f.root / "implicit", f.config)
    explicit = candidate.evaluate_candidate(
        *args, f.root / "explicit", f.config, profile="legacy-v1"
    )
    assert implicit == explicit


def test_frozen_profile_contracts():
    legacy, expanded = candidate.PROFILES["legacy-v1"], candidate.PROFILES["expanded-v1"]
    assert len(legacy.reviewed_ids) == 11 and legacy.pdf_ids == candidate.PDF_IDS
    assert legacy.gold_fingerprint == candidate.GOLD_FINGERPRINT
    assert legacy.gold_sha256 == "30cfdcf31f1036f1e6f813fad34266fa347b5368ee140be7304eb942f0e0d353"
    assert len(expanded.reviewed_ids) == 19 and len(expanded.pdf_ids) == 12
    assert expanded.control_ids == legacy.pdf_ids
    assert expanded.primary_ids == {
        "c1-0031",
        "c1-0032",
        "c1-0033",
        "c1-0035",
        "c1-0040",
        "c1-0043",
        "c1-0048",
        "c1-0049",
    }
    assert not expanded.primary_ids & expanded.control_ids
    assert (
        expanded.gold_sha256 == "f372f54d65916b57994ee62ce1fc00fdc536bcdd459b384c6d6e11e9f114bfaf"
    )
    assert (
        expanded.gold_fingerprint
        == "50b37582e35382055515a16a2163f83a31ae8dcdd74e80729c499c04e65b815e"
    )


@pytest.mark.parametrize("profile", ["legacy-v1", "expanded-v1"])
@pytest.mark.parametrize(
    "fault",
    [
        "bytes",
        "fingerprint",
        "membership",
        "missing",
        "changed",
        "post_change",
        "duplicate",
        "nested_duplicate",
        "draft",
    ],
)
def test_profile_preflight_and_postflight_fail_closed(frozen_runner, monkeypatch, profile, fault):
    f = frozen_runner
    selected = candidate.PROFILES[profile]
    gold = f.gold_paths[profile]
    if fault in {"bytes", "fingerprint", "membership"}:
        change = (
            {"gold_sha256": "0" * 64}
            if fault == "bytes"
            else {"gold_fingerprint": "0" * 64}
            if fault == "fingerprint"
            else {"reviewed_ids": selected.reviewed_ids - {min(selected.reviewed_ids)}}
        )
        monkeypatch.setitem(candidate.PROFILES, profile, replace(selected, **change))
    elif fault in {"missing", "changed"}:
        source = next(f.corpus.iterdir())
        if fault == "missing":
            source.unlink()
        else:
            source.write_bytes(b"changed synthetic source")
    elif fault == "post_change":
        original = candidate._isolated

        def mutate(*args, **kwargs):
            next(f.corpus.iterdir()).write_bytes(b"changed during synthetic run")
            return original(*args, **kwargs)

        monkeypatch.setattr(candidate, "_isolated", mutate)
    else:
        raw = gold.read_text(encoding="utf-8")
        if fault == "duplicate":
            raw = raw.replace(
                '"schema_version": "1.0"', '"schema_version": "1.0", "schema_version": "1.0"', 1
            )
        elif fault == "nested_duplicate":
            raw = raw.replace('"region": "body"', '"region": "body", "region": "body"', 1)
        else:
            raw = raw.replace('"review_status": "reviewed"', '"review_status": "draft"', 1)
        gold.write_text(raw, encoding="utf-8")
        monkeypatch.setitem(
            candidate.PROFILES, profile, replace(selected, gold_sha256=candidate._digest(gold))
        )
    output = f.root / "rejected"
    with pytest.raises(ValueError):
        candidate.evaluate_candidate(f.corpus, f.manifest, gold, output, f.config, profile=profile)
    assert not output.exists()
    if fault != "post_change":
        assert not any(isinstance(c, tuple) for c in f.calls)


def test_unknown_profile_is_rejected_before_any_io(config, tmp_path):
    with pytest.raises(candidate.CandidateError, match="Unknown frozen"):
        candidate.evaluate_candidate(
            tmp_path, tmp_path, tmp_path, tmp_path / "out", config, profile="unknown"
        )


def test_unknown_cli_profile_is_rejected(monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "candidate",
            *[
                v
                for key in (
                    "corpus",
                    "manifest",
                    "gold",
                    "output-dir",
                    "artifacts",
                    "artifact-fingerprint",
                )
                for v in ("--" + key, "unused")
            ],
            "--profile",
            "unknown",
        ],
    )
    with pytest.raises(SystemExit) as exc:
        candidate.main()
    assert exc.value.code == 2
    assert "invalid choice" in capsys.readouterr().err


@pytest.mark.parametrize("include_metadata", [False, True])
def test_worker_warning_counts_and_eligibility_never_export_content(
    config, tmp_path, monkeypatch, include_metadata
):
    from doclens_ai.extraction import fidelity_eval, parsers

    result = normalize(
        config, text(value="SECRET raw body"), NS(self_ref="picture/0", label="picture")
    )
    monkeypatch.setattr(parsers, "extract_file", lambda _: result)
    monkeypatch.setattr(candidate, "extract_candidate", lambda *_args, **_kwargs: result)
    monkeypatch.setattr(
        fidelity_eval,
        "score_record",
        lambda *_: {"metrics": {"required_text_recall": {"passed": 1}}},
    )
    messages = []
    record = NS(anchors=[NS(anchor_id="a1", text="SECRET raw body")])
    candidate._worker(
        NS(put=messages.append), tmp_path / "SECRET.pdf", config, record, include_metadata
    )
    assert messages[-1] == {"complete": True}
    assert "SECRET" not in str(messages)
    for item, name in zip(messages, ("baseline", "docling"), strict=False):
        outcome = item[name]
        if include_metadata:
            assert outcome["warning_counts"] == {"drawings_not_extracted": 1}
            assert outcome["eligible_by_status"] is False
            assert outcome["required_anchor_hits"] == {"a1": True}
        else:
            assert "warning_counts" not in outcome and "eligible_by_status" not in outcome
            assert "required_anchor_hits" not in outcome


@pytest.mark.parametrize(
    "reason,complete", [("timeout", True), ("memory_limit", True), ("worker_failure", False)]
)
def test_expanded_resource_failure_keeps_denominators(frozen_runner, monkeypatch, reason, complete):
    f = frozen_runner

    def limited(*_args, **_kwargs):
        return {
            "blocked": reason,
            "baseline": {"latency_ms": 0.1},
            "peak_process_bytes": 1,
            "wall_ms": 2.0,
        }

    monkeypatch.setattr(candidate, "_isolated", limited)
    report = candidate.evaluate_candidate(
        f.corpus,
        f.manifest,
        f.gold_paths["expanded-v1"],
        f.root / "limited",
        f.config,
        profile="expanded-v1",
    )
    assert len(report["documents"]) == 12
    assert sum(d["label_counts"]["anchors"] for d in report["documents"]) == 12
    assert all(d["blocked"] == reason and "docling" not in d for d in report["documents"])
    assert candidate._execution_complete(report, "expanded-v1") is complete


@pytest.mark.parametrize("phase", ["model_initialization", "missing_dependency", "conversion"])
def test_execution_classification_separates_infrastructure_and_measured_failure(phase):
    doc = {
        "baseline": {"status": "success"},
        "docling": {
            "error_category": "missing_dependency"
            if phase == "missing_dependency"
            else "extraction_failed",
            "diagnostics": {"failure_phase": phase},
        },
    }
    assert candidate._execution_complete({"documents": [doc] * 12}, "expanded-v1") is (
        phase == "conversion"
    )


@pytest.mark.parametrize("failed", [False, True])
def test_anchor_identity_detects_equal_count_swaps_and_unknown_failures(
    frozen_runner, monkeypatch, failed
):
    import json

    from doclens_ai.extraction import fidelity_gold, parsers
    from doclens_ai.extraction.fidelity_eval import _read_sources

    f = frozen_runner
    # Load the synthetic fixture through its explicitly opted-in test boundary.
    records = fidelity_gold.load_gold(f.gold_paths["legacy-v1"], _read_sources(f.manifest))
    record = next(r for r in records if r.document_format == "pdf")
    data = record.model_dump(mode="json")
    data["anchors"] = [
        {**data["anchors"][0], "anchor_id": identity, "text": value}
        for identity, value in (("a1", "SECRET old"), ("a2", "SECRET new"))
    ]
    record = fidelity_gold.FidelityRecord.model_validate_json(json.dumps(data))
    baseline = replace(
        normalize(f.config, text(value="SECRET old")),
        source_sha256=record.source_sha256,
        source_size_bytes=record.source_size_bytes,
    )
    converted = replace(baseline, blocks=normalize(f.config, text(value="SECRET new")).blocks)
    if failed:
        converted = replace(
            baseline,
            status=ExtractionStatus.FAILED,
            blocks=(),
            error_category=ErrorCategory.EXTRACTION_FAILED,
        )
    monkeypatch.setattr(parsers, "extract_file", lambda _: baseline)
    monkeypatch.setattr(candidate, "extract_candidate", lambda *_args, **_kwargs: converted)
    messages = []
    candidate._worker(NS(put=messages.append), f.corpus / "SECRET.pdf", f.config, record, True)
    left, right = messages[0]["baseline"], messages[1]["docling"]
    assert left["required_anchor_hits"] == {"a1": True, "a2": False}
    if failed:
        assert right["required_anchor_hits"] is None and right["scores"] is None
    else:
        assert right["required_anchor_hits"] == {"a1": False, "a2": True}
        assert left["scores"]["metrics"]["required_text_recall"]["passed"] == 1
        assert right["scores"]["metrics"]["required_text_recall"]["passed"] == 1
    assert "SECRET" not in str(messages)


def test_missing_baseline_is_not_a_complete_expanded_observation():
    doc = {"docling": {"error_category": None}}
    assert not candidate._execution_complete({"documents": [doc] * 12}, "expanded-v1")


@pytest.mark.parametrize("explicit", [False, True])
def test_cli_preserves_legacy_default_and_budgets(monkeypatch, capsys, explicit):
    arguments = ["candidate"]
    for key in ("corpus", "manifest", "gold", "output-dir", "artifacts"):
        arguments.extend(("--" + key, "unused"))
    arguments.extend(("--artifact-fingerprint", "a" * 64))
    if explicit:
        arguments.extend(("--profile", "legacy-v1"))
    monkeypatch.setattr(sys, "argv", arguments)

    def evaluate(*args, profile):
        assert profile == "legacy-v1"
        assert args[4].timeout_seconds == 180
        assert args[4].max_process_bytes == 2048 * 1024**2
        return {
            "documents": [{"docling": {"error_category": None}}] * 4,
            "deterministic_fingerprint": "a" * 64,
        }

    monkeypatch.setattr(candidate, "evaluate_candidate", evaluate)
    assert candidate.main() == 0
    assert '"status": "evaluated"' in capsys.readouterr().out


def test_legacy_limits_keep_original_execution_classification():
    doc = {"blocked": "timeout", "baseline": {}}
    assert not candidate._execution_complete({"documents": [doc] * 4}, "legacy-v1")


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
