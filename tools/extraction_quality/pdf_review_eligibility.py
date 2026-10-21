"""Validate documentary admission records, never infer rights or human review.

The recorded decision is an explicit, auditable interpretation of captured terms.
Hash validation establishes its binding, not the legal truth of that interpretation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool

from doclens_ai.eda.corpus_v2 import read_json
from doclens_ai.extraction.fidelity_gold import FidelityRecord, fingerprint

OGL = "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/"
ATTRIBUTION = "Contains public sector information licensed under the Open Government Licence v3.0."


class StrictRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Evidence(StrictRecord):
    path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    url: str | None
    locator: str = Field(min_length=1)


class Candidate(StrictRecord):
    document_id: str
    disposition: Literal["admit", "blocked", "excluded"]
    reasons: list[str]
    source_sha256: str
    source_size_bytes: int
    source_page_url: str
    download_url: str
    publisher: str = Field(min_length=1)
    family_id: str
    pages: list[dict]
    evidence_refs: list[str]
    document_inspection_ref: str | None
    license_offer_ref: str | None
    license_url: str | None
    annotation_use: StrictBool | None
    adaptation_granted: StrictBool | None
    third_party_rights: Literal["none_identified", "unresolved"]
    exclusions: list[str]
    sensitivity: Literal["public", "unresolved"]
    scope: Literal["new_source_annotations_local_dev"] | None
    attribution: str | None
    existing_annotation_reuse_authorized: Literal[False]
    annotation_provenance: str = Field(min_length=1)
    rationale: str = Field(min_length=1)


class Eligibility(StrictRecord):
    version: Literal["pdf-review-eligibility-v1"]
    revision: str = Field(min_length=1)
    supersedes: Evidence
    manifest_sha256: str
    gold_sha256: str
    license_grant_ref: str
    evidence: dict[str, Evidence]
    candidates: list[Candidate]
    split: Literal["dev"]
    publicly_exposed: Literal[True]
    independent_gold: Literal["NOT_EVALUATED"]
    decision_basis: Literal["documentary_analysis_not_reviewer_attestation"]


def validate(
    path: Path,
    manifest: Path,
    gold: Path,
    records: tuple[FidelityRecord, ...],
    paths: dict[str, Path],
    metadata: dict,
) -> tuple[tuple[FidelityRecord, ...], dict]:
    """Verify the full attempted denominator before selecting authorized originals."""
    from tools.extraction_quality import pdf_table_review_packet as packet
    from tools.extraction_quality.pdf_review_validation import original_pages

    packet.no_links(path)
    if path.stat().st_size > 1024**2:
        raise packet.PacketError("Eligibility record bound exceeded")
    value = Eligibility.model_validate(read_json(path, max_bytes=1024**2))
    if (value.manifest_sha256, value.gold_sha256) != (packet.sha(manifest), packet.sha(gold)):
        raise packet.PacketError("Eligibility frozen input mismatch")
    references = {**value.evidence, "supersedes": value.supersedes}
    for ref in references.values():
        relative = Path(ref.path)
        target = path.parent / relative
        if relative.is_absolute() or ".." in relative.parts:
            raise packet.PacketError("Eligibility evidence path rejected")
        packet.no_links(target)
        if packet.sha(target) != ref.sha256:
            raise packet.PacketError("Eligibility evidence identity mismatch")
    grant = references.get(value.license_grant_ref)
    if grant is None or grant.url != OGL:
        raise packet.PacketError("Missing explicit license grant evidence")
    ids = [c.document_id for c in value.candidates]
    if len(ids) != len(set(ids)) or set(ids) != {r.document_id for r in records}:
        raise packet.PacketError("Eligibility denominator or duplicate identity mismatch")
    by_id = {r.document_id: r for r in records}
    admitted = []
    for candidate in value.candidates:
        key = candidate.document_id
        record, row = by_id[key], metadata[key]
        if (
            (candidate.source_sha256, candidate.source_size_bytes)
            != (record.source_sha256, record.source_size_bytes)
            or candidate.source_page_url != row.get("source_page_url")
            or candidate.download_url != row.get("download_url")
            or candidate.family_id != "f-" + fingerprint(candidate.source_page_url)[:24]
            or candidate.pages != original_pages(paths[key])
            or not candidate.evidence_refs
            or any(ref not in references for ref in candidate.evidence_refs)
        ):
            raise packet.PacketError("Eligibility source, page or family mismatch")
        if candidate.disposition != "admit":
            if not candidate.reasons:
                raise packet.PacketError("Missing exclusion reason")
            continue
        offer = references.get(candidate.license_offer_ref)
        inspection = references.get(candidate.document_inspection_ref)
        if (
            candidate.reasons
            or candidate.annotation_use is not True
            or candidate.adaptation_granted is not True
            or candidate.license_url != OGL
            or candidate.third_party_rights == "unresolved"
            or candidate.exclusions
            or candidate.sensitivity != "public"
            or candidate.scope != "new_source_annotations_local_dev"
            or candidate.attribution != ATTRIBUTION
            or offer is None
            or offer.url != candidate.source_page_url
            or inspection is None
            or candidate.license_offer_ref not in candidate.evidence_refs
            or candidate.document_inspection_ref not in candidate.evidence_refs
            or value.license_grant_ref not in candidate.evidence_refs
        ):
            raise packet.PacketError("Annotation authorization unresolved or excluded")
        # A generic licensing link alone cannot bind an unrelated PDF to the offer.
        offered_page = (path.parent / offer.path).read_text(encoding="utf-8")
        if candidate.download_url not in offered_page or OGL not in offered_page:
            raise packet.PacketError("Source-bound license offer missing")
        admitted.append(record)
    if not admitted:
        raise packet.PacketError("No authorized annotation candidates")
    selected = tuple(sorted(admitted, key=lambda r: r.document_id))
    return selected, {
        "revision": value.revision,
        "record_sha256": packet.sha(path),
        "record_fingerprint": fingerprint(value.model_dump(mode="json")),
        "pool": len(ids),
        **{
            kind: sum(c.disposition == kind for c in value.candidates)
            for kind in ("admit", "blocked", "excluded")
        },
        "split": value.split,
        "publicly_exposed": value.publicly_exposed,
    }
