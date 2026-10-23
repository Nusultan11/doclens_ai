"""Synthetic-only runtime measurement; standalone upload, no repository imports."""

import hashlib
import importlib.metadata
import json
import os
import platform
import time
from datetime import UTC, datetime
from pathlib import Path


def main():
    import psutil
    import torch

    root = Path("/kaggle/working")
    started = time.monotonic()
    report = {
        "run_id": "extraction-20261023-preflight-v1",
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "started_utc": datetime.now(UTC).isoformat(),
        "python": platform.python_version(),
        "packages": {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()},
        "cpu_count": os.cpu_count(),
        "ram": dict(psutil.virtual_memory()._asdict()),
        "disk": dict(psutil.disk_usage(root)._asdict()),
        "cuda": torch.version.cuda,
        "devices": [],
        "status": "failed",
    }
    try:
        torch.set_num_threads(2)
        for device in ["cpu", "cuda:0"]:
            before = time.monotonic()
            x = torch.ones((512, 512), device=device)
            y = x @ x
            valid = bool((y == 512).all().item())
            if not valid:
                raise RuntimeError("incorrect_matrix_result")
            report[device] = {
                "valid": valid,
                "device": str(y.device),
                "seconds": time.monotonic() - before,
            }
        for i in range(torch.cuda.device_count()):
            p = torch.cuda.get_device_properties(i)
            report["devices"].append({"index": i, "name": p.name, "vram_bytes": p.total_memory})
        report["peak_cuda_allocated_bytes"] = torch.cuda.max_memory_allocated(0)
        report["status"] = "completed"
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
    report["wall_seconds"] = time.monotonic() - started
    report["finished_utc"] = datetime.now(UTC).isoformat()
    path = root / "preflight.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    (root / "checksums.json").write_text(
        json.dumps({path.name: hashlib.sha256(path.read_bytes()).hexdigest()})
    )
    print(json.dumps({k: v for k, v in report.items() if k != "packages"}), flush=True)
    return 0 if report["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
