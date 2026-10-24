"""Additive DocumentIR v2 wire contract. Observations are not trusted evidence.

The v1 ExtractionResult API remains unchanged. Native observations retain that
entire result, including unsupported metadata, rather than guessing missing facts.
"""

from __future__ import annotations

import math
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from doclens_ai.extraction.models import DocumentFormat, ExtractionResult, SourceLocation

IR_VERSION = "2.0"
ADAPTER_VERSION = "2.0"
# These relationships must survive as one evidence unit. Reading order links
# independent units and never makes an entire document an atomic chunk.
ATOMIC_RELATION_KINDS = frozenset(
    {"contains", "header_value", "row_value", "unit_value", "period_value", "formula_value"}
)
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Coordinate = Annotated[float, Field(strict=True)]


class Contract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SourceIdentity(Contract):
    sha256: Digest | None = None
    size_bytes: Annotated[int, Field(strict=True, ge=0)] | None = None
    document_format: DocumentFormat | None = None
    # IDs must be supplied by the caller; a content hash never establishes scope.
    document_version_id: str | None = None
    workspace_id: str | None = None


class Geometry(Contract):
    """An observed rectangle in a named page coordinate system, never inferred."""

    coordinate_system: Literal["top_left_points", "bottom_left_points", "top_left_pixels"]
    x0: Coordinate
    y0: Coordinate
    x1: Coordinate
    y1: Coordinate
    page_width: Coordinate
    page_height: Coordinate

    @model_validator(mode="after")
    def bounds(self) -> Geometry:
        values = (self.x0, self.y0, self.x1, self.y1, self.page_width, self.page_height)
        if not all(math.isfinite(value) for value in values):
            raise ValueError("geometry must be finite")
        if not (0 <= self.x0 < self.x1 <= self.page_width):
            raise ValueError("invalid horizontal geometry")
        if not (0 <= self.y0 < self.y1 <= self.page_height):
            raise ValueError("invalid vertical geometry")
        return self


class Provenance(Contract):
    engine: str = Field(min_length=1)
    revision: str = Field(min_length=1)
    implementation_sha256: Digest
    adapter_version: str = ADAPTER_VERSION
    observation_id: str = Field(min_length=1)
    confidence: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)] | None = None


class Verification(Contract):
    """A claim retained for inspection; independent validation grants eligibility."""

    state: Literal["unknown", "verified", "failed", "unsupported", "unresolved"] = "unknown"
    verifier: str | None = None
    revision: str | None = None
    evidence_sha256: Digest | None = None
    reason: str | None = None


class Element(Contract):
    id: str = Field(min_length=1)
    source: SourceLocation
    provenance: Provenance
    geometry: Geometry | None = None
    verification: Verification = Verification()
    state: Literal["complete", "partial", "failed", "unsupported", "unresolved"] = "complete"
    reason: str | None = None


class TextElement(Element):
    kind: Literal["text"] = "text"
    text: str


class LayoutElement(Element):
    kind: Literal["section", "layout"]
    text: str | None = None
    role: str | None = None


class TableElement(Element):
    kind: Literal["table"] = "table"
    name: str | None = None
    reference: str | None = None


class CellElement(Element):
    kind: Literal["cell"] = "cell"
    text: str | None = None
    row_index: Annotated[int, Field(strict=True, ge=0)]
    column_index: Annotated[int, Field(strict=True, ge=0)]
    row_span: Annotated[int, Field(strict=True, ge=1)] = 1
    column_span: Annotated[int, Field(strict=True, ge=1)] = 1
    raw_value: str | None = None
    data_type: str | None = None
    number_format: str | None = None
    formula: str | None = None
    cached_value: str | None = None


class VisualElement(Element):
    kind: Literal["figure", "image"]
    caption: str | None = None
    content_sha256: Digest | None = None


class FormulaElement(Element):
    kind: Literal["formula"] = "formula"
    expression: str | None = None
    cached_value: str | None = None


DocumentElement = Annotated[
    TextElement | LayoutElement | TableElement | CellElement | VisualElement | FormulaElement,
    Field(discriminator="kind"),
]


class Relation(Contract):
    id: str = Field(min_length=1)
    kind: Literal[
        "contains",
        "header_value",
        "row_value",
        "unit_value",
        "period_value",
        "formula_value",
        "reading_order",
        "duplicate",
        "conflict",
    ]
    source_id: str
    target_id: str
    provenance: Provenance
    verification: Verification = Verification()


class Issue(Contract):
    code: str = Field(min_length=1)
    state: Literal["warning", "partial", "failed", "unsupported", "unresolved"]
    source: SourceLocation | None = None
    element_id: str | None = None
    reason: str | None = None


class DocumentIR(Contract):
    schema_version: Literal["2.0"] = IR_VERSION
    source: SourceIdentity
    state: Literal["complete", "partial", "failed", "unsupported", "unresolved"]
    elements: tuple[DocumentElement, ...] = ()
    relations: tuple[Relation, ...] = ()
    issues: tuple[Issue, ...] = ()
    native: ExtractionResult | None = None

    @field_validator("native", mode="before")
    @classmethod
    def native_wire_kind(cls, value: object) -> object:
        # v1 emits init=False discriminators which dataclass constructors do not
        # accept. Validate and remove just those derived fields on wire import.
        if not isinstance(value, dict) or "blocks" not in value:
            return value
        if not isinstance(value["blocks"], list | tuple):
            raise ValueError("native blocks must be a sequence")
        blocks = []
        for block in value["blocks"]:
            if not isinstance(block, dict):
                raise ValueError("native block must be an object")
            expected = "table" if "rows" in block else "text"
            if block.get("kind", expected) != expected:
                raise ValueError("native block discriminator mismatch")
            blocks.append({key: item for key, item in block.items() if key != "kind"})
        return value | {"blocks": blocks}

    @model_validator(mode="after")
    def references(self) -> DocumentIR:
        ids = {element.id for element in self.elements}
        if len(ids) != len(self.elements):
            raise ValueError("duplicate element identity")
        if len({relation.id for relation in self.relations}) != len(self.relations):
            raise ValueError("duplicate relation identity")
        if any(r.source_id not in ids or r.target_id not in ids for r in self.relations):
            raise ValueError("dangling relation")
        if any(
            issue.element_id is not None and issue.element_id not in ids for issue in self.issues
        ):
            raise ValueError("dangling issue")
        if any(
            element.geometry is not None and element.source.page_number is None
            for element in self.elements
        ):
            raise ValueError("page geometry requires an observed page locator")
        return self
