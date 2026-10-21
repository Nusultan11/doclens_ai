"""Local PDF worksheets and explicitly requested proposals; never automatic review."""

from __future__ import annotations

import argparse
import base64
import copy
import hmac
import json
import math
import os
import secrets
import struct
import subprocess
import tempfile
import zlib
from contextlib import closing
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from doclens_ai.extraction.evidence_v2 import Scope, valid_bbox
from doclens_ai.extraction.fidelity_gold import fingerprint
from tools.extraction_quality import pdf_grid_proposals as grids
from tools.extraction_quality import pdf_review_validation as validation
from tools.extraction_quality import pdf_table_review_packet as packet

VERSION = "ml29-pdf-review-workbench-v1"
MAX_JSON = 20 * 1024**2
ASSETS = Path(__file__).with_name("pdf_review_ui")


class WorkbenchError(ValueError):
    """Fixed public diagnostics only; never expose supplied content or paths."""


def atomic_json(path: Path, value: dict) -> None:
    packet.no_links(path)
    content = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    if len(content) > MAX_JSON:
        raise WorkbenchError("Worksheet size limit")
    descriptor, temporary = tempfile.mkstemp(prefix=".review-", suffix=".partial", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def rgb_png(bitmap) -> bytes:
    """Encode the renderer's packed RGB rows using stdlib only (no image dependency)."""

    def chunk(kind, data):
        return (
            struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
        )

    raw = bytes(bitmap.buffer)
    rows = b"".join(
        b"\x00" + raw[y * bitmap.stride : y * bitmap.stride + bitmap.width * 3]
        for y in range(bitmap.height)
    )
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", bitmap.width, bitmap.height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(rows))
        + chunk(b"IEND", b"")
    )


