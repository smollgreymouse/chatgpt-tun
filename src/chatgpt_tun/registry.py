from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .state import load_registry, update_registry


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolved_dir(path: str | Path) -> Path:
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_dir():
        raise ValueError(f"Project path is not a directory: {resolved}")
    return resolved


def activate_project(path: str | Path, name: str | None = None) -> dict[str, Any]:
    root = _resolved_dir(path)
    explicit_name = name is not None
    requested_name = name or root.name
    if not requested_name or "/" in requested_name or "\\" in requested_name:
        raise ValueError("Project name must be a single non-empty path component")

    result: dict[str, Any] = {}

    def mutate(data: dict[str, Any]) -> None:
        nonlocal result
        projects: dict[str, dict[str, Any]] = data.setdefault("projects", {})

        for existing_name, record in projects.items():
            if Path(record["path"]) == root:
                if explicit_name and existing_name != requested_name:
                    raise ValueError(
                        f"Path is already registered as '{existing_name}'. "
                        "Remove it first if you want to rename it."
                    )
                record["active"] = True
                record["updated_at"] = _now()
                result = dict(record)
                return

        if requested_name in projects and Path(projects[requested_name]["path"]) != root:
            raise ValueError(
                f"Project name '{requested_name}' is already used by {projects[requested_name]['path']}. "
                "Use --name to choose a unique name."
            )

        record = {
            "name": requested_name,
            "path": str(root),
            "active": True,
            "added_at": _now(),
            "updated_at": _now(),
        }
        projects[requested_name] = record
        result = dict(record)

    update_registry(mutate)
    return result


def _find_name(data: dict[str, Any], target: str | Path | None, cwd: Path | None = None) -> str:
    projects: dict[str, dict[str, Any]] = data.get("projects", {})
    if target is None:
        resolved = (cwd or Path.cwd()).expanduser().resolve()
        for name, record in projects.items():
            if Path(record["path"]) == resolved:
                return name
        raise KeyError(f"Current directory is not registered: {resolved}")

    raw = str(target)
    if raw in projects:
        return raw

    candidate = Path(raw).expanduser()
    if candidate.exists():
        resolved = candidate.resolve()
        for name, record in projects.items():
            if Path(record["path"]) == resolved:
                return name
    raise KeyError(f"No registered project matches: {raw}")


def deactivate_project(target: str | Path | None = None, cwd: Path | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {}

    def mutate(data: dict[str, Any]) -> None:
        nonlocal result
        name = _find_name(data, target, cwd)
        record = data["projects"][name]
        record["active"] = False
        record["updated_at"] = _now()
        result = dict(record)

    update_registry(mutate)
    return result


def remove_project(target: str | Path | None = None, cwd: Path | None = None, force: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {}

    def mutate(data: dict[str, Any]) -> None:
        nonlocal result
        name = _find_name(data, target, cwd)
        record = data["projects"][name]
        if record.get("active") and not force:
            raise ValueError(f"Project '{name}' is active. Run 'ctun down {name}' first or use --force.")
        result = dict(record)
        del data["projects"][name]

    update_registry(mutate)
    return result


def list_projects(active_only: bool = False) -> list[dict[str, Any]]:
    data = load_registry()
    records = [dict(v) for v in data.get("projects", {}).values()]
    if active_only:
        records = [record for record in records if record.get("active")]
    return sorted(records, key=lambda record: str(record["name"]).lower())


def get_active_project(name: str) -> dict[str, Any]:
    data = load_registry()
    record = data.get("projects", {}).get(name)
    if not record:
        raise KeyError(f"Unknown project '{name}'")
    if not record.get("active"):
        raise PermissionError(f"Project '{name}' is registered but disabled")
    return dict(record)
