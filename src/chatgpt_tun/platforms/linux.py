"""Linux platform primitives, kept independent of macOS and Windows."""
from .posix import pid_alive, spawn_flags, stop_pid
