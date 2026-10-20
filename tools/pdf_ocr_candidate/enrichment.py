"""Page/region selective OCR observations, isolated from native canonical content."""

from __future__ import annotations

import math
import re
import tempfile
import time
from dataclasses import asdict, replace
from pathlib import Path
from typing import Literal

from pydantic import Field
from pypdf import PdfReader

from doclens_ai.extraction.evidence_v2 import Contract, Digest, Locator, Name, Scope, valid_bbox
from doclens_ai.extraction.fidelity_gold import fingerprint
from doclens_ai.extraction.models import ExtractionResult
from tools.pdf_ocr_candidate import benchmark as existing


class Request(Contract):
    scope: Scope
    locator: Locator
    reason: Literal["missing_text_layer", "unreadable_region", "native_text_loss"]
    observation_reference: Name
    languages: tuple[Literal["ru", "kk", "en"], ...] = Field(min_length=1, max_length=3)


class OCRObservation(Contract):
    scope: Scope
    locator: Locator
    request_sha256: Digest
    engine_revision: Name
    config_sha256: Digest
    literal: str
    state: Literal["needs_review", "duplicate", "failed", "unknown", "not_selected"]
    warnings: tuple[Name, ...]
    numeric_disagreement: bool | None
    # Confidence is diagnostic only; this interface deliberately has no accepted state.
    confidence: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)


def merge_observation(
    request: Request,
    native: ExtractionResult,
    *,
    text: str,
    returned_scope: Scope,
    returned_page: int,
    engine_revision: str,
    config_sha256: str,
    max_characters: int = 100_000,
) -> OCRObservation:
    request = Request.model_validate(request)
    state, warnings, numeric = "needs_review", [], None
    original = next(
        (b.text for b in native.blocks if b.source.page_number == request.locator.page), None
    )
    if (
        request.scope != returned_scope
        or returned_page != request.locator.page
        or native.source_sha256 != request.scope.raw_sha256
        or original is None
    ):
        text, state, warnings = "", "failed", ["source_mismatch"]
    elif len(text) > max_characters:
        text, state, warnings = "", "failed", ["output_limit"]
    else:
        normalized = " ".join(text.split())
        source = " ".join(original.split())
        # A substring inside a signed number is not duplicate evidence: OCR
        # "001.25" must never be deduplicated against native "-001.25".
        exact_overlap = normalized and re.search(
            r"(?<![\w+−.,/:\-])" + re.escape(normalized) + r"(?![\w.,/:\-])", source
        )
        if normalized and (normalized == source or exact_overlap):
            state = "duplicate"
        elif not normalized:
            state, warnings = "unknown", ["empty_ocr"]
        else:
            # Keep signs, decimal separators, periods and date separators literal.
            pattern = r"[-+−]?\d+(?:[.,/:-]\d+)*"
            left, right = re.findall(pattern, original), re.findall(pattern, text)
            numeric = bool(left and right and left != right)
            warnings = ["numeric_disagreement"] if numeric else []
            if original.strip():
                warnings.append("native_ocr_overlap_requires_review")
    return OCRObservation(
        scope=request.scope,
        locator=request.locator,
        request_sha256=fingerprint(request.model_dump(mode="json")),
        engine_revision=engine_revision,
        config_sha256=config_sha256,
        literal=text,
        state=state,
        warnings=tuple(warnings),
        numeric_disagreement=numeric,
    )


