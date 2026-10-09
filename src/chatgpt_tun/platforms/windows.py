"""Windows daemon lifecycle primitives; no Unix signals or process groups."""
import ctypes
import subprocess
from ctypes import wintypes

def pid_alive(pid: int | None) -> bool:
    if not pid or pid <= 0:
        return False
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return ctypes.get_last_error() == 5  # access denied still means potentially alive
    try:
        code = wintypes.DWORD()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
            return False
        return code.value == 259  # STILL_ACTIVE
    finally:
        kernel32.CloseHandle(handle)

def spawn_flags() -> dict:
    return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS}

def stop_pid(pid: int, force: bool = False) -> None:
    # Windows cannot send POSIX SIGTERM to an unrelated detached process.
    # taskkill /T terminates the complete process tree.
    subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], check=False,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
