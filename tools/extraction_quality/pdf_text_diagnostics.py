"""Read-only source-text diagnosis; publish reason codes, never private literal values."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from doclens_ai.extraction.evidence_v2 import valid_bbox
from doclens_ai.extraction.fidelity_gold import fingerprint
from tools.extraction_quality import pdf_grid_proposals as grids
from tools.extraction_quality import pdf_review_validation as validation
from tools.extraction_quality import pdf_table_review_packet as packet


def diagnose(source: Path, expected_sha256: str, page: int, proposal: dict) -> dict:
    """Analyze original candidate geometry in memory; corrections/drafts are never mutated."""
    packet.no_links(source)
    if packet.sha(source) != expected_sha256:
        raise packet.PacketError("Original source SHA mismatch")
    pages = validation.original_pages(source)
    if type(page) is not int or not 1 <= page <= len(pages) or pages[page - 1]["rotation"] != 0:
        raise packet.PacketError("Original page rejected")
    if "candidate" in proposal:
        context = proposal["context"]
        if (
            context["source_sha256"] != expected_sha256
            or context["page_identity"] != pages[page - 1]
        ):
            raise packet.PacketError("Proposal source/page binding mismatch")
        candidate = copy.deepcopy(proposal["candidate"])
    else:
        candidate = copy.deepcopy(proposal)
    if candidate["method"] != grids.METHOD or candidate["status"] != "PROPOSED":
        raise packet.PacketError("Original ruled-grid candidate required")
    xs, ys = candidate["x_boundaries"], candidate["y_boundaries"]
    bbox = [xs[0], ys[-1], xs[-1], ys[0]]
    if not valid_bbox(tuple(bbox), tuple(pages[page - 1]["crop_box_pdf_user_space"])):
        raise packet.PacketError("Original grid outside page")
    grids.check_cells(candidate["cells"], bbox, len(ys) - 1, len(xs) - 1)
    geometry = [
        {
            k: c[k]
            for k in ("row", "column", "row_span", "column_span", "bbox_pdf_user_space_points")
        }
        for c in candidate["cells"]
    ]
    for cell in candidate["cells"]:
        cell.update(literal_text=None, text_status="NO_RELIABLE_TEXT")
    report = {}
    grids.add_text(source, page, candidate, diagnostics=report)
    if packet.sha(source) != expected_sha256:
        raise packet.PacketError("Original source changed during diagnosis")
    report.update(source_sha256=expected_sha256, geometry_fingerprint=fingerprint(geometry))
    return report


def run(
    source: Path,
    expected_sha256: str,
    page: int,
    proposal_path: Path,
    output: Path,
    *,
    root: Path = packet.ROOT,
) -> dict:
    """Only a fresh, ignored ml30c-* sibling directory can receive sanitized output."""
    packet.no_links(output)
    if output.resolve().parent != (
        root / "evaluation-output"
    ).resolve() or not output.name.startswith("ml30c-"):
        raise packet.PacketError("Fresh separate ML-30C diagnostic directory required")
    packet.fresh_output(output, source.parent, root=root)
    report = diagnose(source, expected_sha256, page, validation.read_json(proposal_path))
    output.mkdir()
    packet.write_json(output / "text-diagnostics.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--page", type=int, required=True)
    parser.add_argument("--proposal", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = run(args.source, args.source_sha256, args.page, args.proposal, args.output)
        print(
            json.dumps(
                {k: report[k] for k in ("non_null", "null", "primary_null_reason_counts")},
                sort_keys=True,
            )
        )
    except Exception:  # noqa: BLE001 - content-free CLI diagnostics
        print("BLOCKED: original binding, candidate or fresh private output rejected")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
