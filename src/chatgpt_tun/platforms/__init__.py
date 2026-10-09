"""Platform-specific process and lifecycle operations.

Keep Linux's POSIX behavior unchanged; isolate Windows semantics here.
"""
import os
import sys
if os.name == "nt":
    from .windows import pid_alive, spawn_flags, stop_pid
else:
    from .posix import pid_alive, spawn_flags, stop_pid
PLATFORM = "windows" if os.name == "nt" else ("macos" if sys.platform == "darwin" else "linux")
