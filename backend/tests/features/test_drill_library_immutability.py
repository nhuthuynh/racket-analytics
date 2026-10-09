"""CLI binding of tests/features/drill_library_immutability.feature (ST-053 review round 1,
PE-R1-ST053-01; FR-140; QD-DR-02). Each scenario works on a copy of ``content/drills``; the
base branch's lock is the library's committed ``library.lock``, passed with ``--base-lock``
as the ``drill-lint`` CI job does.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.integration.test_it_03_14_drill_lint import LIBRARY, LINT

scenarios("drill_library_immutability.feature")

LOCK = "library.lock"


@pytest.fixture
def ctx(tmp_path: Path) -> dict[str, Any]:
    return {"tmp": tmp_path}


@given("the base branch locks the drill library")
def base_locks(ctx: dict[str, Any]) -> None:
    ctx["library"] = ctx["tmp"] / "drills"
    shutil.copytree(LIBRARY, ctx["library"])
    ctx["base"] = ctx["tmp"] / "base.lock"
    shutil.copyfile(LIBRARY / LOCK, ctx["base"])


def _lock(ctx: dict[str, Any]) -> dict[str, Any]:
    lock: dict[str, Any] = json.loads((ctx["library"] / LOCK).read_text())
    return lock


def _write_lock(ctx: dict[str, Any], lock: dict[str, Any]) -> None:
    (ctx["library"] / LOCK).write_text(json.dumps(lock, indent=2) + "\n")


@given(parsers.parse('the pull request deletes "{drill}" version {version:d} and its lock line'))
def deletes(ctx: dict[str, Any], drill: str, version: int) -> None:
    (ctx["library"] / drill / f"v{version}.json").unlink()
    lock = _lock(ctx)
    del lock["drills"][f"{drill}@{version}"]
    _write_lock(ctx, lock)


@given(
    parsers.parse(
        'the pull request edits "{drill}" version {version:d} in place and rewrites its lock line'
    )
)
def edits(
    ctx: dict[str, Any], drill: str, version: int, capsys: pytest.CaptureFixture[str]
) -> None:
    path = ctx["library"] / drill / f"v{version}.json"
    doc = json.loads(path.read_text())
    path.write_text(json.dumps({**doc, "summary": doc["summary"] + " Edited."}))
    lock = _lock(ctx)
    del lock["drills"][f"{drill}@{version}"]
    _write_lock(ctx, lock)
    assert int(LINT.load()([str(ctx["library"]), "--update-lock"])) == 0  # relocked by the PR
    capsys.readouterr()


@given(parsers.parse('the pull request adds "{drill}" version {version:d} and locks it'))
def adds(ctx: dict[str, Any], drill: str, version: int, capsys: pytest.CaptureFixture[str]) -> None:
    latest = max((ctx["library"] / drill).glob("v*.json"))
    doc = json.loads(latest.read_text())
    (ctx["library"] / drill / f"v{version}.json").write_text(
        json.dumps({**doc, "version": version})
    )
    argv = [str(ctx["library"]), "--update-lock", "--base-lock", str(ctx["base"])]
    assert int(LINT.load()(argv)) == 0, capsys.readouterr().out
    capsys.readouterr()


@when("the library is validated against the base branch")
def validated(ctx: dict[str, Any], capsys: pytest.CaptureFixture[str]) -> None:
    capsys.readouterr()
    ctx["rc"] = int(LINT.load()([str(ctx["library"]), "--base-lock", str(ctx["base"])]))
    out, err = capsys.readouterr()
    ctx["out"] = out + err


@then(parsers.parse('validation fails naming "{drill}" and "{reason}"'))
def fails(ctx: dict[str, Any], drill: str, reason: str) -> None:
    assert ctx["rc"] == 1, ctx["out"]
    lines = [line for line in ctx["out"].splitlines() if line.startswith("FAIL ")]
    assert any(f"drill {drill}: {reason}:" in line for line in lines), ctx["out"]


@then("validation passes")
def passes(ctx: dict[str, Any]) -> None:
    assert ctx["rc"] == 0, ctx["out"]
    assert "ok, 0 problem(s)" in ctx["out"]
