"""Post-freeze review against public synthetic evidence; never real human review."""

from __future__ import annotations

import copy
import json
import os
import subprocess
import threading
from pathlib import Path

import pytest

from tests.unit.test_pdf_review_workbench import fixture, frozen_hashes, request, seal, update
from tools.extraction_quality import pdf_review_validation as validation
from tools.extraction_quality import pdf_review_workbench as tool
from tools.extraction_quality.pdf_table_review_packet import PacketError


def ready(tmp_path, *, repeated_table=False):
    app, parts = fixture(tmp_path)
    if repeated_table:
        draft = copy.deepcopy(parts[1])
        duplicate = copy.deepcopy(draft["tables"][0])
        duplicate["review_table_id"] = "later-repeat"
        duplicate["bbox_pdf_user_space_points"] = [120.0, 0.0, 220.0, 100.0]
        for cell in duplicate["cells"]:
            cell["bbox_pdf_user_space_points"][0] += 120
            cell["bbox_pdf_user_space_points"][2] += 120
        draft["tables"].append(duplicate)
        parts = (parts[0], draft, *parts[2:])
    key = seal(app, parts)
    update(app, "reveal", confirm_reveal=True)
    adjudication = copy.deepcopy(parts[2])
    adjudication["independent_draft_fingerprint_before_legacy_comparison"] = app.state["documents"][
        key
    ]["seal"]
    update(app, "adjudication", document_id=key, adjudication=adjudication)
    return app, key


def proposed(app, key):
    draft = app.state["documents"][key]["draft"]
    table, cell = draft["tables"][0], draft["tables"][0]["cells"][0]
    cells = [
        {
            k: copy.deepcopy(cell[k])
            for k in (
                "row",
                "column",
                "row_span",
                "column_span",
                "literal_text",
                "bbox_pdf_user_space_points",
            )
        }
    ]
    context = {
        "binding": app.binding,
        "document_id": key,
        "source_sha256": draft["source"]["sha256"],
        "page_identity": app.pages[key][0],
        "table_index": 0,
        "review_table_id": table["review_table_id"],
        "bbox": table["bbox_pdf_user_space_points"],
        "rows": table["row_count"],
        "columns": table["column_count"],
    }
    candidate = {
        "method": "public-synthetic-proposal",
        "status": "PROPOSED",
        "cells": copy.deepcopy(cells),
    }
    return {
        "context": context,
        "candidate": candidate,
        "proposal_id": validation.fingerprint({"context": context, "candidate": candidate}),
        "cells": cells,
    }


def import_proposal(app, key, proposal):
    return update(
        app,
        "proposal-import",
        document_id=key,
        proposal_json=json.dumps(proposal),
        confirm_import=True,
    )


def decide(app, key, action="confirm"):
    adjudication = copy.deepcopy(app.state["documents"][key]["adjudication"])
    draft = app.state["documents"][key]["draft"]
    table, cell = draft["tables"][0], draft["tables"][0]["cells"][0]
    decision = adjudication["proposal_reviews"][0]["decisions"][0]
    decision.update(
        decision=action,
        independent_cell_ref=None
        if action == "reject"
        else {"table_id": table["review_table_id"], "cell_id": cell["review_cell_id"]},
        reviewer_id=draft["reviewer"]["id"],
        reviewed_on="2026-01-02",
        rationale="Public synthetic oracle; real decisions must be supplied by a human",
        original_page_evidence=[{"page_number": 1, "bbox": cell["bbox_pdf_user_space_points"]}],
        ambiguity=False,
    )
    update(app, "adjudication", document_id=key, adjudication=adjudication)
    return copy.deepcopy(adjudication)


