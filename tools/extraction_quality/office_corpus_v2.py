"""Rebuild the separate Office pilot from frozen, bounded local acquisition evidence.

No network calls. This replays the existing GOV.UK/OGL acquisition policy using
saved authoritative page/attachment metadata, not a new blanket rights grant.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit

from doclens_ai.eda import corpus_v2 as corpus
from doclens_ai.extraction.fidelity_gold import fingerprint
from tools.extraction_quality.extraction_v2 import private_destination, write

ALTERNATIVE_RIGHTS = (
    "third party copyright",
    "third-party copyright",
    "all rights reserved",
    "not covered by the open government licence",
    "alternative licence",
    "separate licence",
)
MIME_TYPES = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def prepare(template: Path, root: Path, ledgers: list[Path], legacy: Path, output: Path) -> dict:
    private_destination(output)
    corpus.no_links(root)
    value = corpus.load(template)
    with legacy.open(encoding="utf-8", newline="") as stream:
        old_rows = list(csv.DictReader(stream))
    if len(old_rows) > 2000 or not 0 < len(ledgers) <= 10:
        raise ValueError("qualification budget")
    old_hashes = {r["sha256"] for r in old_rows}
    events = [event for path in ledgers for event in corpus.read_json(path)]
    if not 0 < len(events) <= 200:
        raise ValueError("acquisition event budget")
    samples, seen = [], set(old_hashes)
    for event in events:
        if event["status"] != "admitted":
            raise ValueError("non-admitted event requires separate eligibility resolution")
        if event["format"] not in {"docx", "xlsx"}:
            raise ValueError("Office format required")
        parsed = urlsplit(event["url"])
        source_url = event["source_url"]
        source = urlsplit(source_url)
        if (
            parsed.scheme != "https"
            or parsed.hostname != "assets.publishing.service.gov.uk"
            or source.scheme != "https"
            or source.hostname != "www.gov.uk"
        ):
            raise ValueError("source host rejected")
        if hashlib.sha256(source_url.encode()).hexdigest() != event["source_id"]:
            raise ValueError("source page identity rejected")
        folders = (root, root / "revision-2")
        matching = []
        for folder in folders:
            metadata = folder / (event["source_id"] + "-content.json")
            page = folder / (event["source_id"] + "-page.html")
            if metadata.is_file() and page.is_file():
                corpus.no_links(metadata)
                corpus.no_links(page)
                if (
                    corpus.sha256(metadata) == event["metadata_sha256"]
                    and corpus.sha256(page) == event["page_sha256"]
                ):
                    matching.append((metadata, page))
        if len(matching) != 1:
            raise ValueError("frozen rights/metadata pair rejected")
        metadata_path, page_path = matching[0]
        metadata = corpus.read_json(metadata_path, max_bytes=1024**2)
        if page_path.stat().st_size > 1024**2:
            raise ValueError("rights page budget")
        html = page_path.read_bytes()
        if (
            b"nationalarchives.gov.uk/doc/open-government-licence/version/3" not in html
            or any(p in str(metadata.get("details", {})).lower() for p in ALTERNATIVE_RIGHTS)
            or metadata["base_path"] != source.path
        ):
            raise ValueError("GOV.UK/OGL policy not established")
        attachments = metadata.get("details", {}).get("attachments", [])
        matches = [a for a in attachments if a.get("url") == event["url"]]
        if (
            not parsed.path.lower().endswith("." + event["format"])
            or not matches
            or not any(
                (a.get("file_size") or a.get("size")) == event["size_bytes"]
                and a.get("content_type") == MIME_TYPES[event["format"]]
                for a in matches
            )
        ):
            raise ValueError("attachment/source page binding rejected")
        asset = corpus.Asset(
            path=event["asset_path"],
            sha256=event["sha256"],
            size_bytes=event["size_bytes"],
            format=event["format"],
        )
        corpus.asset_path(root, asset)
        if asset.sha256 in seen or asset.size_bytes > 2 * 1024**2:
            raise ValueError("duplicate or oversized source rejected")
        seen.add(asset.sha256)
        identity = "e2-office-" + hashlib.sha256(event["url"].encode()).hexdigest()[:16]
        if identity != event["sample_id"]:
            raise ValueError("source record identity rejected")
        samples.append(
            corpus.Sample(
                sample_id=identity,
                dataset="additional-" + event["format"],
                release="GOV.UK-20261021",
                revision=event["metadata_sha256"],
                source_record_id=identity,
                cohort="pilot",
                disposition="admitted",
                original=asset,
                rights=corpus.Rights(
                    dataset_license="Open Government Licence v3.0",
                    original_license="Open Government Licence v3.0",
                    local_evaluation=True,
                    annotation_use=None,
                    redistribution=None,
                    sensitivity="public",
                    references=(
                        "docs/eda/corpus_v1_protocol.md",
                        "frozen-source-" + event["source_id"],
                    ),
                ),
                languages=("unknown",),
                document_type="public_sector_office",
                difficulty=("not_reviewed",),
                family_id="f-" + fingerprint(source_url)[:24],
                family_review="unknown",
                split="dev",
                publicly_exposed=True,
                unsupported=("reviewed_language", "independent_gold", "family_completeness"),
            )
        )
    if sum(s.original.size_bytes for s in samples) > 30 * 1024**2:
        raise ValueError("aggregate acquisition budget")
    result = corpus.Corpus(
        revision="extraction-corpus-v2-20261021-office-r2",
        selection_seed="extraction-v2-office-1",
        selection_rule="govuk-office-url-sha256-v1",
        split_revision=value.split_revision,
        targets=value.targets,
        samples=tuple(sorted(samples, key=lambda s: s.sample_id)),
    )
    write(output, result.model_dump(mode="json"))
    return {
        "samples": len(samples),
        "new_pilot_samples": len(samples),
        "manifest_fingerprint": fingerprint(result.model_dump(mode="json")),
        "acquisition_ledger_sha256": [corpus.sha256(p) for p in ledgers],
        "preparer_sha256": corpus.sha256(Path(__file__)),
        "independent_gold": 0,
        "reviewed_languages": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, action="append", required=True)
    parser.add_argument("--legacy-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(
            json.dumps(
                prepare(args.template, args.root, args.ledger, args.legacy_manifest, args.output),
                sort_keys=True,
            )
        )
        return 0
    except Exception:  # noqa: BLE001 - never print private paths or metadata bodies
        print("BLOCKED: frozen source/rights/bytes/duplicate qualification failed")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
