"""Freeze original-only local development reviewer inputs; never accept human Gold.

Only reviewer/ is a handoff. The surrounding selection/audit records are private
coordinator evidence. Existing PDF workbench state is read and pinned, never rebuilt.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from openpyxl.utils.cell import coordinate_to_tuple

from doclens_ai.eda import corpus_v2 as corpus
from doclens_ai.extraction.fidelity_gold import fingerprint
from tools.extraction_quality import office_readiness_oracle as office
from tools.extraction_quality import pdf_table_review_packet as pdf_packet
from tools.extraction_quality import readiness_release as release
from tools.extraction_quality.pdf_review_validation import original_pages
from tools.extraction_quality.pdf_review_workbench import Workbench
from tools.extraction_quality.readiness_evaluator import Observation
from tools.extraction_quality.readiness_io import ROOT, atomic, atomic_bytes, confined
from tools.extraction_quality.readiness_source_checks import resolve_xml

VERSION = "blind-extraction-review-batch-1"
PDF_IDS = ("c1-0033", "c1-0040")
DEFAULT_RELEASE = "evaluation-output/extraction-readiness-continuation-20261023-v2"
PDF_ROOT = "evaluation-output/qg00-annotation-rights-20261021"
RULE = "rights-family-first; DOCX nested/tables/ancillary; XLSX cells<=20000; descending; id tie"
INSTRUCTIONS = """Blind Extraction review — local development only

Use only this reviewer directory, the bound originals and a separate writable
answer directory. Do not edit these frozen inputs. Do not open the coordinator
records, parser captures, machine oracles, historical labels or proposal sidecars.
These exposed development sources are not a fresh sealed test. A reviewer must
disclose their own prior exposure; packet validation cannot authenticate a human.

PDF: resume the already prepared original-only workspace through the coordinator.
Freeze independent annotations before any legacy/proposal comparison. Do not
reinitialize it. Office: inspect originals with macros, links and recalculation
disabled; do not save originals. Physical XML order is not rendered reading order.
No Word pages, display values, roles, spans or semantic links have been inferred.
The locator inventory is an address checklist, not expected extracted content.
Null means unknown, not a reviewed absence. Record literal evidence, physical
locators, language/family decisions, coverage omissions and ambiguities yourself.
Keep formulas and cached results separate; never calculate formulas for this task.

