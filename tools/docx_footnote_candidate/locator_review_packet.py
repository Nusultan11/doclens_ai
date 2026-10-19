"""Local-only draft preparation. Neither a Gold editor nor a fidelity scorer."""

from __future__ import annotations

import argparse
import csv
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import time
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from doclens_ai.extraction.docx_footnote_candidate import FootnoteLimits, extract_footnotes
from doclens_ai.extraction.fidelity_eval import _read_sources, normalize, verify_corpus
from doclens_ai.extraction.fidelity_gold import FidelityRecord, fingerprint, load_gold
from doclens_ai.extraction.parsers import ExtractionLimits
from tools.docx_footnote_candidate import benchmark as existing

ROOT = Path(__file__).resolve().parents[2]
VERSION = "docx-footnote-locator-review-draft-v1"
ADDRESS_VERSION = "docx-footnote-ooxml-address-v1"
MAX_HINTS = 10_000
BUILD_SECONDS = 15.0
INPUT_CODE = (
    "src/doclens_ai/extraction/docx_footnote_candidate.py",
    "src/doclens_ai/extraction/fidelity_gold.py",
    "src/doclens_ai/extraction/fidelity_eval.py",
    "src/doclens_ai/extraction/parsers.py",
    "src/doclens_ai/extraction/models.py",
    "tools/docx_footnote_candidate/benchmark.py",
)


class PacketError(ValueError):
    """Only fixed diagnostics may leave this boundary."""


def require_unoptimized() -> None:
    """Inherited OOXML address checks rely on assertions being executed."""
    if sys.flags.optimize != 0:
        raise PacketError("Optimized Python execution rejected")


def no_links(path: Path) -> None:
    if any(p.is_symlink() or p.is_junction() for p in (path, *path.parents)):
        raise PacketError("Linked input/output rejected")


