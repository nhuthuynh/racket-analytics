"""Binds tests/features/golden_matches_gs_an_1.feature (ST-049; NFR-004; FR-151; QD-GD-03).

Pure domain plus the dataset CLI: the sheet is built by the real projection from the frozen tag
script (``tests.regression.test_golden_an``), the stats by ``racket.analytics``, the integrity
check by ``racket-manifest-check``. No API and no database (the stored path is
``tests/integration/test_st_049_golden_match_over_stored_sheet.py``).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from racket.dataset import cli as manifest_cli
from tests.regression.test_golden_an import (
    METRICS,
    SET_DIR,
    differences,
    expected,
    product_stats,
    script,
)

scenarios("golden_matches_gs_an_1.feature")


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {}


@given("a copy of the golden set GS-AN-1")
def copy_of_set(ctx: dict[str, Any], tmp_path: Path) -> None:
    ctx["set_dir"] = shutil.copytree(SET_DIR, tmp_path / "golden_matches")


@given("the committed golden set GS-AN-1")
def committed_set(ctx: dict[str, Any]) -> None:
    ctx["set_dir"] = SET_DIR


@given(parsers.parse('side A\'s AN-04 count of "{match}" is changed in the copy'))
def change_expected(ctx: dict[str, Any], match: str) -> None:
    path = ctx["set_dir"] / "expected" / f"{match}.json"
    data = json.loads(path.read_text())
    data["metrics"]["AN-04"]["A"]["count"] += 1
    path.write_text(json.dumps(data))


@when("the manifest check runs on the copy")
@when("the manifest check runs on it")
def run_manifest_check(ctx: dict[str, Any], capsys: pytest.CaptureFixture[str]) -> None:
    ctx["rc"] = manifest_cli.main([str(ctx["set_dir"])])
    captured = capsys.readouterr()
    ctx["output"] = captured.out + captured.err


@then(parsers.parse('the check fails naming "{name}"'))
def check_fails(ctx: dict[str, Any], name: str) -> None:
    assert ctx["rc"] == 1, ctx["output"]
    assert name in ctx["output"]
    assert "sha256 differs" in ctx["output"]


@then(parsers.parse('the check passes as "{summary}"'))
def check_passes(ctx: dict[str, Any], summary: str) -> None:
    assert ctx["rc"] == 0, ctx["output"]
    assert summary in ctx["output"]


@given(
    parsers.parse(
        'golden match "{match}" with its first winner re-tagged as an unforced error'
    )
)
def retagged(ctx: dict[str, Any], match: str) -> None:
    s = script(match)
    tag = next(t for g in s["games"] for t in g["tags"] if t["ending"] == "winner")
    tag["ending"] = "unforced_error"
    ctx["match"], ctx["script"] = match, s


@given(parsers.parse('golden match "{match}" as scripted, with its corrections'))
def as_scripted(ctx: dict[str, Any], match: str) -> None:
    ctx["match"], ctx["script"] = match, script(match)


@when("its starter stats are compared with GS-AN-1")
def compare(ctx: dict[str, Any]) -> None:
    got = product_stats(ctx["script"])
    want = expected(ctx["match"])["metrics"]
    ctx["got"] = got
    ctx["found"] = [d for m in METRICS for d in differences(ctx["match"], m, want[m], got[m])]


@then(parsers.parse('a difference names "{prefix}" and a side'))
def a_difference(ctx: dict[str, Any], prefix: str) -> None:
    assert ctx["found"], "a re-tagged rally went unnoticed"
    assert all(d.startswith(prefix) and " side " in d for d in ctx["found"]), ctx["found"]


@then("there is no difference")
def no_difference(ctx: dict[str, Any]) -> None:
    assert not ctx["found"], "\n".join(ctx["found"])


@then(parsers.parse("no stat counts rallies {first:d} to {last:d}, which need a decision"))
def not_counted(ctx: dict[str, Any], first: int, last: int) -> None:
    excluded = set(range(first, last + 1))
    counted = {
        n
        for sides in ctx["got"].values()
        for fields in sides.values()
        for n in fields.get("rallies", [])
    }
    assert not counted & excluded, sorted(counted & excluded)
