"""Binds tests/features/r1_release_notes.feature (ST-082; REL-1.1, FR-055.R1): the check run as
a process, as the ci.yml doc-check job runs it, on a copy of the real R1 release notes with one
planted break per scenario, against the real traceability matrix and infra/env.example."""

from __future__ import annotations

from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from release_notes_fixtures import (
    NOTES,
    drop_notice,
    drop_row,
    run_check,
    set_flag_default,
    set_setting,
    strip_pn,
)

pytestmark = [pytest.mark.scenario, pytest.mark.integration]

scenarios("r1_release_notes.feature")


@pytest.fixture
def ctx(tmp_path: Path) -> dict:
    return {"copy": tmp_path / "r1-rc.md"}


def _edit(ctx: dict, fn, *args: str) -> None:
    ctx["copy"].write_text(fn(ctx["copy"].read_text(), *args))


@given("a copy of the R1 release notes")
def copy(ctx: dict) -> None:
    ctx["copy"].write_text(NOTES.read_text())


@given('the "unofficial scoring" notice removed from the copy')
def no_notice(ctx: dict) -> None:
    _edit(ctx, drop_notice)


@given(parsers.parse('the feature row "{fr}" removed from the copy'))
def no_fr(ctx: dict, fr: str) -> None:
    _edit(ctx, drop_row, fr)


@given(parsers.parse('the flag "{flag}" listed with default "{value}"'))
def wrong_default(ctx: dict, flag: str, value: str) -> None:
    _edit(ctx, set_flag_default, flag, value)


@given(parsers.parse('the runtime setting "{setting}" listed as "{value}"'))
def setting(ctx: dict, setting: str, value: str) -> None:
    _edit(ctx, set_setting, setting, value)


@given(parsers.parse('the runtime setting row "{setting}" removed from the copy'))
def no_setting(ctx: dict, setting: str) -> None:
    _edit(ctx, drop_row, setting)


@given(parsers.parse('the limitation "{row}" with its P-n removed'))
def no_pn(ctx: dict, row: str) -> None:
    _edit(ctx, strip_pn, row)


@when("the release-notes check runs on the copy")
def run(ctx: dict) -> None:
    ctx["proc"] = run_check("--notes", str(ctx["copy"]))


@then(parsers.parse('the check exits 1 naming "{word}"'))
def fails(ctx: dict, word: str) -> None:
    out = ctx["proc"].stdout + ctx["proc"].stderr
    assert ctx["proc"].returncode == 1, out
    assert any(ln.startswith("FAIL") and word in ln for ln in out.splitlines()), out


@then(parsers.parse('the check exits 0 with "{text}"'))
def passes(ctx: dict, text: str) -> None:
    out = ctx["proc"].stdout + ctx["proc"].stderr
    assert ctx["proc"].returncode == 0, out
    assert text in ctx["proc"].stdout, out
