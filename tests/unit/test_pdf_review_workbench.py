"""Synthetic local review only; no human labels or private source text in fixtures."""

from __future__ import annotations

import copy
import csv
import hashlib
import http.client
import json
import threading
from dataclasses import replace

import pytest

from tests.unit.test_ml28_review import completed
from tools.extraction_quality import pdf_review_validation as validation
from tools.extraction_quality import pdf_review_workbench as tool
from tools.extraction_quality import pdf_table_review_packet as packet


def fixture(tmp_path, *, cohort=False):
    parts = completed(tmp_path)
    data = parts[0]
    if cohort:
        from pypdf import PdfWriter

        source = data[2] / "SECOND_SYNTHETIC.pdf"
        writer = PdfWriter()
        writer.add_blank_page(300, 400)
        writer.add_blank_page(300, 400)
        writer.write(source)
        with data[1].open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            fields, rows = reader.fieldnames, list(reader)
        row = dict(
            rows[0],
            document_id="c1-0002",
            sha256=packet.sha(source),
            size_bytes=str(source.stat().st_size),
        )
        with data[1].open("w", encoding="utf-8", newline="") as stream:
            output = csv.DictWriter(stream, fieldnames=fields)
            output.writeheader()
            output.writerows([*rows, row])
        record = json.loads(data[3].read_text(encoding="utf-8"))
        second = dict(
            record,
            document_id=row["document_id"],
            source_sha256=row["sha256"],
            source_size_bytes=source.stat().st_size,
        )
        data[3].write_text(json.dumps(record) + "\n" + json.dumps(second) + "\n", encoding="utf-8")
        data = (
            *data[:4],
            replace(
                data[4],
                manifest_sha256=packet.sha(data[1]),
                gold_sha256=packet.sha(data[3]),
                documents=2,
                reviewed_records=2,
                table_documents=2,
            ),
            data[5],
        )
    bundle = data[0] / "evaluation-output/bundle"
    packet.generate(*data[1:4], bundle, expected=data[4], allow_synthetic=True, root=data[0])
    app = tool.Workbench(
        *data[1:4],
        bundle,
        data[0] / "evaluation-output/workbench",
        root=data[0],
        expected=data[4],
        allow_synthetic=True,
    )
    return app, parts


def update(app, action, **payload):
    return app.update(action, {"revision": app.view()["revision"], **payload})


def fill(app, parts):
    draft = copy.deepcopy(parts[1])
    draft["state"] = "DRAFT_NOT_REVIEWED"
    draft["completion"]["signed_review_fingerprint"] = None
    key = parts[3].document_id
    update(app, "draft", document_id=key, draft=draft)
    for page in app.pages[key]:
        update(app, "inspect", document_id=key, page=page["page_number"], inspected=True)
    return key


def seal(app, parts):
    key = fill(app, parts)
    update(app, "freeze", document_id=key, confirm_freeze=True)
    return key


