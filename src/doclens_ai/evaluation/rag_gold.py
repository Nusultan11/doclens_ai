"""Independent RAG answer Gold. Retrieval labels do not establish reference answers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictStr, model_validator

from doclens_ai.evaluation.gold import load_corpus_manifest_hashes
from doclens_ai.llm.provider import strict_json
from doclens_ai.services.retrieval import SourceLocation

StableID = str


class RagAnchor(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    evidence_id: StableID = Field(pattern=r"^[a-z0-9][a-z0-9._-]{2,127}$")
    document_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    document_format: Literal["pdf", "docx", "xlsx"]
    locator: SourceLocation
    source_start: int = Field(ge=0)
    source_end: int = Field(gt=0)
    verified_quote: StrictStr = Field(min_length=1, max_length=8000)

    @model_validator(mode="after")
    def located(self):
        location = self.locator
        if (
            self.source_start >= self.source_end
            or not self.verified_quote.strip()
            or (self.document_format == "pdf" and location.page_number is None)
            or (self.document_format == "docx" and location.block_index is None)
            or (
                self.document_format == "xlsx"
                and (
                    location.sheet_index is None
                    or (location.cell_coordinate is None and location.table_index is None)
                )
            )
        ):
            raise ValueError("incomplete RAG evidence anchor")
        return self


class RagGoldExample(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    schema_version: Literal["rag-gold-1.0"] = "rag-gold-1.0"
    dataset_revision: Literal["synthetic-rag-gold-v1", "corpus-v1-rag-gold-v1"]
    synthetic_fixture: StrictBool
    question_id: StableID = Field(pattern=r"^[a-z0-9][a-z0-9._-]{2,127}$")
    document_family_id: StableID = Field(pattern=r"^[a-z0-9][a-z0-9._-]{2,127}$")
    split: Literal["dev", "test"]
    language: Literal["en", "ru", "kk"]
    category: Literal["fact", "number", "table", "identifier", "version", "unanswerable"]
    question: StrictStr = Field(min_length=1, max_length=2000)
    answerable: StrictBool
    # Scope of manual negative judgment too; never use these as retrieval filters.
    source_document_sha256: list[str] = Field(min_length=1, max_length=100)
    accepted_answers: list[StrictStr] = Field(max_length=50)
    reference_answer: StrictStr | None = Field(max_length=8000)
    evidence: list[RagAnchor] = Field(max_length=100)
    required_citation_refs: list[StableID] = Field(max_length=100)
    reviewer_status: Literal["fixture", "draft", "reviewed", "adjudicated"]
    reviewer_count: int = Field(ge=0)

    @model_validator(mode="after")
    def label_contract(self):
        import re

        if not self.question.strip() or any(
            not re.fullmatch(r"[0-9a-f]{64}", value) for value in self.source_document_sha256
        ):
            raise ValueError("invalid question or source identity")
        if len(set(self.source_document_sha256)) != len(self.source_document_sha256):
            raise ValueError("duplicate source identities")
        if self.synthetic_fixture:
            if (
                self.dataset_revision != "synthetic-rag-gold-v1"
                or self.reviewer_status != "fixture"
                or self.reviewer_count != 0
            ):
                raise ValueError("synthetic labels must not claim human review")
        elif (
            self.dataset_revision != "corpus-v1-rag-gold-v1"
            or self.reviewer_status not in {"reviewed", "adjudicated"}
            or self.reviewer_count < (2 if self.reviewer_status == "adjudicated" else 1)
        ):
            raise ValueError("real RAG Gold requires reviewed answer labels")
        ids = [item.evidence_id for item in self.evidence]
        if len(set(ids)) != len(ids) or len(set(self.required_citation_refs)) != len(
            self.required_citation_refs
        ):
            raise ValueError("duplicate RAG evidence references")
        if any(item.document_sha256 not in self.source_document_sha256 for item in self.evidence):
            raise ValueError("evidence outside reviewed sources")
        if self.answerable:
            if (
                not self.evidence
                or not self.required_citation_refs
                or not set(self.required_citation_refs) <= set(ids)
                or not (self.accepted_answers or self.reference_answer)
                or self.category == "unanswerable"
                or any(not value.strip() or len(value) > 8000 for value in self.accepted_answers)
                or (self.reference_answer is not None and not self.reference_answer.strip())
            ):
                raise ValueError("unsupported answer label")
        elif (
            self.accepted_answers
            or self.reference_answer is not None
            or self.evidence
            or self.required_citation_refs
            or self.category != "unanswerable"
        ):
            raise ValueError("inconsistent unanswerable label")
        return self


class RagGoldDataset(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    examples: tuple[RagGoldExample, ...]
    fingerprint: str


def validate_rag_gold(examples, *, manifest_path=None):
    examples = tuple(sorted(examples, key=lambda item: item.question_id))
    if not examples or len({e.question_id for e in examples}) != len(examples):
        raise ValueError("RAG Gold must contain unique questions")
    if len({e.dataset_revision for e in examples}) != 1:
        raise ValueError("mixed RAG Gold revisions")
    families, source_families = {}, {}
    for example in examples:
        if families.setdefault(example.document_family_id, example.split) != example.split:
            raise ValueError("RAG document family crosses dev/test")
        for source in example.source_document_sha256:
            if source_families.setdefault(source, example.document_family_id) != (
                example.document_family_id
            ):
                raise ValueError("related RAG source assigned to different families")
    if not examples[0].synthetic_fixture:
        if manifest_path is None or not set(source_families) <= load_corpus_manifest_hashes(
            manifest_path
        ):
            raise ValueError("reviewed real RAG Gold requires approved corpus identities")
    normalized = [e.model_dump(mode="json") for e in examples]
    fingerprint = hashlib.sha256(
        json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return RagGoldDataset(examples=examples, fingerprint=fingerprint)


def load_rag_gold(path: str | Path, *, manifest_path=None):
    # Private files only. Error details must never be printed by the operational CLI.
    path = Path(path)
    if path.stat().st_size > 10_000_000:
        raise ValueError("RAG Gold file too large")
    records = [
        RagGoldExample.model_validate(strict_json(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return validate_rag_gold(records, manifest_path=manifest_path)
