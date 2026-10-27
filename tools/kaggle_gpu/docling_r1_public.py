"""Standalone Linux R1-public executor; explicit frozen inputs, never legacy private data."""

from __future__ import annotations

import base64
import hashlib
import importlib.metadata
import json
import math
import os
import re
import signal
import socket
import subprocess
import sys
import time
import traceback
import urllib.request
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

CONFIG = {}  # Replaced exactly once by the local explicit staging builder.
EXPORTS = (
    "native.json",
    "backend-pages.json",
    "conversion-metadata.json",
    "effective-options.json",
)
NUMBER = re.compile(r"(?<![\w.])[-+−]?\d+(?:[.,]\d+)*(?:%?)(?![\w.])")
TOKEN = re.compile(r"\w+|[^\w\s]", re.UNICODE)


def sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def fingerprint(value, *, native=False):
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=native
        ).encode()
    ).hexdigest()


def write(path: Path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=True, indent=2)


def safe_path(root: Path, name: str) -> Path:
    relative = PurePosixPath(name)
    if relative.is_absolute() or not relative.parts or ".." in relative.parts or "\\" in name:
        raise ValueError("unsafe_relative_path")
    return root.joinpath(*relative.parts)


def download(url: str, path: Path, expected_sha: str, expected_bytes: int):
    if path.exists():
        raise ValueError("fresh_download_required")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    count, h = 0, hashlib.sha256()
    with (
        urllib.request.urlopen(
            urllib.request.Request(url, headers={"User-Agent": "DocLens-research/1.0"}), timeout=120
        ) as response,
        temporary.open("xb") as out,
    ):
        while block := response.read(1024**2):
            count += len(block)
            if count > expected_bytes:
                raise ValueError("download_size_exceeded")
            h.update(block)
            out.write(block)
    if count != expected_bytes or h.hexdigest() != expected_sha:
        raise ValueError("download_identity_mismatch")
    temporary.rename(path)


