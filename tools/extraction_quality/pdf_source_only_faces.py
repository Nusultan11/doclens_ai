"""Source-only local rectangular-face proposals, never annotation-driven grids.

Inference accepts PDF bytes and a frozen generic configuration only. Faces use
actual inner ink edges of four qualified filled bars. Their interpretation as
table cells, reading order, spans and semantic relationships is unverified.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from io import BytesIO

import pdfplumber
from pypdf import PdfReader

from tools.extraction_quality.pdf_cell_recovery import _rulings

METHOD = "source-only-local-filled-bar-faces-v1"


@dataclass(frozen=True)
class Config:
    max_file_bytes: int = 50 * 1024**2
    max_pages: int = 100
    max_rules: int = 512
    max_characters: int = 200_000
    max_faces: int = 2048
    max_operations: int = 20_000_000
    min_face_side: float = 3.0
    min_component_faces: int = 4

    def __post_init__(self):
        if any(
            type(v) not in (int, float) or not 0 < v < float("inf") for v in asdict(self).values()
        ):
            raise ValueError("Invalid frozen configuration")


def intersects(a, b):
    return max(a[0], b[0]) < min(a[2], b[2]) and max(a[1], b[1]) < min(a[3], b[3])


def contains(outer, inner):
    return (
        outer[0] <= inner[0] < inner[2] <= outer[2] and outer[1] <= inner[1] < inner[3] <= outer[3]
    )


def faces_from_rules(rules: list[dict], config: Config) -> list[dict]:
    """Discover locally closed faces; never complete a global Cartesian lattice."""
    if len(rules) > config.max_rules:
        raise ValueError("Rule limit")
    horizontal = [r for r in rules if r["axis"] == "h"]
    vertical = sorted((r for r in rules if r["axis"] == "v"), key=lambda r: r["bbox"])
    found = {}
    operations = 0
    for bottom in horizontal:
        for top in horizontal:
            low, high = bottom["bbox"][3], top["bbox"][1]
            if high - low < config.min_face_side:
                continue
            sides = [v for v in vertical if v["bbox"][1] <= low and v["bbox"][3] >= high]
            for left, right in zip(sides, sides[1:], strict=False):
                operations += len(rules)
                if operations > config.max_operations:
                    raise ValueError("Face operation limit")
                x0, x1 = left["bbox"][2], right["bbox"][0]
                if x1 - x0 < config.min_face_side or any(
                    h["bbox"][0] > x0 or h["bbox"][2] < x1 for h in (bottom, top)
                ):
                    continue
                box = [x0, low, x1, high]
                # Partial/internal bars make this a nonrectangular or ambiguous face.
                if any(intersects(box, r["bbox"]) for r in rules):
                    continue
                refs = [r["source_object_index"] for r in (left, bottom, right, top)]
                key = tuple(box)
                if key in found:
                    found[key]["boundary_support_alternatives"].append(refs)
                else:
                    found[key] = dict(
                        bbox=box, boundary_objects=refs, boundary_support_alternatives=[]
                    )
                if len(found) > config.max_faces:
                    raise ValueError("Face count limit")
    return sorted(found.values(), key=lambda f: (-f["bbox"][3], f["bbox"][0]))


def components(faces: list[dict], config: Config) -> list[list[int]]:
    """Require a shared physical bar plus overlapping side projections."""
    neighbours = {i: set() for i in range(len(faces))}
    for i, a in enumerate(faces):
        for j in range(i):
            b = faces[j]
            ra, rb = a["boundary_objects"], b["boundary_objects"]
            xoverlap = min(a["bbox"][2], b["bbox"][2]) > max(a["bbox"][0], b["bbox"][0])
            yoverlap = min(a["bbox"][3], b["bbox"][3]) > max(a["bbox"][1], b["bbox"][1])
            if (
                (ra[0] == rb[2] or ra[2] == rb[0])
                and yoverlap
                or (ra[1] == rb[3] or ra[3] == rb[1])
                and xoverlap
            ):
                neighbours[i].add(j)
                neighbours[j].add(i)
    groups, seen = [], set()
    for i in range(len(faces)):
        if i in seen:
            continue
        group, todo = [], [i]
        while todo:
            current = todo.pop()
            if current in seen:
                continue
            seen.add(current)
            group.append(current)
            todo.extend(sorted(neighbours[current] - seen))
        if (
            len(group) >= config.min_component_faces
            and len({faces[k]["bbox"][0] for k in group}) >= 2
            and len({faces[k]["bbox"][3] for k in group}) >= 2
        ):
            groups.append(sorted(group))
    return groups


DEFAULT_CONFIG = Config()


def infer(data: bytes, config: Config = DEFAULT_CONFIG) -> dict:
    """No source IDs, Gold, plans, regions, dimensions, labels or decisions accepted."""
    if not isinstance(data, bytes) or not 0 < len(data) <= config.max_file_bytes:
        raise ValueError("Source byte limit")
    reader = PdfReader(BytesIO(data), strict=False)
    if reader.is_encrypted or not 0 < len(reader.pages) <= config.max_pages:
        raise ValueError("Unsupported source")
    pages = []
    with pdfplumber.open(BytesIO(data)) as document:
        for number, page in enumerate(document.pages, 1):
            original = reader.pages[number - 1]
            if (
                original.rotation != 0
                or original.get("/UserUnit", 1) != 1
                or list(original.cropbox) != list(original.mediabox)
                or list(original.mediabox)[:2] != [0, 0]
            ):
                pages.append(
                    dict(page=number, regions=[], cells=[], issues=["UNSUPPORTED_TRANSFORM"])
                )
                continue
            if len(page.chars) > config.max_characters:
                raise ValueError("Character limit")
            chars = [
                dict(
                    index=i,
                    text=c["text"],
                    upright=c["upright"],
                    bbox=[c["x0"], page.height - c["bottom"], c["x1"], page.height - c["top"]],
                )
                for i, c in enumerate(page.chars)
            ]
            rules = _rulings(data, number)
            faces = faces_from_rules(rules, config)
            groups = components(faces, config)
            chosen = sorted({i for group in groups for i in group})
            assigned, crossing = {}, set()
            for glyph in chars:
                hits = [i for i in chosen if intersects(faces[i]["bbox"], glyph["bbox"])]
                if not hits or not glyph["text"].strip():
                    continue
                if (
                    len(hits) != 1
                    or not glyph["upright"]
                    or not contains(faces[hits[0]]["bbox"], glyph["bbox"])
                    or "\ufffd" in glyph["text"]
                    or not glyph["text"].isprintable()
                ):
                    crossing.update(hits)
                else:
                    assigned[glyph["index"]] = hits[0]
            cells = []
            for i in chosen:
                inside = [g for g in chars if contains(faces[i]["bbox"], g["bbox"])]
                owned = [
                    g for g in inside if assigned.get(g["index"]) == i or not g["text"].strip()
                ]
                has_text = any(g["text"].strip() for g in owned)
                cells.append(
                    dict(
                        cell_id=f"p{number}-face{i}",
                        face_index=i,
                        **faces[i],
                        glyph_indices=[g["index"] for g in owned],
                        literal_text=None
                        if i in crossing or not has_text
                        else "".join(g["text"] for g in owned),
                        text_status=(
                            "CROSSING_OR_UNSUPPORTED_GLYPH"
                            if i in crossing
                            else "SOURCE_CHARACTERS_ONLY"
                            if has_text
                            else "NO_INTERIOR_TEXT_LAYER_GLYPHS"
                        ),
                        exact_border_fidelity="NOT_EVALUATED",
                        semantic_role=None,
                    )
                )
            regions = [
                dict(
                    region_id=f"p{number}-region{j}",
                    face_indices=group,
                    bbox=[
                        min(faces[i]["bbox"][0] for i in group),
                        min(faces[i]["bbox"][1] for i in group),
                        max(faces[i]["bbox"][2] for i in group),
                        max(faces[i]["bbox"][3] for i in group),
                    ],
                )
                for j, group in enumerate(groups)
            ]
            pages.append(
                dict(
                    page=number,
                    source_characters=chars,
                    source_rules=rules,
                    closed_faces=len(faces),
                    regions=regions,
                    cells=cells,
                    unassigned_nonspace_glyphs=[
                        g["index"]
                        for g in chars
                        if g["text"].strip() and g["index"] not in assigned
                    ],
                    issues=["UNREVIEWED_CELL_INTERPRETATION"]
                    + (["NO_SUPPORTED_REGION"] if not regions else [])
                    + (["CROSSING_GLYPHS_UNRESOLVED"] if crossing else []),
                )
            )
    return dict(
        method=METHOD,
        source_sha256=hashlib.sha256(data).hexdigest(),
        source_size_bytes=len(data),
        config=asdict(config),
        pages=pages,
        status="needs_review",
        independent_gold=False,
        relationships=[],
        coordinate_basis="pdf_user_space_unrotated_inner_ink_edges",
        qg_01="NOT_EVALUATED",
    )
