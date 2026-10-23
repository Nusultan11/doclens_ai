"""Strict, offline prediction input and literal Office-oracle comparison.

Source-native oracles are machine references, never independent human Gold.
Missing predictions/references remain in the attempted document denominator.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from collections import Counter, defaultdict
from contextlib import closing
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from doclens_ai.eda import corpus_v2 as corpus
from doclens_ai.extraction.evidence_v2 import valid_bbox
from doclens_ai.extraction.fidelity_gold import fingerprint
from tools.extraction_quality import office_readiness_oracle as oracle
from tools.extraction_quality.readiness_io import ROOT, atomic, cached, confined, private_root


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Observation(Strict):
    kind: Literal[
        "pdf_text",
        "pdf_reading_order",
        "pdf_ocr_transcript",
        "pdf_table",
        "pdf_cell",
        "pdf_relation",
        "pdf_provenance",
        "docx_element",
        "xlsx_cell",
        "xlsx_sheet",
        "xlsx_display",
    ]
    locator: dict[str, JsonValue]
    fields: dict[str, JsonValue]

    @model_validator(mode="after")
    def genuine_locator(self):
        if self.kind.startswith("pdf_"):
            page = self.locator.get("page")
            if type(page) is not int or page < 1:
                raise ValueError("genuine PDF page required")
            if "bbox" in self.locator:
                box = self.locator["bbox"]
                if (
                    not isinstance(box, list)
                    or len(box) != 4
                    or any(type(v) not in (int, float) for v in box)
                    or not valid_bbox(tuple(box))
                ):
                    raise ValueError("invalid PDF region")
            if (
                self.locator.get("coordinate_basis", "pdf_user_space_unrotated")
                != "pdf_user_space_unrotated"
            ):
                raise ValueError("PDF coordinates must be normalized with source geometry")
            for key in ("row_span", "column_span", "row", "column"):
                if key in self.fields and (
                    type(self.fields[key]) is not int
                    or self.fields[key] < (1 if "span" in key else 0)
                ):
                    raise ValueError("invalid PDF topology")
        if self.kind == "docx_element" and (
            not isinstance(self.locator.get("part"), str)
            or not isinstance(self.locator.get("xml_path"), str)
            or "page" in self.locator
        ):
            raise ValueError("DOCX package locator required; inferred pages rejected")
        if self.kind.startswith("xlsx_") and (
            not isinstance(self.locator.get("part"), str)
            or not isinstance(self.locator.get("sheet_id"), str)
            or (self.kind == "xlsx_cell" and not isinstance(self.locator.get("cell"), str))
        ):
            raise ValueError("XLSX sheet/cell locator required")
        for key in ("part",):
            part = self.locator.get(key)
            if isinstance(part, str) and (
                part.startswith(("/", "\\")) or ".." in Path(part).parts or ":" in part
            ):
                raise ValueError("unsafe package locator")
        return self


class Prediction(Strict):
    source_id: str
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: Literal["success", "needs_review", "failed"]
    failure: str | None
    observations: list[Observation] = Field(max_length=200_000)

    @model_validator(mode="after")
    def unique_observations(self):
        keys = [fingerprint([o.kind, o.locator]) for o in self.observations]
        if len(set(keys)) != len(keys):
            raise ValueError("duplicate observation identity")
        if self.status == "failed" and (not self.failure or self.observations):
            raise ValueError("failed prediction requires reason and no partial observations")
        return self


class Predictions(Strict):
    version: Literal["readiness-predictions-1.0"]
    model_identity: str
    predictions: list[Prediction] = Field(max_length=2000)

    @model_validator(mode="after")
    def unique_sources(self):
        if len({p.source_id for p in self.predictions}) != len(self.predictions):
            raise ValueError("duplicate prediction source")
        return self


def validate_oracle(value: dict, source: dict) -> None:
    if (
        value["version"] not in {"office-source-oracle-1.0", oracle.VERSION}
        or value["tier"] != "SOURCE_NATIVE_ORACLE"
        or value["source_id"] != source["id"]
        or value["source_sha256"] != source["sha256"]
        or value["format"] != source["format"]
        or value["human_reviewed"] is not False
        or value["independent_gold"] is not False
        or value["reviewer"] is not None
    ):
        raise ValueError("oracle source/tier/review binding rejected")
    if source["rights"].get("new_annotation") is not True:
        raise ValueError("source-native oracle requires established annotation rights")


def oracle_observations(value: dict) -> list[dict]:
    result = []
    if value["format"] == "docx":
        for part in value["observations"]["parts"].values():
            for ordinal, node in enumerate(part["elements"]):
                fields = {k: v for k, v in node.items() if k != "locator"}
                fields["part_element_ordinal"] = ordinal
                result.append(
                    {"kind": "docx_element", "locator": node["locator"], "fields": fields}
                )
    else:
        for sheet in value["observations"]["sheets"]:
            if sheet.get("state") == "UNSUPPORTED_SHEET_KIND":
                continue
            locator = {
                "part": sheet["relationship"]["part"],
                "sheet_id": sheet["sheet"]["sheetId"],
                "sheet_name": sheet["sheet"]["name"],
            }
            result.append(
                {"kind": "xlsx_sheet", "locator": locator, "fields": {"merges": sheet["merges"]}}
            )
            for cell in sheet["cells"]:
                fields = {
                    k: v
                    for k, v in cell.items()
                    if k
                    not in {
                        "locator",
                        "display_value",
                        "date_interpretation",
                    }
                }
                result.append({"kind": "xlsx_cell", "locator": cell["locator"], "fields": fields})
    return result


def validate_pdf_pages(source: dict, observations: list[Observation]) -> None:
    """Read bounds from the exact original bytes, never optional matrix hints."""
    if not observations:
        return
    import pypdfium2 as pdfium

    asset = corpus.Asset.model_validate(source.get("source_reference", {}))
    if asset.format != "pdf" or asset.sha256 != source["sha256"]:
        raise ValueError("SHA-bound PDF original required for page validation")
    path = confined(ROOT, asset.path)
    try:
        with path.open("rb") as stream:
            raw = stream.read(asset.size_bytes + 1)
    except OSError as error:
        raise ValueError("SHA-bound PDF original unavailable") from error
    if len(raw) != asset.size_bytes or hashlib.sha256(raw).hexdigest() != asset.sha256:
        raise ValueError("PDF original bytes do not match source identity")
    try:
        with pdfium.PdfDocument(raw) as document:
            for observation in observations:
                number = observation.locator["page"]
                if not 1 <= number <= len(document):
                    raise ValueError("prediction page outside original")
                box = observation.locator.get("bbox")
                if box is not None:
                    with closing(document[number - 1]) as page:
                        if not (
                            page.get_rotation() == 0
                            and 0 <= box[0] < box[2] <= page.get_width()
                            and 0 <= box[1] < box[3] <= page.get_height()
                        ):
                            raise ValueError("prediction region outside original page geometry")
    except pdfium.PdfiumError as error:
        raise ValueError("PDF original cannot provide trustworthy page bounds") from error


def compare(population: list[dict], predictions: Predictions, references: dict[str, dict]) -> dict:
    sources = {r["id"]: r for r in population}
    if len(sources) != len(population):
        raise ValueError("duplicate denominator source")
    if not set(references).issubset(sources):
        raise ValueError("orphan oracle reference")
    supplied = {p.source_id: p for p in predictions.predictions}
    for key, prediction in supplied.items():
        if key not in sources or prediction.source_sha256 != sources[key]["sha256"]:
            raise ValueError("prediction source/SHA mismatch")
        if sources[key]["rights"]["local_evaluation"] is not True:
            raise ValueError("unknown evaluation rights")
        if sources[key].get("reserved_qa_family"):
            raise ValueError("reserved QA family is excluded from development comparison")
        if sources[key].get("split", "dev") != "dev":
            raise ValueError("sealed test cannot enter development scorer")
        if any(
            not o.kind.startswith(sources[key]["format"] + "_") for o in prediction.observations
        ):
            raise ValueError("prediction observation format mismatch")
        if sources[key]["format"] == "pdf":
            validate_pdf_pages(sources[key], prediction.observations)
    counts = defaultdict(Counter)
    rows = []
    for source in population:
        key = source["id"]
        prediction = supplied.get(key)
        reference = references.get(key)
        if reference:
            validate_oracle(reference, source)
        expected = oracle_observations(reference) if reference else []
        got = (
            {fingerprint([o.kind, o.locator]): o.fields for o in prediction.observations}
            if prediction
            else {}
        )
        for observation in expected:
            actual = got.get(fingerprint([observation["kind"], observation["locator"]]), {})
            for field, value in observation["fields"].items():
                metric = observation["kind"] + "." + field
                counts[metric]["expected"] += 1
                if field in actual:
                    counts[metric]["observed"] += 1
                    counts[metric]["exact"] += int(fingerprint(value) == fingerprint(actual[field]))
        rows.append(
            {
                "source_id": key,
                "format": source["format"],
                "status": prediction.status if prediction else "NOT_ATTEMPTED",
                "failure": prediction.failure if prediction else None,
                "reference": "SOURCE_NATIVE_ORACLE" if reference else "NOT_EVALUATED",
                "oracle_observations": len(expected),
                "independent_gold": False,
            }
        )
    return {
        "version": "readiness-oracle-scorer-1.0",
        "model_identity": predictions.model_identity,
        "attempted_population": len(rows),
        "prediction_documents": len(supplied),
        "eligible_development_documents": sum(
            r["rights"].get("local_evaluation") is True
            and not r.get("reserved_qa_family")
            and r.get("split", "dev") == "dev"
            for r in population
        ),
        "source_processing_statuses": dict(
            Counter(r.get("status", "NOT_ATTEMPTED") for r in population)
        ),
        "prediction_statuses": dict(Counter(r["status"] for r in rows)),
        "reference_documents": len(references),
        "metrics": dict(counts),
        "rows": rows,
        "quality": "NOT_EVALUATED",
        "QG-00": "NOT_EVALUATED",
        "QG-01": "NOT_EVALUATED",
        "scope": "literal_source_native_comparator_not_independent_quality",
        "unsupported_independent_dimensions": [
            "pdf_text",
            "pdf_reading_order",
            "pdf_ocr_CER_WER",
            "pdf_tables_cells_spans_relations_provenance",
            "xlsx_display",
            "document_semantics",
        ],
    }


def run_office(output: Path) -> dict:
    private_root(output)
    sealed = (output / "RELEASE.json").exists()
    if sealed:
        from tools.extraction_quality.readiness_release import verify_runtime

        verify_runtime(output)
    matrix = output / "effective-matrix.json"
    ledger = corpus.read_json(
        matrix if matrix.exists() else output / "incremental-ledger.json", max_bytes=256 * 1024**2
    )
    rows = {r["id"]: r for r in ledger["population"]}
    if not sealed and (output / "parent-proof.json").exists():
        from tools.extraction_quality.readiness_release import validate_continuation

        validate_continuation(output, ledger)
    decisions_path = output / (
        "office-rights-v2.json"
        if (output / "office-rights-v2.json").exists()
        else "office-rights-v1.json"
    )
    decisions = corpus.read_json(decisions_path)["decisions"]
    seen, timings = set(), []
    for decision in decisions:
        key = decision["source_id"]
        if key in seen or key not in rows:
            raise ValueError("duplicate or unknown Office rights identity")
        seen.add(key)
        source = rows[key]
        if decision["source_sha256"] != source["sha256"] or decision["reviewer"] is not None:
            raise ValueError("rights source or fabricated reviewer")
        if decision["disposition"] != "ADMIT":
            continue
        if (
            decision["new_annotation"] is not True
            or source.get("reserved_qa_family")
            or source["rights"].get("new_annotation") is not True
            or source.get("split", "dev") != "dev"
        ):
            raise ValueError("annotation rights/family exclusion")
        for evidence in [*decision["evidence"], decision["license_capture"]]:
            if corpus.sha256(confined(ROOT, evidence["path"])) != evidence["sha256"]:
                raise ValueError("rights evidence drift")
        ref = source["source_reference"]
        path = confined(ROOT, ref["path"])
        binding = {
            "source_sha256": source["sha256"],
            "rights_sha256": corpus.sha256(decisions_path),
            "oracle_code": corpus.sha256(Path(oracle.__file__)),
        }
        reuse = decision.get("reuse_oracle")
        if reuse:
            target = confined(ROOT, reuse["path"])
            if corpus.sha256(target) != reuse["sha256"]:
                raise ValueError("inherited oracle drift")
            binding["inherited_oracle_sha256"] = reuse["sha256"]
        if decision.get("selected_cells") is not None:
            binding["selected_cells"] = decision["selected_cells"]
        if sealed and not confined(output, "office-oracles/" + key + ".checkpoint.json").exists():
            raise ValueError("cannot create oracle inside immutable release")
        started = time.perf_counter()
        value, hit = cached(
            output,
            "office-oracles/" + key,
            binding,
            lambda p=path, s=source, r=reuse, d=decision: (
                corpus.read_json(confined(ROOT, r["path"]), max_bytes=256 * 1024**2)
                if r
                else oracle.observe(
                    p, s["id"], s["sha256"], s["format"], selected_cells=d.get("selected_cells")
                )
            ),
        )
        validate_oracle(value, source)
        timings.append(
            {"source_id": key, "cache_hit": hit, "seconds": time.perf_counter() - started}
        )
    return {
        "oracles": len(timings),
        "cache_hits": sum(r["cache_hit"] for r in timings),
        "timings": timings,
    }


def manifest_oracles(output: Path, population: list[dict]) -> dict[str, dict]:
    """Select only canonical, source-bound oracles covered by the manifest."""
    manifest = corpus.read_json(output / "RELEASE.json")
    listed = {
        p: digest
        for p, digest in manifest["artifact_sha256"].items()
        if p.startswith("office-oracles/")
    }
    directory = confined(output, "office-oracles")
    actual = {}
    for path in directory.rglob("*"):
        corpus.no_links(path)
        if path.is_file():
            actual[path.relative_to(output).as_posix()] = path
    if set(actual) != set(listed):
        raise ValueError("Office oracle inventory differs from frozen manifest")
    sources = {r["id"]: r for r in population}
    references = {}
    for relative, path in sorted(actual.items()):
        if (
            path.parent != directory
            or path.suffix != ".json"
            or path.name.casefold() == "release.json"
            or corpus.sha256(path) != listed[relative]
        ):
            raise ValueError("unexpected, misnamed or unhashed Office oracle")
        if path.name.endswith(".checkpoint.json"):
            sibling = relative.removesuffix(".checkpoint.json") + ".json"
            if sibling not in actual:
                raise ValueError("orphan Office oracle checkpoint")
            continue
        value = corpus.read_json(path, max_bytes=256 * 1024**2)
        if not isinstance(value, dict):
            raise ValueError("Office oracle object required")
        key = value.get("source_id")
        if (
            not isinstance(key, str)
            or key not in sources
            or key in references
            or path.name != key + ".json"
            or sources[key]["format"] not in {"docx", "xlsx"}
            or sources[key]["rights"].get("local_evaluation") is not True
            or sources[key].get("reserved_qa_family")
            or sources[key].get("split", "dev") != "dev"
            or corpus.sha256(path) != listed[relative]
        ):
            raise ValueError("duplicate, misnamed or source-unbound Office oracle")
        validate_oracle(value, sources[key])
        references[key] = value
    return references


def score(output: Path, prediction_path: Path) -> dict:
    private_root(output)
    from tools.extraction_quality.readiness_release import verify_runtime

    verify_runtime(output)
    matrix = corpus.read_json(output / "effective-matrix.json", max_bytes=256 * 1024**2)
    predictions = Predictions.model_validate(
        corpus.read_json(prediction_path, max_bytes=64 * 1024**2)
    )
    references = manifest_oracles(output, matrix["population"])
    result = compare(matrix["population"], predictions, references)
    pdf_path = output / "pdf-references.json"
    if pdf_path.exists():
        from tools.extraction_quality.readiness_pdf_metrics import compare as compare_pdf
        from tools.extraction_quality.readiness_pdf_metrics import validate_reference

        source_rows = {r["id"]: r for r in matrix["population"]}
        supplied = {p.source_id: p for p in predictions.predictions}
        result["pdf_dimensions"] = {}
        for reference in corpus.read_json(pdf_path, max_bytes=64 * 1024**2)["sources"]:
            key = reference["source_id"]
            if key in result["pdf_dimensions"]:
                raise ValueError("duplicate PDF source reference")
            validate_reference(reference, source_rows[key])
            result["pdf_dimensions"][key] = compare_pdf(supplied.get(key), reference)
        result["pdf_reference_documents"] = len(result["pdf_dimensions"])
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("office", "score"))
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--predictions", type=Path)
    parser.add_argument("--metrics", type=Path)
    args = parser.parse_args()
    if args.mode == "office":
        result = run_office(args.release)
    else:
        if args.predictions is None or args.metrics is None:
            parser.error("score requires --predictions and --metrics")
        private_root(args.metrics.parent)
        if args.metrics.exists() or args.metrics.resolve().is_relative_to(args.release.resolve()):
            raise ValueError("fresh metrics outside immutable release required")
        result = score(args.release, args.predictions)
        atomic(args.metrics, result)
    print(
        json.dumps(
            {
                k: v
                for k, v in result.items()
                if k not in {"rows", "metrics", "timings", "pdf_dimensions"}
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
