"""Separate offline Corpus v2: immutable assets, honest review and family isolation.

The manifest is private when populated. This module never downloads, rewrites
originals or upgrades publisher/automatic annotations into independent Gold.
"""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from doclens_ai.extraction.evidence_v2 import Contract, Digest, Name, Page
from doclens_ai.extraction.fidelity_gold import fingerprint

SampleID = Annotated[str, Field(pattern=r"^e2-[a-z0-9-]{1,80}$")]
Split = Literal["train", "dev", "test", "exposed_test"]
Language = Annotated[str, Field(pattern=r"^(?:[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*|unknown|other)$")]


class Asset(Contract):
    path: str = Field(min_length=1, max_length=500)
    sha256: Digest
    size_bytes: int = Field(gt=0, le=50 * 1024**2)
    format: Literal["pdf", "docx", "xlsx", "png", "json"]

    @model_validator(mode="after")
    def relative_path(self) -> Self:
        parts = PurePosixPath(self.path).parts
        if (
            "\\" in self.path
            or ":" in self.path
            or self.path.startswith("/")
            or any(p in {"..", "."} for p in self.path.split("/"))
            or not parts
            or any(not p for p in self.path.split("/"))
            or PurePosixPath(self.path).suffix.lower() != "." + self.format
        ):
            raise ValueError("relative asset path required")
        return self


class Rights(Contract):
    dataset_license: Name | None
    original_license: Name | None
    local_evaluation: bool | None
    annotation_use: bool | None
    redistribution: bool | None
    references: tuple[Name, ...]
    sensitivity: Literal["public", "private_authorized", "unknown"]


class Review(Contract):
    status: Literal["none", "automatic", "publisher_human", "independent_human", "synthetic"]
    reviewer: Name | None = None
    reviewed_on: Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}$")] | None = None
    original_inspected: bool = False
    independent: bool = False
    attestation: Name | None = None
    adjudication: Name | None = None

    @model_validator(mode="after")
    def provenance(self) -> Self:
        if self.reviewed_on and date.fromisoformat(self.reviewed_on) > date.today():
            raise ValueError("future review rejected")
        if self.status == "independent_human":
            if not all(
                (
                    self.reviewer,
                    self.reviewed_on,
                    self.original_inspected,
                    self.independent,
                    self.attestation,
                )
            ) or re.search(r"\b(codex|chatgpt|assistant|gpt|llm)\b", self.reviewer or "", re.I):
                raise ValueError("independent human attestation required")
        elif self.independent:
            raise ValueError("independence requires independent review")
        return self


class Annotation(Contract):
    asset: Asset
    auxiliary: Asset | None = None
    kind: Literal["doclaynet_coco", "pubtables_pdf", "fintabnet_c", "omnidocbench", "ocr_text"]
    revision: Name
    provenance: Name
    coordinate_system: Literal[
        "image_top_left_xywh", "publisher_pymupdf_top_left", "image_polygon", "none"
    ]
    source_sha256: Digest
    source_page: int | None = Field(default=None, ge=1)
    review: Review

    @model_validator(mode="after")
    def coordinates(self) -> Self:
        expected = {
            "doclaynet_coco": "image_top_left_xywh",
            "pubtables_pdf": "publisher_pymupdf_top_left",
            "fintabnet_c": "publisher_pymupdf_top_left",
            "omnidocbench": "image_polygon",
            "ocr_text": "none",
        }
        if self.coordinate_system != expected[self.kind]:
            raise ValueError("annotation coordinate basis does not match source kind")
        if self.asset.format != "json" or (self.auxiliary and self.auxiliary.format != "json"):
            raise ValueError("annotation JSON payload required")
        return self


