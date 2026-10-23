"""Loss-aware native observations and partial-Gold diagnostics, not qualification."""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass
from typing import Any


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
        ).encode()
    ).hexdigest()


@dataclass(frozen=True)
class Observation:
    native_id: str
    kind: str
    text: str | None
    page: int | None
    order: int | None
    bbox: tuple[float, ...] | None = None
    coordinate_system: str | None = None
    table: str | None = None
    row: int | None = None
    column: int | None = None
    row_span: int | None = None
    column_span: int | None = None
    parent: str | None = None
    confidence: float | None = None
    unresolved: tuple[str, ...] = ()

    def __post_init__(self):
        if not self.native_id or not self.kind:
            raise ValueError("observation_identity")
        if self.page is not None and (type(self.page) is not int or self.page < 1):
            raise ValueError("observation_page")
        for number in (self.row, self.column, self.order):
            if number is not None and (type(number) is not int or number < 0):
                raise ValueError("observation_index")
        for number in (self.row_span, self.column_span):
            if number is not None and (type(number) is not int or number < 1):
                raise ValueError("observation_span")
        if self.text is not None and not isinstance(self.text, str):
            raise ValueError("observation_text")
        if self.bbox is not None:
            if len(self.bbox) not in (4, 8) or any(
                type(n) not in (int, float) or not math.isfinite(n) for n in self.bbox
            ):
                raise ValueError("observation_geometry")
            if len(self.bbox) == 4 and not (
                self.bbox[0] < self.bbox[2] and self.bbox[1] < self.bbox[3]
            ):
                raise ValueError("observation_rectangle")
        if self.confidence is not None and (
            type(self.confidence) not in (float, int)
            or not math.isfinite(self.confidence)
            or not 0 <= self.confidence <= 1
        ):
            raise ValueError("observation_confidence")


def unique(observations: list[Observation]) -> tuple[Observation, ...]:
    if len({o.native_id for o in observations}) != len(observations):
        raise ValueError("duplicate_native_identity")
    return tuple(observations)


def normalized(text: str) -> str:
    # The frozen historical whitespace-only equivalence. No Unicode/numeric repair.
    return " ".join(text.split())


def exact_present(needle: str, text: str) -> bool:
    needle, text = normalized(needle), normalized(text)
    if not needle:
        return False
    # Prevent 125 from crediting 00125 and unsigned values from crediting -values.
    if any(ch.isdigit() for ch in needle):
        return re.search(r"(?<![\w+\-−.,])" + re.escape(needle) + r"(?![\w.,])", text) is not None
    return needle in text


def score(record, observations: tuple[Observation, ...] | None) -> dict:
    anchors = record.anchors
    numeric = tuple(a for a in anchors if any(c.isdigit() for c in a.text))
    if observations is None:
        return {
            "anchor_presence": None,
            "numeric_presence": None,
            "page_presence": None,
            "order_presence": None,
            "denominators": {
                "anchors": len(anchors),
                "numeric_anchors": len(numeric),
                "page_anchors": len(anchors),
                "order_pairs": len(record.order_pairs),
            },
        }
    presence, pages, located = {}, {}, {}
    for anchor in anchors:
        candidates = [
            o for o in observations if o.text is not None and exact_present(anchor.text, o.text)
        ]
        presence[anchor.anchor_id] = bool(candidates)
        matches = [o for o in candidates if o.page == anchor.source.page_number]
        pages[anchor.anchor_id] = len(matches) >= anchor.occurrence
        if len(matches) >= anchor.occurrence:
            located[anchor.anchor_id] = matches[anchor.occurrence - 1]
    order = {}
    for pair in record.order_pairs:
        a, b = located.get(pair.before), located.get(pair.after)
        # Within-one-observation order is measured from literal offsets, never guessed.
        if a and b and a.order is not None and b.order is not None:
            ai = normalized(a.text).find(
                normalized(next(x.text for x in anchors if x.anchor_id == pair.before))
            )
            bi = normalized(b.text).find(
                normalized(next(x.text for x in anchors if x.anchor_id == pair.after))
            )
            order[f"{pair.before}:{pair.after}"] = (a.order, ai) < (b.order, bi)
        else:
            order[f"{pair.before}:{pair.after}"] = False
    return {
        "anchor_presence": presence,
        "numeric_presence": {a.anchor_id: presence[a.anchor_id] for a in numeric},
        "page_presence": pages,
        "order_presence": order,
        "denominators": {
            "anchors": len(anchors),
            "numeric_anchors": len(numeric),
            "page_anchors": len(anchors),
            "order_pairs": len(record.order_pairs),
        },
    }


def compare(before: dict, after: dict) -> dict:
    result = {}
    for name in ("anchor_presence", "numeric_presence", "page_presence", "order_presence"):
        a, b = before[name], after[name]
        if a is None or b is None:
            result[name] = {"lost": None, "recovered": None, "status": "UNKNOWN"}
        else:
            if a.keys() != b.keys():
                raise ValueError("paired_denominator_mismatch")
            result[name] = {
                "lost": sorted(k for k in a if a[k] and not b[k]),
                "recovered": sorted(k for k in a if not a[k] and b[k]),
            }
    return result


def serialize(observations):
    return [asdict(o) for o in observations]