@pytest.mark.parametrize("action", ["confirm", "revise", "reject"])
def test_accepted_corrected_rejected_export_only_frozen_independent_cells(tmp_path, action):
    app, key = ready(tmp_path)
    frozen = frozen_hashes(app)
    snapshot = copy.deepcopy(app.state["documents"][key]["draft"])
    proposal = proposed(app, key)
    if action != "confirm":
        proposal["cells"][0]["literal_text"] = "Rejected or corrected synthetic candidate"
    import_proposal(app, key, proposal)
    decide(app, key, action)
    result = app.validate(
        app.view()["revision"], export=True, export_revision="public-synthetic-proposal-review-v1"
    )
    assert result["summary"]["export_ready"] and result["exported"]
    directory = app.output / "checks" / result["check_id"]
    gold = json.loads((directory / "reviewed-gold-v2.json").read_text(encoding="utf-8"))
    exported = gold["documents"][0]
    assert exported["review"]["kind"] == "synthetic_fixture"
    assert exported["revision"] == "public-synthetic-proposal-review-v1"
    assert (
        exported["tables"][0]["cells"][0]["literal"]
        == snapshot["tables"][0]["cells"][0]["literal_text"]
    )
    assert "Rejected or corrected synthetic candidate" not in json.dumps(gold)
    audit = json.loads((directory / "review" / key / "adjudication.json").read_text())
    assert audit["proposal_reviews"][0]["proposal"] == proposal
    assert audit["proposal_reviews"][0]["decisions"][0]["decision"] == action
    assert exported["decisions_sha256"] == validation.fingerprint(audit)
    assert app.state["documents"][key]["draft"] == snapshot
    assert frozen == frozen_hashes(app)


def test_c1_0040_table_row_column_mismatch_requires_explicit_source_correction(tmp_path):
    app, key = ready(tmp_path)
    proposal = proposed(app, key)
    proposal["context"]["review_table_id"] = "separate-box-counted-as-first-table"
    proposal["cells"][0].update(row=2, column=1)
    proposal["proposal_id"] = validation.fingerprint(
        {k: proposal[k] for k in ("context", "candidate")}
    )
    import_proposal(app, key, proposal)
    decide(app, key, "confirm")
    assert not app.validate(app.view()["revision"])["summary"]["export_ready"]
    decide(app, key, "revise")
    result = app.validate(
        app.view()["revision"], export=True, export_revision="public-synthetic-proposal-review-v1"
    )
    assert result["summary"]["export_ready"]
    assert app.state["documents"][key]["draft"]["tables"][0]["cells"][0]["row"] == 0


def test_repeated_literal_in_later_table_cannot_confirm_first_source_occurrence(tmp_path):
    app, key = ready(tmp_path, repeated_table=True)
    proposal = proposed(app, key)
    import_proposal(app, key, proposal)
    adjudication = decide(app, key)
    decision = adjudication["proposal_reviews"][0]["decisions"][0]
    later = app.state["documents"][key]["draft"]["tables"][1]["cells"][0]
    assert later["literal_text"] == proposal["cells"][0]["literal_text"]
    decision["independent_cell_ref"]["table_id"] = "later-repeat"
    decision["original_page_evidence"] = [
        {"page_number": 1, "bbox": later["bbox_pdf_user_space_points"]}
    ]
    update(app, "adjudication", document_id=key, adjudication=adjudication)
    assert not app.validate(app.view()["revision"])["summary"]["export_ready"]


