from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from doclens_ai.extraction.models import DocumentFormat

GOLD_SCHEMA_VERSION = "1.0"
CORPUS_V1_DATASET_REVISION = "corpus-v1-retrieval-gold-v1"
SYNTHETIC_DATASET_REVISION = "synthetic-retrieval-gold-v1"
KNOWN_DATASET_REVISIONS = frozenset({CORPUS_V1_DATASET_REVISION, SYNTHETIC_DATASET_REVISION})

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_STABLE_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{2,127}$")
_CELL_RANGE = re.compile(r"^[A-Z]{1,3}[1-9][0-9]{0,6}(?::[A-Z]{1,3}[1-9][0-9]{0,6})?$")


class GoldValidationError(ValueError):
    """Raised when a Gold dataset cannot be safely evaluated."""


class Language(StrEnum):
    RU = "ru"
    KK = "kk"
    EN = "en"


class QuestionCategory(StrEnum):
    FACT = "fact"
    NUMBER = "number"
    TABLE = "table"
    IDENTIFIER = "identifier"
    VERSION = "version"
    UNANSWERABLE = "unanswerable"


class DatasetSplit(StrEnum):
    DEV = "dev"
    TEST = "test"


class ReviewStatus(StrEnum):
    DRAFT = "draft"
    REVIEWED = "reviewed"
    ADJUDICATED = "adjudicated"


class AdjudicationState(StrEnum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    RESOLVED = "resolved"


@dataclass(frozen=True, slots=True)
class EvidenceLocator:
    page_number: int | None = None
    block_index: int | None = None
    sheet_index: int | None = None
    sheet_name: str | None = None
    cell_coordinate: str | None = None
    table_index: int | None = None
    row_index: int | None = None
    column_index: int | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            name: value
            for name, value in (
                ("page_number", self.page_number),
                ("block_index", self.block_index),
                ("sheet_index", self.sheet_index),
                ("sheet_name", self.sheet_name),
                ("cell_coordinate", self.cell_coordinate),
                ("table_index", self.table_index),
                ("row_index", self.row_index),
                ("column_index", self.column_index),
            )
            if value is not None
        }


@dataclass(frozen=True, slots=True)
class EvidenceAnchor:
    evidence_id: str
    document_sha256: str
    document_format: DocumentFormat
    locator: EvidenceLocator
    source_start: int | None = None
    source_end: int | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "evidence_id": self.evidence_id,
            "document_sha256": self.document_sha256,
            "document_format": self.document_format.value,
            "locator": self.locator.to_dict(),
        }
        if self.source_start is not None:
            payload["source_start"] = self.source_start
            payload["source_end"] = self.source_end
        return payload


@dataclass(frozen=True, slots=True)
class GoldExample:
    schema_version: str
    question_id: str
    dataset_revision: str
    synthetic_fixture: bool
    document_family_id: str
    language: Language
    question: str
    category: QuestionCategory
    answerable: bool
    source_document_sha256: str
    evidence: tuple[EvidenceAnchor, ...]
    split: DatasetSplit
    review_status: ReviewStatus
    reviewer_count: int
    adjudication_state: AdjudicationState

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "question_id": self.question_id,
            "dataset_revision": self.dataset_revision,
            "synthetic_fixture": self.synthetic_fixture,
            "document_family_id": self.document_family_id,
            "language": self.language.value,
            "question": self.question,
            "category": self.category.value,
            "answerable": self.answerable,
            "source_document_sha256": self.source_document_sha256,
            "evidence": [anchor.to_dict() for anchor in self.evidence],
            "split": self.split.value,
            "review_status": self.review_status.value,
            "reviewer_count": self.reviewer_count,
            "adjudication_state": self.adjudication_state.value,
        }


@dataclass(frozen=True, slots=True)
class GoldDataset:
    examples: tuple[GoldExample, ...]
    dataset_revision: str
    fingerprint: str

    def by_question_id(self) -> dict[str, GoldExample]:
        return {example.question_id: example for example in self.examples}


def load_gold_jsonl(
    path: str | Path,
    *,
    corpus_manifest_path: str | Path | None = None,
) -> GoldDataset:
    """Load and strictly validate one immutable Gold dataset snapshot."""

    records = _load_jsonl(path, kind="Gold")
    examples = tuple(
        _parse_example(record, line_number=index) for index, record in enumerate(records, start=1)
    )
    return validate_gold_dataset(
        examples,
        corpus_manifest_path=corpus_manifest_path,
    )


