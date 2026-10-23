"""Candidate-neutral PDF diagnostics over explicit source/reference tiers.

IoU 0.5 is the existing EX-v2 diagnostic matching rule, not a quality gate.
Literal Unicode/signs are retained; compact glyph comparison removes whitespace
only and is reported separately from exact text. Unknown fields earn no credit.
"""

from __future__ import annotations

from collections import Counter

from doclens_ai.extraction.evidence_v2 import valid_bbox
from tools.extraction_quality.comparison_v2 import iou, layout
from tools.extraction_quality.extraction_v2 import exact_positions

VERSION = "readiness-pdf-diagnostics-1.0"


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


def compare(prediction, reference: dict) -> dict:
    if reference["independent_gold"] is not False or reference["human_reviewed"] is not False:
        raise ValueError("source/publisher references cannot claim human Gold")
    observations = prediction.observations if prediction else []
    texts = [o for o in observations if o.kind == "pdf_text"]
    actual = [o for o in observations if o.kind == "pdf_cell"]
    expected = reference.get("cells", [])
    anchors = reference.get("anchors", [])
    presence = []
    for anchor in anchors:
        matches = [
            o
            for o in texts
            if o.locator["page"] == anchor["page"]
            and isinstance(o.fields.get("text"), str)
            and exact_positions(o.fields["text"], anchor["literal"])
        ]
        presence.append(
            {
                "reference_id": anchor["reference_id"],
                "page": anchor["page"],
                "observed": bool(matches),
                "tier": anchor["tier"],
            }
        )
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
        "literal_anchor_presence": {
            "expected": len(presence),
            "observed": sum(a["observed"] for a in presence),
            "items": presence,
        },
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
