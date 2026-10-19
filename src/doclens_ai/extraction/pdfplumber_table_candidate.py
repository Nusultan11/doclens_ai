"""Conservative offline geometry comparator; never production routing or OCR."""

from __future__ import annotations

import hashlib
import math
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from doclens_ai.extraction.models import (
    ExtractionStatus,
    SourceLocation,
    TableBlock,
    TableCell,
    TableRow,
)
from doclens_ai.extraction.pdf_table_candidate import supplement

VERSION = "pdfplumber-ruled-offline-v1"
SETTINGS = {
    "vertical_strategy": "lines",
    "horizontal_strategy": "lines",
    "snap_tolerance": 0,
    "join_tolerance": 0,
    "intersection_tolerance": 0,
    "edge_min_length": 3,
    "edge_min_length_prefilter": 1,
}
TEXT_SETTINGS = {"layout": False, "x_tolerance": 3, "y_tolerance": 3, "expand_ligatures": False}


@dataclass(frozen=True, slots=True)
class Limits:
    max_file_bytes: int = 50 * 1024**2
    max_pages: int = 100
    max_characters: int = 500_000
    max_edges: int = 5_000
    max_cells: int = 10_000
    max_tables: int = 100
    timeout_seconds: float = 15.0

    def __post_init__(self) -> None:
        if (
            any(
                type(v) is not int or v <= 0
                for k, v in asdict(self).items()
                if k != "timeout_seconds"
            )
            or type(self.timeout_seconds) not in (int, float)
            or not 0 < self.timeout_seconds < float("inf")
        ):
            raise ValueError("Invalid candidate limits")


@dataclass(frozen=True, slots=True)
class Cell:
    row: int
    column: int
    bounds: tuple[float, float, float, float]
    text: str
    character_indices: tuple[int, ...]
    boundary_edge_indices: tuple[tuple[int, ...], ...]


@dataclass(frozen=True, slots=True)
class Grid:
    page: int
    table_index: int
    bounds: tuple[float, float, float, float]
    cells: tuple[Cell, ...]

    def block(self, order: int) -> TableBlock:
        def location(cell: Cell | None = None) -> SourceLocation:
            return SourceLocation(
                page_number=self.page,
                block_index=order,
                table_index=self.table_index,
                row_index=cell.row if cell else None,
                column_index=cell.column if cell else None,
            )

        return TableBlock(
            order,
            self.table_index,
            tuple(
                TableRow(
                    r,
                    tuple(
                        TableCell(c.row, c.column, c.text, location(c))
                        for c in self.cells
                        if c.row == r
                    ),
                )
                for r in sorted({c.row for c in self.cells})
            ),
            location(),
        )


@dataclass(frozen=True, slots=True)
class Page:
    page: int
    bounds: tuple[float, float, float, float]
    status: str
    issues: tuple[str, ...]
    detected_tables: int
    tables: int
    characters: int
    edges: int


@dataclass(frozen=True, slots=True)
class Evidence:
    status: ExtractionStatus
    source_sha256: str | None = None
    source_size_bytes: int | None = None
    grids: tuple[Grid, ...] = ()
    pages: tuple[Page, ...] = ()
    issues: tuple[str, ...] = ()
    schema_version: str = VERSION
    coordinate_system: str = "pdfplumber_x0_top_x1_bottom_points"

    def to_dict(self) -> dict:
        return asdict(self)


class _Review(Exception):
    pass


class _Limit(Exception):
    pass


def _box(values) -> tuple[float, float, float, float]:
    if len(values) != 4:
        raise _Review("invalid_bounds")
    box = tuple(float(v) for v in values)
    if (
        any(not math.isfinite(v) or abs(v) > 10**7 for v in box)
        or box[0] >= box[2]
        or box[1] >= box[3]
    ):
        raise _Review("invalid_bounds")
    return box


def _inside(a, b) -> bool:
    return b[0] <= a[0] < a[2] <= b[2] and b[1] <= a[1] < a[3] <= b[3]


