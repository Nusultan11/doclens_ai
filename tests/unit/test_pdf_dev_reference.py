"""Public synthetic sources only; no private labels or reviewer attestations."""

from __future__ import annotations

import copy
import csv
from collections import Counter

import pytest

from tests.unit.test_pdf_assisted_review import build, fixture
from tools.extraction_quality import pdf_assisted_review as assisted
from tools.extraction_quality import pdf_dev_reference as tool
from tools.extraction_quality import pdf_table_review_packet as packet


@pytest.fixture(scope="module")
def public_package(tmp_path_factory):
    output, _ = build(fixture(tmp_path_factory.mktemp("dev-reference"), partition=True))
    files = {
        p.relative_to(output).as_posix(): packet.sha(p) for p in output.rglob("*") if p.is_file()
    }
    packet.write_json(output / "VERIFIED.json", {"files": files})
    payload = assisted.read(output / "proposals.json")
    kinds = Counter(i["kind"] for i in payload["items"])
    counts = tool.Counts(
        len(payload["items"]),
        kinds["cell"],
        kinds["text_anchor"],
        kinds["printed_unit"],
        kinds["table"],
    )
    confirmation = dict(
        confirmation_source="explicit_user_message",
        confirmed_on="2026-10-22",
        scope="source_comparison_report_only",
        report_level_confirmed=True,
        report_artifact_identity="NOT_SEPARATELY_SUPPLIED",
        reviewer_id=None,
        per_item_decisions_supplied=False,
        independent_review=False,
        reported_counts=counts.to_dict(),
        unresolved_dimensions=list(tool.UNRESOLVED),
    )
    return output, payload, counts, confirmation


def test_deterministic_projection_preserves_ids_literals_and_uncertainty(public_package):
    _, payload, counts, confirmation = public_package
    actual, inventory = tool.project(payload, confirmation, counts)
    assert (actual, inventory) == tool.project(copy.deepcopy(payload), confirmation, counts)
    assert {i["item_id"] for i in inventory} == {i["item_id"] for i in payload["items"]}
    assert all(i["per_item_human_decision"] is None for i in inventory)
    assert [i["original_proposal"] for i in inventory] == payload["items"]
    assert not actual["independent_gold"] and not actual["sealed_test"]
    assert actual["qg_00"] == actual["qg_01"] == "NOT_EVALUATED"
    cells = actual["documents"][0]["cells"]
    assert [c["literal_text"] for c in cells] == ["W1", "W2", ""]
    assert cells[-1]["source_text_evidence"]["uncertainty"]
    assert cells[-1]["boundary_context"]["semantic_interpretation"] is None
    assert all(c["locator_context"]["exact_border_fidelity"] == "UNRESOLVED" for c in cells)
    assert actual["documents"][0]["logical_grids"][0]["logical_slot_coverage_complete"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("independent_gold", True),
        ("sealed_test", True),
        ("split", "test"),
        ("qg_00", "PASS"),
        ("qg_01", "PASS"),
        ("per_item_human_approval", True),
        ("unresolved_dimensions", []),
        ("semantic_roles", ["verified_header"]),
    ],
)
def test_promotion_and_unsupported_fields_rejected(public_package, field, value):
    _, payload, counts, confirmation = public_package
    actual, _ = tool.project(payload, confirmation, counts)
    actual[field] = value
    with pytest.raises(ValueError, match="fields or promotion"):
        tool.validate_payload(actual, payload, confirmation, counts)


@pytest.mark.parametrize(
    "field,value",
    [
        ("reviewer_id", "fabricated"),
        ("independent_review", True),
        ("per_item_decisions_supplied", True),
        ("scope", "all_semantics"),
        ("unresolved_dimensions", []),
        ("confirmed_on", "not-a-date"),
    ],
)
def test_confirmation_cannot_create_human_attestations(public_package, field, value):
    _, _, counts, confirmation = public_package
    modified = copy.deepcopy(confirmation)
    modified[field] = value
    with pytest.raises(ValueError):
        tool.validate_confirmation(modified, counts)


@pytest.mark.parametrize(
    "change", ["choice", "approval", "source", "missing", "duplicate", "header"]
)
def test_malformed_or_invented_decisions_rejected(public_package, tmp_path, change):
    output, payload, _, _ = public_package
    tool.validate_decisions(output / "review_decisions.csv", payload)
    with (output / "review_decisions.csv").open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    fields = assisted.FIELDS.copy()
    if change == "choice":
        rows[0]["decision"] = "silently_promote"
    elif change == "approval":
        rows[0]["decision"] = "accept"
    elif change == "source":
        rows[0]["source_sha256"] = "0" * 64
    elif change == "missing":
        rows.pop()
    elif change == "duplicate":
        rows.append(rows[0])
    else:
        fields.remove("reviewer_notes")
        rows = [{k: v for k, v in row.items() if k in fields} for row in rows]
    path = tmp_path / "decisions.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(ValueError):
        tool.validate_decisions(path, payload)


def test_source_drift_and_rehashed_manifest_rejected(public_package, tmp_path):
    import shutil

    output, payload, _, _ = public_package
    digest = packet.sha(output / "artifact-manifest.json")
    assert tool.verify_package(output, digest) == payload
    changed = tmp_path / "changed"
    shutil.copytree(output, changed)
    pdf = next((changed / "sources").glob("*.pdf"))
    pdf.write_bytes(pdf.read_bytes() + b"\n% drift")
    with pytest.raises(ValueError, match="package drift"):
        tool.verify_package(changed, digest)
    manifest = assisted.read(changed / "artifact-manifest.json")
    manifest[pdf.relative_to(changed).as_posix()] = packet.sha(pdf)
    (changed / "artifact-manifest.json").unlink()
    packet.write_json(changed / "artifact-manifest.json", manifest)
    with pytest.raises(ValueError, match="manifest pin drift"):
        tool.verify_package(changed, digest)


@pytest.mark.parametrize("change", ["literal", "anchor", "coordinate", "occupancy"])
def test_projection_requires_exact_item_and_grid_binding(public_package, change):
    _, original, counts, confirmation = public_package
    payload = copy.deepcopy(original)
    doc = payload["documents"][0]
    if change == "anchor":
        doc["text_anchors"][0]["literal_text"] = "invented"
    else:
        cell = doc["tables"][0]["cells"][0]
        if change == "literal":
            cell["literal_text"] = "invented"
        elif change == "coordinate":
            cell["bbox_pdf_user_space_points"][0] += 1
        else:
            doc["tables"][0]["row_count"] += 1
    with pytest.raises(ValueError):
        tool.project(payload, confirmation, counts)
