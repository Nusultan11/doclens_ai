"""Admission, CUDA evidence and complete failure accounting without inference."""

import copy
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.kaggle_gpu import marker_r1_public as runner


def cohort():
    return [
        {
            "document_id": f"rp-{i:04}",
            "sha256": f"{i:064x}",
            "cloud_admission": "CLOUD_ADMITTED",
            "split": "dev",
            "license": "CC-BY-4.0",
        }
        for i in range(1, 12)
    ]


def test_exact_cohort_is_required():
    runner.admit(cohort())
    with pytest.raises(ValueError, match="eleven"):
        runner.admit(cohort()[:-1])
    rows = cohort()
    rows[1]["sha256"] = rows[0]["sha256"]
    with pytest.raises(ValueError, match="duplicate_source"):
        runner.admit(rows)


@pytest.mark.parametrize(
    "field,value",
    [("split", "test"), ("split", "qa"), ("cloud_admission", "UNRESOLVED"), ("license", "unknown")],
)
def test_denied_inputs_fail_closed(field, value):
    rows = cohort()
    rows[0][field] = value
    with pytest.raises(ValueError, match="not_admitted"):
        runner.admit(rows)


@pytest.mark.parametrize(
    "text",
    [
        "CUDA0",
        "offloaded 25/25 layers to GPU CUDA0",
        "offloaded 0/25 layers to GPU CUDA0 eval time",
    ],
)
def test_enumeration_or_offload_alone_is_not_inference(text):
    with pytest.raises(ValueError, match="inference_unverified"):
        runner.cuda_proof(text)


def test_actual_cuda_inference_proof():
    assert (
        runner.cuda_proof("CUDA0 offloaded 25/25 layers to GPU; eval time = 5 ms")[
            "offloaded_layers"
        ]
        == 25
    )


def test_setup_failure_preserves_all_22_unknowns(monkeypatch):
    monkeypatch.setattr(runner, "CONFIG", {"cohort": cohort()})
    rows = []
    runner.account_missing(rows)
    runner.account_missing(rows)
    assert len(rows) == 22
    assert all(r["receipt"]["status"] == "not_started" for r in rows)
    assert not runner.repeat_check(rows[:1] * 2)["complete_observations"]


def test_repeated_failures_do_not_become_success(monkeypatch):
    monkeypatch.setattr(runner, "CONFIG", {"cohort": cohort()})
    rows = [{"repeat": 1, "document_id": "rp-0001", "receipt": {"status": "timeout"}}]
    runner.account_missing(rows)
    assert len(rows) == 22 and rows[0]["receipt"]["status"] == "timeout"
    first = {"receipt": {"status": "memory_limit"}}
    assert runner.repeat_check([first, copy.deepcopy(first)]) == {
        "agrees": True,
        "complete_observations": False,
    }
    other = copy.deepcopy(first)
    other["receipt"]["status"] = "completed"
    assert runner.repeat_check([first, other])["agrees"] is False


def test_gpu_worker_drops_credentials_and_pins_local_assets(tmp_path, monkeypatch):
    monkeypatch.setenv("KAGGLE_API_TOKEN", "dummy-test-only")
    env = runner.environment(Path("/code"), tmp_path / "profile", Path("/models"))
    assert "KAGGLE_API_TOKEN" not in env
    assert env["CUDA_VISIBLE_DEVICES"] == "0"
    assert env["TORCH_DEVICE"] == "cpu"
    assert env["SURYA_INFERENCE_BACKEND"] == "llamacpp"
    assert env["LLAMA_CPP_EXTRA_ARGS"] == "--seed 0 -lv 5"


def test_embedded_helper_hash_is_checked(monkeypatch):
    monkeypatch.setattr(
        runner,
        "CONFIG",
        {
            "code": {
                "tools/kaggle_gpu/docling_r1_public.py": {"base64": "cGFzcw==", "sha256": "0" * 64}
            }
        },
    )
    with pytest.raises(ValueError, match="helper_identity"):
        runner.helpers()


def test_owned_cleanup_skips_reused_pids_and_records_non_running_zombies(monkeypatch):
    import psutil

    class Process:
        def __init__(self, pid, created, status):
            self.pid, self.created, self.state, self.killed = pid, created, status, False

        def create_time(self):
            return self.created

        def status(self):
            return self.state

        def is_running(self):
            return not self.killed

        def kill(self):
            self.killed = True

        def wait(self, timeout):
            return 0

    escaped = Process(1, 10, psutil.STATUS_RUNNING)
    reused = Process(2, 99, psutil.STATUS_RUNNING)
    zombie = Process(3, 10, psutil.STATUS_ZOMBIE)
    processes = {p.pid: p for p in (escaped, reused, zombie)}
    monkeypatch.setattr(psutil, "Process", lambda pid: processes[pid])
    remaining, zombies = runner.cleanup_owned({p.pid: (p, 10) for p in processes.values()})
    assert remaining == [] and zombies == [3]
    assert escaped.killed and not reused.killed and not zombie.killed


@pytest.mark.parametrize(
    "scenario,outcome",
    [
        ("normal", "completed"),
        ("rss", "memory_limit"),
        ("wall", "timeout"),
        ("processes", "process_limit"),
        ("files", "output_limit"),
    ],
)
def test_bounded_controller_cleans_escaped_child_and_preserves_outcome(
    monkeypatch, tmp_path, scenario, outcome
):
    import psutil

    state = {"child_alive": True, "worker_alive": True}

    class Process:
        def __init__(self, pid):
            self.pid = pid

        def children(self, recursive):
            return [Process(101 + i) for i in range(8 if scenario == "processes" else 1)]

        def memory_info(self):
            return SimpleNamespace(rss=1)

        def create_time(self):
            return 10

        def status(self):
            if self.pid == 100 and not state["worker_alive"]:
                raise psutil.NoSuchProcess(self.pid)
            return psutil.STATUS_RUNNING

        def is_running(self):
            return state["child_alive"]

        def kill(self):
            state["child_alive"] = False

        def wait(self, timeout):
            state["worker_alive"] = False
            return 0

    class Child:
        pid = 100

        def __init__(self, *args, **kwargs):
            self.polls = 0

        def poll(self):
            self.polls += 1
            if self.polls == 1:
                return None
            state["worker_alive"] = False
            return 0

        def wait(self, timeout):
            return 0

    policy = {"policy": {"scratch_bytes": 0 if scenario == "files" else 1024}}
    if scenario == "files":
        for name in ("after",):
            (tmp_path / name).mkdir()
            (tmp_path / name / "artifact.json").write_text("{}")
    monkeypatch.setattr(runner, "CONFIG", policy)
    monkeypatch.setattr(runner.subprocess, "Popen", Child)
    monkeypatch.setattr(psutil, "Process", Process)
    monkeypatch.setattr(psutil, "wait_procs", lambda *a, **k: ([], [Process(101)]))
    monkeypatch.setattr(runner.os, "killpg", lambda *a: None, raising=False)
    monkeypatch.setattr(runner.signal, "SIGKILL", 9, raising=False)
    monkeypatch.setattr(runner.time, "sleep", lambda *a: None)
    ticks = iter(range(1000))
    monkeypatch.setattr(runner.time, "monotonic", lambda: next(ticks) / 10)
    seconds, cap = (0 if scenario == "wall" else 10), (1 if scenario == "rss" else 1024)
    after = runner.bounded_process([], tmp_path / "after", seconds, {}, rss_limit=cap)
    assert after["status"] == outcome and not state["child_alive"]
    assert after["worker_outcome"] == outcome
    assert after["remaining_owned_pids"] == []
