from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

from chatgpt_tun.jobs import JobManager, MAX_LOG_BYTES
from chatgpt_tun.registry import activate_project, deactivate_project


@pytest.fixture
def setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CHATGPT_TUN_HOME", str(tmp_path / "state"))
    root = tmp_path / "demo"
    root.mkdir()
    activate_project(root)
    manager = JobManager()
    yield manager
    manager.shutdown()


def wait(manager: JobManager, job_id: str, limit: float = 5):
    deadline = time.monotonic() + limit
    while time.monotonic() < deadline:
        item = manager.status("demo", job_id)
        if item["status"] not in ("starting", "running", "cancelling"):
            return item
        time.sleep(.02)
    pytest.fail("job did not finish")


def test_returns_immediately_and_fetches_incremental_output(setup):
    job = setup.start("demo", [sys.executable, "-u", "-c",
        "import time; print('hello', flush=True); time.sleep(.3); print('world')"])
    assert job["status"] == "running"
    assert job["id"]
    final = wait(setup, job["id"])
    assert final["status"] == "completed"
    first = setup.output("demo", job["id"], max_bytes=6)
    second = setup.output("demo", job["id"], offset=first["next_offset"])
    assert first["text"] + second["text"] == "hello\nworld\n"
    assert second["next_offset"] > first["next_offset"]


def test_request_id_is_idempotent_and_conflict_detected(setup):
    argv = [sys.executable, "-c", "print('once')"]
    first = setup.start("demo", argv, request_id="same")
    repeated = setup.start("demo", argv, request_id="same")
    assert first["id"] == repeated["id"]
    with pytest.raises(ValueError, match="different"):
        setup.start("demo", [sys.executable, "-c", "print('twice')"], request_id="same")
    wait(setup, first["id"])


def test_cancel_and_timeout(setup):
    cmd = [sys.executable, "-c", "import time; time.sleep(30)"]
    cancelled = setup.start("demo", cmd)
    setup.cancel("demo", cancelled["id"])
    assert wait(setup, cancelled["id"])["status"] == "cancelled"
    expired = setup.start("demo", cmd, timeout=1)
    assert wait(setup, expired["id"])["status"] == "timed_out"


def test_log_is_bounded(setup):
    job = setup.start("demo", [sys.executable, "-c",
        "import sys; sys.stdout.write('x' * (9 * 1024 * 1024))"])
    final = wait(setup, job["id"])
    assert final["status"] == "completed"
    assert final["stdout_truncated"]
    assert (setup.root / (job["id"] + ".stdout")).stat().st_size == MAX_LOG_BYTES


def test_restart_preserves_completed_jobs(setup):
    job = setup.start("demo", [sys.executable, "-c", "print('persist')"])
    wait(setup, job["id"])
    again = JobManager()
    assert again.status("demo", job["id"])["status"] == "completed"
    assert "persist" in again.output("demo", job["id"])["text"]


def test_restart_marks_orphaned_job_interrupted(setup):
    job = setup.start("demo", [sys.executable, "-c", "print('hi')"])
    wait(setup, job["id"])
    with setup.lock:
        setup.jobs[job["id"]]["status"] = "running"
        setup._save(setup.jobs[job["id"]])
    recovered = JobManager()
    assert recovered.status("demo", job["id"])["status"] == "interrupted"


def test_disabled_project_blocks_job_access(setup):
    job = setup.start("demo", [sys.executable, "-c", "print('ok')"])
    wait(setup, job["id"])
    deactivate_project("demo")
    with pytest.raises(PermissionError):
        setup.status("demo", job["id"])
    with pytest.raises(PermissionError):
        setup.output("demo", job["id"])


def test_invalid_log_arguments(setup):
    job = setup.start("demo", [sys.executable, "-c", "print(1)"])
    wait(setup, job["id"])
    with pytest.raises(ValueError):
        setup.output("demo", job["id"], stream="../bad")
    with pytest.raises(KeyError):
        setup.status("demo", "not-a-job")
