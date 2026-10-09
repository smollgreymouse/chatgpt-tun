"""POSIX daemon lifecycle primitives for Linux and macOS."""
import os
import signal
import subprocess

def pid_alive(pid: int | None) -> bool:
    if not pid or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True

def spawn_flags() -> dict:
    return {"start_new_session": True}

def stop_pid(pid: int, force: bool = False) -> None:
    os.killpg(pid, signal.SIGKILL if force else signal.SIGTERM)
