"""Isolated Marker R1-public; reuses frozen Docling metrics and bounded execution."""

from __future__ import annotations

import base64
import importlib.metadata
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tarfile
import threading
import time
import traceback
import types
from datetime import UTC, datetime
from pathlib import Path

CONFIG = {}  # Replaced exactly once by the local explicit staging builder.


def helpers():
    """The controller needs only this committed, hash-bound stdlib helper module."""
    if not CONFIG:
        from tools.kaggle_gpu import docling_r1_public

        return docling_r1_public
    name = "tools/kaggle_gpu/docling_r1_public.py"
    data = base64.b64decode(CONFIG["code"][name]["base64"], validate=True)
    import hashlib

    if hashlib.sha256(data).hexdigest() != CONFIG["code"][name]["sha256"]:
        raise ValueError("helper_identity_mismatch")
    module = types.ModuleType("frozen_public_helpers")
    exec(compile(data, name, "exec"), module.__dict__)
    module.CONFIG = CONFIG
    return module


def admit(cohort):
    if len(cohort) != 11 or len({r["document_id"] for r in cohort}) != 11:
        raise ValueError("exact_frozen_eleven_required")
    if len({r["sha256"] for r in cohort}) != 11:
        raise ValueError("duplicate_source")
    for row in cohort:
        if (
            row["cloud_admission"] != "CLOUD_ADMITTED"
            or row["split"] != "dev"
            or row["license"] != "CC-BY-4.0"
        ):
            raise ValueError("source_not_admitted")


def cuda_proof(log: str):
    offload = re.search(r"offloaded\s+([1-9][0-9]*)/[0-9]+\s+layers to GPU", log)
    # Offload plus actual completed inference timings; enumeration alone is insufficient.
    if not offload or "CUDA0" not in log or "eval time" not in log:
        raise ValueError("actual_cuda_inference_unverified")
    return {"device": "llama.cpp CUDA0", "offloaded_layers": int(offload.group(1))}


def inventory(root: Path):
    h = helpers()
    return {p: h.sha(h.safe_path(root, p)) for p in CONFIG["model_inventory"]}


def prepare(root: Path):
    """Acquire exact successful R0 v4 bytes; never select newer model revisions."""
    import requests

    h = helpers()
    for item in CONFIG["assets"]:
        target = h.safe_path(root, item["path"])
        target.parent.mkdir(parents=True, exist_ok=True)
        count = 0
        with (
            requests.get(item["url"], timeout=120, stream=True) as response,
            target.open("xb") as out,
        ):
            response.raise_for_status()
            for block in response.iter_content(1024**2):
                count += len(block)
                if count > item["maximum_bytes"]:
                    raise ValueError("asset_size_limit")
                out.write(block)
        if h.sha(target) != item["sha256"]:
            raise ValueError("model_asset_identity_mismatch")
    with tarfile.open(root / "runtime.tar.gz") as archive:
        archive.extractall(root / "runtime", filter="data")
    if inventory(root) != CONFIG["model_inventory"]:
        raise ValueError("extracted_runtime_identity_mismatch")


def environment(code: Path, profile: Path, models: Path):
    env = helpers().environment(code, profile)
    runtime = models / "runtime/llama-b11617"
    libraries = list(Path("/usr/local/lib/python3.13/dist-packages/nvidia").glob("*/lib"))
    env.update(
        CUDA_VISIBLE_DEVICES="0",
        SURYA_INFERENCE_BACKEND="llamacpp",
        SURYA_INFERENCE_PARALLEL="1",
        SURYA_INFERENCE_KEEP_ALIVE="false",
        SURYA_INFERENCE_STARTUP_TIMEOUT="120",
        TORCH_DEVICE="cpu",
        FAST_DETECTOR_DEVICE="cpu",
        FAST_LAYOUT_NUM_THREADS="2",
        LLAMA_CPP_BINARY=str(runtime / "llama-server"),
        LLAMA_CPP_EXTRA_ARGS="--seed 0 -lv 5",
        SURYA_GGUF_LOCAL_MODEL_PATH=str(models / "surya-ocr-2-gguf/surya-2.gguf"),
        SURYA_GGUF_LOCAL_MMPROJ_PATH=str(models / "surya-ocr-2-gguf/surya-2-mmproj.gguf"),
        OCR_ERROR_MODEL_CHECKPOINT=str(models / "ocr-error"),
        FONT_PATH=str(models / "render-font/GoNotoCurrent-Regular.ttf"),
        FAST_LAYOUT_MODEL_CHECKPOINT=str(models / "surya_layout2"),
        FAST_ORDER_MODEL_CHECKPOINT=str(models / "surya_layout2/order"),
        LD_LIBRARY_PATH=":".join(
            [
                env.get("LD_LIBRARY_PATH", ""),
                "/usr/local/nvidia/lib64",
                str(runtime),
                *map(str, libraries),
            ]
        ),
    )
    return env


