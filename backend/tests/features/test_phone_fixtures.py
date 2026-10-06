"""Binds tests/features/phone_fixtures.feature (ST-025; sprint-01 §14.3.9; NFR-025; OQ-06).

"Coverage of the set" and "Probe every fixture" are RED until ST-025 adds fixtures/clips/phones-v1
with the per-clip manifest entries proposed in tests/support/contract.py. The consent rule in
racket-manifest-check is in the gate.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, scenario, scenarios, then, when

from tests.support import contract
from tests.support.paths import BACKEND, FIXTURES, SYNTHETIC_60S

pytestmark = pytest.mark.slow

# Only the scenarios that need the phones-v1 clips wait on ST-025 (QA-RV1-06 / SRE-S2-04); the
# consent rule ("File with people and no consent record") passes today and belongs in the gate.
_WAITS_ON_ST_025 = pytest.mark.red_until(story="ST-025")


@_WAITS_ON_ST_025
@scenario("phone_fixtures.feature", "Coverage of the set")
def test_coverage_of_the_set() -> None:
    pass


@_WAITS_ON_ST_025
@scenario("phone_fixtures.feature", "Probe every fixture")
def test_probe_every_fixture() -> None:
    pass


scenarios("phone_fixtures.feature")

PHONES = FIXTURES / contract.PHONES_V1_DIR


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {}


def _manifest() -> dict[str, Any]:
    path = PHONES / "manifest.json"
    if not path.is_file():
        pytest.fail(f"RED until ST-025: {path.relative_to(FIXTURES.parent)} does not exist")
    data: dict[str, Any] = json.loads(path.read_text("utf-8"))
    return data


@given("the phone fixture set version 1")
def phone_set(ctx: dict[str, Any]) -> None:
    ctx["manifest"] = _manifest()
    assert ctx["manifest"]["version"] >= 1


@then("it has files from at least 5 phone models")
def five_models(ctx: dict[str, Any]) -> None:
    assert len({c["device_model"] for c in ctx["manifest"]["clips"]}) >= 5


@then("at least one file has a variable frame rate")
def one_vfr(ctx: dict[str, Any]) -> None:
    assert any(c["vfr"] is True for c in ctx["manifest"]["clips"])


@then("every file is listed in its manifest with model, frame rate and consent status")
def every_file_listed(ctx: dict[str, Any]) -> None:
    clips = ctx["manifest"]["clips"]
    listed = {c["path"] for c in clips}
    on_disk = {
        str(p.relative_to(PHONES))
        for p in PHONES.rglob("*")
        if p.suffix.lower() in {".mp4", ".mov"}
    }
    assert on_disk == listed
    for clip in clips:
        assert clip["device_model"]
        assert clip["fps"] > 0
        assert "shows_people" in clip
        assert "consent_record" in clip


@given("a fixture file shows people")
def file_shows_people(ctx: dict[str, Any], tmp_path: Path) -> None:
    target = tmp_path / "set"
    shutil.copytree(SYNTHETIC_60S, target)
    manifest = json.loads((target / "manifest.json").read_text("utf-8"))
    manifest["clips"] = [
        {
            "path": "clip.mp4",
            "device_model": "test-phone",
            "fps": 60,
            "vfr": False,
            "shows_people": True,
            "consent_record": "pending",
        }
    ]
    ctx["set"], ctx["manifest"] = target, manifest


@given("its manifest has no consent record")
def no_consent(ctx: dict[str, Any]) -> None:
    ctx["manifest"]["clips"][0]["consent_record"] = None
    (ctx["set"] / "manifest.json").write_text(json.dumps(ctx["manifest"], indent=2), "utf-8")


@when("the integrity check runs")
def integrity_check(ctx: dict[str, Any]) -> None:
    ctx["result"] = subprocess.run(
        ["uv", "run", "--no-sync", "racket-manifest-check", str(ctx["set"])],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
    )


@then("the check fails and names the file")
def check_fails(ctx: dict[str, Any]) -> None:
    result = ctx["result"]
    assert result.returncode == 1, result.stdout + result.stderr
    assert "clip.mp4" in result.stdout + result.stderr


@when("each file is probed")
def probe_each(ctx: dict[str, Any]) -> None:
    ffprobe = shutil.which("ffprobe")
    assert ffprobe, "ffprobe is needed to probe the fixtures"
    ctx["probes"] = {}
    for clip in ctx["manifest"]["clips"]:
        out = subprocess.run(
            [ffprobe, "-v", "error", "-show_format", "-show_streams", "-of", "json",
             str(PHONES / clip["path"])],
            capture_output=True, text=True, check=False, timeout=60,
        )  # fmt: skip
        ctx["probes"][clip["path"]] = json.loads(out.stdout or "{}")


@then("every file reports container, codec, frame rate and duration")
def every_file_reports(ctx: dict[str, Any]) -> None:
    for path, probe in ctx["probes"].items():
        video = [s for s in probe.get("streams", []) if s.get("codec_type") == "video"]
        assert video, path
        assert probe["format"]["format_name"], path
        assert video[0]["codec_name"] in {"h264", "hevc"}, path
        assert video[0]["avg_frame_rate"] not in {"0/0", ""}, path
        assert float(probe["format"]["duration"]) > 0, path
