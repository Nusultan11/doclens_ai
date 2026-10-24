"""Independent, fail-closed observation admission; not a factual verifier.

Review records and engine/reviewer allowlists are trusted caller inputs. They must
be loaded from an authorized review/configuration store, never from engine output
or request JSON. Matching a review proves only the recorded approval and structural
checks; it does not itself establish model fidelity or production qualification.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, fields
from typing import Literal

from doclens_ai.extraction.ir import (
    ATOMIC_RELATION_KINDS,
    CellElement,
    DocumentIR,
    Element,
    FormulaElement,
    Relation,
    SourceIdentity,
    TableElement,
)
from doclens_ai.extraction.models import DocumentFormat

VALIDATOR_VERSION = "2.1"


def canonical_digest(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode()
    ).hexdigest()


def observation_digest(subject: Element | Relation) -> str:
    return canonical_digest(subject.model_dump(mode="json"))


@dataclass(frozen=True)
class ReviewDecision:
    subject_id: str
    subject_kind: Literal["element", "relation"]
    observation_sha256: str
    state: Literal["verified", "failed", "unresolved", "unsupported"]


@dataclass(frozen=True)
class EvidenceReview:
    source: SourceIdentity
    document_sha256: str
    reviewer: str
    revision: str
    decisions: tuple[ReviewDecision, ...]


@dataclass(frozen=True)
class EvidencePolicy:
    # These are exact engine/revision/implementation hashes, not capability claims.
    allowed_engines: frozenset[tuple[str, str, str]] = frozenset()
    trusted_reviewers: frozenset[tuple[str, str]] = frozenset()
    allow_verified_pdf: bool = False
    allowed_kinds: frozenset[str] = frozenset({"text", "section", "table", "cell", "formula"})
    required_kinds: frozenset[str] = frozenset()
    required_relations: frozenset[str] = frozenset()
    max_elements: int = 100_000
    max_relations: int = 200_000

    def __post_init__(self) -> None:
        if self.max_elements <= 0 or self.max_relations <= 0:
            raise ValueError("evidence limits must be positive")


DEFAULT_EVIDENCE_POLICY = EvidencePolicy()


def evidence_policy_fingerprint(policy: EvidencePolicy) -> str:
    return canonical_digest(
        {
            key: sorted(value) if isinstance(value, frozenset) else value
            for key, value in asdict(policy).items()
        }
    )


@dataclass(frozen=True)
class EvidenceValidation:
    allowed: tuple[str, ...]
    rejected: tuple[tuple[str, tuple[str, ...]], ...]
    global_reasons: tuple[str, ...]
    fingerprint: str
    validator_version: str = VALIDATOR_VERSION


def _engine_allowed(subject: Element | Relation, policy: EvidencePolicy) -> bool:
    p = subject.provenance
    return (p.engine, p.revision, p.implementation_sha256) in policy.allowed_engines


def _locator_valid(element: Element, fmt: DocumentFormat) -> bool:
    loc = element.source
    for key in (
        "page_number",
        "block_index",
        "sheet_index",
        "table_index",
        "row_index",
        "column_index",
    ):
        value = getattr(loc, key)
        if value is not None and (
            type(value) is not int or value < (1 if key == "page_number" else 0)
        ):
            return False
    if loc.xml_path is not None and any(type(n) is not int or n < 0 for n in loc.xml_path):
        return False
    if fmt is DocumentFormat.PDF:
        return loc.page_number is not None and all(
            getattr(loc, field) is None
            for field in (
                "part_uri",
                "xml_path",
                "sheet_index",
                "sheet_name",
                "cell_coordinate",
                "note_id",
                "relationship_id",
            )
        )
    if element.geometry is not None or loc.page_number is not None:
        return False  # Office adapters cannot invent pages or page geometry.
    if fmt is DocumentFormat.DOCX:
        return (
            loc.part_uri is not None
            and loc.part_uri.startswith("/")
            and ".." not in loc.part_uri.split("/")
            and loc.xml_path is not None
            and loc.sheet_index is None
            and loc.sheet_name is None
            and loc.cell_coordinate is None
        )
    if fmt is DocumentFormat.XLSX:
        if not (
            loc.sheet_index is not None
            and loc.sheet_name
            and loc.cell_coordinate
            and loc.row_index is not None
            and loc.column_index is not None
        ):
            return False
        match = re.fullmatch(r"([A-Z]{1,3})([1-9][0-9]{0,6})", loc.cell_coordinate)
        if match is None:
            return False
        column = 0
        for character in match[1]:
            column = column * 26 + ord(character) - ord("A") + 1
        return (
            int(match[2]) == loc.row_index + 1 <= 1_048_576
            and column == loc.column_index + 1 <= 16_384
        )
    return False


def _element_reasons(element: Element, fmt: DocumentFormat, policy: EvidencePolicy) -> list[str]:
    reasons = []
    if element.state != "complete":
        reasons.append("incomplete_element")
    if element.verification.state in {"failed", "unsupported", "unresolved"}:
        reasons.append("negative_verification")
    if element.kind not in policy.allowed_kinds:
        reasons.append("unsupported_capability")
    if not _engine_allowed(element, policy):
        reasons.append("engine_not_allowed")
    if not _locator_valid(element, fmt):
        reasons.append("invalid_locator")
    if isinstance(element, CellElement):
        if (
            element.row_index != element.source.row_index
            or element.column_index != element.source.column_index
        ):
            reasons.append("cell_locator_mismatch")
        if element.data_type == "e" or (
            element.formula is not None and element.cached_value is None
        ):
            reasons.append("unusable_cell_value")
    if isinstance(element, FormulaElement) and (
        not element.expression or element.cached_value is None
    ):
        reasons.append("unusable_formula")
    for field in ("text", "raw_value", "formula", "expression", "cached_value", "caption"):
        value = getattr(element, field, None)
        if value is not None and any(
            c == "\ufffd" or 0xD800 <= ord(c) <= 0xDFFF or ord(c) < 32 and c not in "\t\n\r"
            for c in value
        ):
            reasons.append("corrupt_text")
    return reasons


def validate_ir(
    ir: DocumentIR,
    *,
    expected: SourceIdentity,
    review: EvidenceReview | None,
    policy: EvidencePolicy = DEFAULT_EVIDENCE_POLICY,
) -> EvidenceValidation:
    # Revalidate even in-memory model_copy/model_construct inputs before admission.
    ir = DocumentIR.model_validate_json(ir.model_dump_json())
    global_reasons = []
    if (
        not expected.sha256
        or expected.size_bytes is None
        or expected.size_bytes <= 0
        or expected.document_format is None
        or not expected.workspace_id
        or not expected.document_version_id
    ):
        global_reasons.append("incomplete_source_identity")
    if ir.source != expected:
        global_reasons.append("source_identity_mismatch")
    if ir.native is not None and (
        ir.native.source_sha256 != expected.sha256
        or ir.native.source_size_bytes != expected.size_bytes
        or ir.native.document_format != expected.document_format
    ):
        global_reasons.append("native_source_identity_mismatch")
    if ir.state not in {"complete", "partial"}:
        global_reasons.append("unusable_document")
    if expected.document_format is DocumentFormat.PDF and not policy.allow_verified_pdf:
        global_reasons.append("pdf_not_enabled")
    if len(ir.elements) > policy.max_elements or len(ir.relations) > policy.max_relations:
        global_reasons.append("evidence_limit")
    if review is None:
        global_reasons.append("missing_review")
    elif (
        review.source != expected
        or review.document_sha256 != canonical_digest(ir.model_dump(mode="json"))
        or (review.reviewer, review.revision) not in policy.trusted_reviewers
    ):
        global_reasons.append("untrusted_review")
    decisions = (
        {} if review is None else {(d.subject_kind, d.subject_id): d for d in review.decisions}
    )
    if review is not None and len(decisions) != len(review.decisions):
        global_reasons.append("duplicate_review_decision")
    if any(i.element_id is None and i.state != "warning" for i in ir.issues):
        global_reasons.append("unresolved_document_issue")

    def reviewed(subject: Element | Relation, kind: str) -> bool:
        decision = decisions.get((kind, subject.id))
        return (
            decision is not None
            and decision.state == "verified"
            and decision.observation_sha256 == observation_digest(subject)
        )

    unresolved_ids = {i.element_id for i in ir.issues if i.state != "warning"}
    rejected = {}
    for element in ir.elements:
        reasons = _element_reasons(element, expected.document_format, policy)
        if not reviewed(element, "element"):
            reasons.append("element_not_reviewed")
        if element.id in unresolved_ids:
            reasons.append("unresolved_element_issue")
        if reasons:
            rejected[element.id] = set(reasons)
    # Exact native addresses can have multiple observations. Never choose an owner
    # or discard contradictions merely because one engine has higher confidence.
    locations: dict[tuple, list[str]] = {}
    for element in ir.elements:
        if isinstance(element, TableElement):
            continue
        key = (
            element.kind,
            tuple(getattr(element.source, f.name) for f in fields(element.source)),
            element.geometry,
        )
        locations.setdefault(key, []).append(element.id)
    for ids in locations.values():
        if len(ids) > 1:
            for identity in ids:
                rejected.setdefault(identity, set()).add("ambiguous_observation_ownership")
    by_id = {e.id: e for e in ir.elements}
    children: dict[str, list[CellElement]] = {}
    owners: dict[str, list[str]] = {}
    edges = []
    for relation in ir.relations:
        if relation.kind in ATOMIC_RELATION_KINDS or relation.kind in {"conflict", "duplicate"}:
            edges.append((relation.source_id, relation.target_id))
        parent, child = by_id[relation.source_id], by_id[relation.target_id]
        bad_type = False
        if relation.kind == "contains" and isinstance(parent, TableElement):
            if not isinstance(child, CellElement):
                bad_type = True
            else:
                children.setdefault(parent.id, []).append(child)
                owners.setdefault(child.id, []).append(parent.id)
                bad_type = any(
                    getattr(parent.source, field) != getattr(child.source, field)
                    for field in ("page_number", "part_uri", "sheet_index", "table_index")
                )
        if relation.kind in {
            "header_value",
            "row_value",
            "unit_value",
            "period_value",
            "formula_value",
        }:
            bad_type = not isinstance(child, CellElement)
        if relation.kind == "formula_value" and not isinstance(
            parent, FormulaElement | CellElement
        ):
            bad_type = True
        if (
            relation.kind in {"conflict", "duplicate"}
            or bad_type
            or not reviewed(relation, "relation")
            or not _engine_allowed(relation, policy)
            or relation.verification.state in {"failed", "unsupported", "unresolved"}
        ):
            for identity in (relation.source_id, relation.target_id):
                rejected.setdefault(identity, set()).add("unresolved_relation")
    for identity, parents in owners.items():
        if len(parents) > 1:
            rejected.setdefault(identity, set()).add("ambiguous_table_ownership")
    grid_area = 0
    for element in ir.elements:
        if not isinstance(element, TableElement):
            continue
        cells = children.get(element.id, ())
        if not cells:
            rejected.setdefault(element.id, set()).add("missing_table_cells")
        occupied = set()
        for cell in cells:
            grid_area += cell.row_span * cell.column_span
            if grid_area > policy.max_elements:
                rejected.setdefault(element.id, set()).add("table_grid_limit")
                break
            for row in range(cell.row_index, cell.row_index + cell.row_span):
                for column in range(cell.column_index, cell.column_index + cell.column_span):
                    position = (row, column)
                    if position in occupied:
                        rejected.setdefault(element.id, set()).add("overlapping_table_cells")
                    occupied.add(position)
    # Any unsafe member holds its whole atomic evidence group. This also
    # prevents a row/value from being indexed after losing an unreviewed header.
    adjacent = {element.id: [] for element in ir.elements}
    for a, b in edges:
        adjacent[a].append(b)
        adjacent[b].append(a)
    pending = list(rejected)
    while pending:
        for identity in adjacent[pending.pop()]:
            if identity not in rejected:
                rejected[identity] = {"unsafe_related_evidence"}
                pending.append(identity)
    eligible = {e.id for e in ir.elements if e.id not in rejected}
    actual_kinds = {e.kind for e in ir.elements if e.id in eligible}
    actual_relations = {
        r.kind for r in ir.relations if r.source_id in eligible and r.target_id in eligible
    }
    if (
        not policy.required_kinds <= actual_kinds
        or not policy.required_relations <= actual_relations
    ):
        global_reasons.append("required_capability_not_validated")
    fingerprint = canonical_digest(
        {
            "validator": VALIDATOR_VERSION,
            "source": expected.model_dump(mode="json"),
            "review": None
            if review is None
            else {
                "reviewer": review.reviewer,
                "revision": review.revision,
                "document_sha256": review.document_sha256,
                "source": review.source.model_dump(mode="json"),
                "decisions": [asdict(d) for d in review.decisions],
            },
            "policy": {
                **asdict(policy),
                "allowed_engines": sorted(policy.allowed_engines),
                "trusted_reviewers": sorted(policy.trusted_reviewers),
                "allowed_kinds": sorted(policy.allowed_kinds),
                "required_kinds": sorted(policy.required_kinds),
                "required_relations": sorted(policy.required_relations),
            },
            "ir_sha256": canonical_digest(ir.model_dump(mode="json")),
        }
    )
    return EvidenceValidation(
        allowed=() if global_reasons else tuple(e.id for e in ir.elements if e.id not in rejected),
        rejected=tuple((key, tuple(sorted(value))) for key, value in sorted(rejected.items())),
        global_reasons=tuple(global_reasons),
        fingerprint=fingerprint,
    )