class Sample(Contract):
    sample_id: SampleID
    dataset: Name
    release: Name
    revision: Name
    source_record_id: Name
    cohort: Literal["pilot", "legacy_control", "synthetic"]
    disposition: Literal["attempted", "admitted", "rejected", "unavailable", "excluded"]
    reasons: tuple[Name, ...] = ()
    original: Asset | None
    page: Page | None = None
    original_page_number: int | None = Field(default=None, ge=1)
    image: Asset | None = None
    annotation: Annotation | None = None
    rights: Rights
    languages: tuple[Language, ...] = Field(min_length=1)
    document_type: Name
    difficulty: tuple[Name, ...]
    family_id: Name
    related_families: tuple[Name, ...] = ()
    near_duplicate_group: Name | None = None
    normalized_text_sha256: Digest | None = None
    family_review: Literal["unknown", "automatic", "human"]
    family_review_reference: Name | None = None
    split: Split
    publicly_exposed: bool
    unsupported: tuple[Name, ...] = ()

    @model_validator(mode="after")
    def binding(self) -> Self:
        if self.disposition == "admitted" and self.original is None:
            raise ValueError("admitted original required")
        if self.disposition != "admitted" and not self.reasons:
            raise ValueError("disposition reason required")
        if self.page and (not self.original or self.original.format != "pdf"):
            raise ValueError("PDF page identity required")
        if self.annotation and (
            not self.original
            or self.annotation.source_sha256 != self.original.sha256
            or self.annotation.source_page != (self.page.number if self.page else None)
        ):
            raise ValueError("annotation source/page binding rejected")
        if self.publicly_exposed and self.split == "test":
            raise ValueError("exposed material cannot become sealed test")
        if self.cohort != "pilot" and self.split != "dev":
            raise ValueError("controls and synthetic fixtures are development only")
        if self.split == "test" and self.family_review != "human":
            raise ValueError("unreviewed family cannot enter sealed test")
        if self.family_review == "human" and not self.family_review_reference:
            raise ValueError("family review provenance required")
        return self


class Target(Contract):
    dataset: Name
    unit: Literal["pages", "table_pages", "tables", "documents"]
    minimum: int = Field(ge=0)
    maximum: int = Field(ge=0)
    blockers: tuple[Name, ...]

    @model_validator(mode="after")
    def bounds(self) -> Self:
        if self.maximum < self.minimum:
            raise ValueError("target bounds rejected")
        return self


class Corpus(Contract):
    schema_version: Literal["extraction-corpus-2.0"] = "extraction-corpus-2.0"
    revision: Name
    selection_seed: Name
    selection_rule: Literal["sha256-seed-dataset-record-v1", "govuk-office-url-sha256-v1"] = (
        "sha256-seed-dataset-record-v1"
    )
    split_revision: Name
    targets: tuple[Target, ...]
    samples: tuple[Sample, ...] = Field(max_length=2000)

    @model_validator(mode="after")
    def identities(self) -> Self:
        if len({s.sample_id for s in self.samples}) != len(self.samples):
            raise ValueError("duplicate sample identity")
        source_keys = {
            (
                s.dataset,
                s.release,
                s.revision,
                s.source_record_id,
                s.original_page_number,
                s.page.number if s.page else None,
            )
            for s in self.samples
        }
        if len(source_keys) != len(self.samples):
            raise ValueError("duplicate source record/page identity")
        if len({t.dataset for t in self.targets}) != len(self.targets):
            raise ValueError("duplicate target identity")
        return self


def no_links(path: Path) -> None:
    for part in (path.absolute(), *path.absolute().parents):
        if part.is_symlink() or part.is_junction():
            raise ValueError("linked path rejected")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024**2), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def read_json(path: Path, *, max_bytes: int = 20 * 1024**2):
    no_links(path)
    if path.stat().st_size > max_bytes:
        raise ValueError("JSON limit")
    raw = path.read_bytes()
    if len(raw) > max_bytes:
        raise ValueError("JSON limit")
    return json.loads(raw, object_pairs_hook=_unique_pairs)