class Workbench:
    """Single-writer state with immutable independent snapshots and tab revisions."""

    def __init__(
        self,
        manifest: Path,
        corpus: Path,
        gold: Path,
        bundle: Path,
        output: Path,
        *,
        resume: bool = False,
        root: Path = packet.ROOT,
        expected: packet.Expected | None = None,
        allow_synthetic: bool = False,
        eligibility: Path | None = None,
    ):
        for path in (bundle, output, root):
            packet.no_links(path)
        self.manifest, self.corpus, self.gold = manifest, corpus, gold
        self.bundle, self.output, self.root = bundle.resolve(), output.resolve(), root.resolve()
        self.expected, self.allow_synthetic = expected or packet.Expected(), allow_synthetic
        self.eligibility = eligibility
        self.identity, self.paths, records, _ = packet.preflight(
            manifest,
            corpus,
            gold,
            self.expected,
            allow_synthetic=allow_synthetic,
            eligibility=eligibility,
        )
        self.records = {r.document_id: r for r in records}
        self.pages = {
            k: validation.original_pages(p) for k, p in self.paths.items() if k in self.records
        }
        self._verify_bundle()
        self.scopes = {
            k: Scope(
                workspace_id="offline-corpus-v1",
                document_id=k,
                version_id=r.source_sha256,
                raw_sha256=r.source_sha256,
            )
            for k, r in self.records.items()
        }
        self.binding = fingerprint(
            {"inputs": self.identity, "packet": packet.sha(self.bundle / "artifact-manifest.json")}
        )
        self._private_output()
        self.state_path = self.output / "workbench.json"
        self.renders: dict[tuple[str, int], dict] = {}  # Session memory only; never persisted.
        if resume:
            self.state = validation.read_json(self.state_path)
            self._check_state()
        else:
            packet.fresh_output(self.output, corpus, root=self.root)
            self.output.mkdir(parents=True)
            documents = {}
            for key, record in self.records.items():
                draft, _, _ = packet.worksheets(record, self.pages[key])
                draft["reviewer"].update(
                    kind=None, annotation_authorized=None, annotation_permission_reference=None
                )
                draft.update(text_anchors=[], order_pairs=[])
                documents[key] = {
                    "draft": draft,
                    "inspected_pages": [],
                    "seal": None,
                    "adjudication": None,
                }
            self.state = {
                "version": VERSION,
                "binding": self.binding,
                "exposed": False,
                "documents": documents,
            }
            atomic_json(self.state_path, self.state)

    def _private_output(self) -> None:
        packet.no_links(self.output)
        if (
            not any(
                self.output.is_relative_to(self.root / name) and self.output != self.root / name
                for name in ("evaluation-output", "local-evaluation")
            )
            or self.output.is_relative_to(self.corpus.resolve())
            or self.output.is_relative_to(self.bundle)
            or self.bundle.is_relative_to(self.output)
            or subprocess.run(
                ["git", "check-ignore", "-q", str(self.output)],
                cwd=self.root,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            ).returncode
        ):
            raise WorkbenchError("Ignored private output outside frozen inputs required")

    def _verify_bundle(self) -> None:
        packet.no_links(self.bundle)
        manifest = validation.read_json(self.bundle / "artifact-manifest.json")
        marker = validation.read_json(self.bundle / "COMPLETE.json")
        expected = {"inputs.json", "summary.json", "REVIEW.md"}
        for key in self.records:
            expected.add(f"sources/{key}.pdf")
            expected.update(
                f"review/{key}/{name}.json"
                for name in ("independent", "legacy-assertions", "adjudication")
            )
        if (
            set(manifest) != expected
            or marker.get("packet_fingerprint") != fingerprint(manifest)
            or marker.get("artifact_manifest_sha256")
            != packet.sha(self.bundle / "artifact-manifest.json")
        ):
            raise WorkbenchError("Frozen packet identity mismatch")
        for name, digest in manifest.items():
            path = self.bundle / name
            packet.no_links(path)
            if packet.sha(path) != digest:
                raise WorkbenchError("Frozen packet artifact mismatch")
        if validation.read_json(self.bundle / "inputs.json")["inputs"] != self.identity:
            raise WorkbenchError("Frozen packet source mismatch")

    def _check_draft(self, key: str, draft: dict) -> None:
        template, _, _ = packet.worksheets(self.records[key], self.pages[key])
        if (
            draft["source"] != template["source"]
            or draft["version"] != template["version"]
            or [{k: p[k] for k in self.pages[key][0]} for p in draft["pages"]] != self.pages[key]
        ):
            raise WorkbenchError("Original page identity mismatch")
        # Reject supplied coordinates outside observed pages, even on partial saves.
        crops = {p["page_number"]: tuple(p["crop_box_pdf_user_space"]) for p in self.pages[key]}

        def box(page, bbox):
            if page not in crops or (
                bbox is not None
                and (
                    not isinstance(bbox, list)
                    or len(bbox) != 4
                    or not valid_bbox(tuple(bbox), crops[page])
                )
            ):
                raise WorkbenchError("Original page or coordinates rejected")

        for page in draft["pages"]:
            for region in page["regions"]:
                box(page["page_number"], region["bbox_pdf_user_space_points"])
        for table in draft["tables"]:
            box(table["page_number"], table["bbox_pdf_user_space_points"])
            for cell in table["cells"]:
                box(
                    cell.get("page_number", table["page_number"]),
                    cell["bbox_pdf_user_space_points"],
                )
            for region in table.get("source_regions", []):
                box(region["page_number"], region["bbox_pdf_user_space_points"])
        for anchor in draft.get("text_anchors", []):
            box(anchor["locator"]["page"], anchor["locator"]["bbox"])

    def _validate_independent(self, key: str, draft: dict) -> None:
        if self.eligibility is not None:
            identity = packet.preflight(
                self.manifest,
                self.corpus,
                self.gold,
                self.expected,
                allow_synthetic=self.allow_synthetic,
                eligibility=self.eligibility,
            )[0]
            if identity != self.identity:
                raise WorkbenchError("Annotation eligibility changed; rebuild handoff")
            if draft["family_language"]["split"] != "dev":
                raise WorkbenchError("Exposed control requires dev split")
        proposals = self.output / "grid-proposals"
        packet.no_links(proposals)
        if any(proposals.glob(f"{key}-*.json")) or any(
            t.get("assisted_grid_proposals") for t in draft["tables"]
        ):
            raise WorkbenchError(
                "Assisted draft requires separate independent review before Gold freeze"
            )
        _, _, undecided = packet.worksheets(self.records[key], self.pages[key])
        validation.validate_document(
            draft,
            undecided,
            self.records[key],
            self.pages[key],
            self.scopes[key],
            "ml29-review-v1",
            allow_synthetic=self.allow_synthetic,
            independent_only=True,
        )

    def _check_state(self) -> None:
        if (
            self.state.get("version") != VERSION
            or self.state.get("binding") != self.binding
            or set(self.state["documents"]) != set(self.records)
            or type(self.state.get("exposed")) is not bool
        ):
            raise WorkbenchError("Resumable state mismatch")
        for key, item in self.state["documents"].items():
            self._check_draft(key, item["draft"])
            if self._proposal_bindings(key, item["adjudication"]) != item.get(
                "proposal_review_bindings", []
            ):
                raise WorkbenchError("Imported proposal population changed")
            if item["seal"] is not None:
                snapshot = validation.read_json(self.output / "snapshots" / f"{key}.json")
                if (
                    snapshot != item["draft"]
                    or validation.draft_fingerprint(snapshot) != item["seal"]
                ):
                    raise WorkbenchError("Frozen independent draft changed")
                self._validate_independent(key, snapshot)
            elif item["adjudication"] is not None or self.state["exposed"]:
                raise WorkbenchError("Premature legacy exposure")

    def _proposal_bindings(self, key: str, adjudication: dict | None) -> list[str]:
        entries = (adjudication or {}).get("proposal_reviews", [])
        if not isinstance(entries, list):
            raise WorkbenchError("Imported proposal population changed")
        bindings = []
        for entry in entries:
            bound = validation.proposal_review(
                entry["proposal"], self.state["documents"][key]["draft"]["source"], self.pages[key]
            )
            if entry["proposal_sha256"] != bound["proposal_sha256"]:
                raise WorkbenchError("Imported proposal changed")
            bindings.append(bound["proposal_sha256"])
        if len(set(bindings)) != len(bindings):
            raise WorkbenchError("Duplicate imported proposal")
        return bindings

    def _current(self, expected: str | None = None) -> str:
        self._private_output()
        if validation.read_json(self.state_path) != self.state:
            raise WorkbenchError("Local state changed; restart to resume")
        revision = fingerprint(self.state)
        if expected is not None and not hmac.compare_digest(revision, expected):
            raise WorkbenchError("Stale tab; reload saved state")
        self._check_state()
        return revision

    def _commit(self, state: dict) -> None:
        self._private_output()
        atomic_json(self.state_path, state)
        self.state = state

    def view(self) -> dict:
        revision = self._current()
        return {
            "revision": revision,
            "exposed": self.state["exposed"],
            "documents": {
                k: {
                    n: copy.deepcopy(v[n])
                    for n in ("draft", "seal", "inspected_pages", "adjudication")
                    if n != "adjudication" or self.state["exposed"]
                }
                for k, v in self.state["documents"].items()
            },
        }

    def update(self, action: str, payload: dict) -> dict:
        self._current(payload["revision"])
        state = copy.deepcopy(self.state)
        if action in {"draft", "inspect", "freeze", "adjudication"}:
            key = payload["document_id"]
            item = state["documents"][key]
            if action in {"draft", "inspect", "freeze"} and item["seal"] is not None:
                raise WorkbenchError("Independent draft is frozen")
            if action == "draft":
                draft = payload["draft"]
                self._check_draft(key, draft)
                if (
                    draft["state"] != "DRAFT_NOT_REVIEWED"
                    or draft["completion"]["signed_review_fingerprint"] is not None
                ):
                    raise WorkbenchError("Only the explicit freeze action seals a draft")
                item["draft"] = draft
            elif action == "inspect":
                page = payload["page"]
                if type(page) is not int or not 1 <= page <= len(self.pages[key]):
                    raise WorkbenchError("Original page rejected")
                if type(payload["inspected"]) is not bool:
                    raise WorkbenchError("Human inspection choice required")
                inspected = set(item["inspected_pages"])
                inspected.add(page) if payload["inspected"] else inspected.discard(page)
                item["inspected_pages"] = sorted(inspected)
            elif action == "freeze":
                if payload.get("confirm_freeze") is not True or item["inspected_pages"] != list(
                    range(1, len(self.pages[key]) + 1)
                ):
                    raise WorkbenchError("Every original page needs human inspection")
                draft = item["draft"]
                draft["state"] = "REVIEWED"
                draft["completion"]["signed_review_fingerprint"] = validation.draft_fingerprint(
                    draft
                )
                self._validate_independent(key, draft)
                item["seal"] = draft["completion"]["signed_review_fingerprint"]
                directory = self.output / "snapshots"
                packet.no_links(directory)
                directory.mkdir(exist_ok=True)
                snapshot = directory / f"{key}.json"
                if snapshot.exists():
                    # Recovery after a write failure is permitted only for identical content.
                    if validation.read_json(snapshot) != draft:
                        raise WorkbenchError("Existing frozen snapshot differs")
                else:
                    packet.write_json(snapshot, draft)
            else:
                if not state["exposed"]:
                    raise WorkbenchError("Legacy comparison is still locked")
                adjudication = copy.deepcopy(payload["adjudication"])
                for old, supplied in zip(
                    item["adjudication"].get("proposal_reviews", []),
                    adjudication.get("proposal_reviews", []),
                    strict=False,
                ):
                    # JSON in browsers changes 0.0 to 0. Retain the original hash-bound
                    # representation only when every supplied immutable value agrees.
                    if (
                        old["proposal_sha256"] == supplied["proposal_sha256"]
                        and old["proposal"] == supplied["proposal"]
                    ):
                        supplied["proposal"] = copy.deepcopy(old["proposal"])
                if self._proposal_bindings(key, adjudication) != item.get(
                    "proposal_review_bindings", []
                ):
                    raise WorkbenchError("Imported proposal population changed")
                item["adjudication"] = adjudication
        elif action == "proposal-import":
            key = payload["document_id"]
            item = state["documents"][key]
            if (
                not state["exposed"]
                or not item["seal"]
                or payload.get("confirm_import") is not True
            ):
                raise WorkbenchError("Freeze blind review before importing proposed cells")
            entry = validation.proposal_review(
                json.loads(payload["proposal_json"]), item["draft"]["source"], self.pages[key]
            )
            if entry["proposal"]["context"]["binding"] != self.binding:
                raise WorkbenchError("Proposal packet binding mismatch")
            entries = item["adjudication"].setdefault("proposal_reviews", [])
            if any(
                e["proposal"]["proposal_id"] == entry["proposal"]["proposal_id"] for e in entries
            ):
                raise WorkbenchError("Proposal already imported; resume its saved decisions")
            entries.append(entry)
            item.setdefault("proposal_review_bindings", []).append(entry["proposal_sha256"])
        elif action == "reveal":
            if payload.get("confirm_reveal") is not True or not all(
                v["seal"] for v in state["documents"].values()
            ):
                raise WorkbenchError("Freeze every independent draft before legacy comparison")
            if not state["exposed"]:
                for key, item in state["documents"].items():
                    _, _, adjudication = packet.worksheets(self.records[key], self.pages[key])
                    adjudication["independent_draft_fingerprint_before_legacy_comparison"] = item[
                        "seal"
                    ]
                    item["adjudication"] = adjudication
                state["exposed"] = True
        else:
            raise WorkbenchError("Unknown worksheet action")
        self._commit(state)
        return self.view()

    def legacy(self, key: str) -> dict:
        self._current()
        if not self.state["exposed"] or key not in self.records:
            raise WorkbenchError("Legacy comparison is still locked")
        return validation.read_json(self.bundle / "review" / key / "legacy-assertions.json")

    def pdf(self, key: str) -> Path:
        if key not in self.records:
            raise WorkbenchError("Unknown source")
        path = self.bundle / "sources" / f"{key}.pdf"
        packet.no_links(path)
        if packet.sha(path) != self.records[key].source_sha256:
            raise WorkbenchError("Original bytes changed")
        return path

    def _page(self, payload: dict) -> tuple[str, int, Path, dict]:
        key, number = payload["document_id"], payload["page"]
        path = self.pdf(key)
        if type(number) is not int or not 1 <= number <= len(self.pages[key]):
            raise WorkbenchError("Original page rejected")
        identity = self.pages[key][number - 1]
        if (
            payload["page_identity"] != identity
            or validation.original_pages(path) != self.pages[key]
        ):
            raise WorkbenchError("Original page identity mismatch")
        return key, number, path, identity

    def render_page(self, payload: dict) -> dict:
        """Render authorized bytes to memory. Only a verified unrotated mapping is exposed."""
        self._current(payload["revision"])
        key, number, path, identity = self._page(payload)
        try:
            import pypdfium2 as pdfium
        except ImportError as exc:
            raise WorkbenchError(
                "Visual capture needs optional local pypdfium2 (tested 5.14.0)"
            ) from exc
        from pypdf import PdfReader

        crop = identity["crop_box_pdf_user_space"]
        media = identity["media_box_pdf_user_space"]
        if (
            identity["rotation"] != 0
            or PdfReader(path).pages[number - 1].get("/UserUnit", 1) != 1
            or not valid_bbox(tuple(crop), tuple(media))
        ):
            raise WorkbenchError(
                "Capture disabled: requires rotation 0, UserUnit 1 and contained CropBox"
            )
        width, height = crop[2] - crop[0], crop[3] - crop[1]
        scale = min(2.0, 3000 / width, 3000 / height)
        with (
            pdfium.PdfDocument(path.read_bytes()) as document,
            closing(document[number - 1]) as page,
        ):
            if (
                page.get_rotation() != 0
                or any(abs(a - b) > 0.001 for a, b in zip(page.get_bbox(), crop, strict=True))
                or any(
                    abs(a - b) > 0.001
                    for a, b in zip(page.get_size(), (width, height), strict=True)
                )
            ):
                raise WorkbenchError("Capture disabled: renderer/page geometry mismatch")
            with closing(
                page.render(
                    scale=scale,
                    rotation=0,
                    may_draw_forms=False,
                    force_bitmap_format=pdfium.raw.FPDFBitmap_BGR,
                    rev_byteorder=True,
                )
            ) as bitmap:
                if bitmap.width * bitmap.height > 9_000_000 or bitmap.mode != "RGB":
                    raise WorkbenchError("Capture disabled: renderer bitmap rejected")
                converter = bitmap.get_posconv(page)
                for pixel, expected in (
                    ((0, 0), (crop[0], crop[3])),
                    ((bitmap.width, bitmap.height), (crop[2], crop[1])),
                ):
                    if any(
                        abs(a - b) > 0.001
                        for a, b in zip(converter.to_page(*pixel), expected, strict=True)
                    ):
                        raise WorkbenchError("Capture disabled: renderer transform mismatch")
                metadata = {
                    "document_id": key,
                    "page": number,
                    "page_identity": identity,
                    "source_sha256": self.records[key].source_sha256,
                    "width": bitmap.width,
                    "height": bitmap.height,
                    "scale": scale,
                    "renderer": str(pdfium.PYPDFIUM_INFO.version),
                }
                png = rgb_png(bitmap)
        metadata["render_id"] = fingerprint(metadata)
        self.renders[key, number] = metadata
        return {**metadata, "png_base64": base64.b64encode(png).decode("ascii")}

    def annotate(self, payload: dict) -> dict:
        """Explicitly assign only geometry; all semantic fields remain human supplied."""
        self._current(payload["revision"])
        key, number, _, _ = self._page(payload)
        if self.state["documents"][key]["seal"] is not None:
            raise WorkbenchError("Independent draft is frozen")
        rendered = self.renders.get((key, number))
        if rendered is None or payload["render_id"] != rendered["render_id"]:
            raise WorkbenchError("Render this original page before assigning geometry")
        draft = copy.deepcopy(payload["draft"])
        self._check_draft(key, draft)
        bbox = payload["bbox"]
        crop = self.pages[key][number - 1]["crop_box_pdf_user_space"]
        if (
            not isinstance(bbox, list)
            or len(bbox) != 4
            or any(type(v) not in (int, float) or not math.isfinite(v) for v in bbox)
            or not valid_bbox(tuple(bbox), tuple(crop))
        ):
            raise WorkbenchError("Original rectangle rejected")
        target = payload["target"]

        def index(items, name):
            value = target[name]
            if type(value) is not int or not 0 <= value < len(items):
                raise WorkbenchError("Select an existing worksheet target")
            return items[value]

        if target["kind"] == "region":
            destination = index(draft["pages"][number - 1]["regions"], "region")
        elif target["kind"] in {"table", "cell"}:
            table = index(draft["tables"], "table")
            if table["page_number"] != number:
                raise WorkbenchError("Rectangle target is on a different page")
            destination = table if target["kind"] == "table" else index(table["cells"], "cell")
            if destination.get("page_number", number) != number:
                raise WorkbenchError("Rectangle target is on a different page")
            if target["kind"] == "table":
                destination["coordinate_basis"] = "pdf_user_space_unrotated"
        else:
            raise WorkbenchError("Select a region, table or cell")
        destination["bbox_pdf_user_space_points"] = bbox
        return self.update("draft", {**payload, "draft": draft})

    def _grid_target(self, payload: dict):
        self._current(payload["revision"])
        key, number, path, identity = self._page(payload)
        item = self.state["documents"][key]
        if item["seal"] is not None:
            raise WorkbenchError("Independent draft is frozen")
        index = payload["table_index"]
        if type(index) is not int or not 0 <= index < len(item["draft"]["tables"]):
            raise WorkbenchError("Select a saved table for proposals")
        table = item["draft"]["tables"][index]
        if table["page_number"] != number:
            raise WorkbenchError("Proposal table is on a different page")
        if any(c.get("page_number", number) != number for c in table["cells"]) or any(
            region["page_number"] != number for region in table.get("source_regions", [])
        ):
            raise WorkbenchError("Assisted grid requires a single original page")
        directory = self.output / "grid-proposals"
        packet.no_links(directory)
        return (
            key,
            number,
            path,
            identity,
            table,
            directory / f"{key}-{index}-{fingerprint(table)}.json",
        )

    def grid_proposal(self, action: str, payload: dict) -> dict:
        """Sidecar proposals never mutate the worksheet; only explicit acceptance appends."""
        key, number, path, identity, table, destination = self._grid_target(payload)
        if action == "grid-propose":
            rendered = self.render_page(payload)
            candidate = grids.detect(
                rendered,
                table["bbox_pdf_user_space_points"],
                table["row_count"],
                table["column_count"],
            )
            grids.add_text(path, number, candidate)
            context = {
                "binding": self.binding,
                "source_sha256": self.records[key].source_sha256,
                "render_id": rendered["render_id"],
                "renderer": rendered["renderer"],
                "document_id": key,
                "page_identity": identity,
                "table_index": payload["table_index"],
                "table_fingerprint": fingerprint(table),
                "bbox": table["bbox_pdf_user_space_points"],
                "rows": table["row_count"],
                "columns": table["column_count"],
            }
            # Old saved proposals retain their original identity on regeneration.
            if (
                not destination.exists()
                or "review_table_id" in validation.read_json(destination)["context"]
            ):
                context["review_table_id"] = table["review_table_id"]
            original = {"context": context, "candidate": candidate}
            record = {**original, "proposal_id": fingerprint(original), "cells": candidate["cells"]}
            # Regeneration must not discard resumable human corrections silently.
            if destination.exists():
                previous = validation.read_json(destination)
                if previous["proposal_id"] != record["proposal_id"]:
                    raise WorkbenchError(
                        "Saved proposal differs; resume it or select another saved table"
                    )
                record = previous
            else:
                self._private_output()
                destination.parent.mkdir(exist_ok=True)
                atomic_json(destination, record)
        else:
            if not destination.is_file():
                raise WorkbenchError(
                    "No proposal for this saved table; generate or select matching table"
                )
            record = validation.read_json(destination)
        context = record["context"]
        if (
            record["proposal_id"]
            != fingerprint({"context": context, "candidate": record["candidate"]})
            or context["binding"] != self.binding
            or context["document_id"] != key
            or context["source_sha256"] != self.records[key].source_sha256
            or context["page_identity"] != identity
            or context["table_index"] != payload["table_index"]
        ):
            raise WorkbenchError("Saved proposal identity mismatch")
        applicable = context["table_fingerprint"] == fingerprint(table)
        if action in {"grid-correct", "grid-accept"}:
            if (
                not applicable
                or payload["proposal_revision"] != fingerprint(record)
                or record["candidate"]["status"] != "PROPOSED"
            ):
                raise WorkbenchError("Proposal is stale, unresolved or already applied")
            if action == "grid-correct":
                grids.check_cells(
                    payload["cells"], context["bbox"], context["rows"], context["columns"]
                )
                record["cells"] = sorted(
                    copy.deepcopy(payload["cells"]), key=lambda c: (c["row"], c["column"])
                )
                atomic_json(destination, record)
            else:
                if payload.get("confirm_accept") is not True:
                    raise WorkbenchError("Explicit proposal acceptance required")
                grids.check_cells(
                    record["cells"], context["bbox"], context["rows"], context["columns"]
                )
                draft = copy.deepcopy(self.state["documents"][key]["draft"])
                target = draft["tables"][payload["table_index"]]
                occupied = set()
                for cell in target["cells"]:
                    row, column = cell["row"], cell["column"]
                    rs, cs = cell["row_span"], cell["column_span"]
                    if (
                        any(type(v) is not int for v in (row, column, rs, cs))
                        or row < 0
                        or column < 0
                        or rs <= 0
                        or cs <= 0
                        or row + rs > context["rows"]
                        or column + cs > context["columns"]
                    ):
                        raise WorkbenchError(
                            "Existing cells need explicit row/column/span resolution"
                        )
                    slots = {
                        (r, c) for r in range(row, row + rs) for c in range(column, column + cs)
                    }
                    if occupied & slots:
                        raise WorkbenchError("Existing manual cell grid positions conflict")
                    occupied.update(slots)
                added = 0
                for proposed in record["cells"]:
                    if (proposed["row"], proposed["column"]) in occupied:
                        continue  # Existing manually entered cells are preserved exactly.
                    if any(
                        existing.get("bbox_pdf_user_space_points") is not None
                        and grids.intersects(
                            proposed["bbox_pdf_user_space_points"],
                            existing["bbox_pdf_user_space_points"],
                        )
                        for existing in table["cells"]
                    ):
                        raise WorkbenchError("Proposed geometry overlaps an existing manual cell")
                    cell = packet.worksheets(self.records[key], self.pages[key])[0]["cell_template"]
                    cell.update(
                        {
                            k: proposed[k]
                            for k in (
                                "row",
                                "column",
                                "row_span",
                                "column_span",
                                "bbox_pdf_user_space_points",
                                "literal_text",
                            )
                        }
                    )
                    cell["review_cell_id"] = (
                        f"proposal-{record['proposal_id'][:16]}-r{cell['row']}-c{cell['column']}"
                    )
                    cell["proposal_origin"] = {
                        "proposal_id": record["proposal_id"],
                        "method": grids.METHOD,
                    }
                    if any(
                        existing["review_cell_id"] == cell["review_cell_id"]
                        for existing in target["cells"]
                    ):
                        raise WorkbenchError(
                            "Proposed cell identity conflicts with an existing cell"
                        )
                    target["cells"].append(cell)
                    added += 1
                # Durable assistance provenance, with no review/uncertainty/completeness decisions.
                target.setdefault("assisted_grid_proposals", []).append(record["proposal_id"])
                state = self.update(
                    "draft", {"revision": payload["revision"], "document_id": key, "draft": draft}
                )
                return {"state": state, "added": added, "preserved": len(table["cells"])}
        return {**record, "proposal_revision": fingerprint(record), "applicable": applicable}

    def validate(
        self, revision: str, *, export: bool = False, export_revision: str | None = None
    ) -> dict:
        self._current(revision)
        if not self.state["exposed"]:
            raise WorkbenchError("Complete independent review before adjudication")
        if export and (
            not isinstance(export_revision, str)
            or not export_revision.strip()
            or export_revision == "ml29-review-v1"
        ):
            raise WorkbenchError("Provide a new independent Gold revision")
        gold_revision = export_revision if export else "ml29-review-v1"
        checks = self.output / "checks"
        packet.no_links(checks)
        checks.mkdir(exist_ok=True)
        destination = Path(tempfile.mkdtemp(prefix="check-", dir=checks))
        for key, item in self.state["documents"].items():
            folder = destination / "review" / key
            folder.mkdir(parents=True)
            packet.write_json(folder / "independent.json", item["draft"])
            packet.write_json(folder / "adjudication.json", item["adjudication"])
        summary, documents = validation.validate_workflow(
            self.manifest,
            self.corpus,
            self.gold,
            destination / "review",
            self.scopes,
            gold_revision,
            expected=self.expected,
            allow_synthetic=self.allow_synthetic,
            eligibility=self.eligibility,
        )
        packet.write_json(destination / "validation.json", summary)
        if export:
            if not summary["export_ready"]:
                raise WorkbenchError("Independent review incomplete; no Gold exported")
            packet.write_json(
                destination / "reviewed-gold-v2.json",
                {
                    "schema_version": "reviewed-pdf-population-2.0",
                    "revision": gold_revision,
                    "documents": [d.model_dump(mode="json") for d in documents],
                },
            )
        return {"check_id": destination.name, "summary": summary, "exported": export}


