"""EX-06 offline text-layer diagnosis and literal RU/KK/EN OCR scoring.

Signals suggest inspection routes; low text or a missing ToUnicode map does not
prove a scan or incorrect encoding. OCR observations never replace native text.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from pypdf import PdfReader

from doclens_ai.eda.corpus_v2 import asset_path, audit, load
from tools.extraction_quality.extraction_v2 import private_destination, write

KAZAKH = "ӘҒҚҢӨҰҮҺІәғқңөұүһі"
NUMBERS = re.compile(r"(?<![\w+−.,/:\-])[-+−]?\d+(?:[.,/:-]\d+)*(?![\w.,/:\-])")


def signals(text: str, *, images: int, fonts: int, suspicious_fonts: int) -> dict:
    characters = len("".join(text.split()))
    replacement = text.count("\ufffd")
    if replacement or suspicious_fonts:
        route = "encoding_risk_requires_inspection"
    elif images and characters < 20:
        route = "likely_scanned_requires_render_inspection"
    elif images:
        route = "mixed_resources_requires_region_inspection"
    elif characters >= 20:
        route = "native_text_present"
    else:
        route = "low_text_unknown"
    return {
        "native_nonspace_characters": characters,
        "replacement_characters": replacement,
        "image_resources": images,
        "font_resources": fonts,
        "custom_fonts_without_tounicode": suspicious_fonts,
        "route": route,
        "classification_verified": False,
        "ocr_selected": False,
    }


def diagnose(path: Path) -> list[dict]:
    reader = PdfReader(path)
    if reader.is_encrypted or not 0 < len(reader.pages) <= 2000:
        raise ValueError("PDF inventory rejected")
    rows = []
    for number, page in enumerate(reader.pages, 1):
        resources = page.get("/Resources", {})
        resources = resources.get_object() if hasattr(resources, "get_object") else resources
        fonts = resources.get("/Font", {})
        fonts = fonts.get_object() if hasattr(fonts, "get_object") else fonts
        objects = resources.get("/XObject", {})
        objects = objects.get_object() if hasattr(objects, "get_object") else objects
        if len(fonts) + len(objects) > 10_000:
            raise ValueError("resource inventory limit")
        suspicious = sum(
            font.get_object().get("/Subtype") == "/Type0" and "/ToUnicode" not in font.get_object()
            for font in fonts.values()
        )
        images = sum(obj.get_object().get("/Subtype") == "/Image" for obj in objects.values())
        text = page.extract_text() or ""
        if len(text) > 5_000_000:
            raise ValueError("page text limit")
        rows.append(
            {
                "page": number,
                **signals(text, images=images, fonts=len(fonts), suspicious_fonts=suspicious),
                "unsupported": ["nested_form_images", "visible_ink", "CMap_correctness"],
            }
        )
    return rows


def edit_distance(left, right) -> int:
    if len(left) * len(right) > 25_000_000 or max(len(left), len(right)) > 100_000:
        raise ValueError("edit-distance budget")
    if len(left) < len(right):
        left, right = right, left
    previous = list(range(len(right) + 1))
    for i, a in enumerate(left, 1):
        current = [i]
        for j, b in enumerate(right, 1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (a != b)))
        previous = current
    return previous[-1]


def score(
    reference: str,
    observed: str,
    *,
    language: str,
    evidence_class: str,
    anchors: tuple[str, ...] = (),
) -> dict:
    if language not in {"ru", "kk", "en"} or evidence_class not in {
        "independent_human",
        "publisher_reference",
        "synthetic",
        "legacy_attestation",
    }:
        raise ValueError("explicit language and reference provenance required")
    char_errors = edit_distance(reference, observed)
    words = reference.split()
    word_errors = edit_distance(words, observed.split())
    expected_numbers, actual_numbers = (
        Counter(NUMBERS.findall(reference)),
        Counter(NUMBERS.findall(observed)),
    )
    from tools.extraction_quality.extraction_v2 import exact_positions

    return {
        "language": language,
        "evidence_class": evidence_class,
        "character_errors": char_errors,
        "reference_characters": len(reference),
        "cer": char_errors / len(reference) if reference else None,
        "word_errors": word_errors,
        "reference_words": len(words),
        "wer": word_errors / len(words) if words else None,
        "required_anchors": len(anchors),
        "anchors_recovered": sum(bool(exact_positions(observed, a)) for a in anchors),
        "numeric_reference_occurrences": sum(expected_numbers.values()),
        "numeric_missing_or_changed": sum((expected_numbers - actual_numbers).values()),
        "numeric_added_or_duplicated": sum((actual_numbers - expected_numbers).values()),
        "kazakh_reference_character_counts": {c: reference.count(c) for c in KAZAKH},
        "source_alignment": "NOT_EVALUATED",
        "quality": "NOT_EVALUATED",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        private_destination(args.output)
        value = load(args.manifest)
        admission = {r["sample_id"]: r for r in audit(value, args.root)["rows"]}
        rows = []
        for sample in value.samples:
            if sample.original and sample.original.format == "pdf":
                if not admission[sample.sample_id]["native_eligible"]:
                    rows.append(
                        {
                            "sample_id": sample.sample_id,
                            "pages": None,
                            "failure": "source_ineligible",
                        }
                    )
                    continue
                try:
                    path = asset_path(args.root, sample.original)
                    pages = diagnose(path)
                    asset_path(args.root, sample.original)
                    rows.append({"sample_id": sample.sample_id, "pages": pages, "failure": None})
                except Exception:  # noqa: BLE001 - retain failed documents without exception text
                    rows.append(
                        {
                            "sample_id": sample.sample_id,
                            "pages": None,
                            "failure": "diagnostic_unavailable",
                        }
                    )
        result = {
            "execution": "PASS" if rows and all(r["failure"] is None for r in rows) else "BLOCKED",
            "attempted_documents": len(rows),
            "rows": rows,
            "routes": dict(Counter(p["route"] for r in rows for p in r["pages"] or [])),
            "quality": "NOT_EVALUATED",
            "ocr_executed": False,
        }
        args.output.mkdir(parents=True)
        write(args.output / "diagnostics.json", result)
        print(json.dumps({k: v for k, v in result.items() if k != "rows"}, sort_keys=True))
        return 0 if result["execution"] == "PASS" else 2
    except Exception:  # noqa: BLE001 - private source errors are never printed
        print("BLOCKED: source, manifest or fresh private output rejected")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