Rights cover new local source annotations of government material only. Preserve
OGL attribution; exclude logos, third-party content and populated personal data.
Permission does not extend to unrelated existing annotations, training or cloud.
All review, independence, permission, viewer and inspection attestations must be
supplied by actual reviewers. This tool validates frozen blank inputs only; it
cannot approve completed answers or export Gold. Use existing strict review/Gold
validators and a separate reviewed revision after genuine review/adjudication.
"""


def family_map(rows: list[dict]) -> dict[str, str]:
    """Reuse connected-family rules, including RAW, normalized and near duplicates."""
    samples = []
    for row in rows:
        samples.append(
            corpus.Sample(
                sample_id=row["id"] if row["id"].startswith("e2-") else "e2-" + row["id"],
                dataset="blind-review",
                release=VERSION,
                revision="1",
                source_record_id=row["id"],
                cohort="pilot",
                disposition="admitted",
                original=corpus.Asset.model_validate(row["source_reference"]),
                rights=corpus.Rights(
                    dataset_license=None,
                    original_license=None,
                    local_evaluation=None,
                    annotation_use=None,
                    redistribution=None,
                    references=(),
                    sensitivity="unknown",
                ),
                languages=("unknown",),
                document_type=row["format"],
                difficulty=(),
                family_id=row["family"],
                related_families=tuple(row.get("related_families") or ()),
                near_duplicate_group=row.get("near_duplicate_group"),
                normalized_text_sha256=row.get("normalized_text_sha256"),
                family_review="unknown",
                split="dev",
                publicly_exposed=True,
            )
        )
    components = corpus.family_components(tuple(samples))
    return {r["id"]: components[s.sample_id] for r, s in zip(rows, samples, strict=True)}


def select(rows: list[dict]) -> dict:
    ids = [r["id"] for r in rows]
    if len(ids) != len(set(ids)) or not set(PDF_IDS) <= set(ids):
        raise ValueError("duplicate or missing source identity")
    components = family_map(rows)
    reserved = {
        components[r["id"]]
        for r in rows
        if r.get("reserved_qa_family") is not False or r["split"] != "dev"
    }
    decisions = []
    for row in sorted(rows, key=lambda r: r["id"]):
        reasons = []
        if components[row["id"]] in reserved:
            reasons.append("reserved_qa_or_non_dev_connected_family")
        if row["rights"].get("local_evaluation") is not True:
            reasons.append("local_evaluation_unresolved")
        if row["rights"].get("new_annotation") is not True:
            reasons.append("annotation_rights_unresolved")
        if row["source_reference"]["sha256"] != row["sha256"]:
            raise ValueError("source SHA binding mismatch")
        decisions.append({"id": row["id"], "component": components[row["id"]], "reasons": reasons})
    by_id = {r["id"]: r for r in rows}
    eligible = {d["id"] for d in decisions if not d["reasons"]}
    if not set(PDF_IDS) <= eligible:
        raise ValueError("existing PDF source is no longer eligible")
    if len({components[key] for key in PDF_IDS}) != len(PDF_IDS):
        raise ValueError("reused PDF families overlap")
    chosen = list(PDF_IDS)
    for fmt in ("docx", "xlsx"):
        candidates = []
        for key in sorted(eligible):
            row = by_id[key]
            if row["format"] != fmt or components[key] in {components[i] for i in chosen}:
                continue
            meta = row.get("metadata") or {}
            if fmt == "docx":
                fields = ("nested_tables", "body_tables", "ancillary_xml_text_characters")
                if not all(type(meta.get(k)) is int and meta[k] >= 0 for k in fields):
                    continue
                score = tuple(meta[k] for k in fields)
            else:
                count = meta.get("stored_xml_cells")
                if type(count) is not int or not 0 < count <= 20_000:
                    continue
                score = (count,)
            candidates.append((tuple(-v for v in score), key))
        if not candidates:
            raise ValueError("no eligible structurally qualified Office original")
        chosen.append(min(candidates)[1])
    for decision in decisions:
        decision["selected"] = decision["id"] in chosen
        if not decision["selected"] and not decision["reasons"]:
            row = by_id[decision["id"]]
            meta = row.get("metadata") or {}
            if row["format"] not in {"docx", "xlsx"}:
                reason = "outside_reused_two_pdf_scope"
            elif decision["component"] in {components[key] for key in chosen}:
                reason = "same_selected_connected_family"
            elif row["format"] == "xlsx" and type(meta.get("stored_xml_cells")) is int:
                reason = (
                    "stored_cell_budget"
                    if not 0 < meta["stored_xml_cells"] <= 20_000
                    else "ranked_below_selected_structural_coverage"
                )
            elif row["format"] == "docx" and all(
                type(meta.get(k)) is int and meta[k] >= 0
                for k in ("nested_tables", "body_tables", "ancillary_xml_text_characters")
            ):
                reason = "ranked_below_selected_structural_coverage"
            else:
                reason = "structural_metadata_unavailable"
            decision["reasons"] = [reason]
    return {
        "version": VERSION,
        "rule": RULE,
        "selected": chosen,
        "population": len(rows),
        "decisions": decisions,
        "family_completeness": "NOT_EVALUATED",
        "split": "dev",
        "independent_gold": False,
    }


def office_locators(path: Path, fmt: str) -> list[dict]:
    """Enumerate physical addresses only; never load or emit an oracle or prediction."""
    locators = []
    with office.Package(path) as package:
        if fmt == "docx":
            queue, seen = [("word/document.xml", "document")], {}
            supported = {
                "header": "hdr",
                "footer": "ftr",
                "footnotes": "footnotes",
                "endnotes": "endnotes",
                "comments": "comments",
            }
            while queue:
                part, kind = queue.pop(0)
                if part in seen:
                    if seen[part] != kind:
                        raise ValueError("conflicting DOCX part type")
                    continue
                seen[part] = kind
                root = package.xml(part)
                if root.tag != f"{{{office.W}}}{kind}":
                    raise ValueError("DOCX part/root mismatch")
                for rel in package.relationships(part).values():
                    name = rel["type"].rsplit("/", 1)[-1]
                    if not rel["external"] and name in supported:
                        queue.append((rel["part"], supported[name]))

                def walk(node, address, part=part, root=root):
                    if address.count("/") > 128:
                        raise ValueError("XML depth bound")
                    if node.tag in {
                        f"{{{office.W}}}{n}"
                        for n in (
                            "p",
                            "tbl",
                            "tr",
                            "tc",
                            "sectPr",
                            "footnote",
                            "endnote",
                            "comment",
                        )
                    }:
                        locator = {"part": part, "xml_path": address, "namespaces": {"w": office.W}}
                        if resolve_xml(root, locator) is not node:
                            raise ValueError("unresolved physical locator")
                        locators.append(locator)
                    counts = Counter()
                    for child in node:
                        counts[child.tag] += 1
                        # Foreign wrappers are intentionally outside this inventory contract.
                        if child.tag.startswith("{" + office.W + "}"):
                            walk(
                                child,
                                address + f"/w:{office.local(child.tag)}[{counts[child.tag]}]",
                            )

                walk(root, f"/w:{kind}[1]")
        elif fmt == "xlsx":
            root = package.xml("xl/workbook.xml")
            if root.tag != f"{{{office.S}}}workbook":
                raise ValueError("workbook root mismatch")
            relationships = package.relationships("xl/workbook.xml")
            sheets, sheet_parts = set(), set()
            for sheet in root.findall(f"{{{office.S}}}sheets/{{{office.S}}}sheet"):
                rel = relationships[sheet.attrib[f"{{{office.R}}}id"]]
                sid = sheet.attrib["sheetId"]
                if (
                    sid in sheets
                    or rel["part"] in sheet_parts
                    or rel["external"]
                    or not rel["type"].endswith("/worksheet")
                ):
                    raise ValueError("unsupported or duplicate worksheet")
                sheets.add(sid)
                sheet_parts.add(rel["part"])
                xml = package.xml(rel["part"])
                if xml.tag != f"{{{office.S}}}worksheet":
                    raise ValueError("worksheet root mismatch")
                for cell in xml.findall(
                    f"{{{office.S}}}sheetData/{{{office.S}}}row/{{{office.S}}}c"
                ):
                    address = cell.attrib["r"]
                    row, column = coordinate_to_tuple(address)
                    if not 1 <= row <= 1048576 or not 1 <= column <= 16384:
                        raise ValueError("cell outside worksheet bounds")
                    if address != address.upper() or str(row) != address.lstrip(
                        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                    ):
                        raise ValueError("noncanonical cell address")
                    locators.append({"part": rel["part"], "sheet_id": sid, "cell": address})
        else:
            raise ValueError("Office format required")
    if not 0 < len(locators) <= 20_000 or len({fingerprint(v) for v in locators}) != len(locators):
        raise ValueError("duplicate, empty or over-budget physical inventory")
    kind = "docx_element" if fmt == "docx" else "xlsx_cell"
    for locator in locators:
        Observation(kind=kind, locator=locator, fields={})
    return locators


def office_sheet(row: dict, path: Path) -> dict:
    return {
        "version": VERSION,
        "source_id": row["id"],
        "source_sha256": row["sha256"],
        "source_size_bytes": row["source_reference"]["size_bytes"],
        "format": row["format"],
        "state": "DRAFT_NOT_REVIEWED",
        "reviewer": None,
        "reviewed_on": None,
        "human_reviewed": False,
        "independent_gold": False,
        "physical_locators": office_locators(path, row["format"]),
        "review_template": {
            "locator": None,
            "literal": None,
            "stored_value": None,
            "formula": None,
            "cached_value": None,
            "display_value": None,
            "row_span": None,
            "column_span": None,
            "role": None,
            "relationships": None,
            "reading_order": None,
            "language": None,
            "family_decision": None,
            "ambiguity": None,
            "original_inspected": None,
            "annotation_authorized": None,
            "permission_reference": None,
            "parser_outputs_seen": None,
            "legacy_seen": None,
            "prior_exposure": None,
            "viewer": None,
            "viewer_version": None,
            "render_settings": None,
        },
        "annotations": [],
        "coverage_complete": None,
    }


def pdf_inputs() -> tuple[dict[str, bytes], dict[str, str]]:
    base = confined(ROOT, PDF_ROOT)
    # Resume validation is read-only: it checks packet hashes, source binding and
    # worksheet/proposal state without initializing, resetting or serving the UI.
    workbench = Workbench(
        ROOT / "docs/eda/corpus_v1_manifest.csv",
        ROOT / "local-corpus",
        ROOT / release.GOLD,
        base / "packet-1",
        base / "workspace",
        resume=True,
        root=ROOT,
        eligibility=ROOT / release.ELIGIBILITY,
    )
    paths, records = workbench.paths, workbench.records.values()
    workspace = base / "workspace/workbench.json"
    state = workbench.state
    if state["exposed"] is not False or set(state["documents"]) != set(PDF_IDS):
        raise ValueError("PDF workspace exposed or wrong population")
    files = {}
    protected = {workspace.relative_to(ROOT).as_posix(): corpus.sha256(workspace)}
    for record in records:
        key = record.document_id
        draft, _, _ = pdf_packet.worksheets(record, original_pages(paths[key]))
        draft["reviewer"].update(
            kind=None, annotation_authorized=None, annotation_permission_reference=None
        )
        draft.update(text_anchors=[], order_pairs=[])
        entry = state["documents"][key]
        if entry != {"draft": draft, "inspected_pages": [], "seal": None, "adjudication": None}:
            raise ValueError("PDF workspace is no longer a pristine blind draft")
        files[f"review/{key}/independent.json"] = encode(draft)
        files[f"sources/{key}.pdf"] = paths[key].read_bytes()
        protected[paths[key].relative_to(ROOT).as_posix()] = record.source_sha256
    return files, protected


def encode(value: dict) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    ).encode()


def attribution(selected: list[str], release_root: Path) -> bytes:
    with (ROOT / "docs/eda/corpus_v1_manifest.csv").open(encoding="utf-8", newline="") as stream:
        sources = {r["document_id"]: r for r in csv.DictReader(stream)}
    decisions = {
        r["source_id"]: r
        for r in corpus.read_json(release_root / "office-rights-v2.json")["decisions"]
    }
    pdf_rights = {
        r["document_id"]: r for r in corpus.read_json(ROOT / release.ELIGIBILITY)["candidates"]
    }
    lines = [
        "Contains public sector information licensed under the Open Government Licence v3.0.",
        "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/",
        "Local source annotations only; excludes logos, third-party material and personal data.",
    ]
    for key in selected:
        if key in sources:
            row = sources[key]
            publisher = pdf_rights.get(key, {}).get("publisher", row["publisher"])
            lines.append(f"{key}: {publisher}; {row['source_page_url']}; {row['download_url']}")
        else:
            row = decisions[key]
            if row["disposition"] != "ADMIT" or row["new_annotation"] is not True:
                raise ValueError("source-specific annotation permission missing")
            lines.append(f"{key}: UK Government; {row['source_page']}; {row['attachment']}")
    return ("\n".join(lines) + "\n").encode("utf-8")


def expected_inputs(release_root: Path) -> tuple[dict, dict[str, bytes], dict[str, str]]:
    release.verify(release_root)
    matrix = corpus.read_json(release_root / "effective-matrix.json")
    rows = matrix["population"]
    selection = select(rows)  # Freeze choice before reading any selected Office content.
    files, protected = pdf_inputs()
    by_id = {r["id"]: r for r in rows}
    for key in selection["selected"]:
        row = by_id[key]
        path = corpus.asset_path(ROOT, corpus.Asset.model_validate(row["source_reference"]))
        if row["format"] != "pdf":
            files[f"sources/{key}.{row['format']}"] = path.read_bytes()
            files[f"review/{key}/independent.json"] = encode(office_sheet(row, path))
        protected[path.relative_to(ROOT).as_posix()] = row["sha256"]
    files["REVIEW.txt"] = INSTRUCTIONS.encode("utf-8")
    # A source-qualified attribution accompanies the reviewer originals, without diagnostic fields.
    files["ATTRIBUTION.txt"] = attribution(selection["selected"], release_root)
    protected[(release_root / "RELEASE.json").relative_to(ROOT).as_posix()] = corpus.sha256(
        release_root / "RELEASE.json"
    )
    protected[Path(__file__).relative_to(ROOT).as_posix()] = corpus.sha256(Path(__file__))
    return selection, files, protected


def prepare(output: Path, release_root: Path) -> dict:
    corpus.no_links(output)
    if output.exists() or not output.resolve().is_relative_to(ROOT / "evaluation-output"):
        raise ValueError("fresh private destination required")
    selection, files, protected = expected_inputs(release_root)
    output.mkdir(parents=True)
    atomic(output / "selection.json", selection)
    for relative, data in files.items():
        atomic_bytes(confined(output / "reviewer", relative), data)
    inventory = {
        p.relative_to(output).as_posix(): corpus.sha256(p) for p in output.rglob("*") if p.is_file()
    }
    manifest = {
        "version": VERSION,
        "release_root": release_root.relative_to(ROOT).as_posix(),
        "artifact_sha256": inventory,
        "protected_sha256": protected,
        "selected": selection["selected"],
        "human_reviews": 0,
        "quality": "NOT_EVALUATED",
        "family_completeness": "NOT_EVALUATED",
    }
    manifest["fingerprint"] = fingerprint(manifest)
    atomic(output / "BATCH.json", manifest)
    return verify(output)


def verify(output: Path) -> dict:
    corpus.no_links(output)
    if not output.resolve().is_relative_to(ROOT / "evaluation-output"):
        raise ValueError("private batch required")
    manifest = corpus.read_json(output / "BATCH.json")
    if (
        set(manifest)
        != {
            "version",
            "release_root",
            "artifact_sha256",
            "protected_sha256",
            "selected",
            "human_reviews",
            "quality",
            "family_completeness",
            "fingerprint",
        }
        or manifest["version"] != VERSION
    ):
        raise ValueError("batch schema or prediction leakage")
    if (
        fingerprint({k: v for k, v in manifest.items() if k != "fingerprint"})
        != manifest["fingerprint"]
    ):
        raise ValueError("batch fingerprint mismatch")
    selection, files, protected = expected_inputs(confined(ROOT, manifest["release_root"]))
    expected = {
        "selection.json": encode(selection),
        **{"reviewer/" + p: b for p, b in files.items()},
    }
    actual = set()
    for path in output.rglob("*"):
        corpus.no_links(path)
        if path.is_file() and path != output / "BATCH.json":
            actual.add(path.relative_to(output).as_posix())
    if actual != set(expected) or set(manifest["artifact_sha256"]) != set(expected):
        raise ValueError("unexpected artifact or prediction leakage")
    if manifest["protected_sha256"] != protected or manifest["selected"] != selection["selected"]:
        raise ValueError("source/workspace binding drift")
    if (
        type(manifest["human_reviews"]) is not int
        or manifest["human_reviews"] != 0
        or manifest["quality"] != "NOT_EVALUATED"
        or manifest["family_completeness"] != "NOT_EVALUATED"
    ):
        raise ValueError("forged review or quality claim")
    for relative, data in expected.items():
        path = confined(output, relative)
        if (
            path.read_bytes() != data
            or corpus.sha256(path) != manifest["artifact_sha256"][relative]
        ):
            raise ValueError("frozen input drift, forged review, leakage or invalid locator")
    for relative, digest in protected.items():
        if corpus.sha256(confined(ROOT, relative)) != digest:
            raise ValueError("protected input drift")
    return {
        "status": "PASS",
        "fingerprint": manifest["fingerprint"],
        "selected": selection["selected"],
        "files": len(expected),
        "human_reviews": 0,
        "quality": "NOT_EVALUATED",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "verify"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--release", type=Path, default=Path(DEFAULT_RELEASE))
    args = parser.parse_args()
    try:
        result = (
            prepare(args.output.resolve(), args.release.resolve())
            if args.mode == "prepare"
            else verify(args.output.resolve())
        )
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"status": "BLOCKED", "error_class": type(error).__name__}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
