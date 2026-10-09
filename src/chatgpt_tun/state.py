from __future__ import annotations

import contextlib
import json
import os
import secrets
import tempfile
from pathlib import Path
from typing import Any, Callable, Iterator

from .platforms import advisory_lock

APP_NAME = "chatgpt-tun"


def state_dir() -> Path:
    override = os.environ.get("CHATGPT_TUN_HOME")
    if override:
        root = Path(override).expanduser()
    else:
        xdg = os.environ.get("XDG_STATE_HOME")
        root = Path(xdg).expanduser() / APP_NAME if xdg else Path.home() / ".local" / "state" / APP_NAME
    root.mkdir(parents=True, exist_ok=True)
    return root


def config_path() -> Path:
    return state_dir() / "config.json"


def registry_path() -> Path:
    return state_dir() / "registry.json"


def runtime_path() -> Path:
    return state_dir() / "runtime.json"


def log_path() -> Path:
    return state_dir() / "daemon.log"


def _default_config() -> dict[str, Any]:
    return {
        "version": 1,
        "host": "127.0.0.1",
        "port": 8765,
        "ngrok_bin": "ngrok",
        "public_url": None,
        "endpoint_token": secrets.token_urlsafe(32),
    }


def _default_registry() -> dict[str, Any]:
    return {"version": 1, "projects": {}}


@contextlib.contextmanager
def _file_lock(path: Path) -> Iterator[None]:
    """Cross-process advisory lock. Linux/macOS use flock; Windows uses msvcrt."""
    lock_path = path.with_suffix(path.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as fh:
        with advisory_lock(fh):
            yield


@contextlib.contextmanager
def daemon_lifecycle_lock() -> Iterator[None]:
    """Serialize daemon start/stop across independent ctun CLI processes."""
    with _file_lock(state_dir() / "daemon-lifecycle"):
        yield


def _read_json_unlocked(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Cannot read state file {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"State file {path} must contain a JSON object")
    return data


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, sort_keys=True)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        with contextlib.suppress(FileNotFoundError):
            tmp.unlink()


def _load_or_create(path: Path, default_factory: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    with _file_lock(path):
        if not path.exists():
            data = default_factory()
            _atomic_write_json(path, data)
            return data
        return _read_json_unlocked(path, default_factory())


def load_config() -> dict[str, Any]:
    return _load_or_create(config_path(), _default_config)


def update_config(mutator: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
    path = config_path()
    with _file_lock(path):
        data = _read_json_unlocked(path, _default_config())
        mutator(data)
        _atomic_write_json(path, data)
        return data


def load_registry() -> dict[str, Any]:
    return _load_or_create(registry_path(), _default_registry)


def update_registry(mutator: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
    path = registry_path()
    with _file_lock(path):
        data = _read_json_unlocked(path, _default_registry())
        data.setdefault("projects", {})
        mutator(data)
        _atomic_write_json(path, data)
        return data


def load_runtime() -> dict[str, Any]:
    path = runtime_path()
    with _file_lock(path):
        return _read_json_unlocked(path, {})


def write_runtime(data: dict[str, Any]) -> None:
    path = runtime_path()
    with _file_lock(path):
        _atomic_write_json(path, data)


def update_runtime(mutator: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
    path = runtime_path()
    with _file_lock(path):
        data = _read_json_unlocked(path, {})
        mutator(data)
        _atomic_write_json(path, data)
        return data


def clear_runtime(expected_pid: int | None = None) -> None:
    path = runtime_path()
    with _file_lock(path):
        if not path.exists():
            return
        if expected_pid is not None:
            data = _read_json_unlocked(path, {})
            if data.get("daemon_pid") != expected_pid:
                return
        with contextlib.suppress(FileNotFoundError):
            path.unlink()


def normalize_public_url(url: str) -> str:
    return url.rstrip("/")


def endpoint_path(config: dict[str, Any]) -> str:
    token = str(config["endpoint_token"])
    return f"/{token}/mcp"


def connector_url(config: dict[str, Any]) -> str | None:
    public = config.get("public_url")
    if not public:
        return None
    return normalize_public_url(str(public)) + endpoint_path(config)
