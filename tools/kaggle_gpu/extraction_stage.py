"""Explicit single-script staging and downloaded-artifact verification."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def configured_stage(source: Path, destination: Path, config: dict, *, slug: str, title: str):
    marker = "CONFIG = {}  # Replaced exactly once by the local explicit staging builder."
    text = source.read_text(encoding="utf-8")
    if text.count(marker) != 1:
        raise ValueError("configuration_marker_invalid")
    generated = destination.with_suffix(".py")
    generated.parent.mkdir(parents=True, exist_ok=True)
    with generated.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(text.replace(marker, "CONFIG = " + repr(config)))
    return stage(generated, destination, slug=slug, title=title, internet=True)


def stage(source: Path, destination: Path, *, slug: str, title: str, internet: bool) -> dict:
    """Never traverse the repository; the only upload payload is this reviewed script."""
    if source.is_symlink() or source.suffix != ".py" or destination.exists():
        raise ValueError("fresh_stage_and_regular_python_source_required")
    if slug != "-".join(title.lower().split()):
        raise ValueError("title_slug_mismatch")
    destination.mkdir(parents=True)
    data = source.read_text(encoding="utf-8").replace("\r\n", "\n")
    with (destination / "runner.py").open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(data)
    metadata = {
        "id": "nurs2005/" + slug,
        "title": title,
        "code_file": "runner.py",
        "language": "python",
        "kernel_type": "script",
        "is_private": True,
        "enable_gpu": True,
        "enable_internet": internet,
        "machine_shape": "NvidiaTeslaT4",
        "dataset_sources": [],
        "competition_sources": [],
        "kernel_sources": [],
        "model_sources": [],
    }
    (destination / "kernel-metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    manifest = {p.name: sha(p) for p in sorted(destination.iterdir())}
    # Outside upload directory: exact upload inventory, not another uploaded asset.
    destination.with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def verify(directory: Path, expected_source_sha: str, run_id: str, report_name: str) -> dict:
    checksums = json.loads((directory / "checksums.json").read_text())
    if report_name not in checksums:
        raise ValueError("missing_report_checksum")
    for name, expected in checksums.items():
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts or "\\" in name:
            raise ValueError("unsafe_artifact_path")
        path = directory / relative
        if path.is_symlink() or not path.resolve().is_relative_to(directory.resolve()):
            raise ValueError("unsafe_artifact_path")
        if sha(path) != expected:
            raise ValueError("artifact_checksum_mismatch")
    report = json.loads((directory / report_name).read_text())
    if report["source_sha256"] != expected_source_sha or report["run_id"] != run_id:
        raise ValueError("stale_or_mismatched_run")
    return report


def main():
    parser = argparse.ArgumentParser(description="Stage one synthetic-only extraction R0.")
    parser.add_argument(
        "candidate", choices=["docling", "marker", "ppstructure", "paddlevl", "mineru"]
    )
    parser.add_argument("destination", type=Path)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    directory = Path(__file__).parent
    config = json.loads((directory / "extraction_registry.json").read_text())[args.candidate]
    config["run_id"] = args.run_id
    label = {
        "docling": "Docling",
        "marker": "Marker",
        "ppstructure": "PPStructure",
        "paddlevl": "PaddleVL",
        "mineru": "MinerU",
    }[args.candidate]
    print(
        configured_stage(
            directory / "extraction_remote.py",
            args.destination,
            config,
            slug=f"doclens-extraction-{label.lower()}-r0",
            title=f"DocLens Extraction {label} R0",
        )
    )


if __name__ == "__main__":
    main()