def selective_page(
    path: Path,
    native: ExtractionResult,
    request: Request,
    *,
    runtime: existing.Runtime,
    limits: existing.Limits,
    work: Path,
) -> OCRObservation:
    """Bridge existing resource guards; full-page EN reuses the frozen candidate.

    RU/KK/mixed require pre-existing local traineddata. Region rendering supports
    unrotated pages with identical MediaBox/CropBox only; no guessed transforms.
    Every observation remains unverified regardless of OCR confidence.
    """
    request = Request.model_validate(request)
    config = fingerprint(
        {
            "runtime": "ml28-selective-ocr-v1",
            "languages": request.languages,
            "limits": asdict(limits),
            "psm": 3,
            "oem": 1,
        }
    )

    def failure(code, state="failed"):
        return OCRObservation(
            scope=request.scope,
            locator=request.locator,
            request_sha256=fingerprint(request.model_dump(mode="json")),
            engine_revision="tesseract-local-unverified",
            config_sha256=config,
            literal="",
            state=state,
            warnings=(code,),
            numeric_disagreement=None,
        )

    if len(set(request.languages)) != len(request.languages):
        return failure("unsupported_language", "unknown")
    if path.stat().st_size > limits.max_file_bytes:
        return failure("file_limit")
    if (
        native.source_sha256 != request.scope.raw_sha256
        or existing.digest(path) != native.source_sha256
    ):
        return failure("source_mismatch")
    original = next(
        (b.text for b in native.blocks if b.source.page_number == request.locator.page), None
    )
    if original is None:
        return failure("source_page_mismatch")
    if request.reason == "missing_text_layer" and original.strip():
        return failure("native_text_layer_present", "not_selected")
    languages = tuple({"ru": "rus", "kk": "kaz", "en": "eng"}[x] for x in request.languages)
    if not all(Path(p).is_file() for p in (runtime.tesseract, runtime.renderer)):
        return failure("missing_models_or_runtime", "unknown")
    if not all((Path(runtime.tessdata) / (lang + ".traineddata")).is_file() for lang in languages):
        return failure("unsupported_language_data", "unknown")
    try:
        import psutil  # noqa: F401 - command monitor requires this before launching
    except ImportError:
        return failure("missing_resource_monitor", "unknown")
    reader = PdfReader(path)
    if len(reader.pages) > limits.max_pages or request.locator.page > len(reader.pages):
        return failure("page_limit")
    page = reader.pages[request.locator.page - 1]
    if not valid_bbox(tuple(map(float, page.mediabox))):
        return failure("invalid_page")
    pixels = math.ceil(float(page.mediabox.width) * limits.dpi / 72) * math.ceil(
        float(page.mediabox.height) * limits.dpi / 72
    )
    if pixels > limits.max_pixels and request.locator.bbox is None:
        return failure("pixel_limit")
    if request.locator.bbox is not None and (
        page.rotation != 0
        or tuple(page.mediabox) != tuple(page.cropbox)
        or not valid_bbox(request.locator.bbox, tuple(map(float, page.mediabox)))
    ):
        return failure("region_transform_unqualified", "unknown")
    try:
        if request.languages == ("en",) and request.locator.bbox is None:
            text, metadata = existing.ocr_page(path, request.locator.page, runtime, limits, work)
        else:
            text, metadata = _region_or_multilingual(
                path, page, request, languages, runtime, limits, work
            )
    except existing.BoundedFailure as exc:
        return failure(exc.category)
    if existing.digest(path) != request.scope.raw_sha256:
        return failure("source_mismatch")
    config = fingerprint(
        {
            "settings": config,
            "tesseract": existing.digest(Path(runtime.tesseract)),
            "renderer": existing.digest(Path(runtime.renderer)),
            "models": {
                lang: existing.digest(Path(runtime.tessdata) / (lang + ".traineddata"))
                for lang in languages
            },
        }
    )
    return merge_observation(
        request,
        native,
        text=text,
        returned_scope=request.scope,
        returned_page=metadata["page"],
        engine_revision="tesseract-local",
        config_sha256=config,
        max_characters=limits.max_characters,
    )


def _region_or_multilingual(path, page, request, languages, runtime, limits, work):
    started = time.monotonic()
    crop = []
    if request.locator.bbox is not None:
        left, bottom, right, top = request.locator.bbox
        scale = limits.dpi / 72
        x = math.floor((left - float(page.mediabox.left)) * scale)
        y = math.floor((float(page.mediabox.top) - top) * scale)
        width = math.ceil((right - float(page.mediabox.left)) * scale) - x
        height = math.ceil((float(page.mediabox.top) - bottom) * scale) - y
        if min(width, height) <= 0 or width * height > limits.max_pixels:
            raise existing.BoundedFailure("pixel_limit")
        crop = ["-x", str(x), "-y", str(y), "-W", str(width), "-H", str(height)]
    with tempfile.TemporaryDirectory(dir=work, prefix="region-") as directory:
        rendered = Path(directory) / "page"
        output = Path(directory) / "ocr"
        number = str(request.locator.page)
        existing.command(
            [
                runtime.renderer,
                "-f",
                number,
                "-l",
                number,
                "-singlefile",
                "-r",
                str(limits.dpi),
                "-gray",
                *crop,
                str(path),
                str(rendered),
            ],
            work,
            limits,
        )
        ink = existing.pgm_ink(rendered.with_suffix(".pgm"), limits)
        if ink < limits.min_ink_fraction:
            return "", {"page": request.locator.page, "state": "blank_render"}
        remaining = min(
            limits.tool_timeout_seconds, limits.timeout_seconds - (time.monotonic() - started)
        )
        if remaining <= 0:
            raise existing.BoundedFailure("timeout")
        existing.command(
            [
                runtime.tesseract,
                str(rendered.with_suffix(".pgm")),
                str(output),
                "--tessdata-dir",
                runtime.tessdata,
                "-l",
                "+".join(languages),
                "--oem",
                "1",
                "--psm",
                "3",
                "--dpi",
                str(limits.dpi),
            ],
            work,
            replace(limits, tool_timeout_seconds=remaining),
        )
        target = output.with_suffix(".txt")
        if not target.is_file() or target.stat().st_size > limits.max_characters * 4:
            raise existing.BoundedFailure("output_limit")
        try:
            text = target.read_text(encoding="utf-8")
        except UnicodeError:
            raise existing.BoundedFailure("invalid_ocr") from None
        return text, {"page": request.locator.page, "state": "ocr"}
