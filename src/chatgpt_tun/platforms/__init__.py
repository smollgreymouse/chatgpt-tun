"""Platform selector: platform-specific lifecycle, shared MCP logic."""
import os
import sys

if os.name == "nt":
    from .windows import pid_alive, spawn_flags, stop_pid
    PLATFORM = "windows"
elif sys.platform == "darwin":
    from .macos import pid_alive, spawn_flags, stop_pid
    PLATFORM = "macos"
else:
    from .linux import pid_alive, spawn_flags, stop_pid
    PLATFORM = "linux"