def frozen_hashes(app):
    files = [
        app.manifest,
        app.gold,
        *app.paths.values(),
        *(p for p in app.bundle.rglob("*") if p.is_file()),
    ]
    return {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


def test_complete_synthetic_review_uses_existing_full_validator(tmp_path, monkeypatch):
    app, parts = fixture(tmp_path)
    before = frozen_hashes(app)
    key = seal(app, parts)
    snapshot = app.state["documents"][key]["draft"]
    assert snapshot["completion"]["signed_review_fingerprint"] == validation.draft_fingerprint(
        snapshot
    )
    update(app, "reveal", confirm_reveal=True)
    blank = app.view()["documents"][key]["adjudication"]
    assert all(
        d["state"] == "UNRESOLVED" and d["decision"] is None for d in blank["assertion_decisions"]
    )
    assert app.validate(app.view()["revision"])["summary"]["execution"] == "BLOCKED"
    entered = copy.deepcopy(parts[2])
    entered["independent_draft_fingerprint_before_legacy_comparison"] = app.state["documents"][key][
        "seal"
    ]
    update(app, "adjudication", document_id=key, adjudication=entered)
    called = []
    original = validation.validate_workflow

    def validate(*args, **kwargs):
        called.append(True)
        return original(*args, **kwargs)

    monkeypatch.setattr(validation, "validate_workflow", validate)
    result = app.validate(app.view()["revision"])
    assert called and result["summary"]["export_ready"]
    assert result["summary"]["qg_00"] == "NOT_EVALUATED"
    assert before == frozen_hashes(app)
    assert not list(app.output.rglob("*gold*.json"))


def test_independent_mode_never_returns_gold_and_default_still_requires_adjudication(tmp_path):
    _, draft, _, record, pages, scope = completed(tmp_path)
    undecided = packet.worksheets(record, pages)[2]
    assert (
        validation.validate_document(
            draft,
            undecided,
            record,
            pages,
            scope,
            "fixture",
            allow_synthetic=True,
            independent_only=True,
        )
        is None
    )
    with pytest.raises(ValueError):
        validation.validate_document(
            draft, undecided, record, pages, scope, "fixture", allow_synthetic=True
        )


@pytest.mark.parametrize("action", ["legacy", "reveal", "validate", "adjudication"])
def test_server_blinding_cannot_be_bypassed_by_client_state(tmp_path, action):
    app, parts = fixture(tmp_path)
    key = parts[3].document_id
    before = app.view()
    assert "adjudication" not in before["documents"][key]
    assert "frozen_record" not in json.dumps(before) and "assertion_decisions" not in json.dumps(
        before
    )
    with pytest.raises(ValueError):
        if action == "legacy":
            app.legacy(key)
        elif action == "validate":
            app.validate(before["revision"])
        else:
            update(
                app,
                action,
                document_id=key,
                confirm_reveal=True,
                exposed=True,
                adjudication=parts[2],
            )
    assert before == app.view()


@pytest.mark.parametrize(
    "case",
    [
        "partial",
        "machine",
        "exposed",
        "future",
        "uncertain",
        "permission",
        "not_inspected",
        "fake_seal",
        "unit_conflict",
    ],
)
def test_partial_conflicting_or_forged_independent_review_cannot_freeze(tmp_path, case):
    app, parts = fixture(tmp_path)
    key = fill(app, parts)
    draft = copy.deepcopy(app.view()["documents"][key]["draft"])
    if case == "partial":
        draft["completion"]["all_tables_inventoried"] = None
    elif case == "machine":
        draft["reviewer"]["id"] = "Codex"
    elif case == "exposed":
        draft["reviewer"]["parser_outputs_seen"] = True
    elif case == "future":
        draft["reviewer"]["reviewed_on"] = "2999-01-01"
    elif case == "uncertain":
        draft["tables"][0]["cells"][0]["uncertain"] = True
    elif case == "permission":
        draft["reviewer"]["annotation_authorized"] = False
    elif case == "unit_conflict":
        draft["tables"][0]["cells"][2]["value_unit_period_links"] = []
    elif case == "not_inspected":
        update(app, "inspect", document_id=key, page=1, inspected=False)
    else:
        draft["state"] = "REVIEWED"
        draft["completion"]["signed_review_fingerprint"] = validation.draft_fingerprint(draft)
        with pytest.raises(ValueError):
            update(app, "draft", document_id=key, draft=draft)
        return
    update(app, "draft", document_id=key, draft=draft)
    before = app.view()
    with pytest.raises((ValueError, TypeError)):
        update(app, "freeze", document_id=key, confirm_freeze=True)
    assert app.view() == before and app.state["documents"][key]["seal"] is None


@pytest.mark.parametrize("case", ["page", "rotation", "bbox", "nan", "wrong_sha"])
def test_original_identity_and_coordinates_checked_on_save(tmp_path, case):
    app, parts = fixture(tmp_path)
    key = fill(app, parts)
    draft = copy.deepcopy(app.view()["documents"][key]["draft"])
    if case == "page":
        draft["tables"][0]["cells"][0]["page_number"] = 2
    elif case == "rotation":
        draft["pages"][0]["rotation"] = 90
    elif case == "bbox":
        draft["tables"][0]["cells"][0]["bbox_pdf_user_space_points"] = [0.0, 0.0, 9999.0, 9999.0]
    elif case == "nan":
        draft["tables"][0]["cells"][0]["bbox_pdf_user_space_points"] = [0.0, 0.0, float("nan"), 1.0]
    else:
        draft["source"]["sha256"] = "0" * 64
    with pytest.raises(ValueError):
        update(app, "draft", document_id=key, draft=draft)


def test_resumable_drafts_seals_and_stale_tabs(tmp_path):
    app, parts = fixture(tmp_path)
    revision = app.view()["revision"]
    key = fill(app, parts)
    with pytest.raises(ValueError, match="Stale"):
        app.update(
            "inspect", {"revision": revision, "document_id": key, "page": 1, "inspected": True}
        )
    update(app, "freeze", document_id=key, confirm_freeze=True)
    update(app, "reveal", confirm_reveal=True)
    resumed = tool.Workbench(
        app.manifest,
        app.corpus,
        app.gold,
        app.bundle,
        app.output,
        resume=True,
        root=app.root,
        expected=app.expected,
        allow_synthetic=True,
    )
    assert resumed.view() == app.view()
    with pytest.raises(ValueError, match="frozen"):
        update(resumed, "draft", document_id=key, draft=parts[1])


def test_frozen_snapshot_tampering_blocks_resume(tmp_path):
    app, parts = fixture(tmp_path)
    key = seal(app, parts)
    snapshot = app.output / "snapshots" / f"{key}.json"
    value = validation.read_json(snapshot)
    value["tables"][0]["cells"][0]["literal_text"] = "tampered fixture"
    snapshot.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="changed"):
        tool.Workbench(
            app.manifest,
            app.corpus,
            app.gold,
            app.bundle,
            app.output,
            resume=True,
            root=app.root,
            expected=app.expected,
            allow_synthetic=True,
        )


