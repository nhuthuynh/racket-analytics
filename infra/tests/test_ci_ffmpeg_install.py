"""CI-FFMPEG unit tests for scripts/ci/install_ffmpeg.py: the pin, the cache check, the
checksum-verified extraction (fails closed), the per-attempt deadline and the named budget
failure. Negative cases first. No network: the download tests use a fake opener and clock."""

from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path
from typing import Any

import pytest
from conftest import SCRIPTS_DIR
from ffmpeg_fixtures import ARCHIVE, FILES, NAME, build_archive, fill_install_dir, sha256

pytestmark = pytest.mark.unit

_spec = importlib.util.spec_from_file_location(
    "install_ffmpeg", SCRIPTS_DIR / "ci" / "install_ffmpeg.py"
)
assert _spec is not None
assert _spec.loader is not None
ff = importlib.util.module_from_spec(_spec)
sys.modules["install_ffmpeg"] = ff  # dataclasses resolve the module by name
_spec.loader.exec_module(ff)

PINNED = {rel: sha256(data) for rel, data in FILES.items()}


def pin_dict(**over: Any) -> dict[str, Any]:
    pin = {
        "schema": "ffmpeg-pin/v1",
        "tag": "autobuild-test",
        "name": NAME,
        "archive_sha256": sha256(ARCHIVE),
        "sources": ["https://example.invalid/{tag}/{name}.tar.xz"],
        "files": PINNED,
        "licence": "test",
    }
    pin.update(over)
    return pin


# ------------------------------------------------------------------ pin (fails closed)
@pytest.mark.parametrize(
    "over",
    [
        {"archive_sha256": "abc"},
        {"archive_sha256": "Z" * 64},
        {"sources": []},
        {"files": {}},
        {"files": {"bin/ffmpeg": "nothex"}},
        {"files": {"../escape": "a" * 64}},
        {"schema": "ffmpeg-pin/v0"},
    ],
)
def test_a_bad_pin_is_refused(tmp_path: Path, over: dict[str, Any]) -> None:
    path = tmp_path / "pin.json"
    path.write_text(json.dumps(pin_dict(**over)))
    with pytest.raises(ff.PinError):
        ff.load_pin(path)


def test_the_repository_pin_is_valid_and_names_ffmpeg_and_ffprobe() -> None:
    pin = ff.load_pin(SCRIPTS_DIR / "ci" / "ffmpeg-pin.json")
    assert {"bin/ffmpeg", "bin/ffprobe", "LICENSE.txt"} <= set(pin.files)
    assert all(s.startswith("https://") for s in pin.sources)


def test_sources_are_formatted_and_cycled_per_attempt(tmp_path: Path) -> None:
    path = tmp_path / "pin.json"
    path.write_text(json.dumps(pin_dict(sources=["https://a/{tag}/{name}.tar.xz", "https://b/x"])))
    pin = ff.load_pin(path)
    assert ff.source_for(pin, 0) == f"https://a/autobuild-test/{NAME}.tar.xz"
    assert ff.source_for(pin, 1) == "https://b/x"
    assert ff.source_for(pin, 2) == ff.source_for(pin, 0)


# ------------------------------------------------------------------ cache check
def test_an_empty_install_dir_is_a_miss(tmp_path: Path) -> None:
    assert ff.cache_state(tmp_path / "none", PINNED)[0] == "miss"


def test_a_changed_cached_file_is_a_mismatch(tmp_path: Path) -> None:
    fill_install_dir(tmp_path)
    (tmp_path / "bin" / "ffmpeg").write_bytes(b"other")
    state, detail = ff.cache_state(tmp_path, PINNED)
    assert state == "mismatch"
    assert "bin/ffmpeg" in detail


def test_a_cached_file_missing_is_a_mismatch(tmp_path: Path) -> None:
    fill_install_dir(tmp_path)
    (tmp_path / "LICENSE.txt").unlink()
    assert ff.cache_state(tmp_path, PINNED)[0] == "mismatch"


