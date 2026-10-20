"""Original-only public synthetic grid proposals; no private document fixtures."""

from __future__ import annotations

import copy
import json
import os
import subprocess
import threading
from pathlib import Path

import pytest

from tests.unit.test_ml28_review import completed
from tests.unit.test_pdf_review_visual import payload, visual_fixture
from tests.unit.test_pdf_review_workbench import fixture, request, seal, update
from tools.extraction_quality import pdf_grid_proposals as grids
from tools.extraction_quality import pdf_review_validation as validation
from tools.extraction_quality import pdf_review_workbench as tool
from tools.extraction_quality import pdf_text_diagnostics as text_diagnostics


@pytest.fixture(autouse=True)
def renderer():
    pytest.importorskip("pypdfium2")


def grid_fixture(
    tmp_path,
    *,
    irregular=False,
    merged=False,
    borderless=False,
    crossed=False,
    label=None,
    split_word=False,
    empty_text=False,
):
    xs = [40, 100 if irregular else 140, 240]
    ys = [340, 290, 200, 100] if irregular else [340, 260, 180, 100]
    if merged:
        ys = [340 - i * 20 for i in range(13)]
    commands = ["0 G 0.7 w"]
    if not borderless:
        for y in ys:
            commands.append(f"{xs[0]} {y} m {xs[-1]} {y} l S")
        for index, x in enumerate(xs):
            top = ys[1] if merged and index == 1 else ys[0]
            commands.append(f"{x} {ys[-1]} m {x} {top} l S")
    for row in range(len(ys) - 1):
        for column in range(2):
            if empty_text:
                continue
            text = label if label is not None and row == column == 0 else f"R{row}C{column}"
            x = xs[column] + 6
            if split_word and row == column == 0:
                y = ys[row + 1] + 10
                commands.append(f"BT /F1 10 Tf {x} {y} Td (A) Tj ET")
                commands.append(f"BT /F1 10 Tf {x + 10.17} {y} Td (B) Tj ET")
                continue
            if crossed and row == column == 0:
                x = xs[1] - 6
            commands.append(f"BT /F1 10 Tf {x} {ys[row + 1] + 10} Td ({text}) Tj ET")
    app = visual_fixture(tmp_path, content_data=("\n".join(commands) + "\n").encode())
    key = next(iter(app.records))
    draft = copy.deepcopy(app.view()["documents"][key]["draft"])
    table = copy.deepcopy(draft["table_template"])
    table.update(
        review_table_id="public-table",
        page_number=1,
        row_count=len(ys) - 1,
        column_count=2,
        bbox_pdf_user_space_points=[xs[0], ys[-1], xs[-1], ys[0]],
        coordinate_basis="pdf_user_space_unrotated",
    )
    draft["tables"] = [table]
    update(app, "draft", document_id=key, draft=draft)
    return app, xs, ys


def supplied(app, record=None, **extra):
    value = {**payload(app), "table_index": 0, **extra}
    if record:
        value["proposal_revision"] = record["proposal_revision"]
    return value


@pytest.mark.parametrize("irregular", [False, True])
def test_regular_and_nonuniform_ruled_grid_order_text_and_determinism(tmp_path, irregular):
    app, xs, ys = grid_fixture(tmp_path, irregular=irregular)
    before = app.state_path.read_bytes()
    proposal = app.grid_proposal("grid-propose", supplied(app))
    assert proposal == app.grid_proposal("grid-propose", supplied(app))
    assert proposal["candidate"]["status"] == "PROPOSED"
    serialized = json.dumps(proposal)
    assert "SYNTHETIC_PRIVATE_LABEL" not in serialized and "frozen_record" not in serialized
    assert [(c["row"], c["column"]) for c in proposal["cells"]] == [
        (r, c) for r in range(3) for c in range(2)
    ]
    for cell in proposal["cells"]:
        r, c = cell["row"], cell["column"]
        assert cell["literal_text"] == f"R{r}C{c}"
        assert cell["bbox_pdf_user_space_points"] == pytest.approx(
            [xs[c], ys[r + 1], xs[c + 1], ys[r]], abs=0.6
        )
    grids.check_cells(proposal["cells"], [xs[0], ys[-1], xs[-1], ys[0]], 3, 2)
    assert before == app.state_path.read_bytes()
    assert app.state["documents"]["c1-0001"]["draft"]["tables"][0]["cells"] == []


