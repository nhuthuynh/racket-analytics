"""scripts/fixtures/build_phone_manifest.py and the committed phone-profile set (ST-025, NFR-025).

Integration (filesystem + ffprobe). The profile set is synthetic (no people, CC0): it covers
the container/codec/frame-rate shapes phones write, not real phone bitrates (R-05 needs
real recordings, docs/data/phone-fixtures.md).
"""

from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path
from types import ModuleType

import pytest

from racket.dataset.cli import main as manifest_check
from tests.support.paths import FIXTURES, REPO

pytestmark = pytest.mark.integration

TOOL = REPO / "scripts" / "fixtures" / "build_phone_manifest.py"
PROFILES = FIXTURES / "clips" / "phone-profiles-v1"


def _tool() -> ModuleType:
    spec = importlib.util.spec_from_file_location("build_phone_manifest", TOOL)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _one_clip_set(tmp_path: Path, csv_rows: str) -> Path:
    target = tmp_path / "set"
    target.mkdir()
    shutil.copy(PROFILES / "h264-mp4-1080p60.mp4", target / "a.mp4")
    (target / "recordings.csv").write_text(
        "path,device_model,shows_people,consent_record\n" + csv_rows, "utf-8"
    )
    return target


def _build(target: Path) -> int:
    code: int = _tool().main(
        [str(target), "--id", "t", "--version", "1", "--licence", "CC0-1.0",
         "--consent-status", "synthetic"]
    )  # fmt: skip
    return code


@pytest.fixture(autouse=True)
def _needs_ffprobe() -> None:
    assert shutil.which("ffprobe"), "ffprobe is required for this check"


# --- negative cases first -------------------------------------------------------------


def test_tool_refuses_a_csv_that_misses_a_video(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target = _one_clip_set(tmp_path, "")

    assert _build(target) == 1
    assert "a.mp4" in capsys.readouterr().out
    assert not (target / "manifest.json").exists()


def test_people_without_consent_are_written_and_then_fail_the_check(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target = _one_clip_set(tmp_path, "a.mp4,Test Phone,true,\n")

    assert _build(target) == 0
    capsys.readouterr()

    assert manifest_check([str(target)]) == 1
    assert "a.mp4" in capsys.readouterr().out


# --- positive -----------------------------------------------------------------------------


def test_built_manifest_passes_the_check_and_reports_r05_numbers(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target = _one_clip_set(tmp_path, "a.mp4,Test Phone,false,\n")

    assert _build(target) == 0
    r05 = json.loads(capsys.readouterr().out)

    assert manifest_check([str(target)]) == 0
    clip = json.loads((target / "manifest.json").read_text("utf-8"))["clips"][0]
    assert (clip["video_codec"], clip["fps"], clip["vfr"]) == ("h264", 60.0, False)
    assert r05["break_even_mb_per_minute"] == pytest.approx(66.667, abs=0.001)
    assert r05["per_clip"][0]["mb_per_minute"] == pytest.approx(clip["mb_per_minute"])


def test_committed_profile_set_covers_the_phone_shapes() -> None:
    manifest = json.loads((PROFILES / "manifest.json").read_text("utf-8"))
    clips = manifest["clips"]

    assert manifest["consent_status"] == "synthetic"
    assert not any(c["shows_people"] for c in clips)
    assert {c["video_codec"] for c in clips} == {"h264", "hevc"}
    assert any(c["path"].endswith(".mov") for c in clips)
    assert any(c["path"].endswith(".mp4") for c in clips)
    assert any(c["vfr"] for c in clips)
    assert all(c["device_model"].startswith("synthetic-profile/") for c in clips)


def test_committed_profile_clip_entries_match_a_fresh_probe() -> None:
    tool = _tool()
    manifest = json.loads((PROFILES / "manifest.json").read_text("utf-8"))

    for clip in manifest["clips"]:
        row = {
            "path": clip["path"],
            "device_model": clip["device_model"],
            "shows_people": str(clip["shows_people"]).lower(),
            "consent_record": clip["consent_record"] or "",
        }
        fresh = tool.clip_entry(tool.recording(PROFILES, row))
        assert fresh == clip, clip["path"]