@pytest.mark.parametrize(
    "case",
    [
        "missing",
        "ambiguous",
        "reviewer",
        "evidence",
        "date",
        "mapping",
        "duplicate",
        "rejected_mapping",
    ],
)
def test_incomplete_ambiguous_or_invalid_review_cannot_export(tmp_path, case):
    app, key = ready(tmp_path)
    import_proposal(app, key, proposed(app, key))
    adjudication = decide(app, key)
    decision = adjudication["proposal_reviews"][0]["decisions"][0]
    if case == "missing":
        adjudication["proposal_reviews"][0]["decisions"] = []
    elif case == "ambiguous":
        decision["ambiguity"] = True
    elif case == "reviewer":
        decision["reviewer_id"] = "other"
    elif case == "evidence":
        decision["original_page_evidence"] = []
    elif case == "date":
        decision["reviewed_on"] = "2999-01-01"
    elif case == "mapping":
        decision["independent_cell_ref"] = {"table_id": "later-repeat", "cell_id": "same-text"}
    elif case == "duplicate":
        adjudication["proposal_reviews"][0]["decisions"].append(copy.deepcopy(decision))
    else:
        decision["decision"] = "reject"
    update(app, "adjudication", document_id=key, adjudication=adjudication)
    assert not app.validate(app.view()["revision"])["summary"]["export_ready"]
    with pytest.raises(ValueError, match="no Gold exported"):
        app.validate(
            app.view()["revision"],
            export=True,
            export_revision="public-synthetic-proposal-review-v1",
        )
    assert not list(app.output.rglob("reviewed-gold-v2.json"))


def test_unreviewed_import_is_pending_and_cannot_be_dropped_or_relabelled(tmp_path):
    app, key = ready(tmp_path)
    import_proposal(app, key, proposed(app, key))
    before = app.view()
    assert not app.validate(before["revision"])["summary"]["export_ready"]
    for change in ("drop", "relabel"):
        adjudication = copy.deepcopy(app.state["documents"][key]["adjudication"])
        if change == "drop":
            adjudication.pop("proposal_reviews")
        else:
            adjudication["proposal_reviews"][0]["proposal"]["cells"][0]["row"] = 9
        with pytest.raises(ValueError):
            update(app, "adjudication", document_id=key, adjudication=adjudication)
        assert app.view() == before
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
    assert resumed.view() == before
    assert not resumed.validate(before["revision"])["summary"]["export_ready"]


@pytest.mark.parametrize("case", ["source", "page", "cell_page", "candidate", "binding"])
def test_import_rejects_wrong_source_page_or_forged_identity(tmp_path, case):
    app, key = ready(tmp_path)
    proposal = proposed(app, key)
    if case == "source":
        proposal["context"]["source_sha256"] = "0" * 64
    elif case == "page":
        proposal["context"]["page_identity"] = {"page_number": 2}
    elif case == "candidate":
        proposal["candidate"]["cells"][0]["literal_text"] = "forged"
    elif case == "cell_page":
        proposal["cells"][0]["page_number"] = 2
    else:
        proposal["context"]["binding"] = "0" * 64
    if case != "candidate":
        proposal["proposal_id"] = validation.fingerprint(
            {k: proposal[k] for k in ("context", "candidate")}
        )
    before = app.view()
    with pytest.raises((ValueError, KeyError)):
        import_proposal(app, key, proposal)
    assert before == app.view()


def test_predictions_cannot_be_seen_before_blind_freeze(tmp_path):
    app, parts = fixture(tmp_path)
    with pytest.raises(ValueError, match="Freeze blind review"):
        import_proposal(app, parts[3].document_id, {})


@pytest.mark.parametrize("revision", [None, "", "ml29-review-v1"])
def test_export_requires_a_new_explicit_revision(tmp_path, revision):
    app, _ = ready(tmp_path)
    with pytest.raises(ValueError, match="new independent Gold revision"):
        app.validate(app.view()["revision"], export=True, export_revision=revision)
    assert not list(app.output.rglob("reviewed-gold-v2.json"))


def test_standalone_validator_also_blocks_unreviewed_proposal(tmp_path):
    app, key = ready(tmp_path)
    import_proposal(app, key, proposed(app, key))
    item = app.state["documents"][key]
    with pytest.raises((PacketError, TypeError)):
        validation.validate_document(
            item["draft"],
            item["adjudication"],
            app.records[key],
            app.pages[key],
            app.scopes[key],
            "fixture",
            allow_synthetic=True,
        )


