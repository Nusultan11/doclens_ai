"""Source-bound reconciliation retaining all observations and unresolved ownership."""

import hashlib
from dataclasses import fields
from pathlib import Path

from doclens_ai.extraction.ir import DocumentIR, Issue, Provenance, Relation, SourceIdentity

RECONCILER_VERSION = "1.1"


def reconcile(observations: tuple[DocumentIR, ...], *, expected: SourceIdentity) -> DocumentIR:
    if not observations:
        raise ValueError("missing engine observations")
    elements, relations, issues = [], [], []
    for index, original in enumerate(observations):
        ir = DocumentIR.model_validate_json(original.model_dump_json())
        if (ir.source.sha256, ir.source.size_bytes, ir.source.document_format) != (
            expected.sha256,
            expected.size_bytes,
            expected.document_format,
        ):
            raise ValueError("observation source mismatch")
        if ir.source.workspace_id not in {
            None,
            expected.workspace_id,
        } or ir.source.document_version_id not in {None, expected.document_version_id}:
            raise ValueError("observation scope mismatch")
        prefix = f"observation:{index}:"
        elements.extend(e.model_copy(update={"id": prefix + e.id}) for e in ir.elements)
        relations.extend(
            r.model_copy(
                update={
                    "id": prefix + r.id,
                    "source_id": prefix + r.source_id,
                    "target_id": prefix + r.target_id,
                }
            )
            for r in ir.relations
        )
        issues.extend(
            i.model_copy(
                update={"element_id": prefix + i.element_id if i.element_id is not None else None}
            )
            for i in ir.issues
        )
        if ir.state not in {"complete", "partial"}:
            issues.append(Issue(code="engine_incomplete", state="unresolved", reason=ir.state))
    by_location = {}
    for element in elements:
        key = (
            element.kind,
            tuple(getattr(element.source, f.name) for f in fields(element.source)),
            element.geometry,
        )
        by_location.setdefault(key, []).append(element)
    provenance = Provenance(
        engine="reconciler",
        revision=RECONCILER_VERSION,
        implementation_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        observation_id="reconciliation",
    )
    for group in by_location.values():
        if len(group) < 2:
            continue
        anchor = group[0]

        def content(element):
            return element.model_dump(mode="json", exclude={"id", "provenance", "verification"})

        for other in group[1:]:
            kind = "duplicate" if content(anchor) == content(other) else "conflict"
            relations.append(
                Relation(
                    id=f"{kind}:{other.id}",
                    kind=kind,
                    source_id=anchor.id,
                    target_id=other.id,
                    provenance=provenance,
                )
            )
            for element in (anchor, other):
                issues.append(
                    Issue(
                        code="unresolved_observation_ownership",
                        state="unresolved",
                        element_id=element.id,
                        reason=kind,
                    )
                )
    states = {observation.state for observation in observations}
    state = (
        next(iter(states))
        if len(states) == 1 and states <= {"failed", "unsupported", "unresolved"}
        else "partial"
        if issues or states != {"complete"}
        else "complete"
    )
    return DocumentIR(
        source=expected,
        state=state,
        elements=tuple(elements),
        relations=tuple(relations),
        issues=tuple(issues),
        native=observations[0].native if len(observations) == 1 else None,
    )
