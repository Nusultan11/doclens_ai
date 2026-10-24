"""Explicit exact-pin routing, adapted from the design reviewed in draft PR #1.

Registration is an application-owned allowlist, not engine-supplied approval.
No candidate, dependency download, fallback or preprocessing is implicit.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Literal, Protocol

from pydantic import Field, model_validator

from doclens_ai.chunking.models import CHUNKING_SCHEMA_VERSION
from doclens_ai.extraction.adapters import adapt_native
from doclens_ai.extraction.bounded import EXECUTOR_VERSION, ExecutionBudget
from doclens_ai.extraction.ir import (
    ADAPTER_VERSION,
    IR_VERSION,
    Contract,
    Digest,
    DocumentIR,
    Provenance,
)
from doclens_ai.extraction.ir_validation import VALIDATOR_VERSION, canonical_digest
from doclens_ai.extraction.limits import ExtractionLimits
from doclens_ai.extraction.models import DocumentFormat
from doclens_ai.extraction.runtime import extraction_runtime_manifest


class EngineCapability(StrEnum):
    NATIVE_TEXT = "native_text"
    STRUCTURED_TABLES = "structured_tables"
    SPATIAL_LOCATORS = "spatial_locators"
    OCR = "ocr"


class EnginePin(Contract):
    name: str = Field(min_length=1)
    revision: str = Field(min_length=1)
    implementation_sha256: Digest
    # A canonical JSON string is immutable even when it contains nested options.
    options_json: str = "{}"

    @model_validator(mode="after")
    def options(self) -> EnginePin:
        value = json.loads(self.options_json)
        if not isinstance(value, dict) or self.options_json != json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ):
            raise ValueError("effective engine options must be a canonical JSON object")
        return self


class StoredEngineRouteV1(Contract):
    """Exact historical snapshot contract; never infer new execution controls."""

    version: Literal["1.0"] = "1.0"
    engines: tuple[EnginePin, ...] = Field(min_length=1)
    runtime_manifest_json: str
    mode: Literal["native", "verified_ir"] = "native"
    preprocessing: tuple[str, ...] = ()
    ir_version: str = IR_VERSION
    adapter_version: str = ADAPTER_VERSION
    validator_version: str = VALIDATOR_VERSION
    chunker_version: str = CHUNKING_SCHEMA_VERSION
    policy_sha256: Digest | None = None
    review_id: str | None = None
    artifact_version: Literal["1.0"] = "1.0"
    artifact_max_bytes: int = Field(default=64 * 1024 * 1024, gt=0, le=64 * 1024 * 1024)
    ir_chunk_options_json: str = (
        '{"max_characters":1200,"max_chunks":100000,"max_source_characters":5000000}'
    )

    @model_validator(mode="after")
    def chunk_options(self) -> StoredEngineRouteV1:
        value = json.loads(self.ir_chunk_options_json)
        if not isinstance(value, dict) or set(value) != {
            "max_characters",
            "max_chunks",
            "max_source_characters",
        }:
            raise ValueError("IR chunk options must be explicit")
        if any(type(v) is not int or v <= 0 for v in value.values()):
            raise ValueError("IR chunk limits must be positive integers")
        if self.ir_chunk_options_json != json.dumps(value, sort_keys=True, separators=(",", ":")):
            raise ValueError("IR chunk options must be canonical")
        return self

    def fingerprint(self) -> str:
        return canonical_digest(self.model_dump(mode="json"))


class StoredEngineRouteV1_1(StoredEngineRouteV1):
    """Historical bounded route; retain its original fields and fingerprint."""

    version: Literal["1.1"] = "1.1"
    executor_version: Literal["1.0"] = EXECUTOR_VERSION
    execution_budget: ExecutionBudget = Field(default_factory=ExecutionBudget)


class EngineRoute(StoredEngineRouteV1_1):
    version: Literal["1.2"] = "1.2"
    required_capabilities: tuple[EngineCapability, ...] = ()

    @model_validator(mode="after")
    def capabilities(self) -> EngineRoute:
        if self.required_capabilities != tuple(sorted(set(self.required_capabilities))):
            raise ValueError("required capabilities must be unique and in canonical order")
        return self


@dataclass(frozen=True)
class EngineDescriptor:
    name: str
    revision: str
    implementation_sha256: str
    formats: frozenset[DocumentFormat]
    capabilities: frozenset[EngineCapability] = frozenset()

    def __post_init__(self) -> None:
        if (
            not isinstance(self.name, str)
            or not self.name.strip()
            or not isinstance(self.revision, str)
            or not self.revision.strip()
            or not isinstance(self.implementation_sha256, str)
            or re.fullmatch(r"[0-9a-f]{64}", self.implementation_sha256) is None
            or not isinstance(self.formats, frozenset)
            or not self.formats
            or any(not isinstance(fmt, DocumentFormat) for fmt in self.formats)
            or not isinstance(self.capabilities, frozenset)
            or any(not isinstance(capability, EngineCapability) for capability in self.capabilities)
        ):
            raise ValueError("invalid extraction engine descriptor")


class ExtractionEngine(Protocol):
    """Register lightweight adapters; load heavy state only inside extract."""

    @property
    def descriptor(self) -> EngineDescriptor: ...

    def extract(self, source: Path, *, options_json: str) -> DocumentIR: ...


class EngineRoutingError(ValueError):
    pass


class NativeEngine:
    @property
    def descriptor(self) -> EngineDescriptor:
        return EngineDescriptor(
            "native",
            "1.1",
            canonical_digest(extraction_runtime_manifest()),
            frozenset(DocumentFormat),
            frozenset({EngineCapability.NATIVE_TEXT}),
        )

    def extract(self, source: Path, *, options_json: str) -> DocumentIR:
        from doclens_ai.extraction.parsers import extract_file

        options = json.loads(options_json)
        defaults = asdict(ExtractionLimits())
        if options.keys() != defaults.keys() or any(
            type(options[key]) is not type(value) for key, value in defaults.items()
        ):
            raise EngineRoutingError("native route requires every effective parser option")
        descriptor = self.descriptor
        return adapt_native(
            extract_file(source, limits=ExtractionLimits(**options)),
            provenance=Provenance(
                engine=descriptor.name,
                revision=descriptor.revision,
                implementation_sha256=descriptor.implementation_sha256,
                observation_id="native",
            ),
        )


class EngineRegistry:
    def __init__(self, engines: tuple[ExtractionEngine, ...] = ()) -> None:
        self._engines: dict[tuple[str, str, str], ExtractionEngine] = {}
        for engine in engines:
            self.register(engine)

    def register(self, engine: ExtractionEngine) -> None:
        """Application-owned exact-pin allowlist; registration never grants evidence trust."""
        descriptor = engine.descriptor
        if not isinstance(descriptor, EngineDescriptor):
            raise EngineRoutingError("invalid engine registration")
        key = (descriptor.name, descriptor.revision, descriptor.implementation_sha256)
        if key in self._engines:
            raise EngineRoutingError("duplicate engine registration")
        self._engines[key] = engine

    @property
    def descriptors(self) -> tuple[EngineDescriptor, ...]:
        return tuple(engine.descriptor for engine in self._engines.values())

    def resolve(
        self,
        pin: EnginePin,
        fmt: DocumentFormat,
        *,
        require: frozenset[EngineCapability] = frozenset(),
    ) -> ExtractionEngine:
        engine = self._engines.get((pin.name, pin.revision, pin.implementation_sha256))
        if engine is None:
            raise EngineRoutingError("exact engine pin is unavailable")
        descriptor = engine.descriptor
        if (descriptor.name, descriptor.revision, descriptor.implementation_sha256) != (
            pin.name,
            pin.revision,
            pin.implementation_sha256,
        ) or fmt not in descriptor.formats:
            raise EngineRoutingError("engine identity or supported format changed")
        if not require.issubset(descriptor.capabilities):
            raise EngineRoutingError("extraction engine lacks required capabilities")
        return engine

    def extract(self, path: Path, *, route: EngineRoute) -> tuple[DocumentIR, ...]:
        fmt = select_format(path)
        if (
            route.preprocessing
            or route.runtime_manifest_json
            != json.dumps(extraction_runtime_manifest(), sort_keys=True, separators=(",", ":"))
            or route.ir_version != IR_VERSION
            or route.adapter_version != ADAPTER_VERSION
            or route.validator_version != VALIDATOR_VERSION
        ):
            raise EngineRoutingError("unsupported preprocessing or contract version")
        # Resolve all pins before performing any extraction: no partial fallback.
        selected = [
            (pin, self.resolve(pin, fmt, require=frozenset(route.required_capabilities)))
            for pin in route.engines
        ]
        outputs = []
        for pin, engine in selected:
            ir = DocumentIR.model_validate_json(
                engine.extract(path, options_json=pin.options_json).model_dump_json()
            )
            if any(
                (e.provenance.engine, e.provenance.revision, e.provenance.implementation_sha256)
                != (pin.name, pin.revision, pin.implementation_sha256)
                for e in (*ir.elements, *ir.relations)
            ):
                raise EngineRoutingError("engine observation provenance mismatch")
            outputs.append(ir)
        return tuple(outputs)


def select_format(path: str | Path) -> DocumentFormat:
    """Strict extension selection; the selected parser validates the actual bytes."""
    try:
        return DocumentFormat(Path(path).suffix.lstrip(".").lower())
    except ValueError as exc:
        raise EngineRoutingError("unsupported extraction document format") from exc


def default_registry() -> EngineRegistry:
    return EngineRegistry((NativeEngine(),))


def default_route() -> EngineRoute:
    descriptor = NativeEngine().descriptor
    return EngineRoute(
        runtime_manifest_json=json.dumps(
            extraction_runtime_manifest(), sort_keys=True, separators=(",", ":")
        ),
        engines=(
            EnginePin(
                name=descriptor.name,
                revision=descriptor.revision,
                implementation_sha256=descriptor.implementation_sha256,
                options_json=json.dumps(
                    asdict(ExtractionLimits()), sort_keys=True, separators=(",", ":")
                ),
            ),
        ),
    )


def default_route_payload() -> dict:
    return default_route().model_dump(mode="json")
