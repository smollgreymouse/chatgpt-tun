from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .registry import get_active_project

MAX_READ_CHARS = 200_000
MAX_COMMAND_OUTPUT = 200_000


def project_root(project: str) -> Path:
    return Path(get_active_project(project)["path"]).resolve()


def safe_path(project: str, relative: str = ".") -> Path:
    root = project_root(project)
    rel = Path(relative)
    if rel.is_absolute():
        raise ValueError("Path must be relative to the project root")
    candidate = (root / rel).resolve(strict=False)
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Path escapes project root: {relative}") from exc
    return candidate


def list_directory(project: str, path: str = ".", include_hidden: bool = False) -> list[dict[str, Any]]:
    target = safe_path(project, path)
    if not target.is_dir():
        raise ValueError(f"Not a directory: {path}")
    result: list[dict[str, Any]] = []
    root = project_root(project)
    for item in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        if not include_hidden and item.name.startswith("."):
            continue
        stat = item.stat()
        result.append(
            {
                "path": str(item.relative_to(root)),
                "name": item.name,
                "type": "directory" if item.is_dir() else "file",
                "size": stat.st_size,
            }
        )
    return result


def read_text(
    project: str,
    path: str,
    start_line: int = 1,
    end_line: int | None = None,
    max_chars: int = MAX_READ_CHARS,
) -> dict[str, Any]:
    if start_line < 1:
        raise ValueError("start_line must be >= 1")
    if end_line is not None and end_line < start_line:
        raise ValueError("end_line must be >= start_line")
    target = safe_path(project, path)
    if not target.is_file():
        raise ValueError(f"Not a file: {path}")
    text = target.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    selected = lines[start_line - 1 : end_line]
    rendered = "\n".join(selected)
    truncated = len(rendered) > max_chars
    if truncated:
        rendered = rendered[:max_chars]
    return {
        "path": path,
        "start_line": start_line,
        "end_line": start_line + max(0, len(selected) - 1),
        "total_lines": len(lines),
        "truncated": truncated,
        "text": rendered,
    }


def write_text(project: str, path: str, content: str, create_parents: bool = True) -> dict[str, Any]:
    target = safe_path(project, path)
    if create_parents:
        target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return {"path": path, "bytes": len(content.encode("utf-8"))}


def replace_text(project: str, path: str, old: str, new: str, count: int = 0) -> dict[str, Any]:
    if not old:
        raise ValueError("old must not be empty")
    target = safe_path(project, path)
    text = target.read_text(encoding="utf-8")
    occurrences = text.count(old)
    if occurrences == 0:
        raise ValueError("old text was not found")
    replaced = text.replace(old, new, count if count > 0 else -1)
    target.write_text(replaced, encoding="utf-8")
    changed = min(occurrences, count) if count > 0 else occurrences
    return {"path": path, "replacements": changed}


def make_directory(project: str, path: str, parents: bool = True) -> dict[str, Any]:
    target = safe_path(project, path)
    target.mkdir(parents=parents, exist_ok=True)
    return {"path": path, "created": True}


def remove_path(project: str, path: str, recursive: bool = False) -> dict[str, Any]:
    target = safe_path(project, path)
    root = project_root(project)
    if target == root:
        raise ValueError("Refusing to remove the project root")
    if not target.exists() and not target.is_symlink():
        raise ValueError(f"Path does not exist: {path}")
    if target.is_dir() and not target.is_symlink():
        if not recursive:
            target.rmdir()
        else:
            shutil.rmtree(target)
    else:
        target.unlink()
    return {"path": path, "removed": True}


def search_text(
    project: str,
    query: str,
    path: str = ".",
    glob: str = "*",
    max_results: int = 100,
) -> list[dict[str, Any]]:
    if not query:
        raise ValueError("query must not be empty")
    base = safe_path(project, path)
    if not base.is_dir():
        raise ValueError(f"Not a directory: {path}")
    root = project_root(project)
    results: list[dict[str, Any]] = []
    for file_path in base.rglob(glob):
        if len(results) >= max_results:
            break
        if not file_path.is_file() or any(part.startswith(".") for part in file_path.relative_to(root).parts):
            continue
        try:
            if file_path.stat().st_size > 2_000_000:
                continue
            with file_path.open("r", encoding="utf-8", errors="ignore") as fh:
                for line_no, line in enumerate(fh, 1):
                    if query in line:
                        results.append(
                            {
                                "path": str(file_path.relative_to(root)),
                                "line": line_no,
                                "text": line.rstrip("\n")[:1000],
                            }
                        )
                        if len(results) >= max_results:
                            break
        except OSError:
            continue
    return results


def run_command(
    project: str,
    argv: list[str],
    cwd: str = ".",
    timeout: int = 60,
    max_output: int = MAX_COMMAND_OUTPUT,
) -> dict[str, Any]:
    if not argv:
        raise ValueError("argv must contain at least one element")
    if timeout < 1 or timeout > 600:
        raise ValueError("timeout must be between 1 and 600 seconds")
    workdir = safe_path(project, cwd)
    if not workdir.is_dir():
        raise ValueError(f"cwd is not a directory: {cwd}")

    completed = subprocess.run(
        argv,
        cwd=workdir,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
        timeout=timeout,
        env=os.environ.copy(),
        check=False,
    )
    stdout = completed.stdout
    stderr = completed.stderr
    truncated = len(stdout) + len(stderr) > max_output
    if truncated:
        remaining = max_output
        stdout = stdout[:remaining]
        remaining -= len(stdout)
        stderr = stderr[: max(0, remaining)]
    return {
        "argv": argv,
        "cwd": cwd,
        "returncode": completed.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "truncated": truncated,
    }