def test_existing_grid_sidecar_without_table_id_keeps_its_identity(tmp_path):
    from tests.unit.test_pdf_grid_proposals import grid_fixture, supplied

    app, _, _ = grid_fixture(tmp_path)
    app.grid_proposal("grid-propose", supplied(app))
    path = next((app.output / "grid-proposals").glob("*.json"))
    old = json.loads(path.read_text(encoding="utf-8"))
    old["context"].pop("review_table_id")
    old["proposal_id"] = validation.fingerprint({k: old[k] for k in ("context", "candidate")})
    path.write_text(json.dumps(old), encoding="utf-8")
    before = path.read_bytes()
    loaded = app.grid_proposal("grid-load", supplied(app))
    assert app.grid_proposal("grid-propose", supplied(app)) == loaded
    assert loaded["proposal_id"] == old["proposal_id"] and before == path.read_bytes()


def test_local_http_proposal_review_and_export_boundaries(tmp_path):
    app, key = ready(tmp_path)
    with tool.ReviewServer(app) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            assert request(server, "proposal-review.js")[0] == 200
            for route in ("proposal-import", "export"):
                for headers in (
                    {"X-Review-Token": "wrong"},
                    {"Origin": "https://attacker.invalid"},
                ):
                    assert (
                        request(server, route, method="POST", payload={}, headers=headers)[0] == 409
                    )
            assert (
                request(
                    server, "export", method="POST", payload={"revision": app.view()["revision"]}
                )[0]
                == 409
            )
            payload = {
                "revision": app.view()["revision"],
                "document_id": key,
                "proposal_json": json.dumps(proposed(app, key)),
                "confirm_import": True,
            }
            assert request(server, "proposal-import", method="POST", payload=payload)[0] == 200
            payload["revision"] = app.view()["revision"]
            assert request(server, "proposal-import", method="POST", payload=payload)[0] == 409
        finally:
            server.shutdown()
            thread.join(timeout=5)


def test_browser_confirm_correct_reject_and_export(tmp_path):
    node = os.environ.get("ML30_NODE")
    if not node or not os.environ.get("ML30_NODE_MODULES"):
        pytest.skip("Set ML30_NODE and ML30_NODE_MODULES for actual independent-review UI")
    app, key = ready(tmp_path)
    frozen = frozen_hashes(app)
    proposals = [proposed(app, key) for _ in range(3)]
    for i, proposal in enumerate(proposals):
        proposal["candidate"]["method"] += f"-{i}"
        proposal["proposal_id"] = validation.fingerprint(
            {k: proposal[k] for k in ("context", "candidate")}
        )
    proposals[1]["cells"][0]["literal_text"] = "Incorrect synthetic prediction"
    proposals[2]["cells"][0]["literal_text"] = "Rejected synthetic prediction"
    table = app.state["documents"][key]["draft"]["tables"][0]
    cell = table["cells"][0]
    cases = tmp_path / "browser-cases.json"
    cases.write_text(
        json.dumps(
            {
                "proposals": [json.dumps(p) for p in proposals],
                "target": {"table_id": table["review_table_id"], "cell_id": cell["review_cell_id"]},
                "evidence": [{"page_number": 1, "bbox": cell["bbox_pdf_user_space_points"]}],
            }
        ),
        encoding="utf-8",
    )
    with tool.ReviewServer(app) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            subprocess.run(
                [
                    node,
                    str(Path(__file__).with_name("pdf_proposal_review.browser.cjs")),
                    f"http://127.0.0.1:{server.server_port}/{server.token}/",
                    str(cases),
                ],
                timeout=120,
                check=True,
            )
        finally:
            server.shutdown()
            thread.join(timeout=5)
    exports = list(app.output.rglob("reviewed-gold-v2.json"))
    assert len(exports) == 1
    content = exports[0].read_text(encoding="utf-8")
    assert (
        "Incorrect synthetic prediction" not in content
        and "Rejected synthetic prediction" not in content
    )
    assert frozen == frozen_hashes(app)
