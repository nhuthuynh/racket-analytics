"""ADR-0053-0049 unit tests for scripts/ci/scheduled_red_notice.py (retro C4; ADR 0053).

The script decides, from one completed workflow run, whether the product owner gets a notice:
`open` (a red scheduled run), `close` (a green scheduled run) or `none` (anything else), and
writes the issue title and body. It never calls GitHub."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest
from conftest import SCRIPTS_DIR

SCRIPT = SCRIPTS_DIR / "ci" / "scheduled_red_notice.py"
URL = "https://github.com/nhuthuynh/racket-analytics/actions/runs/9"
SHA = "cd" * 20


def load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("scheduled_red_notice", SCRIPT)
    assert spec
    assert spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


srn = load() if SCRIPT.exists() else None


@pytest.fixture
def m() -> ModuleType:
    assert srn is not None, f"{SCRIPT} does not exist"
    return srn


def argv(out: Path, **over: str) -> list[str]:
    values = {
        "--workflow": "CI",
        "--event": "schedule",
        "--conclusion": "failure",
        "--run-url": URL,
        "--sha": SHA,
        "--date": "2026-10-30",
        "--out-dir": str(out),
    }
    values.update({f"--{k.replace('_', '-')}": v for k, v in over.items()})
    return [x for pair in values.items() for x in pair]


# ------------------------------------------------------------------ negative first
@pytest.mark.unit
@pytest.mark.parametrize("missing", ["workflow", "event", "conclusion", "run_url", "sha", "date"])
def test_an_empty_input_fails_closed_naming_the_flag(
    m: ModuleType, tmp_path: Path, missing: str, capsys: pytest.CaptureFixture[str]
) -> None:
    assert m.main(argv(tmp_path / "o", **{missing: ""})) == 2
    assert f"--{missing.replace('_', '-')}" in capsys.readouterr().err
    assert not (tmp_path / "o" / "action.txt").exists()


@pytest.mark.unit
def test_a_run_url_outside_github_actions_is_refused(m: ModuleType, tmp_path: Path) -> None:
    assert m.main(argv(tmp_path / "o", run_url="https://evil.example/actions/runs/1")) == 2


@pytest.mark.unit
@pytest.mark.parametrize("ev", ["push", "pull_request", "workflow_dispatch"])
def test_a_run_that_was_not_scheduled_needs_no_notice(m: ModuleType, ev: str) -> None:
    assert m.decide(ev, "failure") == "none"
    assert m.decide(ev, "success") == "none"


@pytest.mark.unit
# CI-NOTICE-CANCELLED (TCR in docs/sprints/05/decisions/CI-NOTICE-CANCELLED.md): "cancelled"
# moved to the red table; run 41622904539 hit its 45 min job timeout and concluded `cancelled`.
@pytest.mark.parametrize("conclusion", ["skipped", "neutral", "action_required", "stale"])
def test_a_scheduled_run_that_neither_failed_nor_passed_changes_nothing(
    m: ModuleType, conclusion: str
) -> None:
    assert m.decide("schedule", conclusion) == "none"


# ------------------------------------------------------------------ positive
@pytest.mark.unit
@pytest.mark.parametrize("conclusion", ["failure", "timed_out", "startup_failure", "cancelled"])
def test_a_red_scheduled_run_opens_a_notice(m: ModuleType, conclusion: str) -> None:
    assert m.decide("schedule", conclusion) == "open"


@pytest.mark.unit
def test_a_green_scheduled_run_closes_the_notice(m: ModuleType) -> None:
    assert m.decide("schedule", "success") == "close"


@pytest.mark.unit
def test_the_title_is_one_per_workflow(m: ModuleType) -> None:
    assert m.title("Nightly quality") == "[CI-RED] scheduled Nightly quality run failed"
    assert m.title("CI") != m.title("Dependency audit")


@pytest.mark.unit
def test_the_red_body_tells_the_po_what_failed_and_what_happens_next(m: ModuleType) -> None:
    body = m.red_body("CI", "timed_out", URL, SHA, "2026-10-30")
    for needle in (URL, SHA, "timed_out", "2026-10-30", "CI FIRST", "product owner"):
        assert needle in body, needle


@pytest.mark.unit
def test_the_green_body_names_the_green_run(m: ModuleType) -> None:
    body = m.green_body("CI", URL, SHA, "2026-10-31")
    assert URL in body
    assert "2026-10-31" in body


@pytest.mark.unit
@pytest.mark.parametrize(
    ("conclusion", "action", "files"),
    [
        ("failure", "open", {"action.txt", "title.txt", "body.md", "summary.json"}),
        ("success", "close", {"action.txt", "title.txt", "body.md", "summary.json"}),
        ("cancelled", "open", {"action.txt", "title.txt", "body.md", "summary.json"}),
        ("skipped", "none", {"action.txt", "summary.json"}),
    ],
)
def test_main_writes_the_action_and_only_the_files_it_needs(
    m: ModuleType, tmp_path: Path, conclusion: str, action: str, files: set[str]
) -> None:
    out = tmp_path / "o"
    assert m.main(argv(out, conclusion=conclusion)) == 0
    assert (out / "action.txt").read_text().strip() == action
    assert {p.name for p in out.iterdir()} == files
    summary = json.loads((out / "summary.json").read_text())
    assert summary == {"action": action, "workflow": "CI", "conclusion": conclusion}


# ------------------------------------------------ CI-NOTICE-CANCELLED (PRC-1.1, PRC-1.2)
EVERY_CONCLUSION = {
    "failure": "open",
    "timed_out": "open",
    "startup_failure": "open",
    "cancelled": "open",
    "success": "close",
    "skipped": "none",
    "neutral": "none",
    "action_required": "none",
    "stale": "none",
}


@pytest.mark.unit
@pytest.mark.parametrize(("conclusion", "action"), sorted(EVERY_CONCLUSION.items()))
def test_every_scheduled_conclusion_has_one_decided_action(
    m: ModuleType, conclusion: str, action: str
) -> None:
    assert m.decide("schedule", conclusion) == action


@pytest.mark.unit
@pytest.mark.parametrize("conclusion", ["cancelled", "timed_out"])
def test_a_cancelled_or_timed_out_scheduled_run_writes_a_red_notice(
    m: ModuleType, tmp_path: Path, conclusion: str
) -> None:
    out = tmp_path / "o"
    assert m.main(argv(out, conclusion=conclusion)) == 0
    assert (out / "action.txt").read_text() == "open\n"
    assert (out / "title.txt").read_text() == "[CI-RED] scheduled CI run failed\n"
    assert f"`{conclusion}`" in (out / "body.md").read_text()


@pytest.mark.unit
def test_the_cancelled_body_says_a_job_timeout_reports_cancelled(m: ModuleType) -> None:
    body = m.red_body("CI", "cancelled", URL, SHA, "2026-11-03")
    assert "timeout-minutes" in body
    assert "timeout-minutes" not in m.red_body("CI", "failure", URL, SHA, "2026-11-03")