def load(path: Path) -> Corpus:
    # Validate via JSON to retain strict tuple/float semantics without accepting coercions.
    return Corpus.model_validate_json(json.dumps(read_json(path)))


def asset_path(root: Path, asset: Asset) -> Path:
    no_links(root)
    path = root / asset.path
    no_links(path)
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("asset escapes storage")
    if path.stat().st_size != asset.size_bytes or sha256(path) != asset.sha256:
        raise ValueError("asset bytes mismatch")
    with path.open("rb") as stream:
        signature = stream.read(8)
    if asset.format == "pdf" and not signature.startswith(b"%PDF-"):
        raise ValueError("PDF signature mismatch")
    if asset.format == "png" and signature != b"\x89PNG\r\n\x1a\n":
        raise ValueError("PNG signature mismatch")
    if asset.format in {"docx", "xlsx"}:
        member = "word/document.xml" if asset.format == "docx" else "xl/workbook.xml"
        with zipfile.ZipFile(path) as archive:
            if len(archive.infolist()) > 20_000 or member not in archive.namelist():
                raise ValueError("Office package rejected")
    return path


def selected_ids(ids: list[str], dataset: str, seed: str, limit: int) -> list[str]:
    """Rank metadata identities before content inspection, retaining attempted ranks externally."""
    if len(ids) > 100_000 or len(set(ids)) != len(ids) or not 0 <= limit <= 2000:
        raise ValueError("selection population or budget rejected")
    return sorted(ids, key=lambda i: (fingerprint([seed, dataset, i]), i))[:limit]


def selection_ledger(ids: list[str], dataset: str, seed: str, limit: int) -> list[dict]:
    selected = set(selected_ids(ids, dataset, seed, limit))
    ranked = selected_ids(ids, dataset, seed, min(len(ids), 2000))
    ranks = {key: rank for rank, key in enumerate(ranked, 1)}
    return [
        {
            "source_record_id": key,
            "selection_rank": ranks.get(key),
            "disposition": "attempted" if key in selected else "excluded",
            "reason": "pending_qualification" if key in selected else "outside_frozen_budget",
        }
        for key in sorted(ids)
    ]


def family_components(samples: tuple[Sample, ...]) -> dict[str, str]:
    parent: dict[str, str] = {}

    def find(key):
        parent.setdefault(key, key)
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    for sample in samples:
        keys = ["family:" + sample.family_id]
        keys += ["family:" + f for f in sample.related_families]
        if sample.original:
            keys.append("raw:" + sample.original.sha256)
        if sample.normalized_text_sha256:
            keys.append("normalized:" + sample.normalized_text_sha256)
        if sample.near_duplicate_group:
            keys.append("near:" + sample.near_duplicate_group)
        for key in keys[1:]:
            a, b = find(keys[0]), find(key)
            parent[max(a, b)] = min(a, b)
        find(keys[0])
    return {s.sample_id: find("family:" + s.family_id) for s in samples}


def assign_splits(samples: tuple[Sample, ...], seed: str) -> dict[str, str]:
    """80/10/10 deterministic sampling policy; unknown families stay dev, exposed stay exposed."""
    components = family_components(samples)
    groups = defaultdict(list)
    for sample in samples:
        groups[components[sample.sample_id]].append(sample)
    output = {}
    for component, group in groups.items():
        bucket = int(fingerprint([seed, component])[:8], 16) % 100
        split = "train" if bucket < 80 else "dev" if bucket < 90 else "test"
        if any(s.publicly_exposed for s in group):
            split = "exposed_test"
        if any(s.family_review != "human" or s.cohort != "pilot" for s in group):
            split = "dev"
        output.update({s.sample_id: split for s in group})
    return output


