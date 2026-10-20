"""Isolated unmodified native baseline, using only a parent-authored source request."""

from __future__ import annotations

import importlib.metadata
import json
import sys
from pathlib import Path

from doclens_ai.extraction.evidence_v2 import Scope
from tools.extraction_quality.table_comparison import Pin, native_capture


def main() -> int:
    try:
        source, destination = map(Path, sys.argv[1:])
        request = json.loads((destination.parent / "request.json").read_text(encoding="utf-8"))
        scope = Scope.model_validate(request["scope"])
        pin = Pin.model_validate_json(json.dumps(request["pin"]))
        if pin.engine != "pypdf" or pin.package_version != importlib.metadata.version("pypdf"):
            return 2
        capture = native_capture(source, scope, pin)
        with destination.open("x", encoding="utf-8") as stream:
            stream.write(capture.model_dump_json())
        return 0
    except Exception:
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