@pytest.mark.parametrize("location", ["tracked", "raw", "bundle"])
def test_private_output_must_be_ignored_and_outside_frozen_inputs(tmp_path, location):
    app, _ = fixture(tmp_path)
    target = {
        "tracked": app.root / "public-review",
        "raw": app.corpus / "review",
        "bundle": app.bundle / "review-session",
    }[location]
    with pytest.raises(ValueError):
        tool.Workbench(
            app.manifest,
            app.corpus,
            app.gold,
            app.bundle,
            target,
            root=app.root,
            expected=app.expected,
            allow_synthetic=True,
        )
    assert not target.exists()


def test_original_pdf_changed_or_path_traversal_not_served(tmp_path):
    app, parts = fixture(tmp_path)
    key = parts[3].document_id
    with pytest.raises(ValueError):
        app.pdf("../../legacy-assertions")
    source = app.bundle / "sources" / f"{key}.pdf"
    source.write_bytes(b"changed synthetic source")
    with pytest.raises(ValueError, match="bytes"):
        app.pdf(key)


@pytest.fixture
def listener(tmp_path):
    app, parts = fixture(tmp_path)
    server = tool.ReviewServer(app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, app, parts
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def request(server, route="state", *, method="GET", payload=None, headers=None):
    connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
    try:
        defaults = {
            "Origin": f"http://127.0.0.1:{server.server_port}",
            "X-Review-Token": server.token,
            "Content-Type": "application/json",
        }
        defaults.update(headers or {})
        connection.request(
            method,
            f"/{server.token}/{route}",
            body=json.dumps(payload) if payload is not None else None,
            headers=defaults,
        )
        response = connection.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        connection.close()


def test_local_http_ui_pdf_and_no_external_assets(listener, capsys):
    server, app, parts = listener
    assert server.server_address[0] == "127.0.0.1"
    status, headers, body = request(server, "")
    assert status == 200 and b"Local PDF review" in body
    assert (
        headers["Cache-Control"] == "no-store"
        and "default-src 'none'" in headers["Content-Security-Policy"]
    )
    key = parts[3].document_id
    status, _, body = request(server, f"original.pdf?document_id={key}")
    assert status == 200 and body == app.pdf(key).read_bytes()
    for name in ("index.html", "workbench.js", "workbench.css"):
        content = (tool.ASSETS / name).read_text(encoding="utf-8")
        assert "https://" not in content and "http://" not in content
    assert request(server, "predictions")[0] == 403
    assert request(server, f"legacy?document_id={key}")[0] == 403
    assert request(server, f"original.pdf?document_id={key}", method="HEAD")[2] == b""
    captured = capsys.readouterr()
    assert not captured.out and not captured.err


@pytest.mark.parametrize(
    "headers",
    [
        {"Host": "attacker.invalid"},
        {"Origin": "https://attacker.invalid"},
        {"Sec-Fetch-Site": "cross-site"},
    ],
)
def test_cross_origin_requests_blocked(listener, headers):
    server, _, _ = listener
    assert request(server, headers=headers)[0] == 403


def test_csrf_wrong_token_invalid_payload_and_legacy_unlock_blocked(listener):
    server, app, _ = listener
    revision = app.view()["revision"]
    assert (
        request(
            server,
            "reveal",
            method="POST",
            payload={"revision": revision, "confirm_reveal": True},
            headers={"X-Review-Token": "forged"},
        )[0]
        == 409
    )
    assert (
        request(
            server, "reveal", method="POST", payload={"revision": revision, "confirm_reveal": True}
        )[0]
        == 409
    )
    assert (
        request(server, "draft", method="POST", payload={"private": "must never echo"})[2].find(
            b"must never echo"
        )
        == -1
    )
    connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
    connection.request("GET", "/wrong-token/state")
    assert connection.getresponse().status == 403
    connection.close()


def test_atomic_write_failure_keeps_resumable_state(tmp_path, monkeypatch):
    app, parts = fixture(tmp_path)
    before = app.state_path.read_bytes()
    monkeypatch.setattr(tool.os, "replace", lambda *a: (_ for _ in ()).throw(OSError("private")))
    with pytest.raises(OSError):
        update(app, "inspect", document_id=parts[3].document_id, page=1, inspected=True)
    assert app.state_path.read_bytes() == before
    assert not list(app.output.glob("*.partial"))


def test_all_documents_and_pages_must_be_frozen_before_any_legacy_is_served(tmp_path):
    app, parts = fixture(tmp_path, cohort=True)
    first = seal(app, parts)
    assert len(app.view()["documents"]) == 2
    with pytest.raises(ValueError):
        update(app, "reveal", confirm_reveal=True)
    with pytest.raises(ValueError):
        app.legacy(first)
    key = "c1-0002"
    second_parts = list(parts)
    second_parts[3] = app.records[key]
    second_parts[1] = copy.deepcopy(parts[1])
    draft, _, _ = packet.worksheets(app.records[key], app.pages[key])
    second_parts[1]["source"] = draft["source"]
    second_parts[1]["pages"] = draft["pages"]
    second_parts[1]["pages"][0].update(copy.deepcopy(parts[1]["pages"][0]))
    second_parts[1]["pages"][1]["table_presence"] = False
    fill(app, second_parts)
    update(app, "inspect", document_id=key, page=2, inspected=False)
    with pytest.raises(ValueError):
        update(app, "freeze", document_id=key, confirm_freeze=True)
    update(app, "inspect", document_id=key, page=2, inspected=True)
    update(app, "freeze", document_id=key, confirm_freeze=True)
    update(app, "reveal", confirm_reveal=True)
    assert app.legacy(first)["source"]["document_id"] == first
    assert app.legacy(key)["source"]["document_id"] == key


def test_http_save_and_resume_state_does_not_promote_review(listener):
    server, app, parts = listener
    state = json.loads(request(server)[2])
    key = parts[3].document_id
    state["documents"][key]["draft"]["pages"][0]["notes"] = "Public synthetic manual note"
    status, _, body = request(
        server,
        "draft",
        method="POST",
        payload={
            "revision": state["revision"],
            "document_id": key,
            "draft": state["documents"][key]["draft"],
            "exposed": True,
            "seal": "forged",
        },
    )
    assert status == 200
    saved = json.loads(body)
    assert not saved["exposed"] and saved["documents"][key]["seal"] is None
    assert (
        app.view()["documents"][key]["draft"]["pages"][0]["notes"] == "Public synthetic manual note"
    )
    assert (
        request(
            server,
            "freeze",
            method="POST",
            payload={"revision": saved["revision"], "document_id": key, "confirm_freeze": True},
        )[0]
        == 409
    )
