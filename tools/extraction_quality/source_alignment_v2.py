"""EX-05: independently re-read physical PDF cells and audit global glyph ownership.

Machine source support is distinct from human Gold. Predicted text, confidence,
headers, units and periods never create source evidence or canonical values.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
from collections import Counter, defaultdict
from pathlib import Path

from doclens_ai.eda.corpus_v2 import read_json, sha256
from doclens_ai.extraction.evidence_v2 import valid_bbox
from doclens_ai.extraction.fidelity_gold import fingerprint
from tools.extraction_quality import pdf_cell_recovery as recovery
from tools.extraction_quality.extraction_v2 import private_destination, write
from tools.extraction_quality.ocr_diagnostics_v2 import NUMBERS


def verify(source: Path, expected_sha256: str, proposals: list[dict]) -> dict:
    if not 0 < len(proposals) <= 100:
        raise ValueError("proposal budget")
    source_results = []
    pins = {
        "code": {
            p.name: sha256(p)
            for p in (
                Path(__file__),
                Path(recovery.__file__),
                Path(recovery.grids.__file__),
                Path(recovery.validation.__file__),
                Path(__file__).with_name("ocr_diagnostics_v2.py"),
            )
        },
        "dependencies": {
            p: importlib.metadata.version(p) for p in ("pypdf", "pypdfium2", "pydantic")
        },
        "method": recovery.METHOD,
    }
    cells, ownership, table_ids = [], defaultdict(list), set()
    for proposal in proposals:
        before = fingerprint(proposal)
        observed = recovery.recover(source, expected_sha256, proposal)
        if fingerprint(proposal) != before:
            raise ValueError("candidate mutation")
        table_id = observed["review_table_id"]
        page = observed["page_identity"]["page_number"]
        if (page, table_id) in table_ids:
            raise ValueError("duplicate table identity")
        table_ids.add((page, table_id))
        proposed = {c["review_cell_id"]: c for c in proposal["cells"]}
        lineage = {c["cell_id"]: c for c in observed["lineage"]["cells"]}
        for cell in observed["cells"]:
            key = cell["review_cell_id"]
            issues = list(observed["issues"]) + list(cell["unresolved"])
            evidence = lineage.get(key)
            native = cell["literal_text"]
            candidate = proposed[key].get("literal_text")
            if candidate is not None and native is not None and candidate != native:
                issues.append("CANDIDATE_LITERAL_CONFLICT")
                if Counter(NUMBERS.findall(candidate)) != Counter(NUMBERS.findall(native)):
                    issues.append("CRITICAL_NUMERIC_CONFLICT")
            if evidence is not None:
                glyphs = evidence["glyphs"]
                start, end = evidence["character_range"]
                indices = [g["index"] for g in glyphs]
                if indices != list(range(start, end)) or not glyphs:
                    issues.append("NONCONTIGUOUS_SOURCE_OBSERVATIONS")
                # This is a replay of one contiguous native range, never parser-word aggregation.
                literal = "".join(chr(g["unicode"]) for g in glyphs)
                if literal != native:
                    issues.append("SOURCE_LITERAL_LINEAGE_MISMATCH")
                for glyph in glyphs:
                    character = chr(glyph["unicode"])
                    if character.isspace():
                        if glyph["generated"] != 0:
                            issues.append("INFERRED_WHITESPACE_NOT_LITERAL_PROOF")
                        continue
                    if (
                        glyph["generated"] != 0
                        or glyph["unicode_mapping_error"] != 0
                        or abs(glyph["angle"]) >= 0.001
                        or not valid_bbox(
                            tuple(glyph["bbox_pdf_user_space_points"]),
                            tuple(cell["bbox_pdf_user_space_points"]),
                        )
                    ):
                        issues.append("UNVERIFIED_GLYPH_MAPPING")
                    ownership[(page, glyph["index"])].append(len(cells))
            else:
                issues.append("MISSING_NATIVE_GLYPHS")
            cells.append(
                {
                    "table_id": table_id,
                    "cell_id": key,
                    "page": page,
                    "source_sha256": expected_sha256,
                    "source_version": expected_sha256,
                    "geometry": {k: cell[k] for k in recovery.GEOMETRY_FIELDS},
                    "method": observed["method"],
                    "candidate_method": proposal["candidate"]["method"],
                    "candidate_fingerprint": before,
                    "native_literal": native,
                    "candidate_agrees": None
                    if candidate is None or native is None
                    else candidate == native,
                    "glyph_range": evidence["character_range"] if evidence else None,
                    "confidence": None,
                    "issues": sorted(set(issues)),
                    "relationships": None,
                    "human_review": "NOT_PERFORMED",
                }
            )
        source_results.append(observed)
    for owners in ownership.values():
        if len(owners) > 1:
            for owner in set(owners):
                cells[owner]["issues"] = sorted(
                    set(cells[owner]["issues"] + ["DUPLICATE_GLYPH_OWNERSHIP"])
                )
    for cell in cells:
        cell["status"] = "machine_source_supported" if not cell["issues"] else "needs_review"
    if sha256(source) != expected_sha256:
        raise ValueError("source changed")
    safe_cells = [
        {k: c[k] for k in ("table_id", "cell_id", "page", "candidate_agrees", "issues", "status")}
        for c in cells
    ]
    summary = {
        "tables": len(proposals),
        "cells_attempted": len(cells),
        "states": dict(sorted(Counter(c["status"] for c in cells).items())),
        "native_literal_available": sum(c["native_literal"] is not None for c in cells),
        "candidate_literals_compared": sum(c["candidate_agrees"] is not None for c in cells),
        "candidate_comparisons_unknown": sum(c["candidate_agrees"] is None for c in cells),
        "candidate_literal_conflicts": sum(
            "CANDIDATE_LITERAL_CONFLICT" in c["issues"] for c in cells
        ),
        "duplicate_glyphs": sum(len(v) > 1 for v in ownership.values()),
        "independently_human_verified": 0,
        "quality": "FAIL"
        if any("CRITICAL_NUMERIC_CONFLICT" in c["issues"] for c in cells)
        else "NOT_EVALUATED",
        "experiment": "REJECT"
        if any("CRITICAL_NUMERIC_CONFLICT" in c["issues"] for c in cells)
        else "INCONCLUSIVE",
        "production_authorized": False,
        "pins_fingerprint": fingerprint(pins),
        "deterministic_fingerprint": fingerprint(
            {
                "source_sha256": expected_sha256,
                "cells": cells,
                "native_observations": source_results,
                "pins": pins,
            }
        ),
    }
    return {
        "source_sha256": expected_sha256,
        "pins": pins,
        "cells": cells,
        "native_observations": source_results,
        "sanitized_cells": safe_cells,
        "summary": summary,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--proposal", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        private_destination(args.output)
        result = verify(args.source, args.source_sha256, [read_json(p) for p in args.proposal])
        args.output.mkdir(parents=True)
        write(args.output / "private-evidence.json", result)
        write(args.output / "summary.json", result["summary"])
        print(json.dumps(result["summary"], sort_keys=True))
        return 0
    except Exception:  # noqa: BLE001 - never publish private candidate literals or source paths
        print("BLOCKED: source, physical cells, proposal identity or fresh destination rejected")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
