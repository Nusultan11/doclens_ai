from __future__ import annotations

from copy import deepcopy

import pytest

from doclens_ai.eda import corpus_v2 as corpus
from doclens_ai.extraction.fidelity_gold import fingerprint
from tools.extraction_quality import readiness_release as release
from tools.extraction_quality.readiness_io import atomic


@pytest.fixture
def continuation(tmp_path, monkeypatch):
    monkeypatch.setattr(release, "ROOT", tmp_path)
    monkeypatch.setattr(release, "private_root", lambda path: None)
    parent = tmp_path / "parent"
    parent.mkdir()
    atomic(parent / "effective-matrix.json", {"population": []})
    manifest = {
        "artifact_sha256": {
            "effective-matrix.json": corpus.sha256(parent / "effective-matrix.json")
        },
        "protected_sha256": {},
        "gates": {},
    }
    manifest["fingerprint"] = fingerprint(manifest)
    atomic(parent / "RELEASE.json", manifest)
    output = tmp_path / "new"
    atomic(
        output / "parent-proof.json",
        {"parent_root": "parent", "manifest_sha256": corpus.sha256(parent / "RELEASE.json")},
    )
    monkeypatch.setattr(release, "read", lambda key: {"reserved_source_sha256": []})
    rows, decisions = [], []
    for i in range(2):
        path = tmp_path / f"original{i}.pdf"
        path.write_bytes(b"%PDF-1.7\n" + str(i).encode())
        ref = {
            "path": path.name,
            "sha256": corpus.sha256(path),
            "size_bytes": path.stat().st_size,
            "format": "pdf",
        }
        scopes = {"local_evaluation": True, "new_annotation": True}
        rows.append(
            {
                "id": f"source-{i}",
                "sha256": ref["sha256"],
                "source_reference": ref,
                "independent_gold": False,
                "split": "dev",
                "family": f"family-{i}",
                "format": "pdf",
                "reserved_qa_family": False,
                "rights": scopes,
            }
        )
        decisions.append(
            {
                "source_id": f"source-{i}",
                "source_sha256": ref["sha256"],
                "reviewer": None,
                "human_reviewed": False,
                "disposition": "ADMIT",
                "basis_kind": "publisher_CC_license",
                "scopes": scopes,
                "grants": scopes,
                "evidence": [{"path": path.name, "sha256": ref["sha256"]}],
            }
        )
    atomic(output / "rights-decisions-v2.json", {"decisions": decisions})
    return output, {"population": rows}, decisions


def test_continuation_positive_and_missing_rights_negative(continuation):
    output, matrix, decisions = continuation
    release.validate_continuation(output, matrix)
    decisions[0]["grants"] = {"local_evaluation": True}
    atomic(output / "rights-decisions-v2.json", {"decisions": decisions})
    with pytest.raises(ValueError, match="illegal rights"):
        release.validate_continuation(output, matrix)


@pytest.mark.parametrize(
    "link", ["family", "near_duplicate_group", "normalized_text_sha256", "related_families"]
)
def test_family_template_translation_leakage_rejected(continuation, link):
    output, matrix, _ = continuation
    a, b = matrix["population"]
    b["split"] = "sealed_candidate"
    release.validate_continuation(output, matrix)
    if link == "related_families":
        b[link] = [a["family"]]
    else:
        a[link] = b[link] = "b" * 64 if link == "normalized_text_sha256" else "shared"
    with pytest.raises(ValueError, match="family crosses"):
        release.validate_continuation(output, matrix)


def test_duplicate_source_bytes_and_fabricated_review_rejected(continuation):
    output, matrix, decisions = continuation
    original = deepcopy(matrix)
    matrix["population"][1]["sha256"] = matrix["population"][0]["sha256"]
    with pytest.raises(ValueError, match="duplicate original"):
        release.validate_continuation(output, matrix)
    decisions[0]["human_reviewed"] = True
    atomic(output / "rights-decisions-v2.json", {"decisions": decisions})
    with pytest.raises(ValueError, match="spoofed review"):
        release.validate_continuation(output, original)


def test_archive_verification_pins_original_code(tmp_path, monkeypatch):
    monkeypatch.setattr(release, "ROOT", tmp_path)
    monkeypatch.setattr(release, "private_root", lambda path: None)
    output = tmp_path / "release"
    atomic(output / "code" / "source.json", {"revision": 1})
    digest = corpus.sha256(output / "code" / "source.json")
    value = {
        "artifact_sha256": {"code/source.json": digest},
        "protected_sha256": {"source.json": digest},
        "final_code_sha256": {"source.json": digest},
        "code_archive": "code",
        "gates": {},
    }
    value["fingerprint"] = fingerprint(value)
    atomic(output / "RELEASE.json", value)
    atomic(tmp_path / "source.json", {"revision": 2})
    assert release.verify(output)["integrity"] == "PASS"
    with pytest.raises(ValueError, match="active scoring code"):
        release.verify_runtime(output)
    (output / "code" / "source.json").write_text("{}")
    with pytest.raises(ValueError, match="protected"):
        release.verify(output)
