"""Strict offline ruled-grid subset. No production routing or semantic header guesses."""

from __future__ import annotations

import hashlib
import math
import time
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from pypdf import PdfReader
from pypdf.generic import TextStringObject

from doclens_ai.extraction.models import (
    ErrorCategory,
    ExtractionResult,
    ExtractionStatus,
    SourceLocation,
    TableBlock,
    TableCell,
    TableRow,
)

VERSION = "pdf-ruled-grid-offline-v1"


@dataclass(frozen=True, slots=True)
class TableLimits:
    max_file_bytes: int = 50 * 1024**2
    max_pages: int = 100
    max_stream_bytes: int = 8 * 1024**2
    max_operations: int = 50_000
    max_segments: int = 500
    max_runs: int = 10_000
    max_characters: int = 500_000
    max_cells: int = 10_000
    max_stack: int = 64
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
            raise ValueError("Invalid table limits")


@dataclass(frozen=True, slots=True)
class CellEvidence:
    row: int
    column: int
    bounds: tuple[float, float, float, float]
    text: str
    operator_index: int | None


@dataclass(frozen=True, slots=True)
class GridEvidence:
    page: int
    table_index: int
    x_lines: tuple[float, ...]
    y_lines: tuple[float, ...]
    cells: tuple[CellEvidence, ...]

    def block(self, order: int) -> TableBlock:
        def location(cell: CellEvidence | None = None) -> SourceLocation:
            return SourceLocation(
                block_index=order,
                page_number=self.page,
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
                for r in range(len(self.y_lines) - 1)
            ),
            location(),
        )


@dataclass(frozen=True, slots=True)
class PageEvidence:
    page: int
    status: str
    issues: tuple[str, ...]
    segments: int
    text_runs: int
    tables: int


@dataclass(frozen=True, slots=True)
class TableEvidence:
    status: ExtractionStatus
    source_sha256: str | None = None
    source_size_bytes: int | None = None
    grids: tuple[GridEvidence, ...] = ()
    pages: tuple[PageEvidence, ...] = ()
    issues: tuple[str, ...] = ()
    schema_version: str = VERSION

    def to_dict(self) -> dict:
        return asdict(self)


class _Unsupported(Exception):
    pass


class _Limit(Exception):
    pass


def _numbers(values, count: int) -> list[float]:
    if len(values) != count:
        raise _Unsupported("invalid_operator_arguments")
    result = [float(v) for v in values]
    if any(not math.isfinite(v) or abs(v) > 10**7 for v in result):
        raise _Unsupported("invalid_geometry")
    return result


def _object(value):
    return value.get_object() if hasattr(value, "get_object") else value


def _axis(matrix) -> tuple[float, float, float, float]:
    a, b, c, d, e, f = _numbers(matrix, 6)
    if b != 0 or c != 0 or a <= 0 or d <= 0:
        raise _Unsupported("rotated_or_sheared_geometry")
    return a, d, e, f


