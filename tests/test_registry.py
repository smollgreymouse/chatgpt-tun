from __future__ import annotations

from pathlib import Path

import pytest

from chatgpt_tun.registry import (
    activate_project,
    deactivate_project,
    list_projects,
    remove_project,
)
from chatgpt_tun.state import connector_url, load_config


@pytest.fixture(autouse=True)
def isolated_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CHATGPT_TUN_HOME", str(tmp_path / "state"))


def test_config_has_stable_secret_endpoint() -> None:
    first = load_config()
    second = load_config()
    assert first["endpoint_token"] == second["endpoint_token"]
    assert first["public_url"] is None

    first["public_url"] = "https://example.ngrok.app"
    assert connector_url(first).endswith(f"/{first['endpoint_token']}/mcp")


def test_up_uses_folder_name_and_registry_is_global(tmp_path: Path) -> None:
    project = tmp_path / "game"
    project.mkdir()

    record = activate_project(project)
    assert record["name"] == "game"
    assert record["active"] is True

    records = list_projects()
    assert [(item["name"], item["path"], item["active"]) for item in records] == [
        ("game", str(project.resolve()), True)
    ]


def test_down_by_current_directory(tmp_path: Path) -> None:
    project = tmp_path / "sprite-processing"
    project.mkdir()
    activate_project(project)

    record = deactivate_project(cwd=project)
    assert record["name"] == "sprite-processing"
    assert record["active"] is False


def test_same_folder_name_collision_requires_explicit_name(tmp_path: Path) -> None:
    one = tmp_path / "one" / "game"
    two = tmp_path / "two" / "game"
    one.mkdir(parents=True)
    two.mkdir(parents=True)
    activate_project(one)

    with pytest.raises(ValueError, match="already used"):
        activate_project(two)

    second = activate_project(two, "game-two")
    assert second["name"] == "game-two"


def test_remove_active_requires_force(tmp_path: Path) -> None:
    project = tmp_path / "kikimora"
    project.mkdir()
    activate_project(project)

    with pytest.raises(ValueError, match="active"):
        remove_project("kikimora")

    removed = remove_project("kikimora", force=True)
    assert removed["name"] == "kikimora"
    assert list_projects() == []
