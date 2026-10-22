"""Actual OS resource/process faults, not mocked timeout/kill behavior."""

import asyncio
import json
from dataclasses import replace

import pytest

from doclens_ai.extraction.bounded import (
    BoundedEngineExecutor,
    EngineExecutionError,
    ExecutionBudget,
)
from doclens_ai.extraction.engines import EnginePin, EngineRegistry, EngineRoute, default_route
from tests.bounded_probe import ProbeEngine


def route(mode="healthy", **budgets):
    return EngineRoute(
        engines=(
            EnginePin(
                name="probe",
                revision="1",
                implementation_sha256="a" * 64,
                options_json=json.dumps({"mode": mode}, sort_keys=True, separators=(",", ":")),
            ),
        ),
        runtime_manifest_json=default_route().runtime_manifest_json,
        execution_budget=replace(ExecutionBudget(wall_seconds=10), **budgets),
    )


def source(tmp_path):
    path = tmp_path / "source.pdf"
    path.write_bytes(b"%PDF-1.7\nbounded\n%%EOF")
    return path


def test_actual_process_returns_json_ir_and_releases_slot(tmp_path):
    async def exercise():
        executor = BoundedEngineExecutor()
        result = await executor.extract(
            EngineRegistry((ProbeEngine(),)), source(tmp_path), route=route()
        )
        assert result[0].elements[0].text == "bounded fixture"
        assert executor.active == 0 and executor.last_pid

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "mode,budget,code",
    [
        ("hang", {"wall_seconds": 2}, "timeout"),
        ("crash", {}, "engine_crash"),
        ("oom", {"memory_bytes": 256 * 1024 * 1024}, "memory_limit"),
        ("cpu", {"cpu_seconds": 1, "wall_seconds": 8}, "engine_crash"),
        ("output", {"output_bytes": 1024}, "output_limit"),
    ],
)
def test_real_hang_crash_oom_cpu_and_output_limits_leave_worker_alive(tmp_path, mode, budget, code):
    async def exercise():
        executor = BoundedEngineExecutor()
        registry, path = EngineRegistry((ProbeEngine(),)), source(tmp_path)
        with pytest.raises(EngineExecutionError) as error:
            await executor.extract(registry, path, route=route(mode, **budget))
        assert error.value.code == code
        if mode in {"hang", "cpu"}:
            assert path.with_suffix(".started").exists()
        if mode == "crash":
            assert executor.last_exitcode == 73
        assert executor.active == 0
        assert (await executor.extract(registry, path, route=route()))[0].elements

    asyncio.run(exercise())


def test_cancellation_and_backpressure_keep_event_loop_and_next_job_alive(tmp_path):
    async def exercise():
        executor = BoundedEngineExecutor()
        registry, path = EngineRegistry((ProbeEngine(),)), source(tmp_path)
        task = asyncio.create_task(executor.extract(registry, path, route=route("hang")))
        ticks = 0
        try:
            while executor.last_pid is None:
                ticks += 1
                await asyncio.sleep(0.01)
            with pytest.raises(EngineExecutionError, match="backpressure"):
                await executor.extract(registry, path, route=route())
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await asyncio.wait_for(task, 3)
            assert executor.active == 0 and ticks > 0
            assert (await executor.extract(registry, path, route=route()))[0].elements
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    asyncio.run(exercise())


def test_unavailable_os_limits_fail_before_engine_work(tmp_path, monkeypatch):
    from doclens_ai.extraction import bounded

    def unavailable(*args):
        raise OSError("injected OS setup failure")

    monkeypatch.setattr(bounded, "_install_limits", unavailable)

    async def exercise():
        executor = BoundedEngineExecutor()
        path = source(tmp_path)
        with pytest.raises(EngineExecutionError, match="limits_unavailable"):
            await executor.extract(EngineRegistry((ProbeEngine(),)), path, route=route("touch"))
        assert not path.with_suffix(".started").exists()
        assert executor.active == 0

    asyncio.run(exercise())


def test_gpu_route_is_explicitly_unsupported_without_claiming_vram_enforcement(tmp_path):
    async def exercise():
        executor = BoundedEngineExecutor()
        with pytest.raises(EngineExecutionError, match="gpu_controls_unavailable"):
            await executor.extract(
                EngineRegistry((ProbeEngine(),)), source(tmp_path), route=route(gpu=True)
            )
        assert executor.last_pid is None and executor.active == 0

    asyncio.run(exercise())
