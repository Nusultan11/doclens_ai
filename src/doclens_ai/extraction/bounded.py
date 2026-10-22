"""Bounded engine processes. No engine/model imports occur before the work gate.

This is resource isolation, not an OS security/egress sandbox. Registry objects
are trusted application adapters; source/model output is never unpickled.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import multiprocessing
import os
import pickle
import signal
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from doclens_ai.extraction.engines import EngineRegistry, EngineRoute
    from doclens_ai.extraction.ir import DocumentIR

EXECUTOR_VERSION = "1.0"


@dataclass(frozen=True)
class ExecutionBudget:
    wall_seconds: float = 60
    cpu_seconds: int = 30
    memory_bytes: int = 1024 * 1024 * 1024
    output_bytes: int = 64 * 1024 * 1024
    request_bytes: int = 1024 * 1024
    max_in_flight: int = 1
    gpu: bool = False

    def __post_init__(self) -> None:
        import math

        if not math.isfinite(self.wall_seconds) or self.wall_seconds <= 0:
            raise ValueError("wall budget must be finite and positive")
        for value in (
            self.cpu_seconds,
            self.memory_bytes,
            self.output_bytes,
            self.request_bytes,
            self.max_in_flight,
        ):
            if type(value) is not int or value <= 0:
                raise ValueError("execution budgets must be positive integers")
        if self.output_bytes < 64:
            raise ValueError("output budget must fit sanitized error records")


class EngineExecutionError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code
        self.retryable = code in {"timeout", "engine_crash", "backpressure"}


def _child(request, response, gate, budget):
    # Spawn bootstrap is trusted Python/application startup. Engine deserialization
    # and invocation wait until the parent has installed and verified OS limits.
    if sys.platform == "linux":
        os.setsid()
    if not gate.wait(min(budget["wall_seconds"], 10)):
        return
    os.environ.update(
        OMP_NUM_THREADS="1",
        MKL_NUM_THREADS="1",
        OPENBLAS_NUM_THREADS="1",
        TOKENIZERS_PARALLELISM="false",
        CUDA_VISIBLE_DEVICES="",
        NVIDIA_VISIBLE_DEVICES="void",
    )
    try:
        with (
            open(os.devnull, "w") as quiet,
            contextlib.redirect_stdout(quiet),
            contextlib.redirect_stderr(quiet),
        ):
            # Only trusted server-side adapter objects, never engine-produced pickle.
            registry, path, route = pickle.loads(request.recv_bytes(budget["request_bytes"]))
            result = registry.extract(path, route=route)
            payload = json.dumps(
                {"observations": [ir.model_dump(mode="json") for ir in result]},
                ensure_ascii=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode()
            if len(payload) > budget["output_bytes"]:
                response.send_bytes(b'{"error":"output_limit"}')
            else:
                response.send_bytes(payload)
    except MemoryError:
        with contextlib.suppress(BrokenPipeError, OSError):
            response.send_bytes(b'{"error":"memory_limit"}')
    except BaseException:
        with contextlib.suppress(BrokenPipeError, OSError):
            response.send_bytes(b'{"error":"engine_failure"}')
    finally:
        request.close()
        response.close()


class _WindowsJob:
    """Documented JobObject memory, user CPU time, process count and tree kill."""

    def __init__(self, pid: int, budget: ExecutionBudget):
        import ctypes as c
        from ctypes import wintypes as w

        class Basic(c.Structure):
            _fields_ = [
                ("process_time", c.c_longlong),
                ("job_time", c.c_longlong),
                ("flags", w.DWORD),
                ("min_working", c.c_size_t),
                ("max_working", c.c_size_t),
                ("active", w.DWORD),
                ("affinity", c.c_size_t),
                ("priority", w.DWORD),
                ("scheduling", w.DWORD),
            ]

        class IO(c.Structure):
            _fields_ = [
                (name, c.c_ulonglong)
                for name in (
                    "read_ops",
                    "write_ops",
                    "other_ops",
                    "read_bytes",
                    "write_bytes",
                    "other_bytes",
                )
            ]

        class Extended(c.Structure):
            _fields_ = [
                ("basic", Basic),
                ("io", IO),
                ("process_memory", c.c_size_t),
                ("job_memory", c.c_size_t),
                ("peak_process", c.c_size_t),
                ("peak_job", c.c_size_t),
            ]

        api = c.WinDLL("kernel32", use_last_error=True)
        api.CreateJobObjectW.argtypes, api.CreateJobObjectW.restype = (
            [c.c_void_p, w.LPCWSTR],
            w.HANDLE,
        )
        api.OpenProcess.argtypes, api.OpenProcess.restype = [w.DWORD, w.BOOL, w.DWORD], w.HANDLE
        api.SetInformationJobObject.argtypes = [w.HANDLE, c.c_int, c.c_void_p, w.DWORD]
        api.SetInformationJobObject.restype = w.BOOL
        api.QueryInformationJobObject.argtypes = [
            w.HANDLE,
            c.c_int,
            c.c_void_p,
            w.DWORD,
            c.c_void_p,
        ]
        api.QueryInformationJobObject.restype = w.BOOL
        api.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
        api.AssignProcessToJobObject.restype = w.BOOL
        api.CloseHandle.argtypes, api.CloseHandle.restype = [w.HANDLE], w.BOOL
        self.api, self.handle = api, api.CreateJobObjectW(None, None)
        process = None
        try:
            if not self.handle:
                raise OSError(c.get_last_error(), "job creation failed")
            info = Extended()
            # JOB_TIME | ACTIVE_PROCESS | PROCESS_MEMORY | JOB_MEMORY | KILL_ON_CLOSE.
            info.basic.flags = 0x4 | 0x8 | 0x100 | 0x200 | 0x2000
            info.basic.job_time = budget.cpu_seconds * 10_000_000
            info.basic.active = 1
            info.process_memory = info.job_memory = budget.memory_bytes
            if not api.SetInformationJobObject(self.handle, 9, c.byref(info), c.sizeof(info)):
                raise OSError(c.get_last_error(), "job limit installation failed")
            process = api.OpenProcess(0x0100 | 0x0001, False, pid)  # SET_QUOTA | TERMINATE.
            if not process or not api.AssignProcessToJobObject(self.handle, process):
                raise OSError(c.get_last_error(), "job assignment failed")
            actual = Extended()
            if not api.QueryInformationJobObject(
                self.handle, 9, c.byref(actual), c.sizeof(actual), None
            ):
                raise OSError(c.get_last_error(), "job limit verification failed")
            if (
                actual.basic.flags & info.basic.flags != info.basic.flags
                or actual.job_memory != budget.memory_bytes
                or actual.process_memory != budget.memory_bytes
                or actual.basic.active != 1
                or actual.basic.job_time != info.basic.job_time
            ):
                raise OSError("job limits differ from requested budget")
        except BaseException:
            self.close()
            raise
        finally:
            if process:
                api.CloseHandle(process)

    def close(self) -> None:
        if self.handle:
            self.api.CloseHandle(self.handle)
            self.handle = None


def _install_limits(pid: int, budget: ExecutionBudget):
    if sys.platform == "win32":
        return _WindowsJob(pid, budget)
    if sys.platform != "linux" or os.geteuid() == 0:
        raise OSError("supported unprivileged OS resource enforcement is unavailable")
    import resource

    limits = (
        (resource.RLIMIT_AS, budget.memory_bytes),
        (resource.RLIMIT_CPU, budget.cpu_seconds),
        (resource.RLIMIT_FSIZE, budget.output_bytes),
        (resource.RLIMIT_CORE, 0),
        (resource.RLIMIT_NPROC, 1),
    )
    for kind, value in limits:
        resource.prlimit(pid, kind, (value, value))
        if resource.prlimit(pid, kind) != (value, value):
            raise OSError("resource limit readback mismatch")
    return None


def _decode(payload: bytes) -> tuple[DocumentIR, ...]:
    from doclens_ai.extraction.ir import DocumentIR

    value = json.loads(payload)
    if "error" in value:
        code = value["error"]
        raise EngineExecutionError(
            code if code in {"memory_limit", "output_limit", "engine_failure"} else "engine_failure"
        )
    return tuple(DocumentIR.model_validate(item) for item in value["observations"])


class BoundedEngineExecutor:
    def __init__(self, *, max_in_flight: int = 1):
        if type(max_in_flight) is not int or max_in_flight <= 0:
            raise ValueError("executor capacity must be positive")
        self.capacity, self.active = max_in_flight, 0
        self.last_pid: int | None = None
        self.last_exitcode: int | None = None

    async def extract(
        self, registry: EngineRegistry, path: Path, *, route: EngineRoute
    ) -> tuple[DocumentIR, ...]:
        budget = route.execution_budget
        if budget.gpu:
            raise EngineExecutionError("gpu_controls_unavailable")
        if budget.max_in_flight != self.capacity:
            raise EngineExecutionError("capacity_mismatch")
        if self.active >= self.capacity:
            raise EngineExecutionError("backpressure")
        self.active += 1
        process = None
        connections = []
        guard = None
        try:
            context = multiprocessing.get_context("spawn")
            child_request, request = context.Pipe(duplex=False)
            connections.extend((child_request, request))
            response, child_response = context.Pipe(duplex=False)
            connections.extend((response, child_response))
            gate = context.Event()
            process = context.Process(
                target=_child,
                args=(child_request, child_response, gate, asdict(budget)),
                daemon=True,
            )
            payload = pickle.dumps((registry, path, route), protocol=5)
            if len(payload) > budget.request_bytes:
                raise EngineExecutionError("request_limit")
            async with asyncio.timeout(budget.wall_seconds):
                process.start()
                self.last_pid = process.pid
                child_request.close()
                child_response.close()
                try:
                    guard = _install_limits(process.pid, budget)
                except (OSError, ValueError) as exc:
                    raise EngineExecutionError("limits_unavailable") from exc
                gate.set()
                await asyncio.to_thread(request.send_bytes, payload)
                while not response.poll():
                    if not process.is_alive():
                        raise EngineExecutionError("engine_crash")
                    await asyncio.sleep(0.01)
                data = await asyncio.to_thread(response.recv_bytes, budget.output_bytes)
                return await asyncio.to_thread(_decode, data)
        except TimeoutError as exc:
            raise EngineExecutionError("timeout") from exc
        except (BrokenPipeError, EOFError, OSError) as exc:
            raise EngineExecutionError("engine_crash") from exc
        finally:
            try:
                if guard is not None:
                    guard.close()  # Windows kills the whole job, including descendants.
                if process is not None and process.pid is not None:
                    if sys.platform == "linux":
                        with contextlib.suppress(ProcessLookupError):
                            os.killpg(process.pid, signal.SIGKILL)
                    if process.is_alive():
                        process.kill()
                    await asyncio.to_thread(process.join, 2)
                    if process.is_alive():
                        raise EngineExecutionError("termination_failed")
                    self.last_exitcode = process.exitcode
                    process.close()
            finally:
                for connection in connections:
                    connection.close()
                self.active -= 1