@pytest.mark.parametrize("options", [{"merged": True}, {"borderless": True}])
def test_merged_and_unsupported_tables_unresolved_not_uniform_guesses(tmp_path, options):
    app, _, _ = grid_fixture(tmp_path, **options)
    proposal = app.grid_proposal("grid-propose", supplied(app))
    assert proposal["candidate"]["status"] == "UNRESOLVED" and not proposal["cells"]
    assert proposal["candidate"]["issues"]
    with pytest.raises(ValueError):
        app.grid_proposal("grid-accept", supplied(app, proposal, confirm_accept=True))


def test_cross_boundary_text_is_unfilled(tmp_path):
    app, _, _ = grid_fixture(tmp_path, crossed=True)
    proposal = app.grid_proposal("grid-propose", supplied(app))
    assert proposal["cells"][0]["literal_text"] is None
    assert proposal["cells"][1]["literal_text"] is None
    assert proposal["cells"][2]["literal_text"] == "R1C0"


@pytest.mark.parametrize("literal, expected", [("A B", "A B"), ("A  B", None)])
def test_literal_spacing_preserved_or_ambiguous_not_normalized(tmp_path, literal, expected):
    app, _, _ = grid_fixture(tmp_path, label=literal)
    proposal = app.grid_proposal("grid-propose", supplied(app))
    assert proposal["cells"][0]["literal_text"] == expected


def test_solid_fill_is_not_mistaken_for_a_two_by_two_grid(tmp_path):
    app = visual_fixture(tmp_path)
    rendered = app.render_page(payload(app))
    proposal = grids.detect(rendered, [60, 100, 180, 200], 2, 2)
    assert proposal["status"] == "UNRESOLVED" and not proposal["cells"]


def test_manual_overlap_remains_a_conflict(tmp_path):
    app, _, _ = grid_fixture(tmp_path)
    draft = copy.deepcopy(app.view()["documents"]["c1-0001"]["draft"])
    cell = copy.deepcopy(draft["cell_template"])
    cell.update(
        review_cell_id="manual-wide",
        row=0,
        column=0,
        row_span=1,
        column_span=1,
        bbox_pdf_user_space_points=[40, 260, 170, 340],
    )
    draft["tables"][0]["cells"] = [cell]
    update(app, "draft", document_id="c1-0001", draft=draft)
    before = app.state_path.read_bytes()
    proposal = app.grid_proposal("grid-propose", supplied(app))
    with pytest.raises(ValueError, match="overlaps"):
        app.grid_proposal("grid-accept", supplied(app, proposal, confirm_accept=True))
    assert app.state_path.read_bytes() == before


def test_just_viewing_proposals_blocks_blind_independent_freeze(tmp_path):
    app, _, _ = grid_fixture(tmp_path)
    app.grid_proposal("grid-propose", supplied(app))
    draft = app.view()["documents"]["c1-0001"]["draft"]
    assert draft["tables"][0]["cells"] == []
    with pytest.raises(ValueError, match="separate independent review"):
        app._validate_independent("c1-0001", draft)


@pytest.mark.parametrize("independent_only", [False, True])
@pytest.mark.parametrize("marker", ["table", "cell"])
def test_standalone_validator_never_promotes_assisted_worksheets(
    tmp_path, independent_only, marker
):
    _, draft, adjudication, record, pages, scope = completed(tmp_path)
    if marker == "table":
        draft["tables"][0]["assisted_grid_proposals"] = ["synthetic-proposal"]
    else:
        draft["tables"][0]["cells"][0]["proposal_origin"] = {"method": grids.METHOD}
    draft["completion"]["signed_review_fingerprint"] = validation.draft_fingerprint(draft)
    with pytest.raises(ValueError, match="separate independent review"):
        validation.validate_document(
            draft,
            adjudication,
            record,
            pages,
            scope,
            "synthetic-check",
            allow_synthetic=True,
            independent_only=independent_only,
        )


