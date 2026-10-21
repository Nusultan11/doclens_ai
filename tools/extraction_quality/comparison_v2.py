"""Offline EX-03/04/07 metric primitives; missing dimensions remain NOT_EVALUATED.

These are exact topology/literal and diagnostic IoU scores, not GriTS, TEDS or
COCO mAP implementations. They consume separate frozen source-bound captures.
"""

from __future__ import annotations

from collections import Counter

from doclens_ai.extraction.evidence_v2 import valid_bbox
from tools.extraction_quality.extraction_v2 import exact_positions


def prf(matched: int, predicted: int, expected: int) -> dict:
    if not 0 <= matched <= min(predicted, expected):
        raise ValueError("metric denominators rejected")
    return {
        "matched": matched,
        "predicted": predicted,
        "expected": expected,
        "precision": matched / predicted if predicted else None,
        "recall": matched / expected if expected else None,
        "f1": 2 * matched / (predicted + expected) if predicted + expected else None,
    }


def iou(a, b) -> float:
    if len(a) != 4 or len(b) != 4 or not valid_bbox(tuple(a)) or not valid_bbox(tuple(b)):
        raise ValueError("invalid region")
    overlap = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
    return overlap / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - overlap)


def layout(reference: list[dict], predicted: list[dict] | None, *, diagnostic_iou=0.5) -> dict:
    if predicted is None:
        return {"status": "NOT_EVALUATED", "reason": "no_region_output"}
    if len(reference) > 500 or len(predicted) > 500 or not 0 < diagnostic_iou <= 1:
        raise ValueError("layout metric budget")
    for region in reference + predicted:
        if (
            len(region["bbox"]) != 4
            or not valid_bbox(tuple(region["bbox"]))
            or type(region["page"]) is not int
            or region["page"] < 1
        ):
            raise ValueError("invalid source region locator")
    # Maximum-cardinality one-to-one matching, deterministic input-index ties.
    edges = {
        i: [
            j
            for j, other in enumerate(reference)
            if region["class"] == other["class"]
            and region["page"] == other["page"]
            and iou(region["bbox"], other["bbox"]) >= diagnostic_iou
        ]
        for i, region in enumerate(predicted)
    }
    matches = {}

    def augment(index, seen):
        for target in edges[index]:
            if target in seen:
                continue
            seen.add(target)
            if target not in matches or augment(matches[target], seen):
                matches[target] = index
                return True
        return False

    for index in edges:
        augment(index, set())
    return {
        "status": "measured_diagnostic_only",
        "diagnostic_iou": diagnostic_iou,
        **prf(len(matches), len(predicted), len(reference)),
        "reading_order": "NOT_EVALUATED",
        "coco_map": "NOT_EVALUATED",
    }


def table_cells(reference: list[dict], predicted: list[dict] | None) -> dict:
    if predicted is None:
        return {"status": "NOT_EVALUATED", "reason": "no_cell_output"}
    if len(reference) > 2048 or len(predicted) > 2048:
        raise ValueError("cell metric budget")

    def keys(cells):
        output, identities, occupied = Counter(), set(), set()
        for cell in cells:
            if (
                type(cell["page"]) is not int
                or cell["page"] < 1
                or not isinstance(cell["literal"], str)
                or any(not isinstance(cell[k], str) or not cell[k] for k in ("table_id", "cell_id"))
            ):
                raise ValueError("invalid source cell identity or unknown literal")
            identity = (cell["page"], cell["table_id"], cell["cell_id"])
            if identity in identities:
                raise ValueError("duplicate cell identity")
            identities.add(identity)
            if any(
                type(cell[k]) is not int or cell[k] < (1 if "span" in k else 0) or cell[k] > 1000
                for k in ("row", "column", "row_span", "column_span")
            ):
                raise ValueError("cell topology rejected")
            if cell["row_span"] * cell["column_span"] > 16_384:
                raise ValueError("cell topology budget")
            slots = {
                (cell["page"], cell["table_id"], r, c)
                for r in range(cell["row"], cell["row"] + cell["row_span"])
                for c in range(cell["column"], cell["column"] + cell["column_span"])
            }
            if occupied & slots or len(occupied | slots) > 16_384:
                raise ValueError("conflicting cell topology")
            occupied |= slots
            output[
                tuple(
                    cell[k]
                    for k in (
                        "page",
                        "table_id",
                        "row",
                        "column",
                        "row_span",
                        "column_span",
                        "literal",
                    )
                )
            ] += 1
        return output

    expected, actual = keys(reference), keys(predicted)
    return {
        "status": "measured_exact_topology_and_literal",
        "grits": "NOT_EVALUATED",
        "teds": "NOT_EVALUATED",
        **prf(sum((expected & actual).values()), sum(actual.values()), sum(expected.values())),
    }


def paired_text(
    reference: tuple[str, ...],
    baseline: dict[int, str],
    candidate: dict[int, str],
    *,
    expected_pages: set[int],
) -> dict:
    """Complete page identity and exact anchors guard any combined offline candidate."""
    if len(reference) > 500 or len(expected_pages) > 2000:
        raise ValueError("paired text budget")
    if set(baseline) != expected_pages or set(candidate) != expected_pages:
        return {
            "execution": "BLOCKED",
            "quality": "NOT_EVALUATED",
            "experiment": "INCONCLUSIVE",
            "failure": "incomplete_page_output",
        }
    before = {
        i for i, a in enumerate(reference) if any(exact_positions(t, a) for t in baseline.values())
    }
    after = {
        i for i, a in enumerate(reference) if any(exact_positions(t, a) for t in candidate.values())
    }
    lost = sorted(before - after)
    return {
        "execution": "PASS",
        "quality": "FAIL" if lost else "NOT_EVALUATED",
        "experiment": "REJECT" if lost else "INCONCLUSIVE",
        "anchors_expected": len(reference),
        "baseline_present": len(before),
        "candidate_present": len(after),
        "lost_anchor_indices": lost,
        "recovered_anchor_indices": sorted(after - before),
        "added_anchor_occurrences": sum(
            max(
                0,
                sum(len(exact_positions(t, a)) for t in candidate.values())
                - sum(len(exact_positions(t, a)) for t in baseline.values()),
            )
            for a in reference
        ),
        "production_authorized": False,
    }
