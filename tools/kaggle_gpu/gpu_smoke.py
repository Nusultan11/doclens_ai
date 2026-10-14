"""Small synthetic CUDA check; no project data, models or downloads."""

from __future__ import annotations

import hashlib
import json
import platform
import time
from datetime import UTC, datetime
from pathlib import Path

import torch


def main() -> int:
    report = {
        "schema_version": 1,
        "started_at_utc": datetime.now(UTC).isoformat(),
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "python_version": platform.python_version(),
        "torch_version": str(torch.__version__),
        "cuda_version": torch.version.cuda,
        "cuda_available": torch.cuda.is_available(),
        "devices": [],
        "status": "failed",
    }
    print(f"PyTorch: {report['torch_version']}", flush=True)
    print(f"CUDA runtime: {report['cuda_version']}", flush=True)
    print(f"CUDA available: {report['cuda_available']}", flush=True)
    exit_code = 1
    try:
        if not report["cuda_available"]:
            raise RuntimeError("CUDA is unavailable; CPU fallback is not permitted")
        for index in range(torch.cuda.device_count()):
            properties = torch.cuda.get_device_properties(index)
            device = {
                "index": index,
                "name": properties.name,
                "total_memory_bytes": properties.total_memory,
                "vram_gib": round(properties.total_memory / 1024**3, 2),
            }
            report["devices"].append(device)
            print(f"GPU {index}: {device['name']}, VRAM {device['vram_gib']} GiB", flush=True)

        device = torch.device("cuda:0")
        size = 1024
        left = torch.ones((size, size), device=device, dtype=torch.float32)
        right = torch.ones_like(left)
        # Exclude allocation and first-use CUDA initialization from this one warm sample.
        torch.mm(left, right)
        torch.cuda.synchronize(device)
        started = time.perf_counter()
        result = torch.mm(left, right)
        torch.cuda.synchronize(device)
        elapsed_seconds = time.perf_counter() - started
        valid = (
            result.device == device
            and tuple(result.shape) == (size, size)
            and bool(torch.isfinite(result).all().item())
            and bool((result == float(size)).all().item())
        )
        report["computation"] = {
            "operation": "matrix_multiplication",
            "device": str(result.device),
            "shape": [size, size],
            "dtype": str(result.dtype),
            "expected_each_value": size,
            "sample_value": result[0, 0].item(),
            "elapsed_seconds": elapsed_seconds,
            "valid": valid,
        }
        if not valid:
            raise RuntimeError("CUDA matrix multiplication returned an invalid result")
        report["status"] = "passed"
        exit_code = 0
        print(f"CUDA matrix multiplication: PASS, {elapsed_seconds:.6f} seconds", flush=True)
    except Exception as error:
        report["error"] = f"{type(error).__name__}: {error}"
        print(f"GPU smoke FAILED: {report['error']}", flush=True)
    report["finished_at_utc"] = datetime.now(UTC).isoformat()
    output = Path("/kaggle/working/gpu_smoke.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Report: {output}", flush=True)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
