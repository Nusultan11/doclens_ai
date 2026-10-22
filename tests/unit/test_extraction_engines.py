"""Exact route pins and source-aware reconciliation, using synthetic engines."""

import hashlib
from dataclasses import replace
from pathlib import Path

import pytest
from docx import Document

from doclens_ai.extraction.engines import (
    EngineDescriptor,
    EnginePin,
    EngineRegistry,
    EngineRoutingError,
    NativeEngine,
    default_registry,
    default_route,
)
from doclens_ai.extraction.ir import DocumentIR, Provenance, SourceIdentity
from doclens_ai.extraction.models import DocumentFormat
from doclens_ai.extraction.reconciliation import reconcile
from tests.unit.test_document_ir import (
    FakeRegionsEngine,
    FakeWordsEngine,
    adapt_regions,
    adapt_words,
)


class FakeWordsIR:
    descriptor = EngineDescriptor(
        "fake-words",
        "fixture-r1",
        hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        frozenset({DocumentFormat.PDF}),
    )

    def extract(self, source: Path, *, options_json: str) -> DocumentIR:
        payload = source.read_bytes()
        element = adapt_words(FakeWordsEngine().extract())
        return DocumentIR(
            source=SourceIdentity(
                sha256=hashlib.sha256(payload).hexdigest(),
                size_bytes=len(payload),
                document_format=DocumentFormat.PDF,
            ),
            state="complete",
            elements=(
                element.model_copy(
                    update={
                        "provenance": Provenance(
                            engine=self.descriptor.name,
                            revision=self.descriptor.revision,
                            implementation_sha256=self.descriptor.implementation_sha256,
                            observation_id="fake-output",
                        )
                    }
                ),
            ),
        )


class FakeRegionsIR(FakeWordsIR):
    descriptor = replace(FakeWordsIR.descriptor, name="fake-regions")

    def extract(self, source: Path, *, options_json: str) -> DocumentIR:
        ir = super().extract(source, options_json=options_json)
        element = adapt_regions(FakeRegionsEngine().extract()).model_copy(
            update={"provenance": ir.elements[0].provenance}
        )
        return ir.model_copy(update={"elements": (element,)})


def pin(engine):
    d = engine.descriptor
    return EnginePin(
        name=d.name, revision=d.revision, implementation_sha256=d.implementation_sha256
    )


def test_default_native_route_matches_parser_and_has_effective_options(tmp_path):
    from doclens_ai.extraction.parsers import extract_file

    path = tmp_path / "source.docx"
    document = Document()
    document.add_paragraph("Native behavior must remain the default.")
    document.save(path)
    routed = default_registry().extract(path, route=default_route())
    assert routed[0].native.to_dict() == extract_file(path).to_dict()
    assert "max_file_bytes" in default_route().engines[0].options_json
    assert default_route().fingerprint() == default_route().fingerprint()


def test_unknown_or_changed_exact_pin_never_falls_back():
    native = NativeEngine()
    registry = default_registry()
    original = default_route().engines[0]
    for change in ({"name": "missing"}, {"revision": "other"}, {"implementation_sha256": "f" * 64}):
        with pytest.raises(EngineRoutingError, match="unavailable"):
            registry.resolve(original.model_copy(update=change), DocumentFormat.PDF)
    with pytest.raises(EngineRoutingError, match="duplicate"):
        EngineRegistry((native, native))


def test_native_route_rejects_missing_effective_options(tmp_path):
    with pytest.raises(EngineRoutingError, match="every effective"):
        NativeEngine().extract(tmp_path / "missing.pdf", options_json="{}")


@pytest.mark.parametrize("field,value", [("options_json", '{"lang":"kk"}'), ("revision", "other")])
def test_effective_options_and_revision_change_route_fingerprint(field, value):
    route = default_route()
    altered = route.model_copy(
        update={"engines": (route.engines[0].model_copy(update={field: value}),)}
    )
    assert altered.fingerprint() != route.fingerprint()


def test_registry_rechecks_descriptor_and_provenance_and_unsupported_preprocessing(tmp_path):
    engine = FakeWordsIR()
    registry = EngineRegistry((engine,))
    original = pin(engine)
    engine.descriptor = replace(engine.descriptor, revision="changed")
    with pytest.raises(EngineRoutingError, match="changed"):
        registry.resolve(original, DocumentFormat.PDF)
    with pytest.raises(EngineRoutingError):
        default_registry().extract(
            tmp_path / "source.pdf",
            route=default_route().model_copy(update={"preprocessing": ("unimplemented",)}),
        )


def test_reconcile_keeps_conflicting_values_confidences_and_exact_source_locations(tmp_path):
    engine = FakeWordsIR()
    path = tmp_path / "source.pdf"
    path.write_bytes(b"%PDF-1.7\nfixture\n%%EOF")
    first = engine.extract(path, options_json="{}")
    second = first.model_copy(
        update={
            "elements": (
                first.elements[0].model_copy(
                    update={
                        "text": "-999 kg",
                        "provenance": first.elements[0].provenance.model_copy(
                            update={"confidence": 0.99}
                        ),
                    }
                ),
            )
        }
    )
    expected = first.source.model_copy(
        update={"workspace_id": "workspace", "document_version_id": "version"}
    )
    merged = reconcile((first, second), expected=expected)
    assert [e.text for e in merged.elements] == ["-10 kg", "-999 kg"]
    assert merged.elements[1].provenance.confidence == 0.99
    assert merged.elements[0].source == first.elements[0].source
    assert merged.elements[0].geometry == first.elements[0].geometry
    assert merged.relations[-1].kind == "conflict"
    assert merged.issues and merged.state == "partial"
    duplicate = reconcile((first, first), expected=expected)
    assert duplicate.relations[-1].kind == "duplicate"
    for field, value in (("sha256", "c" * 64), ("workspace_id", "other")):
        bad = first.model_copy(update={"source": first.source.model_copy(update={field: value})})
        with pytest.raises(ValueError, match="mismatch"):
            reconcile((first, bad), expected=expected)


def test_all_failed_observations_preserve_failed_document_state(tmp_path):
    path = tmp_path / "failed.pdf"
    path.write_bytes(b"%PDF-1.7\nfailed fixture\n%%EOF")
    ir = (
        FakeWordsIR()
        .extract(path, options_json="{}")
        .model_copy(update={"state": "failed", "elements": ()})
    )
    assert reconcile((ir,), expected=ir.source).state == "failed"