def _page(
    page, number: int, limits: TableLimits, tick
) -> tuple[list[GridEvidence], PageEvidence, int]:
    segments, runs = [], []

    def point(x, y):
        return tuple(_numbers((x * cm[0] + cm[2], y * cm[1] + cm[3]), 2))

    def line(a, b):
        nonlocal margin
        if a == b:
            return
        if a[0] != b[0] and a[1] != b[1]:
            raise _Unsupported("nonrectilinear_path")
        segments.append((a, b))
        margin = max(margin, width * max(cm[:2]) / 2)
        if len(segments) > limits.max_segments:
            raise _Limit("segment_limit")

    try:
        if page.rotation or float(page.get("/UserUnit", 1)) != 1:
            raise _Unsupported("rotated_or_scaled_page")
        content = page.get_contents()
        if content is None:
            raise _Unsupported("no_content")
        if len(content.get_data()) > limits.max_stream_bytes:
            raise _Limit("stream_limit")
        operations = content.operations
        if len(operations) > limits.max_operations:
            raise _Limit("operation_limit")
        cm = (1.0, 1.0, 0.0, 0.0)
        width = 1.0
        margin = 0.0
        stack = []
        path = []
        current = None
        start = None
        active = False
        font = None
        size = None
        tm = None
        shown = False
        fonts = _object(_object(page.get("/Resources", {})).get("/Font", {}))
        characters = 0
        for index, (args, op) in enumerate(operations):
            tick()
            if op == b"q":
                if active:
                    raise _Unsupported("graphics_state_in_text")
                stack.append((cm, width))
                if len(stack) > limits.max_stack:
                    raise _Limit("stack_limit")
            elif op == b"Q":
                if active or not stack:
                    raise _Unsupported("invalid_graphics_state")
                cm, width = stack.pop()
            elif op == b"cm":
                if active:
                    raise _Unsupported("graphics_state_in_text")
                a, d, e, f = _axis(args)
                cm = tuple(
                    _numbers((a * cm[0], d * cm[1], e * cm[0] + cm[2], f * cm[1] + cm[3]), 4)
                )
            elif op in (b"m", b"l"):
                p = point(*_numbers(args, 2))
                if op == b"m":
                    current = start = p
                else:
                    if current is None:
                        raise _Unsupported("invalid_path")
                    path.append((current, p))
                    current = p
            elif op == b"re":
                x, y, w, h = _numbers(args, 4)
                if w <= 0 or h <= 0:
                    raise _Unsupported("invalid_path")
                ps = [point(x, y), point(x + w, y), point(x + w, y + h), point(x, y + h)]
                path.extend(zip(ps, ps[1:] + ps[:1], strict=True))
                current = start = ps[0]
            elif op == b"h":
                if current is None or start is None:
                    raise _Unsupported("invalid_path")
                path.append((current, start))
                current = start
            elif op in (b"S", b"s", b"n"):
                if op == b"s" and current is not None:
                    path.append((current, start))
                if op in (b"S", b"s"):
                    for a, b in path:
                        line(a, b)
                path = []
                current = start = None
            elif op == b"BT":
                if active:
                    raise _Unsupported("invalid_text_state")
                active = True
                font = size = tm = None
                shown = False
            elif op == b"ET":
                if not active:
                    raise _Unsupported("invalid_text_state")
                active = False
            elif op == b"Tf":
                if not active or len(args) != 2:
                    raise _Unsupported("invalid_text_state")
                if args[0] not in fonts:
                    raise _Unsupported("missing_font_metrics")
                font = fonts[args[0]].get_object()
                size = _numbers(args[1:], 1)[0]
                if size <= 0:
                    raise _Unsupported("invalid_font_size")
            elif op == b"Tm":
                if not active or shown:
                    raise _Unsupported("multiple_text_positions")
                tm = _axis(args)
            elif op == b"Tj":
                if not active or shown or tm is None or font is None or size is None:
                    raise _Unsupported("missing_or_ambiguous_text_locator")
                shown = True
                if len(args) != 1:
                    raise _Unsupported("invalid_operator_arguments")
                raw = (
                    args[0].original_bytes
                    if isinstance(args[0], TextStringObject)
                    else bytes(args[0])
                )
                if any(v < 32 or v > 126 for v in raw):
                    raise _Unsupported("unsupported_text_encoding")
                if characters + len(raw) > limits.max_characters:
                    raise _Limit("text_limit")
                if (
                    font.get("/Subtype") not in ("/Type1", "/TrueType")
                    or "/ToUnicode" in font
                    or font.get("/Encoding") != "/WinAnsiEncoding"
                ):
                    raise _Unsupported("unsupported_font_mapping")
                widths = _object(font.get("/Widths"))
                first = int(font.get("/FirstChar", -1))
                descriptor = font.get("/FontDescriptor")
                if widths is None or descriptor is None:
                    raise _Unsupported("missing_font_metrics")
                descriptor = descriptor.get_object()
                flags = int(descriptor.get("/Flags", 0))
                if not flags & 32 or flags & 4:
                    raise _Unsupported("unsupported_font_mapping")
                box = _numbers(_object(descriptor.get("/FontBBox", [])), 4)
                if box[0] >= box[2] or box[1] >= box[3]:
                    raise _Unsupported("invalid_font_metrics")
                x = xmax = None
                advance = 0.0
                for v in raw:
                    if not 0 <= v - first < len(widths):
                        raise _Unsupported("missing_font_metrics")
                    glyph_width = float(widths[v - first])
                    if not math.isfinite(glyph_width) or glyph_width <= 0:
                        raise _Unsupported("invalid_font_metrics")
                    left = (advance + box[0] * size / 1000) * tm[0] + tm[2]
                    right = (advance + box[2] * size / 1000) * tm[0] + tm[2]
                    x = left if x is None else min(x, left)
                    xmax = right if xmax is None else max(xmax, right)
                    advance += glyph_width * size / 1000
                if raw:
                    low = point(x, (box[1] * size / 1000) * tm[1] + tm[3])
                    high = point(xmax, (box[3] * size / 1000) * tm[1] + tm[3])
                    runs.append((raw.decode("ascii"), (*low, *high), index))
                    characters += len(raw)
                    if len(runs) > limits.max_runs or characters > limits.max_characters:
                        raise _Limit("text_limit")
            elif op in (b"Tc", b"Tw", b"Ts", b"Tr", b"Tz"):
                value = _numbers(args, 1)[0]
                if value != (100 if op == b"Tz" else 0):
                    raise _Unsupported("unsupported_text_state")
            elif op == b"w":
                width = _numbers(args, 1)[0]
                if width < 0:
                    raise _Unsupported("invalid_geometry")
            elif op in (b"J", b"j", b"M", b"rg", b"RG", b"g", b"G", b"k", b"K"):
                # Paint attributes do not alter geometric centerlines/declared font bounds.
                pass
            else:
                raise _Unsupported("unsupported_operator")
        if active or stack or path:
            raise _Unsupported("incomplete_graphics_state")
        grids, issues = _grids(segments, runs, number, limits, tick, margin)
        x0, y0, x1, y1 = _numbers(page.cropbox, 4)
        if any(
            g.x_lines[0] < x0 or g.x_lines[-1] > x1 or g.y_lines[-1] < y0 or g.y_lines[0] > y1
            for g in grids
        ):
            grids = []
            issues.add("clipped_grid")
        return (
            grids,
            PageEvidence(
                number,
                "needs_review" if issues else "success",
                tuple(sorted(issues)),
                len(segments),
                len(runs),
                len(grids),
            ),
            characters,
        )
    except _Unsupported as exc:
        return [], PageEvidence(number, "needs_review", (str(exc),), len(segments), len(runs), 0), 0


