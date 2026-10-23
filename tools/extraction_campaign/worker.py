"""Private-file IPC worker. Gate precedes framework imports and inference."""

from __future__ import annotations

import json
import os
import socket
import sys
import time
import traceback
from pathlib import Path


def deny_external_network():
    original = socket.socket.connect

    def connect(sock, address):
        if not isinstance(address, tuple) or address[0] not in {"127.0.0.1", "::1", "localhost"}:
            raise RuntimeError("external_network_denied")
        return original(sock, address)

    socket.socket.connect = connect


def docling(job, output):
    from doclens_ai.extraction.docling_candidate import CandidateConfig, _converter
    from doclens_ai.extraction.fidelity_gold import fingerprint as artifact_digest
    from tools.extraction_campaign import adapters
    from tools.extraction_campaign.evidence import serialize

    config = job["configuration"]
    import random

    import numpy
    import torch

    random.seed(0)
    numpy.random.seed(0)
    torch.manual_seed(0)
    options = CandidateConfig(
        artifacts=Path(config["artifacts"]),
        artifact_fingerprint=config["artifact_fingerprint"],
        timeout_seconds=job["policy"]["wall_seconds_per_document"],
    )
    converter = _converter(options)
    if config.get("table_mode", "fast") == "accurate":
        from docling.datamodel.pipeline_options import TableFormerMode

        converter.format_to_options[
            next(iter(converter.format_to_options))
        ].pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE
    start = time.perf_counter()
    result = converter.convert(Path(job["source_path"]))
    conversion = time.perf_counter() - start
    native = result.document.export_to_dict()
    (output / "native.json").write_text(json.dumps(native, ensure_ascii=True), encoding="utf-8")
    backend = []
    for page in result.pages:
        backend.append(
            {
                "page_number": page.page_no + 1,
                "native_page": page.model_dump(mode="json"),
            }
        )
    (output / "backend-pages.json").write_text(json.dumps(backend), encoding="utf-8")
    metadata = result.model_dump(mode="json", exclude={"input", "document", "pages"})
    (output / "conversion-metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    observations = adapters.docling(native)
    from doclens_ai.extraction.docling_candidate import normalize_document
    from doclens_ai.extraction.fidelity_gold import fingerprint

    # Historical lossy projection retained solely to diagnose adapter differences.
    legacy = normalize_document(
        result.document,
        source_sha256=job["source_sha256"],
        source_size_bytes=job["source_size_bytes"],
        config=options,
    )
    (output / "legacy.json").write_text(json.dumps(legacy.to_dict()), encoding="utf-8")
    return {
        "native_status": getattr(result.status, "value", str(result.status)),
        "observations": serialize(observations),
        "conversion_seconds": conversion,
        "legacy_fingerprint": fingerprint(legacy.to_dict()),
        "artifact_fingerprint": artifact_digest(job["model_inventory"]),
    }


def native(job, output):
    from doclens_ai.extraction.parsers import extract_file
    from tools.extraction_campaign.evidence import Observation, serialize

    result = extract_file(Path(job["source_path"]))
    (output / "native.json").write_text(json.dumps(result.to_dict()), encoding="utf-8")
    observations = []
    for block in result.blocks:
        if hasattr(block, "text"):
            observations.append(
                Observation(
                    f"block/{block.order}",
                    "text",
                    block.text,
                    block.source.page_number,
                    len(observations),
                )
            )
    return {"native_status": str(result.status), "observations": serialize(observations)}


def main():
    output = Path(sys.argv[1])
    (output / "ready.json").write_text(json.dumps({"pid": os.getpid()}), encoding="utf-8")
    deadline = time.monotonic() + 20
    while not (output / "gate").exists():
        if time.monotonic() > deadline:
            return 3
        time.sleep(0.01)
    try:
        job = json.loads((output / "job.json").read_text(encoding="utf-8"))
        deny_external_network()
        if job["candidate"] == "probe":
            mode = job["configuration"]["mode"]
            if mode == "hang":
                while True:
                    time.sleep(0.1)
            if mode == "crash":
                os._exit(73)
            if mode == "oom":
                _large = bytearray(2 * 1024**3)
            if mode == "output":
                (output / "native.json").write_bytes(b"x" * 1024**2)
            if mode == "child":
                import subprocess

                child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
                (output / "child.json").write_text(json.dumps({"pid": child.pid}))
                time.sleep(0.3)
            result = {"observations": [], "native_status": "probe"}
        else:
            import importlib.metadata

            actual = {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()}
            if actual != job["environment"]:
                raise ValueError("environment_pin_changed")
            from tools.extraction_campaign.protocol import sha

            if sha(Path(job["source_path"])) != job["source_sha256"]:
                raise ValueError("source_pin_changed")
            start = time.perf_counter()
            result = {"native": native, "docling": docling}[job["candidate"]](job, output)
            result["inference_total_seconds"] = time.perf_counter() - start
            if sha(Path(job["source_path"])) != job["source_sha256"]:
                raise ValueError("source_mutated")
        (output / "result.json").write_text(json.dumps(result, ensure_ascii=True), encoding="utf-8")
        return 0
    except BaseException as exc:
        (output / "error-private.txt").write_text(traceback.format_exc(), encoding="utf-8")
        (output / "error.json").write_text(
            json.dumps({"type": type(exc).__name__}), encoding="utf-8"
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())