def validate_gold_dataset(
    examples: tuple[GoldExample, ...],
    *,
    corpus_manifest_path: str | Path | None = None,
) -> GoldDataset:
    if not examples:
        raise GoldValidationError("Gold dataset must contain at least one example")
    question_ids: set[str] = set()
    revisions: set[str] = set()
    family_splits: dict[str, DatasetSplit] = {}
    source_families: dict[str, str] = {}
    corpus_hashes: set[str] = set()
    for example in examples:
        if example.question_id in question_ids:
            raise GoldValidationError(f"duplicate question_id: {example.question_id}")
        question_ids.add(example.question_id)
        revisions.add(example.dataset_revision)
        previous_split = family_splits.setdefault(
            example.document_family_id,
            example.split,
        )
        if previous_split != example.split:
            raise GoldValidationError(
                f"document family crosses dev/test: {example.document_family_id}"
            )
        previous_family = source_families.setdefault(
            example.source_document_sha256, example.document_family_id
        )
        if previous_family != example.document_family_id:
            raise GoldValidationError("source SHA-256 is assigned to multiple document families")
        if example.dataset_revision == CORPUS_V1_DATASET_REVISION:
            corpus_hashes.add(example.source_document_sha256)
            corpus_hashes.update(anchor.document_sha256 for anchor in example.evidence)
    if len(revisions) != 1:
        raise GoldValidationError("Gold dataset must contain exactly one dataset revision")
    revision = next(iter(revisions))
    if revision not in KNOWN_DATASET_REVISIONS:
        raise GoldValidationError(f"unknown dataset revision: {revision}")
    if revision == CORPUS_V1_DATASET_REVISION:
        if corpus_manifest_path is None:
            raise GoldValidationError("Corpus v1 Gold requires its committed manifest")
        validate_corpus_manifest_references(corpus_hashes, corpus_manifest_path)

    normalized = [
        example.to_dict() for example in sorted(examples, key=lambda item: item.question_id)
    ]
    fingerprint = hashlib.sha256(
        json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return GoldDataset(
        examples=tuple(sorted(examples, key=lambda item: item.question_id)),
        dataset_revision=revision,
        fingerprint=fingerprint,
    )


def validate_corpus_manifest_references(
    document_hashes: set[str],
    manifest_path: str | Path,
) -> None:
    manifest_hashes = load_corpus_manifest_hashes(manifest_path)
    missing = sorted(document_hashes - manifest_hashes)
    if missing:
        raise GoldValidationError(
            "Gold references SHA-256 values absent from the Corpus v1 manifest: "
            + ", ".join(missing)
        )


def load_corpus_manifest_hashes(path: str | Path) -> set[str]:
    manifest_path = Path(path)
    try:
        with manifest_path.open("r", encoding="utf-8", newline="") as source:
            rows = list(csv.DictReader(source))
    except (OSError, UnicodeError) as exc:
        raise GoldValidationError("unable to read Corpus v1 manifest") from exc
    if not rows or "sha256" not in rows[0]:
        raise GoldValidationError("Corpus v1 manifest is empty or missing sha256")
    hashes: set[str] = set()
    for row in rows:
        value = row.get("sha256", "")
        if not isinstance(value, str) or not _SHA256.fullmatch(value):
            raise GoldValidationError("Corpus v1 manifest contains malformed SHA-256")
        if value in hashes:
            raise GoldValidationError("Corpus v1 manifest contains duplicate SHA-256")
        hashes.add(value)
    return hashes


def _parse_example(
    value: object,
    *,
    line_number: int,
) -> GoldExample:
    record = _mapping(value, context=f"Gold line {line_number}")
    _require_exact_keys(
        record,
        required={
            "schema_version",
            "question_id",
            "dataset_revision",
            "synthetic_fixture",
            "document_family_id",
            "language",
            "question",
            "category",
            "answerable",
            "source_document_sha256",
            "evidence",
            "split",
            "review_status",
            "reviewer_count",
            "adjudication_state",
        },
        context=f"Gold line {line_number}",
    )
    schema_version = _string(record["schema_version"], "schema_version")
    if schema_version != GOLD_SCHEMA_VERSION:
        raise GoldValidationError(f"unsupported Gold schema_version: {schema_version}")
    question_id = _stable_id(record["question_id"], "question_id")
    dataset_revision = _string(record["dataset_revision"], "dataset_revision")
    if dataset_revision not in KNOWN_DATASET_REVISIONS:
        raise GoldValidationError(f"unknown dataset revision: {dataset_revision}")
    synthetic_fixture = _boolean(record["synthetic_fixture"], "synthetic_fixture")
    if (dataset_revision == SYNTHETIC_DATASET_REVISION) is not synthetic_fixture:
        raise GoldValidationError("synthetic_fixture contradicts dataset_revision")
    document_family_id = _stable_id(record["document_family_id"], "document_family_id")
    language = _enum(Language, record["language"], "language")
    question = _string(record["question"], "question", max_length=10_000)
    category = _enum(QuestionCategory, record["category"], "category")
    answerable = _boolean(record["answerable"], "answerable")
    source_sha256 = _sha256(record["source_document_sha256"], "source_document_sha256")
    evidence_value = record["evidence"]
    if not isinstance(evidence_value, list):
        raise GoldValidationError("evidence must be a list")
    evidence = tuple(
        _parse_anchor(item, context=f"{question_id} evidence {index}")
        for index, item in enumerate(evidence_value, start=1)
    )
    if answerable and not evidence:
        raise GoldValidationError("answerable examples require positive evidence")
    if not answerable and evidence:
        raise GoldValidationError("unanswerable examples must not contain positive evidence")
    if (category is QuestionCategory.UNANSWERABLE) is not (not answerable):
        raise GoldValidationError("unanswerable category contradicts answerable flag")
    if any(anchor.document_sha256 != source_sha256 for anchor in evidence):
        raise GoldValidationError("evidence must reference the example source document SHA-256")
    evidence_ids = [anchor.evidence_id for anchor in evidence]
    if len(evidence_ids) != len(set(evidence_ids)):
        raise GoldValidationError("evidence_id values must be unique within a question")
    evidence_locations = [
        json.dumps(
            {key: value for key, value in anchor.to_dict().items() if key != "evidence_id"},
            sort_keys=True,
        )
        for anchor in evidence
    ]
    if len(evidence_locations) != len(set(evidence_locations)):
        raise GoldValidationError("duplicate Gold evidence locations")

    split = _enum(DatasetSplit, record["split"], "split")
    review_status = _enum(ReviewStatus, record["review_status"], "review_status")
    reviewer_count = _nonnegative_int(record["reviewer_count"], "reviewer_count")
    adjudication_state = _enum(
        AdjudicationState,
        record["adjudication_state"],
        "adjudication_state",
    )
    _validate_review_state(
        review_status,
        reviewer_count,
        adjudication_state,
    )
    return GoldExample(
        schema_version=schema_version,
        question_id=question_id,
        dataset_revision=dataset_revision,
        synthetic_fixture=synthetic_fixture,
        document_family_id=document_family_id,
        language=language,
        question=question,
        category=category,
        answerable=answerable,
        source_document_sha256=source_sha256,
        evidence=evidence,
        split=split,
        review_status=review_status,
        reviewer_count=reviewer_count,
        adjudication_state=adjudication_state,
    )


def _parse_anchor(value: object, *, context: str) -> EvidenceAnchor:
    record = _mapping(value, context=context)
    _require_exact_keys(
        record,
        required={"evidence_id", "document_sha256", "document_format", "locator"},
        optional={"source_start", "source_end"},
        context=context,
    )
    evidence_id = _stable_id(record["evidence_id"], "evidence_id")
    document_sha256 = _sha256(record["document_sha256"], "document_sha256")
    document_format = _enum(DocumentFormat, record["document_format"], "document_format")
    locator = _parse_locator(record["locator"], document_format=document_format)
    source_start = record.get("source_start")
    source_end = record.get("source_end")
    if (source_start is None) is not (source_end is None):
        raise GoldValidationError("source_start and source_end must be provided together")
    if source_start is not None:
        source_start = _nonnegative_int(source_start, "source_start")
        source_end = _nonnegative_int(source_end, "source_end")
        if source_end <= source_start:
            raise GoldValidationError("source_end must be greater than source_start")
    return EvidenceAnchor(
        evidence_id=evidence_id,
        document_sha256=document_sha256,
        document_format=document_format,
        locator=locator,
        source_start=source_start,
        source_end=source_end,
    )


def _parse_locator(value: object, *, document_format: DocumentFormat) -> EvidenceLocator:
    record = _mapping(value, context="locator")
    allowed = {
        "page_number",
        "block_index",
        "sheet_index",
        "sheet_name",
        "cell_coordinate",
        "table_index",
        "row_index",
        "column_index",
    }
    _require_exact_keys(record, required=set(), optional=allowed, context="locator")
    parsed: dict[str, object] = {}
    for field in allowed - {"sheet_name", "cell_coordinate"}:
        if field in record:
            minimum = 1 if field == "page_number" else 0
            parsed[field] = _int_at_least(record[field], field, minimum)
    if "sheet_name" in record:
        parsed["sheet_name"] = _string(record["sheet_name"], "sheet_name", max_length=255)
    if "cell_coordinate" in record:
        coordinate = _string(record["cell_coordinate"], "cell_coordinate")
        if _CELL_RANGE.fullmatch(coordinate) is None:
            raise GoldValidationError("cell_coordinate must be an A1 cell or range")
        parsed["cell_coordinate"] = coordinate
    locator = EvidenceLocator(**parsed)
    if document_format is DocumentFormat.PDF:
        if locator.page_number is None or any(
            value is not None
            for value in (
                locator.sheet_index,
                locator.sheet_name,
                locator.cell_coordinate,
                locator.table_index,
                locator.row_index,
                locator.column_index,
            )
        ):
            raise GoldValidationError("PDF evidence requires a page locator")
    elif document_format is DocumentFormat.DOCX:
        if locator.block_index is None or any(
            value is not None
            for value in (
                locator.page_number,
                locator.sheet_index,
                locator.sheet_name,
                locator.cell_coordinate,
            )
        ):
            raise GoldValidationError("DOCX evidence requires a block locator")
        if locator.table_index is None and any(
            value is not None for value in (locator.row_index, locator.column_index)
        ):
            raise GoldValidationError("DOCX row/column locators require table_index")
    elif (
        locator.sheet_index is None
        or (locator.cell_coordinate is None and locator.table_index is None)
        or locator.page_number is not None
        or locator.block_index is not None
    ):
        raise GoldValidationError("XLSX evidence requires a sheet and cell/table locator")
    return locator


def _validate_review_state(
    status: ReviewStatus,
    reviewer_count: int,
    adjudication_state: AdjudicationState,
) -> None:
    valid = (
        (
            status is ReviewStatus.DRAFT
            and adjudication_state in {AdjudicationState.NOT_REQUIRED, AdjudicationState.PENDING}
        )
        or (
            status is ReviewStatus.REVIEWED
            and reviewer_count >= 1
            and adjudication_state is AdjudicationState.NOT_REQUIRED
        )
        or (
            status is ReviewStatus.ADJUDICATED
            and reviewer_count >= 2
            and adjudication_state is AdjudicationState.RESOLVED
        )
    )
    if not valid:
        raise GoldValidationError("reviewer/adjudication state is contradictory")
    if status is ReviewStatus.DRAFT:
        raise GoldValidationError("draft examples cannot be presented as Gold")


def _load_jsonl(path: str | Path, *, kind: str) -> list[object]:
    source_path = Path(path)
    try:
        lines = source_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise GoldValidationError(f"unable to read {kind} JSONL") from exc
    records: list[object] = []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line, object_pairs_hook=_unique_json_fields))
        except json.JSONDecodeError as exc:
            raise GoldValidationError(f"malformed {kind} JSON on line {line_number}") from exc
    if not records:
        raise GoldValidationError(f"{kind} JSONL is empty")
    return records