def test_the_pinned_files_in_place_are_a_hit(tmp_path: Path) -> None:
    fill_install_dir(tmp_path)
    assert ff.cache_state(tmp_path, PINNED)[0] == "hit"


# ------------------------------------------------------------------ extraction (fails closed)
def test_an_extracted_file_with_another_checksum_fails_closed(tmp_path: Path) -> None:
    archive = tmp_path / "a.tar.xz"
    archive.write_bytes(build_archive({**FILES, "bin/ffprobe": b"tampered"}))
    dest = tmp_path / "dest"
    with pytest.raises(ff.VerifyError, match=r"sha256 mismatch.*bin/ffprobe"):
        ff.extract(archive, NAME, PINNED, dest)
    assert not (dest / "bin" / "ffprobe").exists()
    assert not (dest / "bin" / "ffmpeg").exists()


def test_a_member_missing_from_the_archive_fails_closed(tmp_path: Path) -> None:
    archive = tmp_path / "a.tar.xz"
    archive.write_bytes(build_archive({k: v for k, v in FILES.items() if k != "bin/ffmpeg"}))
    with pytest.raises(ff.VerifyError, match="bin/ffmpeg"):
        ff.extract(archive, NAME, PINNED, tmp_path / "dest")


def test_extract_installs_only_the_pinned_files_executable(tmp_path: Path) -> None:
    archive = tmp_path / "a.tar.xz"
    archive.write_bytes(ARCHIVE)
    dest = tmp_path / "dest"
    ff.extract(archive, NAME, PINNED, dest)
    assert sorted(str(p.relative_to(dest)) for p in dest.rglob("*") if p.is_file()) == sorted(FILES)
    assert (dest / "bin" / "ffprobe").stat().st_mode & 0o111
    assert ff.cache_state(dest, PINNED)[0] == "hit"


def test_archive_checksum_mismatch_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "a.tar.xz"
    path.write_bytes(b"not the archive")
    with pytest.raises(ff.VerifyError, match="sha256 mismatch"):
        ff.verify_archive(path, sha256(ARCHIVE))


# ------------------------------------------------------------------ bounded download
class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class Trickle(io.RawIOBase):
    """A response that returns one byte per read and advances the fake clock 1 s per read."""

    def __init__(self, clock: FakeClock) -> None:
        self.clock = clock

    def read(self, n: int = -1) -> bytes:  # type: ignore[override]
        self.clock.now += 1.0
        return b"x"

    def __enter__(self) -> Trickle:
        return self

    def __exit__(self, *_: object) -> None:
        return None


def test_a_download_past_its_deadline_raises_attempt_timeout(tmp_path: Path) -> None:
    clock = FakeClock()
    with pytest.raises(ff.AttemptTimeout):
        ff.download(
            "https://a/x",
            tmp_path / "out",
            deadline=5.0,
            opener=lambda url, timeout: Trickle(clock),
            clock=clock,
        )


def test_a_download_finishes_and_writes_the_bytes(tmp_path: Path) -> None:
    out = tmp_path / "out"
    ff.download(
        "https://a/x",
        out,
        deadline=1e9,
        opener=lambda url, timeout: io.BytesIO(ARCHIVE),
        clock=FakeClock(),
    )
    assert out.read_bytes() == ARCHIVE


def test_the_budget_message_names_the_ticket_budget_and_each_attempt() -> None:
    timed_out = "github.com: timed out after 75 s"
    msg = ff.budget_message(180, [timed_out, timed_out])
    assert msg.startswith("CI-FFMPEG: ffmpeg install exceeded its budget of 180 s after 2 attempts")
    assert msg.count("timed out after 75 s") == 2


def test_the_attempt_limits_fit_inside_the_default_budget() -> None:
    assert ff.DEFAULT_ATTEMPTS == 2
    assert ff.DEFAULT_ATTEMPTS * ff.DEFAULT_ATTEMPT_TIMEOUT_S <= ff.DEFAULT_BUDGET_S
    assert ff.DEFAULT_BUDGET_S < 4 * 60  # the workflow step limit (timeout-minutes: 4)
