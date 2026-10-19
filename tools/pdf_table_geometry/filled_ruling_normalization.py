"""ML-26 public-synthetic representation experiment, never production extraction."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from types import SimpleNamespace

from doclens_ai.extraction.pdfplumber_table_candidate import SETTINGS, _grid
from doclens_ai.extraction.pdfplumber_table_candidate import Limits as GridLimits
from tools.pdf_table_geometry import diagnose

VERSION = "filled-ruling-synthetic-v1"
GUARDS = {
    "timeout_seconds": 20.0,
    "max_process_bytes": 512 * 1024**2,
    "max_capture_bytes": 8 * 1024**2,
    "sample_seconds": 0.02,
}


@dataclass(frozen=True, slots=True)
class Limits:
    max_file_bytes: int = 1024**2
    max_objects: int = 256
    max_edges: int = 256
    max_characters: int = 4096
    max_cells: int = 1024
    max_operations: int = 5000
    max_stream_bytes: int = 1024**2
    timeout_seconds: float = 5.0

    def __post_init__(self) -> None:
        for key, value in asdict(self).items():
            if key == "timeout_seconds":
                if type(value) not in (int, float) or not 0 < value < math.inf:
                    raise ValueError("invalid_limits")
            elif type(value) is not int or value <= 0:
                raise ValueError("invalid_limits")


class Review(Exception):
    """Unsupported source geometry, not repaired or accepted."""


def fingerprint(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def direct_rectangles(raw_page, reader, limits: Limits, tick) -> list[dict]:
    """Restricted direct-stream audit; unsupported graphics state fails closed."""
    from pypdf.generic import ContentStream

    if raw_page.get("/Annots") or raw_page.rotation or raw_page.cropbox != raw_page.mediabox:
        raise Review("unsupported_page_state")
    content = raw_page.get_contents()
    if content is None:
        return []
    if len(content.get_data()) > limits.max_stream_bytes:
        raise diagnose.DiagnosticLimit("stream_limit")
    operations = ContentStream(content, reader).operations
    if len(operations) > limits.max_operations:
        raise diagnose.DiagnosticLimit("operation_limit")
    # These operators do not introduce transforms/clipping/alpha/Forms/text modes.
    allowed = {b"re", b"m", b"l", b"S", b"f", b"n", b"BT", b"ET", b"Tf", b"Tm", b"Tj"}
    pending: list[tuple[int, list[float]]] = []
    other_path = False
    rectangles = []
    for index, (args, op) in enumerate(operations):
        tick()
        if op not in allowed:
            raise Review("unsupported_operator")
        if op == b"re":
            values = [float(v) for v in args]
            if len(values) != 4 or not all(math.isfinite(v) for v in values):
                raise Review("invalid_rectangle")
            if values[2] <= 0 or values[3] <= 0:
                raise Review("invalid_rectangle")
            pending.append((index, values))
        elif op in (b"m", b"l"):
            other_path = True
        elif op in (b"f", b"S", b"n"):
            if op == b"f" and (other_path or len(pending) != 1):
                raise Review("ambiguous_fill_path")
            if op != b"n":
                for path_index, values in pending:
                    x, y, width, height = values
                    rectangles.append(
                        {
                            "path_operation": path_index,
                            "paint_operation": index,
                            "paint": op.decode(),
                            "bbox": [
                                x,
                                float(raw_page.mediabox.top) - y - height,
                                x + width,
                                float(raw_page.mediabox.top) - y,
                            ],
                        }
                    )
            pending = []
            other_path = False
    if pending or other_path:
        raise Review("unfinished_path")
    return rectangles


def derived_edges(page, records: list[dict], tick) -> tuple[list[dict], list[dict]]:
    """No page mutation. Every synthetic line lies within its original painted bar."""
    if len(records) != len(page.rects) or page.curves or page.images:
        raise Review("unreconciled_objects")
    origins = []
    fills = any(r.get("fill") for r in page.rects)
    edges = []
    for index, (rect, record) in enumerate(zip(page.rects, records, strict=True)):
        tick()
        bounds = [float(rect[k]) for k in ("x0", "top", "x1", "bottom")]
        if bounds != record["bbox"] or bool(rect.get("fill")) != (record["paint"] == "f"):
            raise Review("rectangle_link_mismatch")
        origin = {
            **record,
            "object_id": f"page:1/rect:{index}",
            "fill": bool(rect["fill"]),
            "stroke": bool(rect["stroke"]),
        }
        origins.append(origin)
        if not fills:
            continue
        width, height = bounds[2] - bounds[0], bounds[3] - bounds[1]
        if (
            not rect["fill"]
            or rect["stroke"]
            or min(width, height) <= 0
            or min(width, height) > 2
            or max(width, height) < 3
            or max(width, height) / min(width, height) < 10
            or rect.get("non_stroking_color") not in (0, (0,), (0, 0, 0))
        ):
            raise Review("ambiguous_painted_shape")
        x0, top, x1, bottom = bounds
        orientation = "h" if width > height else "v"
        if orientation == "h":
            top = bottom = (top + bottom) / 2
        else:
            x0 = x1 = (x0 + x1) / 2
        edges.append(
            {
                "x0": x0,
                "x1": x1,
                "top": top,
                "bottom": bottom,
                "width": x1 - x0,
                "height": bottom - top,
                "orientation": orientation,
                "object_type": "line",
                "source_object_id": origin["object_id"],
                "derived": True,
            }
        )
    if fills:
        if page.lines:
            raise Review("mixed_painted_geometry")
        # Bars must form a complete exact grid. No missing joints are extended.
        hs = [e for e in edges if e["orientation"] == "h"]
        vs = [e for e in edges if e["orientation"] == "v"]
        if (
            len(hs) < 3
            or len(vs) < 3
            or len({e["top"] for e in hs}) != len(hs)
            or len({e["x0"] for e in vs}) != len(vs)
        ):
            raise Review("incomplete_ruling_grid")
        for h in hs:
            for v in vs:
                tick()
                if not h["x0"] <= v["x0"] <= h["x1"] or not v["top"] <= h["top"] <= v["bottom"]:
                    raise Review("unsupported_joint")
        for a, rect in enumerate(page.rects):
            for b in page.rects[a + 1 :]:
                aw, ah = rect["width"], rect["height"]
                if (aw > ah) == (b["width"] > b["height"]):
                    if diagnose.overlaps(
                        tuple(rect[k] for k in ("x0", "top", "x1", "bottom")),
                        tuple(b[k] for k in ("x0", "top", "x1", "bottom")),
                    ):
                        raise Review("overlapping_parallel_bars")
    else:
        edges = [
            {**edge, "source_edge_index": i, "derived": False} for i, edge in enumerate(page.edges)
        ]
    return edges, origins


def normalize(source: Path, limits: Limits | None = None) -> dict:
    """Public synthetic input only; retain originals and publish no cells on review."""
    import pdfplumber
    from pdfplumber.table import TableFinder
    from pypdf import PdfReader

    active = limits or Limits()
    start = time.monotonic()

    def tick() -> None:
        if time.monotonic() - start >= active.timeout_seconds:
            raise diagnose.DiagnosticLimit("timeout")

    if (
        any(p.is_symlink() or p.is_junction() for p in (source, *source.parents))
        or not source.is_file()
        or source.suffix.lower() != ".pdf"
    ):
        raise ValueError("invalid_source")
    if not 0 < source.stat().st_size <= active.max_file_bytes:
        raise diagnose.DiagnosticLimit("input_limit")
    result = {
        "version": VERSION,
        "source_sha256": sha(source),
        "page": 1,
        "coordinate_system": "pdfplumber_x0_top_x1_bottom_points",
        "settings": dict(SETTINGS),
        "limits": asdict(active),
        "status": "needs_review",
        "cells": [],
        "issues": [],
        "original": {},
        "representation_edges": [],
        "origins": [],
    }
    reader = PdfReader(source)
    if len(reader.pages) != 1:
        raise diagnose.DiagnosticLimit("page_limit")
    with pdfplumber.open(source) as pdf:
        page = pdf.pages[0]
        tick()
        if len(page.rects) + len(page.lines) + len(page.curves) > active.max_objects:
            raise diagnose.DiagnosticLimit("object_limit")
        if len(page.chars) > active.max_characters or len(page.edges) > active.max_edges:
            raise diagnose.DiagnosticLimit("object_limit")
        original = TableFinder(page, dict(SETTINGS))
        if len(original.cells) > active.max_cells:
            raise diagnose.DiagnosticLimit("cell_limit")
        result["original"] = {
            "rectangles": [
                {
                    "object_id": f"page:1/rect:{i}",
                    **{k: r.get(k) for k in ("x0", "top", "x1", "bottom", "fill", "stroke")},
                }
                for i, r in enumerate(page.rects)
            ],
            "edges": [dict(e) for e in page.edges],
            "characters": [
                {"index": i, **{k: c[k] for k in ("text", "x0", "top", "x1", "bottom")}}
                for i, c in enumerate(page.chars)
            ],
            "detector_cells": sorted(original.cells),
        }
        try:
            records = direct_rectangles(reader.pages[0], reader, active, tick)
            edges, origins = derived_edges(page, records, tick)
            result["representation_edges"], result["origins"] = edges, origins
            for char in page.chars:
                cb = tuple(char[k] for k in ("x0", "top", "x1", "bottom"))
                if any(r["fill"] and diagnose.overlaps(cb, r["bbox"]) for r in origins):
                    raise Review("text_crosses_painted_bar")
            view = SimpleNamespace(edges=edges, bbox=page.bbox)
            finder = TableFinder(view, dict(SETTINGS))
            if len(finder.cells) > active.max_cells:
                raise diagnose.DiagnosticLimit("cell_limit")
            if len(finder.tables) != 1 or len(finder.cells) != len(finder.tables[0].cells):
                raise Review("not_one_complete_table")
            grid = _grid(
                page,
                finder.tables[0],
                0,
                page.chars,
                edges,
                GridLimits(max_cells=active.max_cells),
                tick,
            )
            assigned = [i for cell in grid.cells for i in cell.character_indices]
            if sorted(assigned) != list(range(len(page.chars))):
                raise Review("unassigned_source_text")
            result["cells"] = [asdict(cell) for cell in grid.cells]
            result["status"] = "accepted_synthetic"
        except Review as exc:
            result["issues"] = [str(exc)]
        except Exception as exc:
            # Reuse frozen ML-24 validation without broadening its acceptance policy.
            from doclens_ai.extraction.pdfplumber_table_candidate import _Review

            if not isinstance(exc, _Review):
                raise
            result["issues"] = [str(exc)]
        tick()
    if sha(source) != result["source_sha256"]:
        raise ValueError("source_drift")
    return result


def collect(stage: Path, resource: dict, digest: str) -> dict | None:
    """Validate before publication; never rename an in-flight capture."""
    path = stage / "result.capture"
    try:
        if (
            resource["failure"]
            or not resource["cleanup"]
            or path.stat().st_size > GUARDS["max_capture_bytes"]
        ):
            return None
        value = json.loads(path.read_text(encoding="utf-8"))
        if (
            not isinstance(value, dict)
            or value.get("version") != VERSION
            or value.get("source_sha256") != digest
            or value.get("status") not in ("accepted_synthetic", "needs_review")
            or not isinstance(value.get("cells"), list)
            or (value["status"] == "needs_review" and value["cells"])
            or (value["status"] == "accepted_synthetic" and not value["cells"])
            or value.get("settings") != dict(SETTINGS)
            or not isinstance(value.get("original"), dict)
        ):
            return None
        path.rename(stage / "result.json")
        return value
    except (OSError, ValueError):
        return None
    finally:
        path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--worker", action="store_true")
    args = parser.parse_args()
    try:
        if args.worker:
            value = normalize(args.input)
            diagnose.write_capture(
                args.output / "result.capture", value, GUARDS["max_capture_bytes"]
            )
            return 0
        from tools.docx_footnote_candidate.benchmark import monitor

        args.output.mkdir(parents=True, exist_ok=False)
        digest = sha(args.input)
        resource = monitor(
            [
                sys.executable,
                "-B",
                str(Path(__file__).resolve()),
                "--worker",
                "--input",
                str(args.input),
                "--output",
                str(args.output),
            ],
            args.output,
            guards=GUARDS,
        )
        value = collect(args.output, resource, digest)
        (args.output / "resource.json").write_text(json.dumps(resource, sort_keys=True) + "\n")
        print(
            json.dumps(
                {
                    "execution": "PASS" if value else "BLOCKED",
                    "quality": "NOT_EVALUATED",
                    "production_authorized": False,
                }
            )
        )
        return 0 if value else 1
    except Exception:
        print("BLOCKED: synthetic normalization failed")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
