"""Run frozen offline candidates serially, retaining every failed attempt and native output."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from pathlib import Path

from tools.extraction_campaign.evidence import Observation, digest, score, serialize
from tools.extraction_campaign.protocol import GOLD, MANIFEST, ROOT, code_pins, sha, write_new


def inventory(root: Path) -> dict[str, str]:
    if not root.is_dir() or root.is_symlink():
        raise ValueError("model_directory_unavailable")
    result = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("model_symlink_rejected")
        if path.is_file() and not any(p.startswith(".") for p in path.relative_to(root).parts):
            result[path.relative_to(root).as_posix()] = sha(path)
    if not result:
        raise ValueError("model_artifacts_empty")
    return result


def environment(python: Path) -> dict:
    command = (
        "import importlib.metadata as m,json,sys; "
        "print(json.dumps({'packages':{d.metadata['Name']:d.version for d in m.distributions()},"
        "'python':sys.version,'executable':sys.executable}))"
    )
    return json.loads(subprocess.check_output([str(python), "-c", command], text=True, timeout=30))


def run_one(python: Path, job: dict, output: Path) -> dict:
    import psutil

    from tools.extraction_campaign.resources import WindowsJob, windows_job_supported

    if output.exists() or not output.resolve().is_relative_to(ROOT / "evaluation-output"):
        raise ValueError("fresh_private_attempt_required")
    output.mkdir(parents=True)
    policy = job["policy"]
    write_new(output / "job.json", job)
    if not windows_job_supported():
        result = {
            "status": "resource_blocked_before_start",
            "reason": "windows_job_controls_unavailable",
            "attempted_inference": False,
            "wall_seconds": None,
            "peak_tree_rss_bytes": None,
            "exit_code": None,
        }
        write_new(output / "receipt.json", result)
        return result
    if psutil.virtual_memory().available < policy.get("minimum_available_ram_bytes", 0):
        result = {
            "status": "resource_blocked_before_start",
            "attempted_inference": False,
            "wall_seconds": None,
            "peak_tree_rss_bytes": None,
            "exit_code": None,
        }
        write_new(output / "receipt.json", result)
        return result
    profile = output / "profile"
    profile.mkdir()
    temp = output / "temp"
    temp.mkdir()
    keys = (
        "SYSTEMROOT",
        "WINDIR",
        "PATH",
        "COMSPEC",
        "PATHEXT",
        "NUMBER_OF_PROCESSORS",
        "PROCESSOR_ARCHITECTURE",
        "SYSTEMDRIVE",
        "PROGRAMDATA",
    )
    env = {k.upper(): v for k, v in os.environ.items() if k.upper() in keys}
    env.update(
        {
            "USERPROFILE": str(profile),
            "APPDATA": str(profile),
            "LOCALAPPDATA": str(profile),
            "TEMP": str(temp),
            "TMP": str(temp),
            "PYTHONPATH": str(ROOT) + os.pathsep + str(ROOT / "src"),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONUNBUFFERED": "1",
            "HF_HUB_OFFLINE": "1",
            "HF_DATASETS_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "HF_HUB_DISABLE_TELEMETRY": "1",
            "DO_NOT_TRACK": "1",
            "CUDA_VISIBLE_DEVICES": "",
            "OMP_NUM_THREADS": "2",
            "MKL_NUM_THREADS": "2",
            "OPENBLAS_NUM_THREADS": "2",
            "TOKENIZERS_PARALLELISM": "false",
            "TORCH_DEVICE": "cpu",
            "PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK": "True",
        }
    )
    env.update(job.get("environment_options", {}))
    process, guard, worker = None, None, None
    peak, started, status, observed_pids = 0, time.monotonic(), "failed", set()
    try:
        with (output / "console-private.txt").open("wb") as log:
            process = subprocess.Popen(
                [
                    str(python.resolve()),
                    "-B",
                    "-m",
                    "tools.extraction_campaign.worker",
                    str(output.resolve()),
                ],
                stdout=log,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                cwd=output,
                env=env,
            )
            ready = output / "ready.json"
            while not ready.exists():
                if process.poll() is not None:
                    raise RuntimeError("worker_bootstrap_failed")
                if time.monotonic() - started > min(15, policy["wall_seconds_per_document"]):
                    raise TimeoutError("worker_bootstrap_timeout")
                time.sleep(0.01)
            pid = json.loads(ready.read_text(encoding="utf-8"))["pid"]
            # Windows venv python may be a launcher: fence the actual gated worker PID.
            worker = psutil.Process(pid)
            guard = WindowsJob(
                pid,
                memory_bytes=policy["os_commit_bytes"],
                cpu_seconds=policy["cpu_seconds"],
                processes=8,
            )
            (output / "gate").touch(exist_ok=False)
            next_notice = started + 30
            while process.poll() is None:
                members = [worker]
                try:
                    members += worker.children(recursive=True)
                except psutil.NoSuchProcess:
                    pass
                rss = 0
                for member in members:
                    try:
                        rss += member.memory_info().rss
                        observed_pids.add(member.pid)
                    except psutil.NoSuchProcess:
                        pass
                peak = max(peak, rss)
                elapsed = time.monotonic() - started
                if rss > policy["process_tree_rss_bytes"]:
                    status = "memory_limit"
                    break
                if elapsed > policy["wall_seconds_per_document"]:
                    status = "timeout"
                    break
                native_bytes = sum(
                    p.stat().st_size for p in output.glob("*.json") if p.name != "job.json"
                )
                total_bytes = sum(p.stat().st_size for p in output.rglob("*") if p.is_file())
                if (
                    native_bytes > policy["native_output_bytes"]
                    or total_bytes > policy["scratch_bytes"]
                ):
                    status = "output_limit"
                    break
                if time.monotonic() > next_notice:
                    print(
                        json.dumps(
                            {
                                "candidate": job["candidate"],
                                "document_id": job.get("document_id"),
                                "running_seconds": round(elapsed),
                                "rss_bytes": rss,
                            }
                        ),
                        flush=True,
                    )
                    next_notice += 30
                time.sleep(0.05)
            else:
                status = "completed" if process.returncode == 0 else "failed"
    except Exception as exc:
        status = "control_failed"
        write_new(output / "control-error.json", {"type": type(exc).__name__})
    finally:
        if guard:
            guard.close()
        if process:
            try:
                parent = psutil.Process(process.pid)
                for child in reversed(parent.children(recursive=True)):
                    try:
                        child.kill()
                    except psutil.NoSuchProcess:
                        pass
                if process.poll() is None:
                    process.kill()
            except psutil.NoSuchProcess:
                pass
            process.wait(timeout=5)
    remaining = []
    for pid in observed_pids:
        if psutil.pid_exists(pid):
            remaining.append(pid)
    if status == "completed":
        native_bytes = sum(p.stat().st_size for p in output.glob("*.json") if p.name != "job.json")
        total_bytes = sum(p.stat().st_size for p in output.rglob("*") if p.is_file())
        if native_bytes > policy["native_output_bytes"] or total_bytes > policy["scratch_bytes"]:
            status = "output_limit"
    if remaining:
        status = "cleanup_unverified"
    result = {
        "status": status,
        "attempted_inference": (output / "gate").exists(),
        "wall_seconds": time.monotonic() - started,
        "peak_tree_rss_bytes": peak,
        "exit_code": process.returncode if process else None,
        "observed_process_count": len(observed_pids),
        "remaining_owned_processes": remaining,
        "gpu_peak_bytes": None,
        "gpu_execution": False,
    }
    if (output / "error.json").exists():
        result["error_type"] = json.loads((output / "error.json").read_text())["type"]
    # Full immutable list includes private native outputs/logs, but is safe metadata only.
    result["artifact_sha256"] = {
        p.relative_to(output).as_posix(): sha(p)
        for p in output.rglob("*")
        if p.is_file() and p.name not in {"gate"}
    }
    write_new(output / "receipt.json", result)
    return result


def run(protocol_dir: Path, configuration: Path, output: Path, ids: list[str], repetitions: int):
    from doclens_ai.extraction.fidelity_eval import _read_sources
    from doclens_ai.extraction.fidelity_gold import load_gold

    protocol = json.loads((protocol_dir / "protocol.json").read_text())
    expected = protocol.pop("fingerprint")
    if digest(protocol) != expected:
        raise ValueError("protocol_fingerprint_mismatch")
    protocol["fingerprint"] = expected
    for name, expected_sha in protocol["input_sha256"].items():
        if sha(ROOT / name) != expected_sha:
            raise ValueError("input_changed")
    for name, expected_sha in protocol["code_sha256"].items():
        if sha(ROOT / name) != expected_sha:
            raise ValueError("registered_code_changed_use_new_revision")
    spec = json.loads(configuration.read_text())
    python = ROOT / spec["python"]
    env = environment(python)
    models = inventory(ROOT / spec["model_root"]) if spec.get("model_root") else {}
    if spec.get("model_fingerprint") != digest(models):
        raise ValueError("model_pin_mismatch")
    if spec.get("environment_fingerprint") != digest(env):
        raise ValueError("environment_pin_mismatch")
    known = {s["document_id"] for s in protocol["sources"]}
    selected = ids or sorted(known)
    if (
        len(selected) != len(set(selected))
        or not set(selected) <= known
        or repetitions not in {1, 2}
    ):
        raise ValueError("run_selection_rejected")
    if output.exists() or not output.resolve().is_relative_to(ROOT / "evaluation-output"):
        raise ValueError("fresh_run_required")
    output.mkdir(parents=True)
    frozen = {
        "protocol": expected,
        "specification": spec,
        "environment": env,
        "model_inventory": models,
        "code_sha256": code_pins(),
        "git_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "document_ids": selected,
        "repetitions": repetitions,
    }
    frozen["fingerprint"] = digest(frozen)
    write_new(output / "registration.json", frozen)
    private = json.loads((protocol_dir / "private-paths.json").read_text())
    records = {r.document_id: r for r in load_gold(GOLD, _read_sources(MANIFEST))}
    rows = []
    for repetition in range(1, repetitions + 1):
        for identity in selected:
            record = records[identity]
            attempt = output / f"repeat-{repetition}" / identity
            job = {
                "candidate": spec["candidate"],
                "document_id": identity,
                "source_path": private[identity],
                "source_sha256": record.source_sha256,
                "source_size_bytes": record.source_size_bytes,
                "configuration": spec["configuration"],
                "environment": env["packages"],
                "environment_options": spec.get("environment_options", {}),
                "model_inventory": models,
                "policy": protocol["policy"] | spec.get("budgets", {}),
            }
            receipt = run_one(python, job, attempt)
            observations = None
            native_status = None
            if receipt["status"] == "completed":
                value = json.loads((attempt / "result.json").read_text())
                native_status = value["native_status"]
                observations = tuple(Observation(**v) for v in value["observations"])
            measurements = score(record, observations)
            native_fingerprints = {}
            for name in (
                "native.json",
                "backend-pages.json",
                "legacy.json",
                "conversion-metadata.json",
            ):
                if (attempt / name).exists():
                    captured = json.loads((attempt / name).read_text(encoding="utf-8"))
                    if name == "legacy.json" or (
                        name == "native.json" and spec["candidate"] == "native"
                    ):
                        captured.pop("latency_ms", None)
                    if name == "conversion-metadata.json":
                        captured.pop("timings", None)
                    native_fingerprints[name] = digest(captured)
            row = {
                "document_id": identity,
                "repeat": repetition,
                "native_status": native_status,
                "receipt": receipt,
                "metrics": measurements,
                "native_fingerprints_except_explicit_latency_ms": native_fingerprints,
                "observation_fingerprint": digest(serialize(observations))
                if observations is not None
                else None,
            }
            rows.append(row)
            write_new(attempt / "scores.json", measurements)
            print(
                json.dumps(
                    {
                        "candidate": spec["candidate"],
                        "repeat": repetition,
                        "document_id": identity,
                        "status": receipt["status"],
                        "seconds": round(receipt["wall_seconds"] or 0, 2),
                    }
                ),
                flush=True,
            )
    if models != (inventory(ROOT / spec["model_root"]) if spec.get("model_root") else {}):
        raise ValueError("model_changed_during_run")
    if environment(python) != env or code_pins() != frozen["code_sha256"]:
        raise ValueError("environment_or_code_changed_during_run")
    for name, expected_sha in protocol["input_sha256"].items():
        if sha(ROOT / name) != expected_sha:
            raise ValueError("input_changed_during_run")
    for identity in selected:
        if sha(Path(private[identity])) != records[identity].source_sha256:
            raise ValueError("original_changed_during_run")
    repeat_agreement = None
    if repetitions == 2:
        repeat_agreement = all(
            a["metrics"] == b["metrics"]
            and a["observation_fingerprint"] == b["observation_fingerprint"]
            and a["native_fingerprints_except_explicit_latency_ms"]
            == b["native_fingerprints_except_explicit_latency_ms"]
            and a["receipt"]["status"] == b["receipt"]["status"]
            for a, b in zip(rows[: len(selected)], rows[len(selected) :], strict=True)
        )
    report = {
        "registration_fingerprint": frozen["fingerprint"],
        "candidate": spec["candidate"],
        "configuration": spec["configuration"],
        "rows": rows,
        "attempted": len(rows),
        "completed": sum(r["receipt"]["status"] == "completed" for r in rows),
        "repeat_agreement": repeat_agreement,
        "quality_gate": "NOT_EVALUATED",
    }
    write_new(output / "report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("protocol", "configuration", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--id", action="append", default=[])
    parser.add_argument("--repetitions", type=int, choices=(1, 2), default=2)
    args = parser.parse_args()
    run(args.protocol, args.configuration, args.output, args.id, args.repetitions)


if __name__ == "__main__":
    main()