def _grids(segments, runs, page, limits, tick, margin=0.0):
    # Components are intersections of actual stroked H/V segments, never proximity clusters.
    normalized = []
    for a, b in segments:
        if a[1] == b[1]:
            normalized.append(("h", a[1], min(a[0], b[0]), max(a[0], b[0])))
        else:
            normalized.append(("v", a[0], min(a[1], b[1]), max(a[1], b[1])))
    normalized = sorted(set(normalized))
    edges = [set() for _ in normalized]
    for i, (kind, pos, lo, hi) in enumerate(normalized):
        tick()
        for j, (other, p, other_lo, other_hi) in enumerate(normalized[:i]):
            if (kind != other and lo <= p <= hi and other_lo <= pos <= other_hi) or (
                kind == other and pos == p and max(lo, other_lo) <= min(hi, other_hi)
            ):
                edges[i].add(j)
                edges[j].add(i)
    remaining = set(range(len(edges)))
    components = []
    while remaining:
        pending = [min(remaining)]
        component = set()
        while pending:
            n = pending.pop()
            if n in component:
                continue
            component.add(n)
            pending.extend(edges[n] - component)
        remaining -= component
        components.append([normalized[i] for i in sorted(component)])
    valid = []
    issues = set()

    def covers(lines, kind, pos, low, high):
        intervals = sorted((lo, hi) for k, p, lo, hi in lines if k == kind and p == pos)
        end = low
        for lo, hi in intervals:
            if lo > end:
                return False
            end = max(end, hi)
        return end >= high

    for lines in components:
        tick()
        xs = tuple(sorted({p for k, p, _, _ in lines if k == "v"}))
        ys = tuple(sorted({p for k, p, _, _ in lines if k == "h"}, reverse=True))
        if len(xs) < 3 or len(ys) < 3:
            issues.add("no_complete_grid")
            continue
        if (len(xs) - 1) * (len(ys) - 1) > limits.max_cells:
            raise _Limit("cell_limit")
        if not all(covers(lines, "v", x, ys[-1], ys[0]) for x in xs) or not all(
            covers(lines, "h", y, xs[0], xs[-1]) for y in ys
        ):
            issues.add("incomplete_or_merged_grid")
            continue
        # No boundary may extend outside the claimed rectangular grid.
        if any(
            lo < (xs[0] if k == "h" else ys[-1]) or hi > (xs[-1] if k == "h" else ys[0])
            for k, _, lo, hi in lines
        ):
            issues.add("ambiguous_grid_extent")
            continue
        assigned = {}
        ambiguous = False
        for text, (x0, y0, x1, y1), op in runs:
            if x1 < xs[0] or x0 > xs[-1] or y1 < ys[-1] or y0 > ys[0]:
                continue
            hits = [
                (r, c)
                for r in range(len(ys) - 1)
                for c in range(len(xs) - 1)
                if xs[c] + margin < x0 < x1 < xs[c + 1] - margin
                and ys[r + 1] + margin < y0 < y1 < ys[r] - margin
            ]
            if len(hits) != 1 or hits[0] in assigned:
                ambiguous = True
                break
            assigned[hits[0]] = (text, op)
        if ambiguous:
            issues.add("ambiguous_text_association")
            continue
        cells = tuple(
            CellEvidence(
                r,
                c,
                (xs[c], ys[r + 1], xs[c + 1], ys[r]),
                assigned.get((r, c), ("", None))[0],
                assigned.get((r, c), ("", None))[1],
            )
            for r in range(len(ys) - 1)
            for c in range(len(xs) - 1)
        )
        valid.append((xs, ys, cells))
    valid.sort(key=lambda g: (-g[1][0], g[0][0]))
    overlapping = set()
    for i, (xs, ys, _) in enumerate(valid):
        for j, (other_x, other_y, _) in enumerate(valid[:i]):
            if max(xs[0], other_x[0]) < min(xs[-1], other_x[-1]) and max(ys[-1], other_y[-1]) < min(
                ys[0], other_y[0]
            ):
                overlapping.update((i, j))
                issues.add("overlapping_grids")
    valid = [grid for i, grid in enumerate(valid) if i not in overlapping]
    grids = [GridEvidence(page, i, xs, ys, cells) for i, (xs, ys, cells) in enumerate(valid)]
    if not grids:
        issues.add("no_complete_grid")
    return grids, issues