def cleanup_owned(observed):
    """R0 ownership rule: PID and creation time must still identify our descendant."""
    import psutil

    remaining, zombies = [], []
    for process, created in observed.values():
        try:
            process = psutil.Process(process.pid)
            if process.create_time() != created:
                continue
            if process.status() == psutil.STATUS_ZOMBIE:
                zombies.append(process.pid)
                continue
            if process.is_running():
                process.kill()
                try:
                    process.wait(timeout=5)
                except psutil.TimeoutExpired:
                    if process.status() == psutil.STATUS_ZOMBIE:
                        zombies.append(process.pid)
                    elif process.is_running():
                        remaining.append(process.pid)
        except psutil.NoSuchProcess:
            pass
        except psutil.Error:
            remaining.append(process.pid)
    return remaining, zombies


def bounded_process(command, output, seconds, env, *, rss_limit):
    """Docling resource controls plus the R0 escaped-descendant cleanup rule."""
    import psutil

    output.mkdir(parents=True, exist_ok=True)
    started, peak, samples, reason = time.monotonic(), 0, 0, None
    observed = {}
    with (output / "console-private.txt").open("wb") as log:
        process = subprocess.Popen(
            command,
            env=env,
            cwd=output,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            while process.poll() is None:
                try:
                    parent = psutil.Process(process.pid)
                    members = [parent, *parent.children(recursive=True)]
                    rss = 0
                    for member in members:
                        try:
                            observed[member.pid] = (member, member.create_time())
                            rss += member.memory_info().rss
                        except psutil.NoSuchProcess:
                            pass
                    peak, samples = max(peak, rss), samples + 1
                    if rss > rss_limit:
                        reason = "memory_limit"
                    elif len(members) > 8:
                        reason = "process_limit"
                except psutil.NoSuchProcess:
                    pass
                if time.monotonic() - started > seconds:
                    reason = "timeout"
                if (
                    sum(p.stat().st_size for p in output.rglob("*") if p.is_file())
                    > CONFIG["policy"]["scratch_bytes"]
                ):
                    reason = "output_limit"
                if reason:
                    break
                time.sleep(0.05)
        finally:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            code = process.wait(timeout=10)
            remaining, zombies = cleanup_owned(observed)
    outcome = reason or ("completed" if code == 0 else "failed")
    return {
        "status": "cleanup_unverified" if remaining else outcome,
        "worker_outcome": outcome,
        "exit_code": code,
        "wall_seconds": time.monotonic() - started,
        "peak_tree_rss_bytes": peak,
        "rss_samples": samples,
        "sample_seconds": 0.05,
        "remaining_owned_pids": remaining,
        "non_running_zombie_pids": zombies,
    }


def bounded(command, output, seconds, env, *, rss_limit):
    """Bound owned workers and preserve sampled device-zero GPU use."""
    h = helpers()
    samples, failures = [], []
    stop = threading.Event()

    def sample():
        while not stop.is_set():
            try:
                value = subprocess.check_output(
                    [
                        "nvidia-smi",
                        "-i",
                        "0",
                        "--query-gpu=memory.used,utilization.gpu",
                        "--format=csv,noheader,nounits",
                    ],
                    text=True,
                    timeout=5,
                ).strip()
                memory, utilization = map(int, value.split(","))
                samples.append(
                    {
                        "monotonic": time.monotonic(),
                        "used_mib": memory,
                        "utilization_percent": utilization,
                    }
                )
            except (OSError, subprocess.SubprocessError, ValueError) as exc:
                failures.append(type(exc).__name__)
            stop.wait(1)

    thread = threading.Thread(target=sample, daemon=True)
    thread.start()
    try:
        receipt = bounded_process(command, output, seconds, env, rss_limit=rss_limit)
    finally:
        stop.set()
        thread.join(timeout=6)
        h.write(output / "gpu-samples.json", {"samples": samples, "errors": failures})
    receipt["gpu_device_0_used_peak_bytes"] = max(
        (s["used_mib"] * 1024**2 for s in samples), default=None
    )
    receipt["gpu_samples"] = len(samples)
    receipt["gpu_sample_failures"] = len(failures)
    receipt["gpu_scope"] = (
        "Device 0 total including baseline; approximately 1-second samples; "
        "not Torch allocated memory."
    )
    return receipt


def worker(job_path: Path):
    h = helpers()
    job = json.loads(job_path.read_text())
    output, source, models = job_path.parent, Path(job["source"]), Path(job["models"])
    try:
        import random
        import resource

        import numpy
        import torch

        policy = CONFIG["policy"]
        for limit, value in (
            (resource.RLIMIT_CPU, policy["cpu_seconds"]),
            (resource.RLIMIT_FSIZE, policy["native_output_bytes"]),
            (resource.RLIMIT_DATA, policy["linux_data_bytes"]),
        ):
            resource.setrlimit(limit, (value, value))
        if h.sha(source) != job["sha256"] or inventory(models) != CONFIG["model_inventory"]:
            raise ValueError("source_or_model_identity_mismatch")
        if {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()} != job[
            "environment"
        ]:
            raise ValueError("environment_changed")
        random.seed(0)
        numpy.random.seed(0)
        torch.manual_seed(0)
        torch.set_num_threads(2)
        # Only the vendor's local inference servers may receive Python connections.
        import socket

        connect = socket.socket.connect

        def local_only(sock, address):
            if not isinstance(address, tuple) or address[0] not in (
                "127.0.0.1",
                "localhost",
                "::1",
            ):
                raise RuntimeError("external_inference_network_denied")
            return connect(sock, address)

        socket.socket.connect = local_only
        socket.socket.connect_ex = lambda *a, **k: (_ for _ in ()).throw(
            RuntimeError("connect_ex_denied")
        )
        from marker.converters.pdf import PdfConverter
        from marker.models import create_model_dict, shutdown_models

        from tools.extraction_campaign import adapters
        from tools.extraction_campaign.evidence import serialize

        options = CONFIG["configuration"]["options"]
        h.write(output / "effective-options.json", options)
        started = time.monotonic()
        artifacts = create_model_dict(inference_backend="llamacpp")
        try:
            converter = PdfConverter(
                artifact_dict=artifacts,
                renderer="marker.renderers.json.JSONRenderer",
                config=options,
            )
            converted_at = time.monotonic()
            raw = converter(str(source)).model_dump(mode="json")
            elapsed = time.monotonic() - converted_at
            h.write(output / "native.json", raw)
        finally:
            shutdown_models(artifacts)
            for log in Path(os.environ["HOME"]).rglob("*.log"):
                shutil.copyfile(log, output / log.name)
        proof = cuda_proof((output / "llamacpp_server.log").read_text(errors="replace"))
        result = {
            "native_status": "completed",
            "conversion_seconds": elapsed,
            "worker_seconds": time.monotonic() - started,
            "cuda_execution": proof,
            "loaded_model_sha256": inventory(models),
            "observations": None,
        }
        try:
            result["observations"] = serialize(adapters.marker(raw))
        except Exception as exc:
            result["adapter_error"] = type(exc).__name__
            (output / "adapter-private.txt").write_text(traceback.format_exc())
        if (
            h.sha(source) != job["sha256"]
            or result["loaded_model_sha256"] != CONFIG["model_inventory"]
        ):
            raise ValueError("source_or_model_postcheck_mismatch")
        h.write(output / "result.json", result)
        return 0
    except BaseException as exc:
        h.write(output / "error.json", {"type": type(exc).__name__})
        (output / "error-private.txt").write_text(traceback.format_exc())
        return 2


def repeat_check(rows):
    fields = (
        "native_status",
        "capture_fingerprints",
        "capture_errors",
        "observation_fingerprint",
        "adapter_error",
        "context_fingerprint",
    )
    return {
        "agrees": all(rows[0].get(k) == rows[1].get(k) for k in fields)
        and rows[0]["receipt"]["status"] == rows[1]["receipt"]["status"],
        "complete_observations": all(r.get("observation_fingerprint") is not None for r in rows),
    }


def account_missing(rows):
    for repetition in (1, 2):
        for source in CONFIG["cohort"]:
            if not any(
                r["repeat"] == repetition and r["document_id"] == source["document_id"]
                for r in rows
            ):
                rows.append(
                    {
                        "repeat": repetition,
                        "document_id": source["document_id"],
                        "source_sha256": source["sha256"],
                        "receipt": {"status": "not_started"},
                    }
                )


def main():
    import psutil

    h = helpers()
    root, temp = Path("/kaggle/working/marker-r1-public"), Path("/tmp") / CONFIG["run_id"]
    root.mkdir(exist_ok=False)
    temp.mkdir(exist_ok=False)
    code, models, venv = temp / "code", temp / "models", temp / "env"
    code.mkdir()
    h.install_code(code)
    h.write(root / "protocol.json", CONFIG)
    report = {
        "run_id": CONFIG["run_id"],
        "source_sha256": h.sha(Path(__file__)),
        "started_utc": datetime.now(UTC).isoformat(),
        "cohort_fingerprint": CONFIG["cohort_fingerprint"],
        "configuration_fingerprint": h.fingerprint(CONFIG),
        "hardware": {"ram": psutil.virtual_memory()._asdict(), "cpus": psutil.cpu_count()},
        "quality": "NOT_EVALUATED",
        "rows": [],
    }
    try:
        admit(CONFIG["cohort"])
        report["gpu_inventory"] = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=index,name,driver_version,memory.total,memory.free",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            timeout=10,
        )
        inputs = root / "inputs"
        inputs.mkdir()
        for source in CONFIG["cohort"]:
            h.download(
                source["pdf_url"],
                inputs / (source["document_id"] + ".pdf"),
                source["sha256"],
                source["size_bytes"],
            )
        h.write(
            root / "ATTRIBUTION.json",
            {
                "sources": CONFIG["cohort"],
                "modifications": "Original PDFs unchanged; machine-generated extraction",
            },
        )
        subprocess.run(h.venv_command(sys.executable, venv), check=True, timeout=60)
        python = str(venv / "bin/python")
        bootstrap = CONFIG["pip_bootstrap"]
        pip_zip = temp / "pip.pyz"
        h.download(bootstrap["url"], pip_zip, bootstrap["sha256"], bootstrap["size_bytes"])
        setup_env = {
            k: os.environ[k] for k in ("PATH", "LD_LIBRARY_PATH", "LANG") if k in os.environ
        }
        setup_env.update(PIP_DISABLE_PIP_VERSION_CHECK="1", CUDA_VISIBLE_DEVICES="0")
        report["setup"] = bounded(
            [python, str(pip_zip), "install", *CONFIG["packages"]],
            root / "setup",
            1200,
            setup_env,
            rss_limit=24 * 1024**3,
        )
        if report["setup"]["status"] != "completed":
            raise RuntimeError("isolated_setup_failed")
        probe_env = environment(code, temp / "probe", models)
        probe = (
            "import importlib.metadata as m,json,sys;"
            "print(json.dumps({'python':sys.version,'packages':"
            "{d.metadata['Name']:d.version for d in m.distributions()}}))"
        )
        runtime = json.loads(
            subprocess.check_output([python, "-c", probe], env=probe_env, text=True, timeout=30)
        )
        h.write(root / "environment.json", runtime)
        report["prepare"] = bounded(
            [python, __file__, "--prepare", str(models)],
            root / "prepare",
            900,
            probe_env,
            rss_limit=24 * 1024**3,
        )
        if report["prepare"]["status"] != "completed":
            raise RuntimeError("model_preparation_failed")
        h.write(root / "model-inventory.json", inventory(models))
        for repetition in (1, 2):
            for source in CONFIG["cohort"]:
                output = root / f"repeat-{repetition}" / source["document_id"]
                output.mkdir(parents=True)
                h.write(
                    output / "job.json",
                    {
                        "source": str(inputs / (source["document_id"] + ".pdf")),
                        "sha256": source["sha256"],
                        "models": str(models),
                        "environment": runtime["packages"],
                    },
                )
                if (
                    psutil.virtual_memory().available
                    < CONFIG["policy"]["minimum_available_ram_bytes"]
                ):
                    receipt = {"status": "resource_blocked_before_start"}
                else:
                    receipt = bounded(
                        [python, __file__, "--worker", str(output / "job.json")],
                        output,
                        CONFIG["policy"]["marker_wall_seconds"],
                        environment(code, output / "profile", models),
                        rss_limit=CONFIG["policy"]["process_tree_rss_bytes"],
                    )
                h.write(output / "receipt.json", receipt)
                result = (
                    json.loads((output / "result.json").read_text())
                    if (output / "result.json").exists()
                    else {}
                )
                captures, errors = h.captures(output, "marker")
                report["rows"].append(
                    {
                        "repeat": repetition,
                        "document_id": source["document_id"],
                        "source_sha256": source["sha256"],
                        "receipt": receipt,
                        "native_status": result.get("native_status"),
                        "adapter_error": result.get("adapter_error"),
                        "capture_fingerprints": captures,
                        "capture_errors": errors,
                        "observation_fingerprint": h.fingerprint(result["observations"])
                        if result.get("observations") is not None
                        else None,
                        "context_fingerprint": h.fingerprint(
                            {
                                k: v
                                for k, v in result.items()
                                if k not in {"conversion_seconds", "worker_seconds"}
                            }
                        )
                        if result
                        else None,
                    }
                )
                print(
                    json.dumps(
                        {
                            "repeat": repetition,
                            "document_id": source["document_id"],
                            "status": receipt["status"],
                        }
                    ),
                    flush=True,
                )
                if (
                    sum(p.stat().st_size for p in root.rglob("*") if p.is_file())
                    > CONFIG["total_output_bytes"]
                ):
                    raise RuntimeError("aggregate_output_limit")
        if inventory(models) != CONFIG["model_inventory"]:
            raise ValueError("model_postcheck_mismatch")
        for source in CONFIG["cohort"]:
            if h.sha(inputs / (source["document_id"] + ".pdf")) != source["sha256"]:
                raise ValueError("source_postcheck_mismatch")
        if any(
            h.sha(h.safe_path(code, name)) != item["sha256"]
            for name, item in CONFIG["code"].items()
        ):
            raise ValueError("code_postcheck_mismatch")
        if (
            json.loads(
                subprocess.check_output([python, "-c", probe], env=probe_env, text=True, timeout=30)
            )
            != runtime
        ):
            raise ValueError("environment_postcheck_mismatch")
        report["source_model_code_environment_postchecks"] = "PASS"
        report["status"] = "completed"
    except BaseException as exc:
        report["status"] = "blocked"
        report["error_type"] = type(exc).__name__
        (root / "exception-private.txt").write_text(traceback.format_exc())
    account_missing(report["rows"])
    report["reproducibility"] = [
        {
            "document_id": s["document_id"],
            **repeat_check([r for r in report["rows"] if r["document_id"] == s["document_id"]]),
        }
        for s in CONFIG["cohort"]
    ]
    report["resources"] = {
        field: h.percentiles([r["receipt"].get(field) for r in report["rows"]])
        for field in ("wall_seconds", "peak_tree_rss_bytes", "gpu_device_0_used_peak_bytes")
    }
    report["finished_utc"] = datetime.now(UTC).isoformat()
    report["report_fingerprint"] = h.fingerprint(report)
    h.write(root / "report.json", report)
    h.write(
        root / "checksums.json",
        {p.relative_to(root).as_posix(): h.sha(p) for p in root.rglob("*") if p.is_file()},
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "rows": len(report["rows"]),
                "report_fingerprint": report["report_fingerprint"],
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--worker":
        raise SystemExit(worker(Path(sys.argv[2])))
    if len(sys.argv) == 3 and sys.argv[1] == "--prepare":
        prepare(Path(sys.argv[2]))
    else:
        main()
