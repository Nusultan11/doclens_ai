"""Selective OCR diagnostics: synthetic source observations, never factual approval."""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import pytest

from doclens_ai.extraction.evidence_v2 import Locator
from doclens_ai.extraction.parsers import extract_file
from tests.unit.test_ml28_evidence import fixture
from tests.unit.test_pdf_ocr_candidate import pdf
from tools.pdf_ocr_candidate import enrichment as ocr


def request(scope, *, languages=("en",), reason="native_text_loss", bbox=None):
    return ocr.Request(
        scope=scope,
        locator=Locator(
            page=1, bbox=bbox, coordinate_basis="pdf_user_space_unrotated" if bbox else None
        ),
        reason=reason,
        observation_reference="synthetic-source-observation",
        languages=languages,
    )


@pytest.mark.parametrize("text", ["001.25 kg", "-001,25 kg", "-001.26 kg", "+001.25 kg"])
def test_numbers_signs_and_decimal_disagreement_is_never_accepted(text):
    scope, _, _, native = fixture()
    observed = ocr.merge_observation(
        request(scope),
        native,
        text=text,
        returned_scope=scope,
        returned_page=1,
        engine_revision="fixture",
        config_sha256="b" * 64,
    )
    assert observed.state == "needs_review" and observed.numeric_disagreement
    assert observed.literal == text and native.blocks[0].text.endswith("2026-Q1")


@pytest.mark.parametrize("text", ["Revenue Division -001.25 kg 2026-Q1", " -001.25  "])
def test_exact_and_overlap_duplicates_are_suppressed_as_diagnostics(text):
    scope, _, _, native = fixture()
    observed = ocr.merge_observation(
        request(scope),
        native,
        text=text,
        returned_scope=scope,
        returned_page=1,
        engine_revision="fixture",
        config_sha256="b" * 64,
    )
    assert observed.state == "duplicate" and observed.literal == text


@pytest.mark.parametrize("case", ["page", "workspace", "document", "version", "sha", "size"])
def test_contaminated_or_oversized_ocr_does_not_merge(case):
    scope, _, _, native = fixture()
    returned = scope
    if case in {"workspace", "document", "version", "sha"}:
        key = {
            "workspace": "workspace_id",
            "document": "document_id",
            "version": "version_id",
            "sha": "raw_sha256",
        }[case]
        returned = scope.model_copy(update={key: "f" * 64 if case == "sha" else "wrong"})
    observed = ocr.merge_observation(
        request(scope),
        native,
        text="new OCR",
        returned_scope=returned,
        returned_page=2 if case == "page" else 1,
        engine_revision="fixture",
        config_sha256="b" * 64,
        max_characters=1 if case == "size" else 1000,
    )
    assert observed.state == "failed" and observed.literal == ""


def local_runtime(tmp_path):
    for name in ("tesseract", "renderer", "eng.traineddata"):
        (tmp_path / name).write_bytes(b"fixture-runtime")
    return ocr.existing.Runtime(
        str(tmp_path / "tesseract"), str(tmp_path / "renderer"), str(tmp_path)
    )


def actual_native(tmp_path, text=""):
    path = pdf(tmp_path / "source.pdf", [text])
    native = extract_file(path)
    scope = fixture()[0].model_copy(update={"raw_sha256": native.source_sha256})
    return path, native, scope


def test_native_text_layer_does_not_trigger_ocr(tmp_path, monkeypatch):
    path, native, scope = actual_native(tmp_path, "Native evidence is present 123")
    monkeypatch.setattr(ocr.existing, "ocr_page", lambda *a: pytest.fail("unexpected OCR"))
    result = ocr.selective_page(
        path,
        native,
        request(scope, reason="missing_text_layer"),
        runtime=local_runtime(tmp_path),
        limits=ocr.existing.Limits(),
        work=tmp_path,
    )
    assert result.state == "not_selected"


@pytest.mark.parametrize("languages", [("ru",), ("kk",), ("ru", "kk", "en")])
def test_missing_language_artifacts_are_explicit(tmp_path, languages):
    path, native, scope = actual_native(tmp_path)
    result = ocr.selective_page(
        path,
        native,
        request(scope, languages=languages),
        runtime=local_runtime(tmp_path),
        limits=ocr.existing.Limits(),
        work=tmp_path,
    )
    assert result.state == "unknown" and result.warnings == ("unsupported_language_data",)


@pytest.mark.parametrize("failure", ["timeout", "memory_limit", "output_limit", "missing_runtime"])
def test_frozen_ocr_failures_remain_isolated(tmp_path, monkeypatch, failure):
    path, native, scope = actual_native(tmp_path)
    monkeypatch.setitem(sys.modules, "psutil", __import__("types").SimpleNamespace())

    def fail(*args):
        raise ocr.existing.BoundedFailure(failure)

    monkeypatch.setattr(ocr.existing, "ocr_page", fail)
    before = native.to_dict()
    result = ocr.selective_page(
        path,
        native,
        request(scope),
        runtime=local_runtime(tmp_path),
        limits=ocr.existing.Limits(),
        work=tmp_path,
    )
    assert result.state == "failed" and result.warnings == (failure,)
    assert native.to_dict() == before


def test_multilingual_region_render_uses_real_transform_and_local_models(tmp_path, monkeypatch):
    path, native, scope = actual_native(tmp_path)
    runtime = local_runtime(tmp_path)
    for name in ("rus", "kaz"):
        (tmp_path / (name + ".traineddata")).write_bytes(b"fixture-language-model")
    monkeypatch.setitem(sys.modules, "psutil", __import__("types").SimpleNamespace())
    calls = []

    def command(args, work, limits):
        calls.append(args)
        if args[0] == runtime.renderer:
            Path(args[-1] + ".pgm").write_bytes(b"P5\n2 2\n255\n\x00\x00\x00\x00")
        else:
            Path(args[2] + ".txt").write_text("Мән -1,25 kg", encoding="utf-8")
        return {"exit_code": 0}

    monkeypatch.setattr(ocr.existing, "command", command)
    req = request(scope, languages=("ru", "kk", "en"), bbox=(72.0, 700.0, 144.0, 720.0))
    result = ocr.selective_page(
        path,
        native,
        req,
        runtime=runtime,
        limits=replace(ocr.existing.Limits(), dpi=72),
        work=tmp_path,
    )
    assert result.state == "needs_review" and result.literal == "Мән -1,25 kg"
    assert calls[0][calls[0].index("-x") + 1] == "72"
    assert calls[0][calls[0].index("-y") + 1] == "72"
    assert calls[1][calls[1].index("-l") + 1] == "rus+kaz+eng"
    assert result.locator == req.locator and not list(tmp_path.glob("region-*"))


def test_invalid_region_pixel_budget_stops_before_render(tmp_path, monkeypatch):
    path, native, scope = actual_native(tmp_path)
    monkeypatch.setitem(sys.modules, "psutil", __import__("types").SimpleNamespace())
    monkeypatch.setattr(ocr.existing, "command", lambda *a: pytest.fail("rendered"))
    result = ocr.selective_page(
        path,
        native,
        request(scope, bbox=(0.0, 0.0, 612.0, 792.0)),
        runtime=local_runtime(tmp_path),
        limits=replace(ocr.existing.Limits(), max_pixels=1),
        work=tmp_path,
    )
    assert result.warnings == ("pixel_limit",)