def _overlap(a, b) -> bool:
    return max(a[0], b[0]) < min(a[2], b[2]) and max(a[1], b[1]) < min(a[3], b[3])


def _boundary(edges, orientation, position, low, high) -> tuple[int, ...]:
    intervals = []
    for i, edge in enumerate(edges):
        if edge.get("orientation") != orientation:
            continue
        pos = edge["x0"] if orientation == "v" else edge["top"]
        lo, hi = (edge["top"], edge["bottom"]) if orientation == "v" else (edge["x0"], edge["x1"])
        if pos == position and lo <= high and hi >= low:
            intervals.append((lo, hi, i))
    end = low
    used = []
    for lo, hi, i in sorted(intervals):
        if lo > end:
            break
        if hi > end:
            end = hi
            used.append(i)
        if end >= high:
            return tuple(used)
    raise _Review("unverified_boundary")


def _grid(page, table, index: int, chars, edges, limits: Limits, tick) -> Grid:
    from pdfplumber.utils import cluster_objects, extract_text

    bounds = _box(table.bbox)
    if not _inside(bounds, _box(page.bbox)):
        raise _Review("clipped_table")
    boxes = [_box(c) for c in table.cells]
    xs = sorted({v for b in boxes for v in (b[0], b[2])})
    ys = sorted({v for b in boxes for v in (b[1], b[3])})
    if len(xs) < 3 or len(ys) < 3:
        raise _Review("insufficient_grid")
    if (len(xs) - 1) * (len(ys) - 1) > limits.max_cells:
        raise _Limit("cell_limit")
    expected = [
        (xs[c], ys[r], xs[c + 1], ys[r + 1]) for r in range(len(ys) - 1) for c in range(len(xs) - 1)
    ]
    if len(set(boxes)) != len(boxes) or set(boxes) != set(expected):
        raise _Review("merged_or_incomplete_grid")
    assigned = {box: [] for box in expected}
    seen = set()
    for i, char in enumerate(chars):
        tick()
        cb = _box((char["x0"], char["top"], char["x1"], char["bottom"]))
        if not _overlap(cb, bounds):
            continue
        matrix = char.get("matrix", ())
        if (
            not char.get("upright")
            or len(matrix) != 6
            or matrix[1] != 0
            or matrix[2] != 0
            or matrix[0] <= 0
            or matrix[3] <= 0
        ):
            raise _Review("rotated_text")
        text = char["text"]
        if (
            not isinstance(text, str)
            or not text
            or "\ufffd" in text
            or re.search(r"\(cid:\d+\)", text)
            or any(ord(c) < 32 and not c.isspace() for c in text)
        ):
            raise _Review("unverified_character_mapping")
        signature = (*cb, text)
        if signature in seen:
            raise _Review("duplicate_text_geometry")
        seen.add(signature)
        hits = [
            box
            for box in expected
            if box[0] < cb[0] < cb[2] < box[2] and box[1] < cb[1] < cb[3] < box[3]
        ]
        if len(hits) != 1:
            raise _Review("ambiguous_text_association")
        assigned[hits[0]].append((i, char))
    cells = []
    for row in range(len(ys) - 1):
        for col in range(len(xs) - 1):
            tick()
            box = (xs[col], ys[row], xs[col + 1], ys[row + 1])
            borders = (
                _boundary(edges, "v", box[0], box[1], box[3]),
                _boundary(edges, "v", box[2], box[1], box[3]),
                _boundary(edges, "h", box[1], box[0], box[2]),
                _boundary(edges, "h", box[3], box[0], box[2]),
            )
            items = assigned[box]
            text = extract_text([c for _, c in items], **TEXT_SETTINGS) if items else ""
            # Only whitespace may be introduced by geometric word/line separation.
            lines = [
                sorted(line, key=lambda char: (char["x0"], char["x1"]))
                for line in cluster_objects(
                    [item for _, item in items], "doctop", TEXT_SETTINGS["y_tolerance"]
                )
            ]
            source_text = "\n".join("".join(char["text"] for char in line) for line in lines)
            actual = "".join(c for c in source_text if not c.isspace())
            if "".join(c for c in text if not c.isspace()) != actual:
                raise _Review("character_preservation_failed")
            numeric_pattern = r"[-+]?\d+(?:[.,]\d+)*"
            if re.findall(numeric_pattern, text) != re.findall(numeric_pattern, source_text):
                raise _Review("numeric_token_ambiguity")
            cells.append(Cell(row, col, box, text, tuple(i for i, _ in items), borders))
    return Grid(page.page_number, index, bounds, tuple(cells))