class ReviewServer(HTTPServer):
    def __init__(self, workbench: Workbench, port: int = 0):
        self.workbench = workbench
        self.token = secrets.token_urlsafe(32)
        super().__init__(("127.0.0.1", port), ReviewHandler)

    def handle_error(self, _request, _client_address) -> None:
        pass  # Closed clients must not cause access paths or tracebacks in logs.


class ReviewHandler(BaseHTTPRequestHandler):
    server: ReviewServer

    def setup(self) -> None:
        super().setup()
        self.connection.settimeout(5)

    def log_message(self, *_args) -> None:
        pass  # Neither private paths/content nor session tokens enter access logs.

    def _send(self, status: int, body: bytes, content_type="application/json") -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'none'; script-src 'self'; "
            "style-src 'self'; frame-src 'self'; connect-src 'self'; img-src blob:; "
            "object-src 'self'; frame-ancestors 'self'; base-uri 'none'; form-action 'none'",
        )
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _route(self) -> tuple[str, dict]:
        host = f"127.0.0.1:{self.server.server_port}"
        if (
            self.headers.get("Host") != host
            or self.headers.get("Origin", f"http://{host}") != f"http://{host}"
            or self.headers.get("Sec-Fetch-Site", "none") not in {"none", "same-origin"}
        ):
            raise WorkbenchError("Local same-origin access required")
        target = urlsplit(self.path)
        prefix = f"/{self.server.token}/"
        if not target.path.startswith(prefix):
            raise WorkbenchError("Session access rejected")
        return target.path[len(prefix) :], parse_qs(target.query)

    def do_GET(self) -> None:
        try:
            route, query = self._route()
            if route in {
                "",
                "workbench.js",
                "annotation.js",
                "grid.js",
                "proposal-review.js",
                "workbench.css",
            }:
                name, mime = {
                    "": ("index.html", "text/html; charset=utf-8"),
                    "workbench.js": ("workbench.js", "text/javascript; charset=utf-8"),
                    "annotation.js": ("annotation.js", "text/javascript; charset=utf-8"),
                    "grid.js": ("grid.js", "text/javascript; charset=utf-8"),
                    "proposal-review.js": ("proposal-review.js", "text/javascript; charset=utf-8"),
                    "workbench.css": ("workbench.css", "text/css; charset=utf-8"),
                }[route]
                self._send(200, (ASSETS / name).read_bytes(), mime)
                return
            if route == "state":
                value = self.server.workbench.view()
            elif route == "legacy":
                value = self.server.workbench.legacy(query["document_id"][0])
            elif route == "original.pdf":
                path = self.server.workbench.pdf(query["document_id"][0])
                self._send(200, path.read_bytes(), "application/pdf")
                return
            else:
                raise WorkbenchError("Unknown local route")
            self._send(200, json.dumps(value, ensure_ascii=False).encode())
        except Exception:  # noqa: BLE001 - fixed content-free boundary
            self._send(403, b'{"error":"Local request rejected"}')

    def do_POST(self) -> None:
        try:
            route, _ = self._route()
            if (
                self.headers.get("Content-Type") != "application/json"
                or self.headers.get("X-Review-Token") != self.server.token
            ):
                raise WorkbenchError("Explicit local worksheet request required")
            length = int(self.headers["Content-Length"])
            if not 0 < length <= MAX_JSON:
                raise WorkbenchError("Worksheet size limit")
            payload = json.loads(self.rfile.read(length))
            if route in {"grid-propose", "grid-load", "grid-correct", "grid-accept"}:
                value = self.server.workbench.grid_proposal(route, payload)
            elif route == "render":
                value = self.server.workbench.render_page(payload)
            elif route == "annotate":
                value = self.server.workbench.annotate(payload)
            elif route == "validate":
                value = self.server.workbench.validate(payload["revision"])
            elif route == "export":
                if payload.get("confirm_export") is not True:
                    raise WorkbenchError("Explicit independent Gold export required")
                value = self.server.workbench.validate(
                    payload["revision"], export=True, export_revision=payload.get("export_revision")
                )
            else:
                value = self.server.workbench.update(route, payload)
            self._send(200, json.dumps(value, ensure_ascii=False).encode())
        except WorkbenchError as exc:
            # These messages are fixed literals authored here, never supplied input.
            self._send(409, json.dumps({"error": str(exc)}).encode())
        except Exception:  # noqa: BLE001 - never reflect private validation errors
            self._send(
                409, b'{"error":"Save or validation blocked; check fields and reload saved state"}'
            )

    do_HEAD = do_GET


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("manifest", "corpus", "gold", "packet", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--eligibility", type=Path)
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    try:
        workbench = Workbench(
            args.manifest,
            args.corpus,
            args.gold,
            args.packet,
            args.output,
            resume=args.resume,
            eligibility=args.eligibility,
        )
        with ReviewServer(workbench, args.port) as server:
            print(
                f"Local review: http://127.0.0.1:{server.server_port}/{server.token}/", flush=True
            )
            server.serve_forever()
    except KeyboardInterrupt:
        return 0
    except Exception:
        print("BLOCKED: local review inputs, state or listener unavailable")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
