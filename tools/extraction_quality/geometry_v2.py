"""EX-01 private visual packet: original PDF, publisher PNG and annotation overlays."""

from __future__ import annotations

import argparse
import base64
import html
import json
import shutil
from pathlib import Path

from doclens_ai.eda.corpus_v2 import asset_path, audit, load
from doclens_ai.eda.dataset_adapters_v2 import doclaynet
from tools.extraction_quality.extraction_v2 import private_destination, write


def packet(root: Path, sample, output: Path, *, frame: str) -> dict:
    private_destination(output)
    report = doclaynet(root, sample, frame=frame)
    original = asset_path(root, sample.original)
    image = asset_path(root, sample.image)
    if report["width"] * report["height"] > 20_000_000 or len(report["regions"]) > 2000:
        raise ValueError("packet image/region budget")
    encoded = base64.b64encode(image.read_bytes()).decode("ascii")
    rectangles = []
    for region in report["regions"]:
        left, top, right, bottom = region["bbox_image"]
        rectangles.append(
            f'<rect x="{left}" y="{top}" width="{right - left}" height="{bottom - top}" '
            'fill="none" stroke="#d11" stroke-width="2"><title>'
            + html.escape(str(region["annotation_id"]) + " " + region["class"])
            + "</title></rect>"
        )
    markup = (
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta http-equiv="Content-Security-Policy" '
        "content=\"default-src 'none'; img-src data:; style-src 'unsafe-inline'\">"
        "<title>Unreviewed geometry packet</title>"
        "<style>body{font:18px sans-serif;max-width:1100px;margin:2em auto}svg{width:100%}</style>"
        "<h1>Automatic geometry inspection packet</h1><p>"
        + html.escape(sample.sample_id)
        + "</p><p>Human review: NOT PERFORMED. Compare the separately copied original.pdf "
        "with the publisher image below. Region agreement does not verify text, reading order, "
        "cell relationships or original-document rights.</p>"
        + f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {report["width"]} '
        + f'{report["height"]}"><image width="100%" height="100%" '
        + f'href="data:image/png;base64,{encoded}"/>'
        + "".join(rectangles)
        + "</svg></html>"
    )
    output.mkdir(parents=True)
    shutil.copyfile(original, output / "original.pdf")
    write(output / "geometry.json", report)
    write(
        output / "manual-checklist.json",
        {
            "sample_id": sample.sample_id,
            "source_sha256": sample.original.sha256,
            "frame": frame,
            "reviewer": None,
            "reviewed_on": None,
            "page_pair_identity": None,
            "crop_media_rotation": None,
            "class_boundaries": None,
            "text_alignment": None,
            "ambiguous_regions": None,
            "adjudication": None,
            "review_status": "NOT_PERFORMED",
        },
    )
    with (output / "inspection.html").open("x", encoding="utf-8") as stream:
        stream.write(markup)
    asset_path(root, sample.original)
    asset_path(root, sample.image)
    return {
        "sample_id": sample.sample_id,
        "regions": len(report["regions"]),
        "unsupported": len(report["unsupported"]),
        "status": report["status"],
        "human_review": "NOT_PERFORMED",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--sample", required=True)
    parser.add_argument("--frame", choices=("media", "crop"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        value = load(args.manifest)
        admission = audit(value, args.root)
        selected = next(s for s in value.samples if s.sample_id == args.sample)
        if not next(
            r["native_eligible"] for r in admission["rows"] if r["sample_id"] == args.sample
        ):
            raise ValueError("unqualified sample")
        print(
            json.dumps(packet(args.root, selected, args.output, frame=args.frame), sort_keys=True)
        )
        return 0
    except Exception:  # noqa: BLE001 - private annotation/source diagnostics stay local
        print("BLOCKED: qualified original/annotation pair or fresh private destination required")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