def near_duplicate_pairs(texts: dict[str, str], *, threshold: float = 0.9) -> list[tuple[str, str]]:
    """Diagnostic token-shingle overlap, never proof that translations/families are complete."""
    if len(texts) > 2000 or sum(map(len, texts.values())) > 20_000_000:
        raise ValueError("near-duplicate inspection limit")
    if not 0 < threshold <= 1:
        raise ValueError("invalid diagnostic threshold")
    features, normalized = {}, {}
    for key, text in texts.items():
        normalized[key] = " ".join(text.casefold().split())
        words = re.findall(r"\w+", text.casefold())
        features[key] = {tuple(words[i : i + 5]) for i in range(max(0, len(words) - 4))}
    keys = sorted(features)
    return [
        (left, right)
        for i, left in enumerate(keys)
        for right in keys[i + 1 :]
        if normalized[left]
        and (
            normalized[left] == normalized[right]
            or features[left]
            and features[right]
            and len(features[left] & features[right]) / len(features[left] | features[right])
            >= threshold
        )
    ]


def audit(corpus: Corpus, root: Path) -> dict:
    components = family_components(corpus.samples)
    splits: dict[str, set[str]] = defaultdict(set)
    for sample in corpus.samples:
        # Rejected/known-unavailable samples remain visible, but aren't split members.
        if sample.disposition == "admitted":
            splits[components[sample.sample_id]].add(sample.split)
    leaking = {key for key, values in splits.items() if len(values) > 1}
    rows, critical_integrity = [], False
    for sample in corpus.samples:
        issues = []
        if sample.disposition != "admitted":
            issues.append("not_admitted")
        if sample.original is None:
            issues.append("original_unavailable")
        else:
            for asset in (
                sample.original,
                sample.image,
                sample.annotation.asset if sample.annotation else None,
                sample.annotation.auxiliary if sample.annotation else None,
            ):
                if asset:
                    try:
                        asset_path(root, asset)
                    except (OSError, ValueError, zipfile.BadZipFile):
                        issues.append("asset_integrity_failed")
                        critical_integrity |= (root / asset.path).exists()
            if sample.page and not issues:
                try:
                    from doclens_ai.eda.dataset_adapters_v2 import page_identity

                    if (
                        page_identity(root / sample.original.path, sample.page.number)
                        != sample.page
                    ):
                        issues.append("page_identity_mismatch")
                        critical_integrity = True
                except Exception:  # noqa: BLE001 - untrusted PDF diagnostics remain local
                    issues.append("page_identity_unavailable")
        rights = sample.rights
        if (
            rights.local_evaluation is not True
            or not rights.original_license
            or not rights.references
        ):
            issues.append("source_rights_unresolved")
        if rights.sensitivity == "unknown":
            issues.append("sensitivity_unresolved")
        if sample.annotation and (rights.annotation_use is not True or not rights.dataset_license):
            issues.append("annotation_rights_unresolved")
        if components[sample.sample_id] in leaking:
            issues.append("family_split_leakage")
        rows.append(
            {
                "sample_id": sample.sample_id,
                "disposition": sample.disposition,
                "issues": sorted(set(issues)),
                "native_eligible": not issues and sample.original.format in {"pdf", "docx", "xlsx"},
                "independent_gold": bool(
                    not issues
                    and sample.cohort == "pilot"
                    and sample.annotation
                    and sample.annotation.review.status == "independent_human"
                ),
            }
        )
    return {
        "manifest_fingerprint": fingerprint(corpus.model_dump(mode="json")),
        "sample_attempts": len(rows),
        "dispositions": dict(sorted(Counter(s.disposition for s in corpus.samples).items())),
        "native_eligible": sum(r["native_eligible"] for r in rows),
        "independent_gold": sum(r["independent_gold"] for r in rows),
        "leaking_components": len(leaking),
        "family_completeness": "NOT_EVALUATED"
        if any(s.family_review != "human" for s in corpus.samples)
        else "declared_review_only",
        "rows": rows,
        "qg_00": "FAIL" if leaking or critical_integrity else "NOT_EVALUATED",
    }
