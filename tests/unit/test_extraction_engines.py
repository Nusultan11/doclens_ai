"""Tests for model-ready extraction routing without loading OCR engines."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from doclens_ai.extraction.engines import (
    EngineCapability,
    EngineDescriptor,
    EngineRegistrationError,
    EngineRegistry,
    NativeEngine,
    default_registry,
    extract_routed,
    select_format,
)
from doclens_ai.extraction.models import DocumentFormat, ExtractionResult, ExtractionStatus


@dataclass(frozen=True)
class StubEngine:
    descriptor: EngineDescriptor

    def extract(self, source: Path) -> ExtractionResult:
        return ExtractionResult(
            schema_version="1.1",
            document_format=DocumentFormat.PDF,
            status=ExtractionStatus.NEEDS_REVIEW,
            source_sha256=None,
            source_size_bytes=None,
        )


def test_native_registry_has_no_implicit_ocr() -> None:
    engines = default_registry()
    assert [item.name for item in engines.descriptors] == ["native"]
    assert engines.route(DocumentFormat.PDF).descriptor.name == "native"
    with pytest.raises(EngineRegistrationError, match="capabilities"):
        engines.route(DocumentFormat.PDF, require=frozenset({EngineCapability.OCR}))


def test_unreviewed_candidate_allowed_only_offline() -> None:
    candidate = StubEngine(
        EngineDescriptor(
            name="candidate",
            version="0.1",
            formats=frozenset({DocumentFormat.PDF}),
            capabilities=frozenset({EngineCapability.OCR}),
        )
    )
    registry = EngineRegistry((NativeEngine(), candidate))
    with pytest.raises(EngineRegistrationError, match="production-approved"):
        registry.route(DocumentFormat.PDF, engine_name="candidate")
    assert registry.route(
        DocumentFormat.PDF,
        engine_name="candidate",
        require=frozenset({EngineCapability.OCR}),
        production=False,
    ) is candidate
    with pytest.raises(EngineRegistrationError, match="format"):
        registry.route(DocumentFormat.XLSX, engine_name="candidate")


def test_registry_rejects_unknown_and_duplicate_engine() -> None:
    registry = EngineRegistry((NativeEngine(),))
    with pytest.raises(EngineRegistrationError, match="duplicate"):
        registry.register(NativeEngine())
    with pytest.raises(EngineRegistrationError, match="not registered"):
        registry.route(DocumentFormat.DOCX, engine_name="missing")


def test_select_format_is_strict() -> None:
    assert select_format("source.PDF") is DocumentFormat.PDF
    assert select_format("source.xlsx") is DocumentFormat.XLSX
    with pytest.raises(EngineRegistrationError, match="unsupported"):
        select_format("source.exe")


def test_candidate_routing_does_not_claim_trusted_evidence(tmp_path: Path) -> None:
    candidate = StubEngine(
        EngineDescriptor(
            name="candidate",
            version="0.1",
            formats=frozenset({DocumentFormat.PDF}),
            capabilities=frozenset({EngineCapability.OCR}),
        )
    )
    path = tmp_path / "sample.pdf"
    path.write_bytes(b"candidate fixture")
    result = extract_routed(
        path,
        registry=EngineRegistry((candidate,)),
        engine_name="candidate",
        production=False,
        require=frozenset({EngineCapability.OCR}),
    )
    assert result.status is ExtractionStatus.NEEDS_REVIEW


def test_native_router_matches_existing_parser(tmp_path: Path) -> None:
    from openpyxl import Workbook

    from doclens_ai.extraction.parsers import extract_file

    path = tmp_path / "source.xlsx"
    workbook = Workbook()
    workbook.active["A1"] = "safe fixture"
    workbook.save(path)

    assert extract_routed(path).to_dict() == extract_file(path).to_dict()
