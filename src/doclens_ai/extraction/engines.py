"""Deterministic extraction engine routing. Optional engines are explicitly registered.

No OCR or model is loaded by this module. The native parser stays the only
production route until an alternative is reviewed and explicitly registered.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Callable, Protocol

from doclens_ai.extraction.models import DocumentFormat, ExtractionResult


class EngineCapability(StrEnum):
    NATIVE_TEXT = "native_text"
    STRUCTURED_TABLES = "structured_tables"
    SPATIAL_LOCATORS = "spatial_locators"
    OCR = "ocr"


class ExtractionEngine(Protocol):
    @property
    def descriptor(self) -> EngineDescriptor: ...

    def extract(self, source: Path) -> ExtractionResult: ...


@dataclass(frozen=True, slots=True)
class EngineDescriptor:
    name: str
    version: str
    formats: frozenset[DocumentFormat]
    capabilities: frozenset[EngineCapability]
    reviewed_for_production: bool = False

    def __post_init__(self) -> None:
        if not self.name or not self.version or not self.formats:
            raise ValueError("engine requires an identity, version and formats")


@dataclass(frozen=True, slots=True)
class NativeEngine:
    """Compatibility adapter; imports optional parser dependencies on invocation."""

    descriptor: EngineDescriptor = EngineDescriptor(
        name="native",
        version="1.1",
        formats=frozenset(DocumentFormat),
        capabilities=frozenset({EngineCapability.NATIVE_TEXT}),
        reviewed_for_production=True,
    )

    def extract(self, source: Path) -> ExtractionResult:
        from doclens_ai.extraction.parsers import extract_file

        return extract_file(source)


class EngineRegistrationError(ValueError):
    """Invalid engine registration or routing request."""


class EngineRegistry:
    """Explicit allowlist of available engines; no implicit model fallbacks."""

    def __init__(self, engines: tuple[ExtractionEngine, ...] = ()) -> None:
        self._engines: dict[str, ExtractionEngine] = {}
        for engine in engines:
            self.register(engine)

    def register(self, engine: ExtractionEngine) -> None:
        descriptor = engine.descriptor
        if descriptor.name in self._engines:
            raise EngineRegistrationError("duplicate extraction engine")
        if not descriptor.name or not descriptor.version or not descriptor.formats:
            raise EngineRegistrationError("invalid extraction engine descriptor")
        self._engines[descriptor.name] = engine

    def route(
        self,
        document_format: DocumentFormat,
        *,
        engine_name: str = "native",
        require: frozenset[EngineCapability] = frozenset(),
        production: bool = True,
    ) -> ExtractionEngine:
        engine = self._engines.get(engine_name)
        if engine is None:
            raise EngineRegistrationError("extraction engine is not registered")
        descriptor = engine.descriptor
        if document_format not in descriptor.formats:
            raise EngineRegistrationError("extraction engine does not support this format")
        if not require.issubset(descriptor.capabilities):
            raise EngineRegistrationError("extraction engine lacks required capabilities")
        if production and not descriptor.reviewed_for_production:
            raise EngineRegistrationError("extraction engine is not production-approved")
        return engine

    @property
    def descriptors(self) -> tuple[EngineDescriptor, ...]:
        return tuple(engine.descriptor for engine in self._engines.values())


def default_registry() -> EngineRegistry:
    """Provide the unchanged native baseline without loading optional models."""

    return EngineRegistry((NativeEngine(),))


def select_format(path: str | Path) -> DocumentFormat:
    """Strict extension-based routing only; the native parser validates file bytes."""

    try:
        return DocumentFormat(Path(path).suffix.lstrip(".").lower())
    except ValueError as exc:
        raise EngineRegistrationError("unsupported extraction document format") from exc


def extract_routed(
    source: str | Path,
    *,
    registry: EngineRegistry | None = None,
    engine_name: str = "native",
    production: bool = True,
    require: frozenset[EngineCapability] = frozenset(),
) -> ExtractionResult:
    """Route through an explicit engine. Never merge or silently downgrade evidence."""

    source_path = Path(source)
    selected = (registry if registry is not None else default_registry()).route(
        select_format(source_path),
        engine_name=engine_name,
        require=require,
        production=production,
    )
    return selected.extract(source_path)
