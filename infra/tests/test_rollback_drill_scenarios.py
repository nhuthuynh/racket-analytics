"""Binds tests/features/rollback_drill.feature (ST-082; REL-1.2; ADR 0058 rule 7): the drill runs
as a process against the recording `docker` stand-in of rollback_fixtures.py."""

from __future__ import annotations

from pathlib import Path

import pytest
from conftest import REPO_ROOT
from pytest_bdd import given, parsers, scenarios, then, when
from rollback_fixtures import calls, make_env, marker_cmd, report, run_drill

pytestmark = [pytest.mark.scenario, pytest.mark.unit]

scenarios("rollback_drill.feature")


@pytest.fixture
def ctx(tmp_path: Path) -> dict:
    return {"tmp": tmp_path}


@given(
    parsers.parse(
        'a Compose project "{project}" whose previous release is "{tag}" at revision "{revision}"'
    )
)
def project(ctx: dict, project: str, tag: str, revision: str) -> None:
    ctx.update(project=project, env=make_env(ctx["tmp"], tag, revision))


@given(parsers.parse('its current release is "{tag}"'))
def current(ctx: dict, tag: str) -> None:
    notes = ctx["tmp"] / "notes.md"
    text = notes.read_text()
    notes.write_text(text.replace("release: r1-rc1\n", f"release: {tag}\n", 1))
    ctx["current"] = tag


@given("the downgrade fails")
def downgrade_fails(ctx: dict) -> None:
    ctx["env"]["FAKE_DOCKER_FAIL"] = "command.downgrade"


@given(parsers.parse('the images of tag "{tag}" are missing'))
def images_missing(ctx: dict, tag: str) -> None:
    ctx["env"]["FAKE_DOCKER_MISSING"] = tag


@when("the rollback drill runs to the previous tag")
def run(ctx: dict) -> None:
    tmp = ctx["tmp"]
    ctx["proc"] = run_drill(
        tmp,
        ctx["env"],
        "--project",
        ctx["project"],
        "--to-previous-tag",
        "--backup-cmd",
        marker_cmd(tmp, "backup"),
        "--restore-cmd",
        marker_cmd(tmp, "restore"),
    )


@then(parsers.parse("the drill exits {rc:d}"))
def exits(ctx: dict, rc: int) -> None:
    assert ctx["proc"].returncode == rc, ctx["proc"].stdout + ctx["proc"].stderr


@then(parsers.parse('the steps ran in the order "{order}"'))
def order(ctx: dict, order: str) -> None:
    names = [s["name"] for s in report(ctx["tmp"])["steps"]]
    assert names == [n.strip() for n in order.split(",")]


@then(parsers.parse('the downgrade ran with the current image to revision "{revision}"'))
def downgrade(ctx: dict, revision: str) -> None:
    (down,) = [
        c for c in calls(ctx["tmp"]) if "run" in c.get("argv", []) and "migrate" in c["argv"]
    ]
    assert down["image_tag"] == ctx["current"]
    assert str(REPO_ROOT / "infra" / "compose.release.yaml") in down["argv"]
    assert down["argv"][-1] == revision


@then(parsers.parse('the redeploy started tag "{tag}" without building'))
def redeploy(ctx: dict, tag: str) -> None:
    ups = [c for c in calls(ctx["tmp"]) if "up" in c.get("argv", [])]
    assert ups, "no redeploy ran"
    up = ups[-1]
    assert up["image_tag"] == tag
    assert "--no-build" in up["argv"]
    assert str(REPO_ROOT / "infra" / "compose.release.yaml") in up["argv"]


@then("no downgrade ran")
def no_downgrade(ctx: dict) -> None:
    assert not [c for c in calls(ctx["tmp"]) if "run" in c.get("argv", [])]