def install_code(root: Path):
    for name, value in CONFIG["code"].items():
        path = safe_path(root, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = base64.b64decode(value["base64"], validate=True)
        if hashlib.sha256(data).hexdigest() != value["sha256"]:
            raise ValueError("embedded_code_identity")
        path.write_bytes(data)


def environment(code: Path, profile: Path) -> dict[str, str]:
    profile.mkdir(parents=True, exist_ok=True)
    env = {k: os.environ[k] for k in ("PATH", "LD_LIBRARY_PATH", "LANG") if k in os.environ}
    env.update(
        HOME=str(profile),
        TMPDIR=str(profile),
        PYTHONPATH=str(code) + ":" + str(code / "src"),
        PYTHONHASHSEED="0",
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONUNBUFFERED="1",
        CUDA_VISIBLE_DEVICES="",
        OMP_NUM_THREADS="2",
        MKL_NUM_THREADS="2",
        OPENBLAS_NUM_THREADS="2",
        TOKENIZERS_PARALLELISM="false",
        HF_HUB_OFFLINE="1",
        TRANSFORMERS_OFFLINE="1",
        HF_HUB_DISABLE_TELEMETRY="1",
        DO_NOT_TRACK="1",
    )
    return env


def venv_command(interpreter: str, target: Path) -> list[str]:
    return [interpreter, "-m", "venv", "--without-pip", str(target)]


def deny_network():
    def denied(*args, **kwargs):
        raise RuntimeError("inference_network_denied")

    socket.socket.connect = denied
    socket.socket.connect_ex = denied


def worker(job_path: Path):
    job = json.loads(job_path.read_text())
    output, source = job_path.parent, Path(job["source"])
    try:
        import resource

        policy = CONFIG["policy"]
        resource.setrlimit(resource.RLIMIT_CPU, (policy["cpu_seconds"], policy["cpu_seconds"]))
        resource.setrlimit(
            resource.RLIMIT_FSIZE, (policy["native_output_bytes"], policy["native_output_bytes"])
        )
        resource.setrlimit(
            resource.RLIMIT_DATA, (policy["linux_data_bytes"], policy["linux_data_bytes"])
        )
        deny_network()
        actual = {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()}
        if actual != job["environment"] or sha(source) != job["sha256"]:
            raise ValueError("source_or_environment_pin_changed")
        started = time.monotonic()
        result = {
            "observations": None,
            "native_status": None,
            "linux_limits": {
                "cpu_seconds": resource.getrlimit(resource.RLIMIT_CPU),
                "file_bytes": resource.getrlimit(resource.RLIMIT_FSIZE),
                "data_bytes": resource.getrlimit(resource.RLIMIT_DATA),
            },
        }
        if job["candidate"] == "native":
            from doclens_ai.extraction.parsers import extract_file
            from tools.extraction_campaign.evidence import Observation, serialize

            value = extract_file(source)
            write(output / "native.json", value.to_dict())
            result["native_status"] = str(value.status)
            result["observations"] = serialize(
                tuple(
                    Observation(f"block/{b.order}", "text", b.text, b.source.page_number, i)
                    for i, b in enumerate(value.blocks)
                    if hasattr(b, "text")
                )
            )
        else:
            import random

            import numpy
            import torch

            from doclens_ai.extraction.docling_candidate import (
                CandidateConfig,
                _converter,
                artifact_inventory,
            )
            from tools.extraction_campaign import adapters
            from tools.extraction_campaign.evidence import serialize

            random.seed(0)
            numpy.random.seed(0)
            torch.manual_seed(0)
            torch.set_num_threads(2)
            if torch.version.cuda is not None or torch.cuda.is_available():
                raise ValueError("frozen_cpu_torch_required")
            models = Path(job["models"])
            if artifact_inventory(models) != CONFIG["required_model_sha256"]:
                raise ValueError("model_identity_mismatch")
            converter = _converter(
                CandidateConfig(
                    artifacts=models,
                    artifact_fingerprint=CONFIG["configuration"]["artifact_fingerprint"],
                    timeout_seconds=policy["docling_wall_seconds"],
                )
            )
            options = next(iter(converter.format_to_options.values())).pipeline_options
            write(output / "effective-options.json", options.model_dump(mode="json"))
            converted_at = time.monotonic()
            converted = converter.convert(source)
            result["conversion_seconds"] = time.monotonic() - converted_at
            raw = converted.document.export_to_dict()
            write(output / "native.json", raw)
            write(
                output / "backend-pages.json", [p.model_dump(mode="json") for p in converted.pages]
            )
            write(
                output / "conversion-metadata.json",
                converted.model_dump(mode="json", exclude={"input", "document", "pages"}),
            )
            result["native_status"] = getattr(converted.status, "value", str(converted.status))
            result["cpu_execution"] = {
                "torch": torch.__version__,
                "cuda": torch.version.cuda,
                "device": "cpu",
                "threads": torch.get_num_threads(),
            }
            result["loaded_model_sha256"] = artifact_inventory(models)
            try:
                result["observations"] = serialize(adapters.docling(raw))
            except Exception as exc:
                result["adapter_error"] = type(exc).__name__
                (output / "adapter-private.txt").write_text(traceback.format_exc())
        result["worker_seconds"] = time.monotonic() - started
        if sha(source) != job["sha256"]:
            raise ValueError("source_changed_after_extraction")
        write(output / "result.json", result)
        return 0
    except BaseException as exc:
        write(output / "error.json", {"type": type(exc).__name__})
        (output / "error-private.txt").write_text(traceback.format_exc())
        return 2


def bounded(command, output: Path, seconds: int, env: dict, *, rss_limit: int):
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
        while process.poll() is None:
            try:
                parent = psutil.Process(process.pid)
                members = [parent, *parent.children(recursive=True)]
                rss = 0
                for member in members:
                    try:
                        rss += member.memory_info().rss
                        observed[member.pid] = member
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
            size = sum(p.stat().st_size for p in output.rglob("*") if p.is_file())
            if size > CONFIG["policy"]["scratch_bytes"]:
                reason = "output_limit"
            if reason:
                os.killpg(process.pid, signal.SIGKILL)
                break
            time.sleep(0.05)
        code = process.wait(timeout=10)
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    _, alive = psutil.wait_procs(list(observed.values()), timeout=5)
    receipt = {
        "status": reason or ("completed" if code == 0 else "failed"),
        "exit_code": code,
        "wall_seconds": time.monotonic() - started,
        "peak_tree_rss_bytes": peak,
        "rss_samples": samples,
        "sample_seconds": 0.05,
        "remaining_owned_pids": [p.pid for p in alive],
    }
    if alive:
        receipt["status"] = "cleanup_unverified"
    return receipt


def captures(output: Path, candidate: str):
    values, errors = {}, {}
    for name in EXPORTS:
        path = output / name
        if not path.exists():
            continue
        try:
            value = json.loads(path.read_text())
            if name == "native.json" and candidate == "native":
                value.pop("latency_ms", None)
            if name == "conversion-metadata.json":
                value.pop("timings", None)
            values[name] = fingerprint(value, native=True)
        except (ValueError, UnicodeError) as exc:
            errors[name] = {"type": type(exc).__name__, "byte_sha256": sha(path)}
    return values, errors


def page_text(observations):
    pages = defaultdict(list)
    for row in observations:
        if row["page"] is not None and row["text"] is not None:
            pages[row["page"]].append(row["text"])
    return {p: " ".join(" ".join(parts).split()) for p, parts in pages.items()}


def comparison(native, candidate):
    if native is None or candidate is None:
        return {"status": "UNKNOWN", "reason": "missing_observations"}
    before, after = page_text(native), page_text(candidate)
    left, right = " ".join(before.values()), " ".join(after.values())
    a, b = Counter(TOKEN.findall(left)), Counter(TOKEN.findall(right))
    numbers_a, numbers_b = Counter(NUMBER.findall(left)), Counter(NUMBER.findall(right))
    chunks = []
    for page, text in before.items():
        words = text.split()
        for i in range(0, len(words), 8):
            chunk = " ".join(words[i : i + 8])
            chunks.append(
                {
                    "page": page,
                    "offset_words": i,
                    "text": chunk,
                    "anywhere": chunk in right,
                    "same_page": chunk in after.get(page, ""),
                }
            )
    return {
        "status": "MEASURED_BASELINE_RELATIVE_NOT_GOLD",
        "tokens_native": sum(a.values()),
        "tokens_retained": sum((a & b).values()),
        "tokens_lost": dict(a - b),
        "tokens_added": dict(b - a),
        "numeric_native": sum(numbers_a.values()),
        "numeric_retained": sum((numbers_a & numbers_b).values()),
        "numeric_lost": dict(numbers_a - numbers_b),
        "numeric_added": dict(numbers_b - numbers_a),
        "chunks": len(chunks),
        "chunks_retained": sum(c["anywhere"] for c in chunks),
        "page_chunks_retained": sum(c["same_page"] for c in chunks),
        "chunk_evidence": chunks,
    }


def percentiles(values):
    values = sorted(v for v in values if v is not None)
    if not values:
        return {"n": 0, "p50": None, "p95": None}

    def at(p):
        i = (len(values) - 1) * p
        return values[math.floor(i)] + (values[math.ceil(i)] - values[math.floor(i)]) * (i % 1)

    return {"n": len(values), "p50": at(0.5), "p95": at(0.95), "max": max(values)}


def main():
    import psutil

    root = Path("/kaggle/working/r1-public")
    root.mkdir(exist_ok=False)
    temp = Path("/tmp") / CONFIG["run_id"]
    temp.mkdir(exist_ok=False)
    code, models, venv = temp / "code", temp / "models", temp / "env"
    code.mkdir()
    install_code(code)
    write(root / "protocol.json", CONFIG)
    report = {
        "run_id": CONFIG["run_id"],
        "source_sha256": sha(Path(__file__)),
        "started_utc": datetime.now(UTC).isoformat(),
        "cohort_fingerprint": CONFIG["cohort_fingerprint"],
        "configuration_fingerprint": fingerprint(CONFIG["configuration"]),
        "hardware": {"ram": dict(psutil.virtual_memory()._asdict()), "cpus": psutil.cpu_count()},
        "quality": "NOT_EVALUATED",
        "gpu_computation": False,
        "rows": [],
    }
    results = {}
    try:
        inputs = root / "inputs"
        inputs.mkdir()
        unavailable = {}
        for source in CONFIG["cohort"]:
            try:
                if source["cloud_admission"] != "CLOUD_ADMITTED":
                    raise ValueError("source_not_cloud_admitted")
                download(
                    source["pdf_url"],
                    inputs / (source["document_id"] + ".pdf"),
                    source["sha256"],
                    source["size_bytes"],
                )
            except Exception as exc:
                unavailable[source["document_id"]] = type(exc).__name__
                (root / (source["document_id"] + "-acquisition-private.txt")).write_text(
                    traceback.format_exc()
                )
        write(
            root / "ATTRIBUTION.json",
            {
                "license": "CC-BY-4.0",
                "sources": CONFIG["cohort"],
                "modifications": "Original PDFs unchanged; extraction outputs machine-generated",
            },
        )
        subprocess.run(venv_command(sys.executable, venv), check=True, timeout=60)
        python = str(venv / "bin/python")
        bootstrap = CONFIG["pip_bootstrap"]
        pip_zip = temp / "pip.pyz"
        download(bootstrap["url"], pip_zip, bootstrap["sha256"], bootstrap["size_bytes"])
        setup_env = dict(os.environ)
        setup_env.update(CUDA_VISIBLE_DEVICES="", PIP_DISABLE_PIP_VERSION_CHECK="1")
        report["setup"] = bounded(
            [python, str(pip_zip), "install", *CONFIG["packages"]],
            root / "setup",
            1200,
            setup_env,
            rss_limit=4 * 1024**3,
        )
        if report["setup"]["status"] != "completed":
            raise RuntimeError("isolated_dependencies_failed")
        for item in CONFIG["model_files"]:
            download(
                item["url"], safe_path(models, item["path"]), item["sha256"], item["size_bytes"]
            )
        write(
            root / "model-inventory.json",
            {m["path"]: sha(safe_path(models, m["path"])) for m in CONFIG["model_files"]},
        )
        probe_env = environment(code, temp / "probe-profile")
        probe = (
            "import importlib.metadata as m,json,sys;"
            "print(json.dumps({'python':sys.version,'packages':"
            "{d.metadata['Name']:d.version for d in m.distributions()}}))"
        )
        runtime = json.loads(
            subprocess.check_output([python, "-c", probe], env=probe_env, text=True, timeout=30)
        )
        write(root / "environment.json", runtime)
        for repetition in (1, 2):
            for source in CONFIG["cohort"]:
                for candidate in ("native", "docling"):
                    identity = source["document_id"]
                    output = root / f"repeat-{repetition}" / identity / candidate
                    output.mkdir(parents=True)
                    job = {
                        "candidate": candidate,
                        "source": str(inputs / (identity + ".pdf")),
                        "sha256": source["sha256"],
                        "models": str(models),
                        "environment": runtime["packages"],
                    }
                    write(output / "job.json", job)
                    if (
                        identity in unavailable
                        or psutil.virtual_memory().available
                        < CONFIG["policy"]["minimum_available_ram_bytes"]
                    ):
                        receipt = {
                            "status": "source_unavailable"
                            if identity in unavailable
                            else "resource_blocked_before_start",
                            "wall_seconds": None,
                            "peak_tree_rss_bytes": None,
                        }
                    else:
                        env = environment(code, output / "profile")
                        receipt = bounded(
                            [python, __file__, "--worker", str(output / "job.json")],
                            output,
                            CONFIG["policy"][candidate + "_wall_seconds"],
                            env,
                            rss_limit=CONFIG["policy"]["process_tree_rss_bytes"],
                        )
                    write(output / "receipt.json", receipt)
                    result = (
                        json.loads((output / "result.json").read_text())
                        if (output / "result.json").exists()
                        else {}
                    )
                    results[repetition, identity, candidate] = result.get("observations")
                    hashes, errors = captures(output, candidate)
                    row = {
                        "repeat": repetition,
                        "document_id": identity,
                        "candidate": candidate,
                        "source_sha256": source["sha256"],
                        "receipt": receipt,
                        "native_status": result.get("native_status"),
                        "adapter_error": result.get("adapter_error"),
                        "capture_fingerprints": hashes,
                        "capture_errors": errors,
                        "observation_fingerprint": fingerprint(result["observations"])
                        if result.get("observations") is not None
                        else None,
                        "worker_context_fingerprint": fingerprint(
                            {
                                k: v
                                for k, v in result.items()
                                if k not in {"worker_seconds", "conversion_seconds"}
                            }
                        )
                        if result
                        else None,
                        "conversion_seconds": result.get("conversion_seconds"),
                    }
                    report["rows"].append(row)
                    print(
                        json.dumps(
                            {
                                "repeat": repetition,
                                "id": identity,
                                "candidate": candidate,
                                "status": receipt["status"],
                                "model_status": row["native_status"],
                                "seconds": receipt["wall_seconds"],
                            }
                        ),
                        flush=True,
                    )
        for source in CONFIG["cohort"]:
            path = inputs / (source["document_id"] + ".pdf")
            if path.exists() and sha(path) != source["sha256"]:
                raise ValueError("source_postcheck_mismatch")
        if any(sha(safe_path(models, m["path"])) != m["sha256"] for m in CONFIG["model_files"]):
            raise ValueError("model_postcheck_mismatch")
        if any(
            sha(safe_path(code, name)) != item["sha256"] for name, item in CONFIG["code"].items()
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
    for repetition in (1, 2):
        for source in CONFIG["cohort"]:
            identity = source["document_id"]
            for candidate in ("native", "docling"):
                if not any(
                    r["repeat"] == repetition
                    and r["document_id"] == identity
                    and r["candidate"] == candidate
                    for r in report["rows"]
                ):
                    report["rows"].append(
                        {
                            "repeat": repetition,
                            "document_id": identity,
                            "candidate": candidate,
                            "receipt": {"status": "not_started"},
                            "source_sha256": source["sha256"],
                        }
                    )
    report["comparisons"] = []
    for repetition in (1, 2):
        for source in CONFIG["cohort"]:
            identity = source["document_id"]
            report["comparisons"].append(
                {
                    "repeat": repetition,
                    "document_id": identity,
                    "metrics": comparison(
                        results.get((repetition, identity, "native")),
                        results.get((repetition, identity, "docling")),
                    ),
                }
            )
    repeat_checks = []
    for source in CONFIG["cohort"]:
        for candidate in ("native", "docling"):
            rows = [
                r
                for r in report["rows"]
                if r["document_id"] == source["document_id"] and r["candidate"] == candidate
            ]
            fields = (
                "native_status",
                "capture_fingerprints",
                "capture_errors",
                "observation_fingerprint",
                "adapter_error",
                "worker_context_fingerprint",
            )
            agrees = (
                all(rows[0].get(k) == rows[1].get(k) for k in fields)
                and rows[0]["receipt"]["status"] == rows[1]["receipt"]["status"]
            )
            repeat_checks.append(
                {
                    "document_id": source["document_id"],
                    "candidate": candidate,
                    "agrees": agrees,
                    "complete_observations": all(
                        r.get("observation_fingerprint") is not None for r in rows
                    ),
                }
            )
    report["reproducibility"] = repeat_checks
    report["resources"] = {
        c: {
            "wall_seconds": percentiles(
                [r["receipt"].get("wall_seconds") for r in report["rows"] if r["candidate"] == c]
            ),
            "rss_bytes": percentiles(
                [
                    r["receipt"].get("peak_tree_rss_bytes")
                    for r in report["rows"]
                    if r["candidate"] == c
                ]
            ),
        }
        for c in ("native", "docling")
    }
    report["finished_utc"] = datetime.now(UTC).isoformat()
    report["report_fingerprint"] = fingerprint(report)
    write(root / "report.json", report)
    write(
        root / "checksums.json",
        {p.relative_to(root).as_posix(): sha(p) for p in root.rglob("*") if p.is_file()},
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
    return 0


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--worker":
        raise SystemExit(worker(Path(sys.argv[2])))
    raise SystemExit(main())
