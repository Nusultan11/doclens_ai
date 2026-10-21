"""Synthetic frozen GOV.UK-shaped metadata tests; no network or actual rights attestation."""

from __future__ import annotations

import csv
import hashlib
import json

import pytest
from docx import Document

from doclens_ai.eda import corpus_v2 as corpus
from tests.unit.test_corpus_v2 import manifest
from tools.extraction_quality import office_corpus_v2 as office


def fixture(tmp_path, monkeypatch):
    monkeypatch.setattr(office, "private_destination", lambda _: None)
    root = tmp_path / "acquisition"
    root.mkdir()
    (root / "assets").mkdir()
    url = "https://assets.publishing.service.gov.uk/media/public-fixture/public.docx"
    source_url = "https://www.gov.uk/government/publications/public-fixture"
    source_id = hashlib.sha256(source_url.encode()).hexdigest()
    sample_id = "e2-office-" + hashlib.sha256(url.encode()).hexdigest()[:16]
    raw = root / "assets" / (sample_id + ".docx")
    document = Document()
    document.add_paragraph("Public synthetic fixture")
    document.save(raw)
    content = root / (source_id + "-content.json")
    content.write_text(
        json.dumps(
            {
                "base_path": "/government/publications/public-fixture",
                "details": {
                    "attachments": [
                        {
                            "url": url,
                            "file_size": raw.stat().st_size,
                            "content_type": office.MIME_TYPES["docx"],
                        }
                    ]
                },
            }
        ),
        encoding="utf-8",
    )
    page = root / (source_id + "-page.html")
    page.write_text(
        '<a href="https://www.nationalarchives.gov.uk/doc/open-government-licence/'
        'version/3/">OGL</a>',
        encoding="utf-8",
    )
    event = {
        "status": "admitted",
        "url": url,
        "source_url": source_url,
        "source_id": source_id,
        "format": "docx",
        "sample_id": sample_id,
        "asset_path": "assets/" + raw.name,
        "size_bytes": raw.stat().st_size,
        "sha256": corpus.sha256(raw),
        "metadata_sha256": corpus.sha256(content),
        "page_sha256": corpus.sha256(page),
    }
    ledger = root / "ledger.json"
    ledger.write_text(json.dumps([event]), encoding="utf-8")
    legacy = tmp_path / "legacy.csv"
    with legacy.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["sha256"])
        writer.writeheader()
        writer.writerow({"sha256": "0" * 64})
    template = tmp_path / "template.json"
    template.write_text(manifest().model_dump_json(), encoding="utf-8")
    return root, ledger, legacy, template, event, content, page


def test_office_pilot_rebuild_preserves_unknown_languages_and_families(tmp_path, monkeypatch):
    root, ledger, legacy, template, event, _, _ = fixture(tmp_path, monkeypatch)
    output = tmp_path / "manifest.json"
    result = office.prepare(template, root, [ledger], legacy, output)
    value = corpus.load(output)
    assert result["new_pilot_samples"] == 1
    assert value.samples[0].original.sha256 == event["sha256"]
    assert value.samples[0].languages == ("unknown",)
    assert value.samples[0].family_review == "unknown"
    assert value.samples[0].split == "dev"
    assert corpus.audit(value, root)["native_eligible"] == 1


@pytest.mark.parametrize(
    "fault",
    [
        "changed_metadata",
        "rights",
        "wrong_attachment",
        "duplicate",
        "source_host",
        "changed_original",
        "mime",
        "missing_mime",
    ],
)
def test_office_qualification_fails_closed(tmp_path, monkeypatch, fault):
    root, ledger, legacy, template, event, content, page = fixture(tmp_path, monkeypatch)
    if fault == "changed_metadata":
        content.write_text("{}")
    elif fault == "rights":
        page.write_text("No OGL evidence")
        event["page_sha256"] = corpus.sha256(page)
    elif fault == "wrong_attachment":
        data = json.loads(content.read_text(encoding="utf-8"))
        data["details"]["attachments"][0]["url"] += "-wrong"
        content.write_text(json.dumps(data))
        event["metadata_sha256"] = corpus.sha256(content)
    elif fault == "duplicate":
        legacy.write_text("sha256\n" + event["sha256"] + "\n")
    elif fault == "source_host":
        event["url"] = "https://untrusted.invalid/public.docx"
    elif fault in {"mime", "missing_mime"}:
        data = json.loads(content.read_text(encoding="utf-8"))
        data["details"]["attachments"][0]["content_type"] = (
            "application/pdf" if fault == "mime" else None
        )
        content.write_text(json.dumps(data))
        event["metadata_sha256"] = corpus.sha256(content)
    else:
        (root / event["asset_path"]).write_bytes(b"changed")
    ledger.write_text(json.dumps([event]), encoding="utf-8")
    with pytest.raises(ValueError):
        office.prepare(template, root, [ledger], legacy, tmp_path / "manifest.json")