def extract_tables(source: str | Path, *, limits: Limits | None = None) -> Evidence:
    active = limits or Limits()
    start = time.monotonic()
    digest = size = None

    def tick():
        if time.monotonic() - start >= active.timeout_seconds:
            raise _Limit("timeout")

    try:
        path = Path(source)
        if (
            any(p.is_symlink() or p.is_junction() for p in (path, *path.parents))
            or not path.is_file()
            or path.suffix.lower() != ".pdf"
        ):
            return Evidence(ExtractionStatus.FAILED, issues=("invalid_source",))
        size = path.stat().st_size
        if not 0 < size <= active.max_file_bytes:
            raise _Limit("input_limit")
        h = hashlib.sha256()
        with path.open("rb") as stream:
            for data in iter(lambda: stream.read(1024**2), b""):
                tick()
                h.update(data)
        digest = h.hexdigest()
        import pdfplumber

        grids = []
        pages = []
        characters = detected_total = 0
        with pdfplumber.open(path) as doc:
            if len(doc.pages) > active.max_pages:
                raise _Limit("page_limit")
            for page in doc.pages:
                tick()
                issues = set()
                found = []
                chars = page.chars
                edges = page.edges
                characters += len(chars)
                if characters > active.max_characters or len(edges) > active.max_edges:
                    raise _Limit("object_limit")
                try:
                    bounds = _box(page.bbox)
                    if page.rotation:
                        raise _Review("rotated_page")
                    tables = sorted(
                        page.find_tables(dict(SETTINGS)),
                        key=lambda t: (t.bbox[1], t.bbox[0], t.bbox[3], t.bbox[2]),
                    )
                    detected_total += len(tables)
                    if detected_total > active.max_tables:
                        raise _Limit("table_limit")
                    if not tables:
                        issues.add("no_supported_table")
                    for i, table in enumerate(tables):
                        tick()
                        if any(
                            i != j and _overlap(table.bbox, other.bbox)
                            for j, other in enumerate(tables)
                        ):
                            issues.add("overlapping_tables")
                            continue
                        try:
                            found.append(_grid(page, table, i, chars, edges, active, tick))
                        except _Review as exc:
                            issues.add(str(exc))
                    if page.images:
                        issues.add("image_content_not_evaluated")
                except _Review as exc:
                    issues.add(str(exc))
                    tables = []
                    found = []
                    bounds = tuple(page.bbox)
                grids.extend(found)
                if sum(len(g.cells) for g in grids) > active.max_cells:
                    raise _Limit("cell_limit")
                pages.append(
                    Page(
                        page.page_number,
                        bounds,
                        "needs_review" if issues else "success",
                        tuple(sorted(issues)),
                        len(tables),
                        len(found),
                        len(chars),
                        len(edges),
                    )
                )
                page.close()
        status = (
            ExtractionStatus.NEEDS_REVIEW
            if not grids or any(p.issues for p in pages)
            else ExtractionStatus.SUCCESS
        )
        return Evidence(status, digest, size, tuple(grids), tuple(pages))
    except _Limit as exc:
        return Evidence(ExtractionStatus.FAILED, digest, size, issues=(str(exc),))
    except Exception:
        return Evidence(ExtractionStatus.FAILED, digest, size, issues=("invalid_pdf_or_runtime",))


__all__ = ["Evidence", "Limits", "SETTINGS", "TEXT_SETTINGS", "extract_tables", "supplement"]
