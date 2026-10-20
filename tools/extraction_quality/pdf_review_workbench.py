"""Local human worksheet workbench. No extraction, predictions, or automatic decisions."""

from __future__ import annotations

import argparse
import copy
import hmac
import json
import os
import secrets
import subprocess
import tempfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from doclens_ai.extraction.evidence_v2 import Scope, valid_bbox
from doclens_ai.extraction.fidelity_gold import fingerprint
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
    ):
        for path in (bundle, output, root):
            packet.no_links(path)
        self.manifest, self.corpus, self.gold = manifest, corpus, gold
        self.bundle, self.output, self.root = bundle.resolve(), output.resolve(), root.resolve()
        self.expected, self.allow_synthetic = expected or packet.Expected(), allow_synthetic
        self.identity, self.paths, records, _ = packet.preflight(
            manifest, corpus, gold, self.expected, allow_synthetic=allow_synthetic
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
                item["adjudication"] = payload["adjudication"]
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

    def validate(self, revision: str) -> dict:
        self._current(revision)
        if not self.state["exposed"]:
            raise WorkbenchError("Complete independent review before adjudication")
        checks = self.output / "checks"
        packet.no_links(checks)
        checks.mkdir(exist_ok=True)
        destination = Path(tempfile.mkdtemp(prefix="check-", dir=checks))
        for key, item in self.state["documents"].items():
            folder = destination / "review" / key
            folder.mkdir(parents=True)
            packet.write_json(folder / "independent.json", item["draft"])
            packet.write_json(folder / "adjudication.json", item["adjudication"])
        summary, _ = validation.validate_workflow(
            self.manifest,
            self.corpus,
            self.gold,
            destination / "review",
            self.scopes,
            "ml29-review-v1",
            expected=self.expected,
            allow_synthetic=self.allow_synthetic,
        )
        packet.write_json(destination / "validation.json", summary)
        return {"check_id": destination.name, "summary": summary}


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
            "style-src 'self'; frame-src 'self'; connect-src 'self'; "
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
            if route in {"", "workbench.js", "workbench.css"}:
                name, mime = {
                    "": ("index.html", "text/html; charset=utf-8"),
                    "workbench.js": ("workbench.js", "text/javascript; charset=utf-8"),
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
            if route == "validate":
                value = self.server.workbench.validate(payload["revision"])
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
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    try:
        workbench = Workbench(
            args.manifest, args.corpus, args.gold, args.packet, args.output, resume=args.resume
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
