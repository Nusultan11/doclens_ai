"""Parser identity usable by API producers without importing parser dependencies."""

import hashlib
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

PARSER_VERSIONS = {"pypdf": "6.20.0", "python-docx": "1.2.0", "openpyxl": "3.1.5", "lxml": "6.1.3"}
IMPLEMENTATION_FILES = (
    "extraction/parsers.py",
    "extraction/models.py",
    "extraction/validation.py",
    "extraction/docx_footnote_candidate.py",
    "extraction/runtime.py",
    "extraction/limits.py",
    "extraction/engines.py",
    "extraction/bounded.py",
    "extraction/ir.py",
    "extraction/adapters.py",
    "extraction/ir_validation.py",
    "extraction/reconciliation.py",
    "chunking/ir.py",
    "services/extraction_artifacts.py",
    "storage/s3.py",
    "chunking/core.py",
    "chunking/models.py",
)


def extraction_runtime_manifest() -> dict[str, object]:
    root = Path(__file__).resolve().parents[1]
    return {
        "parser_versions": dict(PARSER_VERSIONS),
        "contract_runtime_versions": {
            name: version(name) for name in ("pydantic", "pydantic-core")
        },
        "python_version": list(sys.version_info[:3]),
        "implementation_sha256": {
            name: hashlib.sha256((root / name).read_bytes()).hexdigest()
            for name in IMPLEMENTATION_FILES
        },
    }


def runtime_versions_match() -> bool:
    try:
        return all(version(name) == expected for name, expected in PARSER_VERSIONS.items())
    except PackageNotFoundError:
        return False
