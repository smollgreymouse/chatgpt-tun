"""Linux platform primitives, kept independent of macOS and Windows."""
from .posix import advisory_lock, pid_alive, spawn_flags, stop_pid
