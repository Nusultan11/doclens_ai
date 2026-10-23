"""Research-only Windows job limits, including owned auxiliary model processes."""

from __future__ import annotations

import ctypes as c
import os
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


class WindowsJob:
    def __init__(self, pid: int, *, memory_bytes: int, cpu_seconds: int, processes: int = 8):
        if os.name != "nt" or min(pid, memory_bytes, cpu_seconds, processes) <= 0:
            raise ValueError("windows_job_controls_unavailable")
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
        api.AssignProcessToJobObject.argtypes, api.AssignProcessToJobObject.restype = (
            [w.HANDLE, w.HANDLE],
            w.BOOL,
        )
        api.CloseHandle.argtypes, api.CloseHandle.restype = [w.HANDLE], w.BOOL
        self.api, self.handle = api, api.CreateJobObjectW(None, None)
        process = None
        try:
            if not self.handle:
                raise OSError("job_creation_failed")
            info = Extended()
            info.basic.flags = 0x4 | 0x8 | 0x100 | 0x200 | 0x2000
            info.basic.job_time, info.basic.active = cpu_seconds * 10_000_000, processes
            info.process_memory = info.job_memory = memory_bytes
            if not api.SetInformationJobObject(self.handle, 9, c.byref(info), c.sizeof(info)):
                raise OSError("job_limits_unavailable")
            process = api.OpenProcess(0x0100 | 0x0001, False, pid)
            if not process or not api.AssignProcessToJobObject(self.handle, process):
                raise OSError("job_assignment_failed")
            actual = Extended()
            if not api.QueryInformationJobObject(
                self.handle, 9, c.byref(actual), c.sizeof(actual), None
            ):
                raise OSError("job_verification_failed")
            if (
                actual.basic.flags & info.basic.flags != info.basic.flags
                or actual.basic.active != processes
                or actual.job_memory != memory_bytes
                or actual.process_memory != memory_bytes
                or actual.basic.job_time != info.basic.job_time
            ):
                raise OSError("job_readback_mismatch")
        except BaseException:
            self.close()
            raise
        finally:
            if process:
                api.CloseHandle(process)

    def close(self):
        if self.handle:
            self.api.CloseHandle(self.handle)
            self.handle = None