def _unique_json_fields(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise GoldValidationError("duplicate JSON field")
        result[key] = value
    return result


def _mapping(value: object, *, context: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise GoldValidationError(f"{context} must be a JSON object")
    return value


def _require_exact_keys(
    record: dict[str, Any],
    *,
    required: set[str],
    context: str,
    optional: set[str] | None = None,
) -> None:
    optional = optional or set()
    missing = sorted(required - record.keys())
    unknown = sorted(record.keys() - required - optional)
    if missing:
        raise GoldValidationError(f"{context} missing fields: {', '.join(missing)}")
    if unknown:
        raise GoldValidationError(f"{context} has unknown fields: {', '.join(unknown)}")


def _string(value: object, field: str, *, max_length: int = 1024) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > max_length:
        raise GoldValidationError(f"{field} must be a nonblank bounded string")
    return value


def _stable_id(value: object, field: str) -> str:
    parsed = _string(value, field, max_length=128)
    if _STABLE_ID.fullmatch(parsed) is None:
        raise GoldValidationError(f"{field} is not a stable identifier")
    return parsed


def _sha256(value: object, field: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise GoldValidationError(f"{field} must be a lowercase SHA-256")
    return value


def _boolean(value: object, field: str) -> bool:
    if not isinstance(value, bool):
        raise GoldValidationError(f"{field} must be a boolean")
    return value


def _nonnegative_int(value: object, field: str) -> int:
    return _int_at_least(value, field, 0)


def _int_at_least(value: object, field: str, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise GoldValidationError(f"{field} must be an integer >= {minimum}")
    return value


def _enum(enum_type: type[StrEnum], value: object, field: str) -> Any:
    if not isinstance(value, str):
        raise GoldValidationError(f"{field} must be a string")
    try:
        return enum_type(value)
    except ValueError as exc:
        raise GoldValidationError(f"unsupported {field}: {value}") from exc