def test_corrections_acceptance_resume_and_preservation(tmp_path):
    app, _, _ = grid_fixture(tmp_path)
    draft = copy.deepcopy(app.view()["documents"]["c1-0001"]["draft"])
    manual = copy.deepcopy(draft["cell_template"])
    manual.update(
        review_cell_id="manual",
        row=0,
        column=0,
        row_span=1,
        column_span=1,
        bbox_pdf_user_space_points=[41, 261, 139, 339],
        literal_text="Manual literal",
        uncertain=False,
        evidence_reference="human note",
        notes="preserve exactly",
    )
    draft["tables"][0]["cells"] = [manual]
    update(app, "draft", document_id="c1-0001", draft=draft)
    proposal = app.grid_proposal("grid-propose", supplied(app))
    with pytest.raises(ValueError, match="Explicit"):
        app.grid_proposal("grid-accept", supplied(app, proposal))
    corrections = copy.deepcopy(proposal["cells"])
    corrections[1]["literal_text"] = "Explicit human correction"
    corrected = app.grid_proposal("grid-correct", supplied(app, proposal, cells=corrections))
    assert corrected["candidate"]["cells"][1]["literal_text"] == "R0C1"
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
    assert resumed.grid_proposal("grid-load", supplied(resumed)) == corrected
    assert resumed.grid_proposal("grid-propose", supplied(resumed)) == corrected
    with pytest.raises(ValueError, match="stale"):
        resumed.grid_proposal("grid-accept", supplied(resumed, proposal, confirm_accept=True))
    result = resumed.grid_proposal("grid-accept", supplied(resumed, corrected, confirm_accept=True))
    assert result["added"] == 5 and result["preserved"] == 1
    saved = result["state"]["documents"]["c1-0001"]["draft"]
    table = saved["tables"][0]
    assert table["cells"][0] == manual
    assert table["cells"][1]["literal_text"] == "Explicit human correction"
    assert saved["reviewer"] == draft["reviewer"] and saved["completion"] == draft["completion"]
    assert table["structure_complete"] is None and table["merged_or_ambiguous"] is None
    for cell in table["cells"][1:]:
        assert (
            cell["uncertain"] is None
            and cell["evidence_reference"] is None
            and cell["header_role"] is None
        )
        assert cell["value_unit_period_links"] == [] and cell["proposal_origin"]
    with pytest.raises(ValueError):
        resumed.grid_proposal("grid-accept", supplied(resumed, corrected, confirm_accept=True))
    with pytest.raises(ValueError, match="separate independent review"):
        resumed._validate_independent("c1-0001", saved)
    again = tool.Workbench(
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
    assert again.view() == result["state"]


@pytest.mark.parametrize("case", ["overlap", "outside", "duplicate", "missing", "nan", "span"])
def test_invalid_corrections_blocked_without_sidecar_mutation(tmp_path, case):
    app, _, _ = grid_fixture(tmp_path)
    proposal = app.grid_proposal("grid-propose", supplied(app))
    cells = copy.deepcopy(proposal["cells"])
    if case == "overlap":
        cells[1]["bbox_pdf_user_space_points"] = cells[0]["bbox_pdf_user_space_points"]
    elif case == "outside":
        cells[0]["bbox_pdf_user_space_points"][0] = -1
    elif case == "duplicate":
        cells[1]["column"] = 0
    elif case == "missing":
        cells.pop()
    elif case == "nan":
        cells[0]["bbox_pdf_user_space_points"][0] = float("nan")
    else:
        cells[0]["row_span"] = 2
    with pytest.raises(ValueError):
        app.grid_proposal("grid-correct", supplied(app, proposal, cells=cells))
    assert app.grid_proposal("grid-load", supplied(app)) == proposal


def test_frozen_generation_and_acceptance_rejected(tmp_path):
    app, parts = fixture(tmp_path)
    seal(app, parts)
    for action in ("grid-propose", "grid-load", "grid-correct", "grid-accept"):
        with pytest.raises(ValueError, match="frozen"):
            app.grid_proposal(action, supplied(app))


def test_multipage_manual_table_is_not_assigned_a_single_page_grid(tmp_path):
    app, _ = fixture(tmp_path, cohort=True)
    key = "c1-0002"
    draft = copy.deepcopy(app.view()["documents"][key]["draft"])
    table = copy.deepcopy(draft["table_template"])
    cell = copy.deepcopy(draft["cell_template"])
    cell.update(
        page_number=2,
        row=0,
        column=0,
        row_span=1,
        column_span=1,
        bbox_pdf_user_space_points=[1, 1, 10, 10],
    )
    table.update(
        page_number=1,
        row_count=1,
        column_count=1,
        bbox_pdf_user_space_points=[0, 0, 100, 100],
        cells=[cell],
    )
    draft["tables"] = [table]
    update(app, "draft", document_id=key, draft=draft)
    with pytest.raises(ValueError, match="single original page"):
        app.grid_proposal(
            "grid-propose",
            {
                "revision": app.view()["revision"],
                "document_id": key,
                "page": 1,
                "page_identity": app.pages[key][0],
                "table_index": 0,
            },
        )


def test_grid_http_security_and_browser(tmp_path):
    app, _, _ = grid_fixture(tmp_path)
    with tool.ReviewServer(app) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            for route in ("grid-propose", "grid-load", "grid-correct", "grid-accept"):
                assert request(server, route)[0] == 403
                assert (
                    request(
                        server,
                        route,
                        method="POST",
                        payload=supplied(app),
                        headers={"X-Review-Token": "forged"},
                    )[0]
                    == 409
                )
                assert (
                    request(
                        server,
                        route,
                        method="POST",
                        payload=supplied(app),
                        headers={"Origin": "https://attacker.invalid"},
                    )[0]
                    == 409
                )
            assert request(server, "grid.js")[0] == 200
            assert request(server, "legacy?document_id=c1-0001")[0] == 403
            node = os.environ.get("ML30_NODE")
            if not node or not os.environ.get("ML30_NODE_MODULES"):
                pytest.skip("Set ML30_NODE and ML30_NODE_MODULES for actual overlay/acceptance UI")
            subprocess.run(
                [
                    node,
                    str(Path(__file__).with_name("pdf_grid_proposals.browser.cjs")),
                    f"http://127.0.0.1:{server.server_port}/{server.token}/",
                ],
                timeout=120,
                check=True,
            )
        finally:
            server.shutdown()
            thread.join(timeout=5)
    assert len(app.view()["documents"]["c1-0001"]["draft"]["tables"][0]["cells"]) == 6


def test_wrong_page_source_and_forged_proposal_rejected(tmp_path):
    app, _, _ = grid_fixture(tmp_path)
    request_data = supplied(app)
    request_data["page_identity"] = {"page_number": 2}
    with pytest.raises(ValueError, match="identity"):
        app.grid_proposal("grid-propose", request_data)
    proposal = app.grid_proposal("grid-propose", supplied(app))
    path = next((app.output / "grid-proposals").glob("*.json"))
    forged = json.loads(path.read_text(encoding="utf-8"))
    forged["candidate"]["cells"][0]["literal_text"] = "forged"
    path.write_text(json.dumps(forged), encoding="utf-8")
    with pytest.raises(ValueError, match="identity"):
        app.grid_proposal("grid-accept", supplied(app, proposal, confirm_accept=True))


def diagnostic_candidate(app):
    table = app.state["documents"]["c1-0001"]["draft"]["tables"][0]
    return grids.detect(
        app.render_page(payload(app)),
        table["bbox_pdf_user_space_points"],
        table["row_count"],
        table["column_count"],
    )


@pytest.mark.parametrize("options", [{}, {"irregular": True}, {"crossed": True}, {"label": "A  B"}])
def test_diagnostics_do_not_change_any_proposal_field(tmp_path, options):
    app, _, _ = grid_fixture(tmp_path, **options)
    candidate = diagnostic_candidate(app)
    plain, diagnosed = copy.deepcopy(candidate), copy.deepcopy(candidate)
    report = {}
    grids.add_text(app.pdf("c1-0001"), 1, plain)
    grids.add_text(app.pdf("c1-0001"), 1, diagnosed, diagnostics=report)
    assert plain == diagnosed
    assert report["non_null"] + report["null"] == 6
    assert sum(report["primary_null_reason_counts"].values()) == report["null"]
    assert all(c["reason_codes"] for c in report["cells"] if not c["has_literal"])
    serialized = json.dumps(report)
    assert "R0C0" not in serialized and "PRIVATE_SYNTHETIC_FILENAME" not in serialized
    assert "literal_text" not in serialized and "bbox_pdf_user_space_points" not in serialized


def test_diagnostics_crossing_glyph_never_fills_either_neighbor(tmp_path):
    app, _, _ = grid_fixture(tmp_path, crossed=True)
    candidate, report = diagnostic_candidate(app), {}
    grids.add_text(app.pdf("c1-0001"), 1, candidate, diagnostics=report)
    assert candidate["cells"][0]["literal_text"] is None
    assert candidate["cells"][1]["literal_text"] is None
    assert candidate["cells"][2]["literal_text"] == "R1C0"
    assert report["primary_null_reason_counts"]["CHARACTER_BBOX_CROSSES_CELLS"] == 2


@pytest.mark.parametrize(
    "native_flag, code", [(1, "UNICODE_MAPPING_ERROR"), (-1, "UNICODE_MAPPING_UNAVAILABLE")]
)
def test_diagnostics_missing_mapping_is_blocked_and_distinguished(
    tmp_path, monkeypatch, native_flag, code
):
    import pypdfium2 as pdfium

    app, _, _ = grid_fixture(tmp_path)
    candidate, report = diagnostic_candidate(app), {}
    original = pdfium.raw.FPDFText_HasUnicodeMapError
    monkeypatch.setattr(
        pdfium.raw,
        "FPDFText_HasUnicodeMapError",
        lambda t, i: native_flag if i == 0 else original(t, i),
    )
    grids.add_text(app.pdf("c1-0001"), 1, candidate, diagnostics=report)
    assert candidate["cells"][0]["literal_text"] is None
    assert report["primary_null_reason_counts"][code] == 1
    assert report["non_null"] == 5


@pytest.mark.parametrize(
    "native_flag, code",
    [(1, "GENERATED_NONSPACE_CHARACTER"), (-1, "GENERATED_CHARACTER_FLAG_UNAVAILABLE")],
)
def test_diagnostics_generated_identity_is_not_source_text(
    tmp_path, monkeypatch, native_flag, code
):
    import pypdfium2 as pdfium

    app, _, _ = grid_fixture(tmp_path)
    candidate, report = diagnostic_candidate(app), {}
    original = pdfium.raw.FPDFText_IsGenerated
    monkeypatch.setattr(
        pdfium.raw, "FPDFText_IsGenerated", lambda t, i: native_flag if i == 0 else original(t, i)
    )
    grids.add_text(app.pdf("c1-0001"), 1, candidate, diagnostics=report)
    assert candidate["cells"][0]["literal_text"] is None
    assert report["primary_null_reason_counts"][code] == 1


@pytest.mark.parametrize(
    "flag, code",
    [("identity", "INVALID_CHARACTER_IDENTITY"), ("angle", "UNSUPPORTED_CHARACTER_ROTATION")],
)
def test_diagnostics_other_native_failures_remain_unresolved(tmp_path, monkeypatch, flag, code):
    import pypdfium2 as pdfium

    app, _, _ = grid_fixture(tmp_path)
    candidate, report = diagnostic_candidate(app), {}
    name = "FPDFText_GetUnicode" if flag == "identity" else "FPDFText_GetCharAngle"
    original = getattr(pdfium.raw, name)
    replacement = 0 if flag == "identity" else float("nan")
    monkeypatch.setattr(pdfium.raw, name, lambda t, i: replacement if i == 0 else original(t, i))
    grids.add_text(app.pdf("c1-0001"), 1, candidate, diagnostics=report)
    assert candidate["cells"][0]["literal_text"] is None
    assert report["primary_null_reason_counts"][code] == 1


def test_diagnostics_outside_box_does_not_clip_or_move_glyph(tmp_path):
    app, _, _ = grid_fixture(tmp_path)
    candidate, report = diagnostic_candidate(app), {}
    candidate["cells"][0]["bbox_pdf_user_space_points"][0] = 47
    boxes = [copy.deepcopy(c["bbox_pdf_user_space_points"]) for c in candidate["cells"]]
    grids.add_text(app.pdf("c1-0001"), 1, candidate, diagnostics=report)
    assert report["primary_null_reason_counts"]["CHARACTER_BBOX_OUTSIDE_CELL"] == 1
    assert candidate["cells"][0]["literal_text"] is None
    assert boxes == [c["bbox_pdf_user_space_points"] for c in candidate["cells"]]


def test_diagnostics_interleaved_native_order_is_not_sorted_into_cells(tmp_path, monkeypatch):
    import pypdfium2 as pdfium

    app, _, _ = grid_fixture(tmp_path)
    candidate, report = diagnostic_candidate(app), {}
    original = pdfium.PdfTextPage.get_charbox
    monkeypatch.setattr(
        pdfium.PdfTextPage,
        "get_charbox",
        lambda self, i, loose=False: original(self, {1: 5, 5: 1}.get(i, i), loose=loose),
    )
    grids.add_text(app.pdf("c1-0001"), 1, candidate, diagnostics=report)
    assert candidate["cells"][0]["literal_text"] is None
    assert candidate["cells"][1]["literal_text"] is None
    assert report["primary_null_reason_counts"]["INTERLEAVED_CHARACTER_ORDER"] == 2


def test_diagnostics_generated_space_with_degenerate_box_is_not_repaired(tmp_path):
    app, _, _ = grid_fixture(tmp_path, split_word=True)
    candidate, report = diagnostic_candidate(app), {}
    grids.add_text(app.pdf("c1-0001"), 1, candidate, diagnostics=report)
    assert candidate["cells"][0]["literal_text"] is None
    assert report["primary_null_reason_counts"]["GENERATED_WHITESPACE_GAP"] == 1
    assert report["reason_cell_counts"]["DEGENERATE_WHITESPACE_BOX"] == 1


def test_diagnostics_missing_layer_and_limit_are_different(tmp_path, monkeypatch):
    import pypdfium2 as pdfium

    app, _, _ = grid_fixture(tmp_path, empty_text=True)
    candidate, report = diagnostic_candidate(app), {}
    grids.add_text(app.pdf("c1-0001"), 1, candidate, diagnostics=report)
    assert report["primary_null_reason_counts"]["NO_TEXT_LAYER_GLYPHS_IN_CELL"] == 6
    assert report["source_character_count"] == 0
    monkeypatch.setattr(pdfium.PdfTextPage, "count_chars", lambda _: 200_001)
    grids.add_text(app.pdf("c1-0001"), 1, candidate, diagnostics=report)
    assert report["primary_null_reason_counts"]["TEXT_LAYER_LIMIT"] == 6
    assert report["primary_null_reason_counts"]["NO_TEXT_LAYER_GLYPHS_IN_CELL"] == 0


def test_diagnostics_no_grid_does_not_claim_empty_source_layer(tmp_path):
    app, _, _ = grid_fixture(tmp_path)
    proposal, report = {"cells": []}, {}
    grids.add_text(app.pdf("c1-0001"), 1, proposal, diagnostics=report)
    assert report["source_character_count"] is None
    assert report["non_null"] == report["null"] == 0


def test_diagnostics_helper_is_bound_sanitized_repeatable_and_read_only(tmp_path):
    app, _, _ = grid_fixture(tmp_path)
    proposal = app.grid_proposal("grid-propose", supplied(app))
    proposal["cells"][0]["literal_text"] = "manual correction remains untouched"
    before = copy.deepcopy(proposal)
    source = app.pdf("c1-0001")
    digest = app.records["c1-0001"].source_sha256
    report = text_diagnostics.diagnose(source, digest, 1, proposal)
    assert report == text_diagnostics.diagnose(source, digest, 1, proposal)
    assert proposal == before and report["non_null"] == 6
    proposal_path = app.output / "candidate.json"
    proposal_path.write_text(json.dumps(proposal), encoding="utf-8")
    saved = proposal_path.read_bytes()
    output = app.root / "evaluation-output/ml30c-test-diagnostics"
    assert text_diagnostics.run(source, digest, 1, proposal_path, output, root=app.root) == report
    assert json.loads((output / "text-diagnostics.json").read_text(encoding="utf-8")) == report
    assert saved == proposal_path.read_bytes()
    assert "manual correction" not in json.dumps(report) and "R0C0" not in json.dumps(report)
    with pytest.raises(ValueError):
        text_diagnostics.run(source, digest, 1, proposal_path, output, root=app.root)
    for forbidden in (app.output / "ml30c-nested", app.root / "raw/ml30c-output"):
        with pytest.raises(ValueError):
            text_diagnostics.run(source, digest, 1, proposal_path, forbidden, root=app.root)
    with pytest.raises(ValueError, match="SHA"):
        text_diagnostics.diagnose(source, "0" * 64, 1, proposal)
    proposal["context"]["page_identity"] = {"page_number": 2}
    with pytest.raises(ValueError, match="binding"):
        text_diagnostics.diagnose(source, digest, 1, proposal)
