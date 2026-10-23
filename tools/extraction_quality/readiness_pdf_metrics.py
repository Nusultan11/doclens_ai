"""Candidate-neutral PDF diagnostics over explicit source/reference tiers.

IoU 0.5 is the existing EX-v2 diagnostic matching rule, not a quality gate.
Literal Unicode/signs are retained; compact glyph comparison removes whitespace
only and is reported separately from exact text. Unknown fields earn no credit.
"""

from __future__ import annotations

from collections import Counter, defaultdict

from doclens_ai.extraction.evidence_v2 import valid_bbox
from doclens_ai.extraction.fidelity_gold import fingerprint
from tools.extraction_quality.comparison_v2 import iou, layout
from tools.extraction_quality.extraction_v2 import exact_positions

VERSION = "readiness-pdf-diagnostics-1.1"


def validate_reference(reference: dict, source: dict) -> None:
    if (
        source["format"] != "pdf"
        or reference["source_id"] != source["id"]
        or reference["source_sha256"] != source["sha256"]
        or source["rights"].get("new_annotation") is not True
        or source.get("split", "dev") != "dev"
        or source.get("reserved_qa_family")
        or reference["independent_gold"] is not False
        or reference["human_reviewed"] is not False
    ):
        raise ValueError("PDF reference source/rights/tier rejected")
    items = reference.get("cells", []) + reference.get("anchors", [])
    if len({r["reference_id"] for r in items}) != len(items):
        raise ValueError("duplicate PDF reference identity")
    for item in items:
        page = item["page"]
        if type(page) is not int or not 1 <= page <= source["pdf_page_count"]:
            raise ValueError("PDF reference page outside original")
        if "bbox" in item:
            box = item["bbox"]
            geometry = source["pdf_page_geometry"][str(page)]
            if not valid_bbox(tuple(box)) or not (
                geometry["rotation"] == 0
                and 0 <= box[0] < box[2] <= geometry["width"]
                and 0 <= box[1] < box[3] <= geometry["height"]
            ):
                raise ValueError("PDF annotation/source geometry mismatch")


def anchor_metrics(texts, anchors: list[dict]) -> tuple[dict, dict]:
    """Separate page presence from unambiguous, located source occurrences.

    A text observation can locate one literal only when its entire text equals
    that literal. A whole-page block cannot locate each substring it contains.
    Source boxes must distinguish repeated references; missing/overlapping boxes
    are NOT_EVALUATED. Broad predictions matching multiple source boxes earn no
    occurrence credit. IoU uses the existing 0.5 diagnostic rule, not a quality gate.
    """
    groups = defaultdict(list)
    for index, anchor in enumerate(anchors):
        if not isinstance(anchor["literal"], str) or not anchor["literal"]:
            raise ValueError("nonempty literal anchor required")
        groups[anchor["page"], anchor["literal"]].append(index)

    def usable_box(item):
        box = item.get("bbox")
        return (
            box
            if (
                isinstance(box, list)
                and len(box) == 4
                and all(type(v) in (int, float) for v in box)
                and valid_bbox(tuple(box))
            )
            else None
        )

    boxes = [usable_box(anchor) for anchor in anchors]

    def overlaps(a, b):
        return min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1])

    reasons = {i: "missing_source_bbox" for i, box in enumerate(boxes) if box is None}
    presence = []
    for (page, literal), indices in groups.items():
        presence.append(
            {
                "page": page,
                "literal_fingerprint": fingerprint(literal),
                "present": any(
                    o.locator["page"] == page
                    and isinstance(o.fields.get("text"), str)
                    and exact_positions(o.fields["text"], literal)
                    for o in texts
                ),
            }
        )
        for i in indices:
            for j in indices:
                if i != j and boxes[i] is not None and boxes[j] is not None:
                    if overlaps(boxes[i], boxes[j]):
                        reasons[i] = "ambiguous_source_occurrence_boxes"
    predicted_regions = defaultdict(set)
    for observation in texts:
        box = usable_box(observation.locator)
        literal = observation.fields.get("text")
        if box is None or not isinstance(literal, str):
            continue
        page = observation.locator["page"]
        if (page, literal) in groups:
            predicted_regions[page, tuple(box)].add(literal)
    matched = set()
    for (page, box), literals in predicted_regions.items():
        # Exact duplicates collapse. Conflicting labels/overlapping variants
        # cannot establish distinct physical occurrences.
        if len(literals) != 1 or any(
            other_page == page and other != box and overlaps(box, other)
            for other_page, other in predicted_regions
        ):
            continue
        indices = groups[page, next(iter(literals))]
        targets = [i for i in indices if i not in reasons and iou(boxes[i], box) >= 0.5]
        if len(targets) == 1:
            matched.add(targets[0])
    expected = len(anchors) - len(reasons)
    return (
        {
            "unit": "unique_page_literal",
            "per_item_recall": False,
            "expected": len(presence),
            "observed": sum(a["present"] for a in presence),
            "items": presence,
        },
        {
            "status": "NOT_EVALUATED"
            if not expected
            else "PARTIALLY_EVALUATED"
            if reasons
            else "measured_locator_diagnostic_only",
            "expected": expected,
            "matched": len(matched),
            "not_evaluated": len(reasons),
            "reference_items": len(anchors),
            "locator_rule": "one_exact_literal_observation; unique_source_bbox; diagnostic_IoU_0.5",
            "items": [
                {
                    "reference_id": a["reference_id"],
                    "page": a["page"],
                    "status": "NOT_EVALUATED"
                    if i in reasons
                    else "MATCHED"
                    if i in matched
                    else "MISSING",
                    "reason": reasons.get(i),
                }
                for i, a in enumerate(anchors)
            ],
        },
    )