def fresh_output(path: Path, corpus: Path, *, root: Path = ROOT) -> None:
    """Require owned, fresh, Git-ignored local storage outside immutable RAW."""
    no_links(path)
    resolved = path.resolve()
    if (
        path.exists()
        or resolved.is_relative_to(corpus.resolve())
        or not any(
            resolved.is_relative_to(root / name) and resolved != root / name
            for name in ("local-evaluation", "evaluation-output")
        )
        or subprocess.run(
            ["git", "check-ignore", "-q", str(resolved)],
            cwd=root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode
    ):
        raise PacketError("Fresh ignored output required")


def write_json(path: Path, value: dict) -> None:
    """Exclusive destination; publish bounded JSON atomically without overwriting."""
    temporary = path.with_suffix(".partial")
    no_links(path)
    if path.exists() or temporary.exists():
        raise PacketError("Existing output rejected")
    created = False
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as stream:
            created = True
            count = 1  # Final LF also belongs to the byte budget.
            for chunk in json.JSONEncoder(sort_keys=True, indent=2).iterencode(value):
                count += len(chunk.encode("utf-8"))
                if count > existing.GUARDS["max_capture_bytes"]:
                    raise PacketError("Output limit")
                stream.write(chunk)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if created:
            temporary.unlink(missing_ok=True)


def preflight(
    manifest: Path, corpus: Path, gold: Path, *, allow_synthetic: bool = False
) -> tuple[dict, dict[str, Path], tuple[FidelityRecord, ...]]:
    for path in (manifest, corpus, gold):
        no_links(path)
    if manifest.stat().st_size > 1024**2:
        raise PacketError("Manifest limit")
    sources = _read_sources(manifest)
    paths = verify_corpus(corpus, sources, ExtractionLimits())
    for path in corpus.rglob("*"):
        no_links(path)
    records = load_gold(gold, sources, allow_synthetic=allow_synthetic)
    with manifest.open(encoding="utf-8", newline="") as stream:
        if any(
            not row.get(key)
            for row in csv.DictReader(stream)
            for key in ("license", "license_url", "license_basis_url")
        ):
            raise PacketError("Missing source rights metadata")
    selected = tuple(r for r in records if r.document_format == "docx")
    if not selected:
        raise PacketError("No reviewed DOCX population")
    identity = {
        "manifest_sha256": existing.sha(manifest),
        "source_map_fingerprint": fingerprint(sources),
        "gold_sha256": existing.sha(gold),
        "gold_normalized_fingerprint": fingerprint([r.model_dump(mode="json") for r in records]),
        "manifest_documents": len(sources),
        "reviewed_records": len(records),
        "reviewed_docx": len(selected),
        "footnote_labels": sum(a.source.region == "footnote" for r in selected for a in r.anchors),
    }
    return identity, paths, selected


def make_packet(record: FidelityRecord, captured: dict | None) -> dict:
    """Gold is used only after extraction, for a private, unadjudicated draft."""
    if record.document_format != "docx":
        raise PacketError("DOCX record required")
    ancillary = captured["ancillary"] if captured is not None else None
    if ancillary is not None:
        if ancillary["status"] not in {"success", "needs_review", "failed"}:
            raise PacketError("Candidate status rejected")
        if (
            ancillary["source_sha256"] not in (None, record.source_sha256)
            or ancillary["source_size_bytes"] not in (None, record.source_size_bytes)
            or (
                ancillary["status"] != "failed"
                and (ancillary["source_sha256"] is None or ancillary["source_size_bytes"] is None)
            )
        ):
            raise PacketError("Candidate source mismatch")
    observable = ancillary is not None and ancillary["status"] != "failed"
    started = time.monotonic()
    remaining_hints = MAX_HINTS
    reviews = []
    for anchor in record.anchors:
        if anchor.source.region != "footnote":
            continue
        hints, occurrences, truncated = [], 0, False
        needle = normalize(anchor.text)
        if observable:
            for note in ancillary["notes"]:
                for paragraph in note["paragraphs"]:
                    if time.monotonic() - started >= BUILD_SECONDS:
                        raise PacketError("Draft preparation timeout")
                    count = normalize(paragraph["text"]).count(needle)
                    if not count:
                        continue
                    occurrences += count
                    if remaining_hints == 0:
                        truncated = True
                        continue
                    remaining_hints -= 1
                    hints.append(
                        {
                            "part_uri": note["part_uri"],
                            "note_id": note["note_id"],
                            "note_element_index": note["note_element_index"],
                            "paragraph_child_index": paragraph["child_index"],
                            "occurrences": count,
                            "complete": note["complete"] and paragraph["complete"],
                            "reference_ordinals": note["reference_ordinals"],
                        }
                    )
        diagnostic = (
            "UNKNOWN"
            if not observable or truncated
            else "NO_TEXT_MATCH"
            if occurrences == 0
            else "SINGLE_TEXT_CANDIDATE"
            if occurrences == 1
            else "AMBIGUOUS_TEXT_MATCH"
        )
        reviews.append(
            {
                "anchor_id": anchor.anchor_id,
                "gold_text": anchor.text,
                "legacy_gold_locator": anchor.source.model_dump(mode="json"),
                "legacy_occurrence": anchor.occurrence,
                "text_diagnostic": diagnostic,
                "text_hints": hints,
                "text_hints_truncated": truncated,
                "mapping": {
                    "state": "UNRESOLVED",
                    "selected_note_identity": None,
                    "selected_paragraph_child_index": None,
                    "selected_reference_ordinals": None,
                    "reviewer_pseudonym": None,
                    "reviewed_on": None,
                    "original_document_evidence": None,
                    "ambiguity_notes": None,
                },
            }
        )
    return {
        "schema_version": VERSION,
        "locator_identity_version": ADDRESS_VERSION,
        "document_id": record.document_id,
        "source": {
            "sha256": record.source_sha256,
            "size_bytes": record.source_size_bytes,
            "format": record.document_format,
        },
        "review_status": "draft",
        "reviewed_locator_fidelity": "NOT_EVALUATED",
        "production_authorization": False,
        "candidate_status": ancillary["status"] if ancillary is not None else "failed",
        "candidate_observation": ancillary,
        "ooxml_address_checks": captured["address_checks"] if captured is not None else None,
        "anchor_reviews": reviews,
    }


def aggregate(packets: list[dict]) -> dict:
    """Only opaque IDs, bounded counters and fixed states leave private packets."""
    documents = []
    for packet in packets:
        observation = packet["candidate_observation"]
        known = observation is not None and packet["candidate_status"] != "failed"
        reviews = packet["anchor_reviews"]
        documents.append(
            {
                "document_id": packet["document_id"],
                "candidate_status": packet["candidate_status"],
                "observed_notes": len(observation["notes"]) if known else None,
                "observed_references": len(observation["references"]) if known else None,
                "observed_paragraphs": (
                    sum(len(n["paragraphs"]) for n in observation["notes"]) if known else None
                ),
                "incomplete_notes": (
                    sum(not n["complete"] for n in observation["notes"]) if known else None
                ),
                "issue_count": len(observation["issues"]) if observation is not None else None,
                "footnote_labels": len(reviews),
                "unresolved_mappings": len(reviews),
                "text_diagnostics": dict(
                    sorted(Counter(r["text_diagnostic"] for r in reviews).items())
                ),
            }
        )
    return {
        "schema_version": VERSION,
        "attempted_documents": len(packets),
        "candidate_status_counts": dict(
            sorted(Counter(p["candidate_status"] for p in packets).items())
        ),
        "footnote_labels": sum(d["footnote_labels"] for d in documents),
        "unresolved_mappings": sum(d["unresolved_mappings"] for d in documents),
        "reviewed_mappings": 0,
        "reviewed_locator_fidelity": "NOT_EVALUATED",
        "production_authorization": False,
        "documents": documents,
    }


def worker(source: Path, output: Path, expected_sha: str, expected_size: int) -> int:
    # No Gold, reviewed text or expected locator is an input to extraction.
    try:
        require_unoptimized()
        no_links(source)
        if source.stat().st_size != expected_size or existing.sha(source) != expected_sha:
            raise PacketError("Worker source mismatch")
        ancillary = extract_footnotes(source)
        captured = {"ancillary": ancillary.to_dict()}
        captured["address_checks"] = existing.verify_ancillary(source, captured)
        if source.stat().st_size != expected_size or existing.sha(source) != expected_sha:
            raise PacketError("Worker source drift")
        write_json(output / "result.json", captured)
        return 0
    except Exception:
        return 2  # Never echo source values, XML or exceptions.


def generate(manifest: Path, corpus: Path, gold: Path, output: Path) -> dict:
    require_unoptimized()
    fresh_output(output, corpus)
    identity, paths, records = preflight(manifest, corpus, gold)
    code = {p: existing.sha(ROOT / p) for p in INPUT_CODE}
    code["tools/docx_footnote_candidate/locator_review_packet.py"] = existing.sha(Path(__file__))
    code["tests/unit/test_docx_footnote_locator_review_packet.py"] = existing.sha(
        ROOT / "tests/unit/test_docx_footnote_locator_review_packet.py"
    )
    frozen = {
        "inputs": identity,
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "code": code,
        "candidate_limits": asdict(FootnoteLimits()),
        "guards": existing.GUARDS,
        "max_text_hints": MAX_HINTS,
        "draft_build_seconds": BUILD_SECONDS,
        "python": platform.python_version(),
        "packages": {name: importlib.metadata.version(name) for name in ("pydantic", "psutil")},
    }
    output.mkdir(parents=True)
    write_json(output / "inputs.json", frozen)
    packets, resources = [], []
    for record in records:
        stage = output / record.document_id
        stage.mkdir()
        command = [
            sys.executable,
            "-B",
            str(Path(__file__).resolve()),
            "--worker",
            str(paths[record.document_id]),
            "--expected-sha",
            record.source_sha256,
            "--expected-size",
            str(record.source_size_bytes),
            "--output",
            str(stage),
        ]
        runtime = existing.monitor(command, stage)
        resources.append({"document_id": record.document_id, **runtime})
        capture = stage / "result.json"
        raw = (
            json.loads(capture.read_text()) if capture.exists() and not runtime["failure"] else None
        )
        packet = make_packet(record, raw)
        write_json(stage / "review-draft.json", packet)
        packets.append(packet)
    after, _, _ = preflight(manifest, corpus, gold)
    if after != identity or any(existing.sha(ROOT / p) != h for p, h in code.items()):
        raise PacketError("Frozen input/code drift")
    summary = aggregate(packets)
    passed = all(not r["failure"] and r["cleanup"] for r in resources) and all(
        p["candidate_status"] != "failed" for p in packets
    )
    deterministic = {"inputs": frozen, "summary": summary}
    report = {
        "status": "PASS" if passed else "FIX",
        "quality": "NOT_EVALUATED",
        "deterministic": deterministic,
        "deterministic_fingerprint": fingerprint(deterministic),
        "runtime": resources,
    }
    write_json(output / "summary.json", report)
    artifacts = {
        p.relative_to(output).as_posix(): existing.sha(p)
        for p in sorted(output.rglob("*"))
        if p.is_file()
    }
    write_json(output / "artifact-manifest.json", artifacts)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("docs/eda/corpus_v1_manifest.csv"))
    parser.add_argument("--corpus", type=Path, default=Path("local-corpus"))
    parser.add_argument(
        "--gold",
        type=Path,
        default=Path("local-evaluation/extraction_fidelity_v1_expanded_approved.jsonl"),
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--worker", type=Path)
    parser.add_argument("--expected-sha")
    parser.add_argument("--expected-size", type=int)
    args = parser.parse_args()
    try:
        require_unoptimized()
        if args.worker:
            # The parent opens its journal before spawn; no prior capture is accepted.
            fresh_output(args.output / "worker-boundary", args.corpus)
            if not args.output.is_dir():
                raise PacketError("Worker stage rejected")
            entries = list(args.output.iterdir())
            if (
                len(entries) != 1
                or entries[0].name != "resources.jsonl"
                or not entries[0].is_file()
            ):
                raise PacketError("Worker stage rejected")
            no_links(entries[0])
            return worker(args.worker, args.output, args.expected_sha, args.expected_size)
        result = generate(args.manifest, args.corpus, args.gold, args.output)
        print(
            json.dumps(
                {
                    "status": result["status"],
                    "quality": result["quality"],
                    "fingerprint": result["deterministic_fingerprint"],
                    "summary": result["deterministic"]["summary"],
                },
                sort_keys=True,
            )
        )
        return 0 if result["status"] == "PASS" else 1
    except Exception:
        print("BLOCKED: local review packet input, resource or output boundary rejected")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