def extract_tables(source: str | Path, *, limits: TableLimits | None = None) -> TableEvidence:
    active = limits or TableLimits()
    started = time.monotonic()
    digest = size = None

    def tick():
        if time.monotonic() - started >= active.timeout_seconds:
            raise _Limit("timeout")

    try:
        path = Path(source)
        if (
            any(p.is_symlink() or p.is_junction() for p in (path, *path.parents))
            or not path.is_file()
            or path.suffix.lower() != ".pdf"
        ):
            return TableEvidence(ExtractionStatus.FAILED, issues=("invalid_source",))
        size = path.stat().st_size
        if not 0 < size <= active.max_file_bytes:
            raise _Limit("input_limit")
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024**2), b""):
                tick()
                h.update(chunk)
        digest = h.hexdigest()
        grids = []
        pages = []
        chars = 0
        with path.open("rb") as f:
            reader = PdfReader(f, strict=True)
            if reader.is_encrypted:
                return TableEvidence(
                    ExtractionStatus.FAILED, digest, size, issues=("encrypted_pdf",)
                )
            if len(reader.pages) > active.max_pages:
                raise _Limit("page_limit")
            for number, page in enumerate(reader.pages, 1):
                tick()
                found, metadata, count = _page(page, number, active, tick)
                grids.extend(found)
                pages.append(metadata)
                chars += count
                if (
                    chars > active.max_characters
                    or sum(len(g.cells) for g in grids) > active.max_cells
                ):
                    raise _Limit("output_limit")
        status = (
            ExtractionStatus.NEEDS_REVIEW
            if not grids or any(p.issues for p in pages)
            else ExtractionStatus.SUCCESS
        )
        return TableEvidence(status, digest, size, tuple(grids), tuple(pages))
    except _Limit as exc:
        return TableEvidence(ExtractionStatus.FAILED, digest, size, issues=(str(exc),))
    except Exception:
        return TableEvidence(ExtractionStatus.FAILED, digest, size, issues=("invalid_pdf",))


def supplement(native: ExtractionResult, evidence: TableEvidence) -> ExtractionResult:
    """Offline comparison view, preserving all native blocks/warnings verbatim."""
    if (
        native.document_format != "pdf"
        or (evidence.source_sha256 is not None and native.source_sha256 != evidence.source_sha256)
        or (
            evidence.source_size_bytes is not None
            and native.source_size_bytes != evidence.source_size_bytes
        )
    ):
        raise ValueError("PDF evidence identity mismatch")
    failed = ExtractionStatus.FAILED in (native.status, evidence.status)
    review = ExtractionStatus.NEEDS_REVIEW in (native.status, evidence.status)
    blocks = (
        native.blocks
        if failed
        else native.blocks
        + tuple(g.block(len(native.blocks) + i) for i, g in enumerate(evidence.grids))
    )
    return replace(
        native,
        blocks=blocks,
        status=ExtractionStatus.FAILED
        if failed
        else ExtractionStatus.NEEDS_REVIEW
        if review
        else ExtractionStatus.SUCCESS,
        error_category=native.error_category
        or (ErrorCategory.EXTRACTION_FAILED if failed else None),
    )