def compare(prediction, reference: dict) -> dict:
    if reference["independent_gold"] is not False or reference["human_reviewed"] is not False:
        raise ValueError("source/publisher references cannot claim human Gold")
    observations = prediction.observations if prediction else []
    texts = [o for o in observations if o.kind == "pdf_text"]
    actual = [o for o in observations if o.kind == "pdf_cell"]
    expected = reference.get("cells", [])
    anchors = reference.get("anchors", [])
    presence, occurrences = anchor_metrics(texts, anchors)
    metrics = {}
    dimensions = Counter()
    rows = []
    for page in sorted({c["page"] for c in expected} | {o.locator["page"] for o in actual}):
        refs = [c for c in expected if c["page"] == page]
        candidates = [o for o in actual if o.locator["page"] == page and "bbox" in o.locator]
        if len(refs) > 500 or len(candidates) > 500:
            raise ValueError("existing diagnostic region budget exceeded")
        regions = [{"class": "cell", "page": page, "bbox": c["bbox"]} for c in refs]
        predicted = [{"class": "cell", "page": page, "bbox": o.locator["bbox"]} for o in candidates]
        metrics[str(page)] = layout(regions, predicted)
        edges = sorted(
            (
                (-iou(c["bbox"], o.locator["bbox"]), i, j)
                for i, c in enumerate(refs)
                for j, o in enumerate(candidates)
                if iou(c["bbox"], o.locator["bbox"]) >= 0.5
            )
        )
        used_refs, used_candidates, matched = set(), set(), {}
        for _, i, j in edges:
            if i not in used_refs and j not in used_candidates:
                used_refs.add(i)
                used_candidates.add(j)
                matched[i] = j
        for i, cell in enumerate(refs):
            candidate = candidates[matched[i]] if i in matched else None
            findings = {}
            for field in (
                "text",
                "native_nonspace_text",
                "row",
                "column",
                "row_span",
                "column_span",
            ):
                if field not in cell["fields"]:
                    continue
                label = cell["tier"] + "." + field
                dimensions[label + ".expected"] += 1
                observed = candidate.fields.get(field) if candidate else None
                if (
                    field == "native_nonspace_text"
                    and candidate
                    and isinstance(candidate.fields.get("text"), str)
                ):
                    observed = "".join(candidate.fields["text"].split())
                present = observed is not None
                equal = (
                    present
                    and type(observed) is type(cell["fields"][field])
                    and observed == cell["fields"][field]
                )
                dimensions[label + ".observed"] += int(present)
                dimensions[label + ".exact"] += int(equal)
                findings[field] = {"observed": present, "exact": equal}
            rows.append(
                {
                    "reference_id": cell["reference_id"],
                    "page": page,
                    "tier": cell["tier"],
                    "geometry_matched": candidate is not None,
                    "fields": findings,
                }
            )
    return {
        "version": VERSION,
        "quality": "NOT_EVALUATED",
        "independent_gold": False,
        "literal_anchor_presence": presence,
        "literal_anchor_occurrences": occurrences,
        "geometry_diagnostic_by_page": metrics,
        "field_denominators": dict(dimensions),
        "cells": rows,
        "unlocated_predicted_cells": sum("bbox" not in o.locator for o in actual),
        "reading_order": "NOT_EVALUATED",
        "semantic_relationships": "NOT_EVALUATED",
        "ocr_CER_WER": "NOT_EVALUATED",
        "exact_border_fidelity": "NOT_EVALUATED",
        "field_matching": (
            "greatest_IoU_first_one_to_one_input_index_ties; "
            "geometry_uses_existing_maximum_cardinality"
        ),
        "provenance_scope": "bound_source_SHA_and_genuine_page_bbox; not_semantic_proof",
    }
