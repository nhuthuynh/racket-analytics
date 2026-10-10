"""S3-DoD-P10 visibility measurement (FIX-03-1c; sprint-03 §9.1; SEC-RV3-01; PO P12 option b).

Making the repository private, or confirming that it stays public, is the PO's decision (P10);
no agent can or may supply it. The row's status is therefore measured: from what GitHub's API
answers an anonymous reader (the security property is "world-readable or not") and from the
PO's recorded P10 answer. The sprint plan must say the same.

Negative cases first: an answer without a visibility, a GitHub error other than 404, or a
P10 row that does not clearly confirm public never reads as met (fail closed, ADR 0014).
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys

import pytest
from conftest import REPO_ROOT, SCRIPTS_DIR
from repo_visibility_fixtures import PRIVATE, PUBLIC, po_record, sprint_plan

SCRIPT = SCRIPTS_DIR / "measure" / "repo_visibility.py"
PLAN = REPO_ROOT / "docs" / "sprints" / "sprint-03.md"
PO = REPO_ROOT / "docs" / "requirements" / "po-input-2026-10-05.md"
WAITING = 'not met: waiting on P10 (GitHub reports "visibility": "public")'


def _load():
    spec = importlib.util.spec_from_file_location("repo_visibility", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["repo_visibility"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def m():
    return _load()


# --- negative cases first -------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    ("status", "body"),
    [
        (200, json.dumps({"full_name": "o/r"})),
        (200, json.dumps({"visibility": "internal"})),
        (200, "<html>not json</html>"),
        (403, json.dumps({"message": "API rate limit exceeded"})),
        (500, ""),
    ],
)
def test_an_answer_without_a_known_visibility_is_refused(m, status: int, body: str) -> None:
    with pytest.raises(ValueError):
        m.visibility(status, body)


@pytest.mark.unit
@pytest.mark.parametrize(
    "decision",
    [
        "Relayed to the PO on 2026-10-06; still open.",
        "Open: the PO will decide public or private later.",
        "Make it private.",
        "",
    ],
)
def test_a_p10_row_that_does_not_confirm_public_is_not_a_confirmation(m, decision: str) -> None:
    assert m.po_confirmed_public(po_record(decision)) is False


@pytest.mark.unit
def test_a_po_record_without_a_p10_row_is_not_a_confirmation(m) -> None:
    assert m.po_confirmed_public(po_record()) is False


@pytest.mark.unit
def test_a_public_repository_without_a_po_answer_is_not_met(m) -> None:
    result = m.measure(m.visibility(200, PUBLIC), confirmed_public=False)
    assert result == {"visibility": "public", "po_confirmed_public": False, "met": False,
                      "status": WAITING}


@pytest.mark.unit
def test_a_plan_without_an_s3_dod_p10_row_is_refused(m) -> None:
    with pytest.raises(ValueError):
        m.dod_status("| S3-DoD-P6 | x | y | z | w | **not met: waiting on P6** |\n")


# --- positive cases ---------------------------------------------------------------------------


@pytest.mark.unit
def test_visibility_reads_public_private_and_anonymous_404(m) -> None:
    assert m.visibility(200, PUBLIC) == "public"
    assert m.visibility(200, PRIVATE) == "private"
    assert m.visibility(404, json.dumps({"message": "Not Found"})) == "not-found"


@pytest.mark.unit
def test_private_or_hidden_is_met_and_a_confirmed_public_is_met(m) -> None:
    assert m.measure("private", confirmed_public=False)["status"] == "met (repository is private)"
    assert m.measure("not-found", confirmed_public=False)["status"] == (
        "met (repository is private: anonymous GitHub API returns 404)"
    )
    assert m.measure("public", confirmed_public=True)["status"] == "met (PO confirmed public)"


@pytest.mark.unit
@pytest.mark.parametrize(
    "decision",
    ["Confirmed public: keep the repository public", "**Keep public** (PO, 2026-10-12)"],
)
def test_a_p10_row_that_confirms_public_is_a_confirmation(m, decision: str) -> None:
    assert m.po_confirmed_public(po_record(decision)) is True


@pytest.mark.unit
def test_the_plan_verdict_is_compared_without_its_dated_note(m) -> None:
    cell = '**not met: waiting on P10** (GitHub reports `"visibility": "public"`, 2026-10-07)'
    assert m.dod_verdict(m.dod_status(sprint_plan(cell))) == "not met: waiting on P10"
    assert m.dod_verdict("met (PO confirmed public)") == "met"


# --- the repository itself ----------------------------------------------------------------------


@pytest.mark.unit
def test_the_repository_po_record_and_sprint_plan_agree_on_s3_dod_p10(m) -> None:
    """Offline drift guard (runs in CI): the plan may say "not met: waiting on P10" only while
    the PO record has no confirmation; once the PO confirms public the plan must say met."""
    verdict = m.dod_verdict(m.dod_status(PLAN.read_text(encoding="utf-8")))
    confirmed = m.po_confirmed_public(PO.read_text(encoding="utf-8"))
    assert verdict in {"met", "not met: waiting on P10"}
    if confirmed:
        assert verdict == "met"


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("RA_LIVE_GITHUB") != "1",
    reason="live GitHub call; opt-in with RA_LIVE_GITHUB=1 (anonymous API is rate-limited)",
)
def test_live_github_visibility_agrees_with_the_sprint_plan() -> None:
    out = subprocess.run(
        [sys.executable, str(SCRIPT), "--repo", "nhuthuynh/racket-analytics",
         "--po", str(PO), "--dod", str(PLAN)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    # rc 0 = met, 1 = not met; 2 (no answer) and 3 (plan disagrees with GitHub) are failures.
    assert out.returncode in (0, 1), out.stdout + out.stderr
    assert json.loads(out.stdout)["visibility"] in {"public", "private", "not-found"}
