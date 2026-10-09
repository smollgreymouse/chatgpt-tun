from __future__ import annotations

import contextlib
import os
import socket
import subprocess
import sys
import time
from typing import Any

from .platforms import pid_alive, spawn_flags, stop_pid
from .state import clear_runtime, daemon_lifecycle_lock, load_config, load_runtime, log_path


def daemon_running() -> bool:
    runtime = load_runtime()
    return pid_alive(runtime.get("daemon_pid"))


def _port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.3):
            return True
    except OSError:
        return False


def start_daemon(wait_seconds: float = 12.0) -> dict[str, Any]:
    with daemon_lifecycle_lock():
        return _start_daemon_unlocked(wait_seconds)


def _start_daemon_unlocked(wait_seconds: float) -> dict[str, Any]:
    runtime = load_runtime()
    if pid_alive(runtime.get("daemon_pid")):
        return runtime
    clear_runtime()

    log_file = log_path()
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("ab", buffering=0) as log:
        kwargs: dict[str, Any] = {
            "stdin": subprocess.DEVNULL,
            "stdout": log,
            "stderr": subprocess.STDOUT,
            "close_fds": True,
        }
        kwargs.update(spawn_flags())
        process = subprocess.Popen(
            [sys.executable, "-m", "chatgpt_tun.daemon"],
            **kwargs,
        )

    config = load_config()
    deadline = time.monotonic() + wait_seconds
    while time.monotonic() < deadline:
        runtime = load_runtime()
        if runtime.get("daemon_pid") == process.pid and _port_open(str(config["host"]), int(config["port"])):
            return runtime
        if not pid_alive(process.pid):
            break
        time.sleep(0.15)

    runtime = load_runtime()
    error = runtime.get("error")
    suffix = f": {error}" if error else ""
    raise RuntimeError(
        f"chatgpt-tun daemon failed to become ready{suffix}. "
        f"See {log_file}"
    )


def ensure_daemon() -> dict[str, Any]:
    if daemon_running():
        return load_runtime()
    return start_daemon()


def stop_daemon(timeout: float = 5.0) -> bool:
    with daemon_lifecycle_lock():
        return _stop_daemon_unlocked(timeout)


def _stop_daemon_unlocked(timeout: float) -> bool:
    runtime = load_runtime()
    pid = runtime.get("daemon_pid")
    if not pid_alive(pid):
        clear_runtime()
        return False

    assert isinstance(pid, int)
    try:
        stop_pid(pid)
    except ProcessLookupError:
        clear_runtime()
        return False

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not pid_alive(pid):
            clear_runtime(expected_pid=pid)
            return True
        time.sleep(0.1)

    with contextlib.suppress(ProcessLookupError):
        stop_pid(pid, force=True)
    clear_runtime(expected_pid=pid)
    return True


def wait_for_connector_url(timeout: float = 20.0) -> str | None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        runtime = load_runtime()
        if runtime.get("ngrok_ready") and runtime.get("connector_url"):
            return str(runtime["connector_url"])
        if runtime.get("ngrok_error") or runtime.get("error"):
            return None
        time.sleep(0.25)
    return None


def read_log_tail(lines: int = 80) -> str:
    path = log_path()
    if not path.exists():
        return ""
    content = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(content[-max(1, lines) :])
