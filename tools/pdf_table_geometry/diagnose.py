"""Source-only PDF topology audit. No extraction repair, Gold scoring or tuning."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import logging
import math
import sys
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

from doclens_ai.extraction.pdfplumber_table_candidate import SETTINGS

THIN_POINTS = 2.0
NEAR_POINTS = 3.0
VERSION = "pdf-table-geometry-diagnostic-v1"
AREA = Path("evaluation-output/pdf-table-geometry-v1-20261019")


@dataclass(frozen=True, slots=True)
class Limits:
    max_file_bytes: int = 50 * 1024**2
    max_pages: int = 100
    max_characters: int = 500_000
    max_edges: int = 5_000
    max_cells: int = 10_000
    max_operations: int = 50_000
    max_stream_bytes: int = 8 * 1024**2
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
            raise ValueError("Invalid diagnostic limits")


class DiagnosticLimit(Exception):
    pass


def write_capture(path: Path, value: dict, max_bytes: int = 64 * 1024**2) -> None:
    """Stable filename while monitored; only the parent publishes after exit zero."""
    count = 1
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        for chunk in json.JSONEncoder(sort_keys=True, indent=2).iterencode(value):
            count += len(chunk.encode("utf-8"))
            if count > max_bytes:
                raise DiagnosticLimit("output_limit")
            stream.write(chunk)
        stream.write("\n")


def collect_capture(stage: Path, resource: dict) -> dict | None:
    """Never accept incomplete/terminated output; cleanup occurs after monitoring."""
    capture = stage / "result.capture"
    try:
        if resource["failure"] or not resource["cleanup"]:
            return None
        value = json.loads(capture.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            return None
        capture.rename(stage / "result.json")
        return value
    except (ValueError, OSError):
        return None
    finally:
        capture.unlink(missing_ok=True)


def box(values):
    if len(values) != 4 or any(
        not math.isfinite(float(v)) or abs(float(v)) > 10**7 for v in values
    ):
        return None
    result = tuple(float(v) for v in values)
    return result if result[0] < result[2] and result[1] < result[3] else None


def overlaps(a, b):
    return max(a[0], b[0]) < min(a[2], b[2]) and max(a[1], b[1]) < min(a[3], b[3])


def inside(a, b):
    return b[0] <= a[0] < a[2] <= b[2] and b[1] <= a[1] < a[3] <= b[3]


def edge_groups(edges):
    groups = defaultdict(list)
    signatures = []
    for edge in edges:
        orientation = edge.get("orientation")
        if orientation not in ("h", "v"):
            continue
        pos = edge["x0"] if orientation == "v" else edge["top"]
        lo, hi = (edge["top"], edge["bottom"]) if orientation == "v" else (edge["x0"], edge["x1"])
        if (
            not all(math.isfinite(float(v)) and abs(float(v)) <= 10**7 for v in (pos, lo, hi))
            or hi < lo
        ):
            raise ValueError("Invalid edge geometry")
        groups[orientation, pos].append((lo, hi))
        signatures.append((orientation, pos, lo, hi))
    return {k: sorted(v) for k, v in groups.items()}, len(signatures) - len(set(signatures))


def continuous(groups, orientation, position, low, high):
    end = low
    for lo, hi in groups.get((orientation, position), ()):
        if hi < low:
            continue
        if lo > end:
            return False
        end = max(end, hi)
        if end >= high:
            return True
    return False


def topology(edges, tick):
    groups, duplicates = edge_groups(edges)
    overlap_pairs = gaps = near_gaps = 0
    for intervals in groups.values():
        tick()
        end = None
        for i, (lo, hi) in enumerate(intervals):
            overlap_pairs += sum(min(hi, b) > max(lo, a) for a, b in intervals[:i])
            if end is not None and lo > end:
                gaps += 1
                near_gaps += int(lo - end <= NEAR_POINTS)
            end = hi if end is None else max(end, hi)
    horizontal = [(p, a, b) for (o, p), items in groups.items() if o == "h" for a, b in items]
    vertical = [(p, a, b) for (o, p), items in groups.items() if o == "v" for a, b in items]
    crossings = near = 0
    for y, x0, x1 in horizontal:
        tick()
        for x, y0, y1 in vertical:
            dx = max(x0 - x, 0, x - x1)
            dy = max(y0 - y, 0, y - y1)
            if dx == 0 and dy == 0:
                crossings += 1
            elif max(dx, dy) <= NEAR_POINTS:
                near += 1
    return {
        "duplicate_edges": duplicates,
        "collinear_overlap_pairs": overlap_pairs,
        "positive_collinear_gaps": gaps,
        "near_collinear_gaps": near_gaps,
        "exact_crossing_edge_pairs": crossings,
        "near_missing_crossing_pairs": near,
    }


def page_summary(page, limits, tick):
    from pdfplumber.table import TableFinder

    chars = page.chars
    edges = page.edges
    if len(chars) > limits.max_characters or len(edges) > limits.max_edges:
        raise DiagnosticLimit("object_limit")
    groups, _ = edge_groups(edges)
    rectangles = [r for r in page.rects if box((r["x0"], r["top"], r["x1"], r["bottom"]))]
    thin = [
        r
        for r in rectangles
        if min(r["width"], r["height"]) <= THIN_POINTS and max(r["width"], r["height"]) >= 3
    ]
    painted = [(r["x0"], r["top"], r["x1"], r["bottom"]) for r in thin if r.get("fill")]
    finder = TableFinder(page, dict(SETTINGS))
    tick()
    if len(finder.cells) > limits.max_cells:
        raise DiagnosticLimit("cell_limit")
    char_boxes = [box((c["x0"], c["top"], c["x1"], c["bottom"])) for c in chars]
    tables = []
    for index, table in enumerate(
        sorted(finder.tables, key=lambda t: (t.bbox[1], t.bbox[0], t.bbox[3], t.bbox[2]))
    ):
        tick()
        cells = [box(c) for c in table.cells]
        if any(c is None for c in cells):
            raise ValueError("Invalid cell geometry")
        xs = sorted({v for c in cells for v in (c[0], c[2])})
        ys = sorted({v for c in cells for v in (c[1], c[3])})
        missing = 0
        for x0, y0, x1, y1 in cells:
            tick()
            missing += sum(
                not continuous(groups, o, p, lo, hi)
                for o, p, lo, hi in (
                    ("v", x0, y0, y1),
                    ("v", x1, y0, y1),
                    ("h", y0, x0, x1),
                    ("h", y1, x0, x1),
                )
            )
        intersecting = [c for c in char_boxes if c and overlaps(c, table.bbox)]
        hits = []
        for c in intersecting:
            tick()
            hits.append(sum(inside(c, cell) for cell in cells))
        tables.append(
            {
                "table_index": index,
                "cells": len(cells),
                "columns_from_boundaries": len(xs) - 1,
                "rows_from_boundaries": len(ys) - 1,
                "lattice_positions": (len(xs) - 1) * (len(ys) - 1),
                "thin_x_intervals": sum(
                    b - a <= THIN_POINTS for a, b in zip(xs, xs[1:], strict=False)
                ),
                "thin_y_intervals": sum(
                    b - a <= THIN_POINTS for a, b in zip(ys, ys[1:], strict=False)
                ),
                "micro_cells": sum(min(c[2] - c[0], c[3] - c[1]) <= THIN_POINTS for c in cells),
                "centers_in_filled_thin_rectangles": sum(
                    any(
                        r[0] < (c[0] + c[2]) / 2 < r[2] and r[1] < (c[1] + c[3]) / 2 < r[3]
                        for r in painted
                    )
                    for c in cells
                ),
                "missing_source_cell_boundaries": missing,
                "intersecting_char_boxes": len(hits),
                "char_boxes_in_exactly_one_cell": hits.count(1),
                "char_boxes_in_no_cell": hits.count(0),
                "char_boxes_in_multiple_cells": sum(v > 1 for v in hits),
                "minimum_grid_rejection": len(xs) < 3 or len(ys) < 3,
                "nonuniform_lattice_rejection": len(cells) != (len(xs) - 1) * (len(ys) - 1),
            }
        )
    nominal_black = (0, (0,), (0, 0, 0), (0, 0, 0, 1))
    return {
        "page": page.page_number,
        "rotation": page.rotation,
        "characters": len(chars),
        "invalid_char_boxes": char_boxes.count(None),
        "nonupright_characters": sum(not c["upright"] for c in chars),
        "lines": len(page.lines),
        "rectangles_total": len(page.rects),
        "nonpainting_rectangles": sum(
            not r.get("fill") and not r.get("stroke") for r in page.rects
        ),
        "zero_area_rectangles": sum(r["width"] == 0 or r["height"] == 0 for r in page.rects),
        "rectangles": len(rectangles),
        "thin_rectangles": len(thin),
        "filled_thin_rectangles": len(painted),
        "nominal_black_filled_thin_rectangles": sum(
            r.get("fill") and r.get("non_stroking_color") in nominal_black for r in thin
        ),
        "raw_edges": len(edges),
        "edge_types": dict(Counter(e.get("object_type", "UNKNOWN") for e in edges)),
        "finder_edges": len(finder.edges),
        "finder_intersections": len(finder.intersections),
        "native_cells": len(finder.cells),
        "singleton_cells_filtered": len(finder.cells) - sum(len(t.cells) for t in finder.tables),
        "native_micro_cells": sum(
            min(c[2] - c[0], c[3] - c[1]) <= THIN_POINTS for c in finder.cells
        ),
        "native_centers_in_filled_thin_rectangles": sum(
            any(
                r[0] < (c[0] + c[2]) / 2 < r[2] and r[1] < (c[1] + c[3]) / 2 < r[3] for r in painted
            )
            for c in finder.cells
        ),
        "tables": tables,
        **topology(edges, tick),
    }


def analyze_pdf(source: Path, limits: Limits | None = None):
    import pdfplumber
    from pypdf import PdfReader

    active = limits or Limits()
    started = time.monotonic()

    def tick():
        if time.monotonic() - started >= active.timeout_seconds:
            raise DiagnosticLimit("timeout")

    if (
        any(p.is_symlink() or p.is_junction() for p in (source, *source.parents))
        or source.suffix.lower() != ".pdf"
        or not source.is_file()
        or not 0 < source.stat().st_size <= active.max_file_bytes
    ):
        raise DiagnosticLimit("invalid_source_or_size")
    pages = []
    characters = 0
    with source.open("rb") as raw, pdfplumber.open(source) as doc:
        reader = PdfReader(raw, strict=True)
        if len(doc.pages) > active.max_pages or len(reader.pages) != len(doc.pages):
            raise DiagnosticLimit("page_limit")
        for page, native in zip(doc.pages, reader.pages, strict=True):
            tick()
            summary = page_summary(page, active, tick)
            characters += summary["characters"]
            if characters > active.max_characters:
                raise DiagnosticLimit("character_limit")
            stream = native.get_contents()
            operations = []
            if stream is not None:
                if len(stream.get_data()) > active.max_stream_bytes:
                    raise DiagnosticLimit("stream_limit")
                operations = stream.operations
            if len(operations) > active.max_operations:
                raise DiagnosticLimit("operation_limit")
            counts = Counter(op for _, op in operations)
            summary["independent_pypdf_operators"] = {
                op.decode(): counts[op]
                for op in (
                    b"re",
                    b"m",
                    b"l",
                    b"S",
                    b"s",
                    b"f",
                    b"f*",
                    b"B",
                    b"B*",
                    b"b",
                    b"b*",
                    b"F",
                    b"W",
                    b"W*",
                    b"n",
                    b"cm",
                    b"Do",
                )
            }
            pages.append(summary)
            page.close()
    return {"version": VERSION, "pages": pages, "quality": "NOT_EVALUATED"}


def input_identity():
    from tools.pdf_table_candidate import benchmark as base
    from tools.pdfplumber_table_candidate.benchmark import runtime_identity

    sources = base._read_sources(Path("docs/eda/corpus_v1_manifest.csv"))
    paths = base.verify_corpus(Path("local-corpus"), sources, base.ExtractionLimits())
    gold = Path("local-evaluation/extraction_fidelity_v1_expanded_approved.jsonl")
    registered = json.loads(
        Path(
            "evaluation-output/pdfplumber-table-v1-20261019/registration-v2/registration.json"
        ).read_text()
    )
    if (
        base.sha(gold) != registered["gold"]
        or base.fingerprint(sources) != registered["source_map"]
        or base.sha(Path("docs/eda/corpus_v1_manifest.csv")) != registered["manifest"]
        or dict(SETTINGS) != registered["table_settings"]
    ):
        raise ValueError("Input drift")
    for path, digest in registered["code"].items():
        if base.sha(Path(path)) != digest:
            raise ValueError("Frozen code drift")
    records = base.load_gold(gold, sources)
    if (
        len(paths) != 90
        or len(records) != 19
        or len(registered["cohort"]) != 5
        or any(list(sources[k]) != v for k, v in registered["cohort"].items())
    ):
        raise ValueError("Cohort drift")
    artifacts = {}
    for area, count in (("pdf-table-v1-20261019", 39), ("pdfplumber-table-v1-20261019", 84)):
        root = Path("evaluation-output") / area
        manifest = json.loads((root / "terminal-artifact-manifest.json").read_text())
        if len(manifest) != count or any(
            base.sha(root / n) != digest for n, digest in manifest.items()
        ):
            raise ValueError("Frozen artifact drift")
        artifacts[area] = base.sha(root / "terminal-artifact-manifest.json")
    return {
        "manifest": registered["manifest"],
        "gold": registered["gold"],
        "source_map": registered["source_map"],
        "cohort": registered["cohort"],
        "runtime": runtime_identity(),
        "prior_artifacts": artifacts,
    }, paths


def main():
    from tools.pdf_table_candidate import benchmark as base

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        base.require_unoptimized()
        base.fresh_output(
            args.output / "boundary" if args.worker else args.output, Path("local-corpus")
        )
        if args.worker:
            if not args.output.is_dir() or {p.name for p in args.output.iterdir()} != {
                "resources.jsonl"
            }:
                raise ValueError("Worker output rejected")
            with (
                contextlib.redirect_stdout(io.StringIO()),
                contextlib.redirect_stderr(io.StringIO()),
            ):
                logging.disable(logging.CRITICAL)
                report = analyze_pdf(args.worker)
            write_capture(args.output / "result.capture", report)
            return 0
        identity, paths = input_identity()
        pins = {
            p: base.sha(Path(p))
            for p in (
                "tools/pdf_table_geometry/diagnose.py",
                "tests/unit/test_pdf_table_geometry.py",
            )
        }
        args.output.mkdir(parents=True)
        documents = []
        for key in identity["cohort"]:
            stage = args.output / key
            stage.mkdir()
            resource = base.monitor(
                [
                    sys.executable,
                    "-B",
                    str(Path(__file__).resolve()),
                    "--worker",
                    str(paths[key]),
                    "--output",
                    str(stage),
                ],
                stage,
            )
            data = collect_capture(stage, resource)
            documents.append({"document_id": key, "resource": resource, "diagnostic": data})
        after, _ = input_identity()
        if identity != after:
            raise ValueError("Post-audit input drift")
        passed = all(
            d["diagnostic"] is not None
            and d["resource"]["cleanup"]
            and not d["resource"]["failure"]
            for d in documents
        )
        stable = {
            "identity": identity,
            "code": pins,
            "limits": asdict(Limits()),
            "settings": dict(SETTINGS),
            "thin_points": THIN_POINTS,
            "near_points": NEAR_POINTS,
            "documents": [{k: v for k, v in d.items() if k != "resource"} for d in documents],
        }
        base.write_json(
            args.output / "summary.json",
            {
                "status": "PASS" if passed else "BLOCKED",
                "fingerprint": base.fingerprint(stable),
                "stable": stable,
                "resources": [d["resource"] for d in documents],
            },
        )
        base.write_json(
            args.output / "artifact-manifest.json",
            {
                p.relative_to(args.output).as_posix(): base.sha(p)
                for p in sorted(args.output.rglob("*"))
                if p.is_file()
            },
        )
        print(
            json.dumps(
                {
                    "status": "PASS" if passed else "BLOCKED",
                    "documents": len(documents),
                    "fingerprint": base.fingerprint(stable),
                    "quality": "NOT_EVALUATED",
                }
            )
        )
        return 0 if passed else 1
    except Exception as exc:
        print("BLOCKED: geometry diagnostic rejected (" + type(exc).__name__ + ")")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
