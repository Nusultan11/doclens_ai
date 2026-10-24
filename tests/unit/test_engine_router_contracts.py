"""Router behavior reconciled with exact pins; capabilities never grant trust."""

from dataclasses import replace

import pytest
from openpyxl import Workbook

from doclens_ai.extraction.engines import (
    EngineCapability,
    EngineRegistry,
    EngineRoute,
    EngineRoutingError,
    default_registry,
    default_route,
    select_format,
)
from doclens_ai.extraction.models import DocumentFormat
from tests.unit.test_extraction_engines import FakeWordsIR, pin


def test_default_registry_is_native_only_and_has_no_implicit_ocr():
    registry = default_registry()
    assert [d.name for d in registry.descriptors] == ["native"]
    assert registry.resolve(
        default_route().engines[0], DocumentFormat.PDF
    ).descriptor.capabilities == frozenset({EngineCapability.NATIVE_TEXT})
    with pytest.raises(EngineRoutingError, match="capabilities"):
        registry.resolve(
            default_route().engines[0],
            DocumentFormat.PDF,
            require=frozenset({EngineCapability.OCR}),
        )


def test_explicit_registration_rejects_duplicates_unknown_pins_and_formats():
    registry = EngineRegistry()
    engine = FakeWordsIR()
    registry.register(engine)
    assert registry.descriptors == (engine.descriptor,)
    assert registry.resolve(pin(engine), DocumentFormat.PDF) is engine
    with pytest.raises(EngineRoutingError, match="duplicate"):
        registry.register(engine)
    with pytest.raises(EngineRoutingError, match="unavailable"):
        registry.resolve(pin(engine).model_copy(update={"revision": "unknown"}), DocumentFormat.PDF)
    with pytest.raises(EngineRoutingError, match="format"):
        registry.resolve(pin(engine), DocumentFormat.XLSX)


@pytest.mark.parametrize(
    "path,fmt",
    [
        ("source.PDF", DocumentFormat.PDF),
        ("source.docx", DocumentFormat.DOCX),
        ("source.xlsx", DocumentFormat.XLSX),
    ],
)
def test_strict_extension_selection(path, fmt):
    assert select_format(path) is fmt


@pytest.mark.parametrize("path", ["source", "source.exe", "source.pdf.exe"])
def test_unsupported_extension_is_a_routing_error(path):
    with pytest.raises(EngineRoutingError, match="unsupported"):
        select_format(path)


def test_native_xlsx_equivalence_through_single_registry(tmp_path):
    from doclens_ai.extraction.parsers import extract_file

    path = tmp_path / "source.xlsx"
    book = Workbook()
    book.active["A1"] = "safe fixture"
    book.active["B1"] = "00123"
    book.save(path)
    assert (
        default_registry().extract(path, route=default_route())[0].native.to_dict()
        == extract_file(path).to_dict()
    )


def test_capability_selection_preserves_candidate_observations_without_review(tmp_path):
    engine = FakeWordsIR()
    engine.descriptor = replace(engine.descriptor, capabilities=frozenset({EngineCapability.OCR}))
    path = tmp_path / "source.pdf"
    path.write_bytes(b"%PDF-1.7 fixture")
    route = EngineRoute(
        engines=(pin(engine),),
        runtime_manifest_json=default_route().runtime_manifest_json,
        required_capabilities=(EngineCapability.OCR,),
    )
    observations = EngineRegistry((engine,)).extract(path, route=route)
    assert observations[0].elements[0].text == "-10 kg"
    assert observations[0].native is None
    assert observations[0].source.workspace_id is None
    assert (
        observations[0].elements[0].provenance
        == engine.extract(path, options_json="{}").elements[0].provenance
    )


def test_requirements_change_fingerprint_and_are_canonical():
    route = default_route()
    required = route.model_copy(update={"required_capabilities": (EngineCapability.NATIVE_TEXT,)})
    assert route.version == "1.2"
    assert required.fingerprint() != route.fingerprint()
    assert EngineRoute.model_validate_json(required.model_dump_json()) == required
    for requirements in [
        (EngineCapability.OCR, EngineCapability.OCR),
        (EngineCapability.OCR, EngineCapability.NATIVE_TEXT),
    ]:
        payload = route.model_dump(mode="json")
        payload["required_capabilities"] = requirements
        with pytest.raises(ValueError, match="canonical"):
            EngineRoute.model_validate(payload)
    payload["required_capabilities"] = ["invented"]
    with pytest.raises(ValueError):
        EngineRoute.model_validate(payload)


def test_every_selected_pin_is_capability_checked_before_extraction(tmp_path):
    first, second = FakeWordsIR(), FakeWordsIR()
    first.descriptor = replace(first.descriptor, capabilities=frozenset({EngineCapability.OCR}))
    second.descriptor = replace(second.descriptor, name="no-ocr")
    route = EngineRoute(
        engines=(pin(first), pin(second)),
        runtime_manifest_json=default_route().runtime_manifest_json,
        required_capabilities=(EngineCapability.OCR,),
    )
    # Missing source proves no engine ran before the later incompatible pin was rejected.
    with pytest.raises(EngineRoutingError, match="capabilities"):
        EngineRegistry((first, second)).extract(tmp_path / "missing.pdf", route=route)


def test_descriptor_capability_drift_is_rechecked():
    engine = FakeWordsIR()
    engine.descriptor = replace(engine.descriptor, capabilities=frozenset({EngineCapability.OCR}))
    registry = EngineRegistry((engine,))
    original = pin(engine)
    engine.descriptor = replace(engine.descriptor, capabilities=frozenset())
    with pytest.raises(EngineRoutingError, match="capabilities"):
        registry.resolve(original, DocumentFormat.PDF, require=frozenset({EngineCapability.OCR}))


@pytest.mark.parametrize(
    "update",
    [
        {"name": ""},
        {"revision": ""},
        {"implementation_sha256": "unknown"},
        {"formats": frozenset()},
        {"capabilities": frozenset({"invented"})},
    ],
)
def test_invalid_descriptors_are_rejected(update):
    descriptor = FakeWordsIR().descriptor
    with pytest.raises(ValueError):
        replace(descriptor, **update)


def test_exact_versions_can_coexist_without_name_based_fallback():
    first, second = FakeWordsIR(), FakeWordsIR()
    second.descriptor = replace(second.descriptor, revision="fixture-r2")
    registry = EngineRegistry((first, second))
    assert registry.resolve(pin(first), DocumentFormat.PDF) is first
    assert registry.resolve(pin(second), DocumentFormat.PDF) is second


def test_required_capabilities_change_processing_fingerprint():
    from doclens_ai.services.processing import default_processing_configuration_fingerprint

    route = default_route()
    required = route.model_copy(update={"required_capabilities": (EngineCapability.NATIVE_TEXT,)})
    assert default_processing_configuration_fingerprint(
        required
    ) != default_processing_configuration_fingerprint(route)


@pytest.mark.parametrize("version", ["1.0", "1.1"])
def test_historical_routes_cannot_silently_execute_with_new_defaults(version):
    payload = default_route().model_dump(mode="json")
    payload["version"] = version
    payload.pop("required_capabilities")
    with pytest.raises(ValueError):
        EngineRoute.model_validate(payload)
