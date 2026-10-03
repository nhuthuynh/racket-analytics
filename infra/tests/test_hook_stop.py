"""ST-003: the Stop hook runs the unit suite and blocks the turn from ending on failure.

[DPA/AI-10]
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from conftest import run_hook

pytestmark = pytest.mark.unit

HOOK = "stop.py"


def stop_event(active: bool = False) -> dict[str, object]:
    return {"hook_event_name": "Stop", "stop_hook_active": active}


def counting_cmd(tmp: Path, exit_code: int) -> str:
    counter = tmp / "runs.txt"
    return f"echo run >> {counter}; echo 'FAILED tests/unit/test_x.py::test_y' ; exit {exit_code}"


def runs(tmp: Path) -> int:
    counter = tmp / "runs.txt"
    return len(counter.read_text().splitlines()) if counter.exists() else 0


def touch_change(project: Path, name: str = "a.py", content: str = "x = 1\n") -> None:
    (project / name).write_text(content)


# ---------------------------------------------------------------- negative cases first
def test_failing_unit_suite_blocks_the_turn(project: Path, tmp_path: Path) -> None:
    touch_change(project)
    result = run_hook(HOOK, stop_event(), project, {"RA_UNIT_TEST_CMD": counting_cmd(tmp_path, 1)})
    assert result.returncode == 2
    assert "FAILED tests/unit/test_x.py::test_y" in result.stderr
    assert runs(tmp_path) == 1


def test_unit_suite_over_time_budget_blocks(project: Path) -> None:
    touch_change(project)
    result = run_hook(
        HOOK, stop_event(), project, {"RA_UNIT_TEST_CMD": "sleep 5", "RA_STOP_TIMEOUT_S": "1"}
    )
    assert result.returncode == 2
    assert "time budget" in result.stderr


def test_failure_is_not_cached_as_green(project: Path, tmp_path: Path) -> None:
    touch_change(project)
    env = {"RA_UNIT_TEST_CMD": counting_cmd(tmp_path, 1)}
    run_hook(HOOK, stop_event(), project, env)
    second = run_hook(HOOK, stop_event(), project, env)
    assert second.returncode == 2
    assert runs(tmp_path) == 2


# ---------------------------------------------------------------- loop guard, positive cases
def test_already_continuing_from_a_stop_hook_does_not_loop(project: Path, tmp_path: Path) -> None:
    touch_change(project)
    result = run_hook(
        HOOK, stop_event(active=True), project, {"RA_UNIT_TEST_CMD": counting_cmd(tmp_path, 1)}
    )
    assert result.returncode == 0
    assert runs(tmp_path) == 0


def test_passing_unit_suite_lets_the_turn_end(project: Path, tmp_path: Path) -> None:
    touch_change(project)
    result = run_hook(HOOK, stop_event(), project, {"RA_UNIT_TEST_CMD": counting_cmd(tmp_path, 0)})
    assert result.returncode == 0, result.stderr
    assert runs(tmp_path) == 1


def test_unchanged_tree_after_green_run_skips_the_suite(project: Path, tmp_path: Path) -> None:
    touch_change(project)
    env = {"RA_UNIT_TEST_CMD": counting_cmd(tmp_path, 0)}
    run_hook(HOOK, stop_event(), project, env)
    run_hook(HOOK, stop_event(), project, env)
    assert runs(tmp_path) == 1


def test_changed_tree_after_green_run_reruns_the_suite(project: Path, tmp_path: Path) -> None:
    touch_change(project)
    env = {"RA_UNIT_TEST_CMD": counting_cmd(tmp_path, 0)}
    run_hook(HOOK, stop_event(), project, env)
    touch_change(project, content="x = 2\n")
    run_hook(HOOK, stop_event(), project, env)
    assert runs(tmp_path) == 2


def test_hook_logs_do_not_change_the_fingerprint(project: Path, tmp_path: Path) -> None:
    touch_change(project)
    env = {"RA_UNIT_TEST_CMD": counting_cmd(tmp_path, 0)}
    run_hook(HOOK, stop_event(), project, env)
    logs = project / ".claude" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    (logs / "bash-audit.jsonl").write_text('{"command": "ls"}\n')
    run_hook(HOOK, stop_event(), project, env)
    assert runs(tmp_path) == 1


def test_non_git_directory_still_runs_the_suite(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    result = run_hook(HOOK, stop_event(), plain, {"RA_UNIT_TEST_CMD": counting_cmd(tmp_path, 0)})
    assert result.returncode == 0
    assert runs(tmp_path) == 1


def test_malformed_input_does_not_block(project: Path) -> None:
    result = run_hook(HOOK, "nope", project, {"RA_UNIT_TEST_CMD": "exit 1"})
    assert result.returncode == 0


def test_default_command_is_the_repo_unit_script(project: Path) -> None:
    script = project / "scripts" / "test-unit.sh"
    script.parent.mkdir()
    script.write_text("#!/bin/sh\necho repo-unit-script-ran >&2\nexit 1\n")
    script.chmod(0o755)
    subprocess.run(["git", "-C", str(project), "add", "-A"], check=True)
    result = run_hook(HOOK, stop_event(), project)
    assert result.returncode == 2
    assert "repo-unit-script-ran" in result.stderr


def test_inside_github_actions_the_stop_gate_defers_to_ci(project: Path, tmp_path: Path) -> None:
    # The claude-code-action review bot loads this settings.json; CI runs the suites itself.
    touch_change(project)
    result = run_hook(
        HOOK,
        stop_event(),
        project,
        {"RA_UNIT_TEST_CMD": counting_cmd(tmp_path, 1), "GITHUB_ACTIONS": "true"},
    )
    assert result.returncode == 0
    assert runs(tmp_path) == 0


def test_a_different_test_command_is_not_served_from_the_green_cache(
    project: Path, tmp_path: Path
) -> None:
    touch_change(project)
    run_hook(HOOK, stop_event(), project, {"RA_UNIT_TEST_CMD": "true"})
    result = run_hook(HOOK, stop_event(), project, {"RA_UNIT_TEST_CMD": counting_cmd(tmp_path, 1)})
    assert result.returncode == 2
    assert runs(tmp_path) == 1
