"""ST-082 unit tests for scripts/ops/rollback_drill.py, infra/compose.release.yaml and the
`make up IMAGE_TAG=<tag>` path (REL-1.2; ADR 0058 rule 7). The drill runs as a process against a
recording stand-in for `docker` (rollback_fixtures.py); the Makefile is resolved by `make -n`."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml
from conftest import REPO_ROOT
from rollback_fixtures import FINGERPRINT, calls, make_env, marker_cmd, report, run_drill

pytestmark = pytest.mark.unit

TAG, REV = "r1-rehearsal-0020", "0020"
CURRENT = "r1-rc1"  # `release` in the fixture notes (rollback_fixtures.NOTES)
BUILT = {"migrate", "api", "worker", "mailer", "purge", "web"}  # at least these (ST-076a adds more)


def _built() -> set[str]:
    base = yaml.safe_load((REPO_ROOT / "infra" / "compose.yaml").read_text())["services"]
    return {name for name, svc in base.items() if "build" in svc}


def _started() -> set[str]:
    """Built services that `up` starts without a profile: the previous release's image set."""
    base = yaml.safe_load((REPO_ROOT / "infra" / "compose.yaml").read_text())["services"]
    return {name for name, svc in base.items() if "build" in svc and not svc.get("profiles")}


def _drill(tmp_path: Path, *extra: str, **env_over: str):
    env = make_env(tmp_path, TAG, REV)
    env.update(env_over)
    args = ["--project", "racket-drill", "--to-previous-tag"]
    args += ["--backup-cmd", marker_cmd(tmp_path, "backup")]
    return run_drill(tmp_path, env, *args, *extra)


def _compose_calls(tmp_path: Path, word: str) -> list[dict]:
    return [c for c in calls(tmp_path) if "argv" in c and word in c["argv"]]


def _downgrades(tmp_path: Path) -> list[dict]:
    return [
        c
        for c in _compose_calls(tmp_path, "run")
        if any("command.downgrade" in a for a in c["argv"])
    ]


def _integrity(tmp_path: Path) -> list[dict]:
    return [c for c in _compose_calls(tmp_path, "run") if "racket-integrity" in c["argv"]]


# ------------------------------------------------------------------ preconditions (exit 2)
def test_missing_previous_images_refuse_before_any_change(tmp_path: Path) -> None:
    proc = _drill(tmp_path, FAKE_DOCKER_MISSING=f"racket-api:{TAG}")
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "racket-api:" + TAG in proc.stdout + proc.stderr
    assert not _compose_calls(tmp_path, "run")
    assert not [c for c in calls(tmp_path) if c.get("step") == "backup"]


def test_notes_without_the_previous_revision_refuse(tmp_path: Path) -> None:
    env = make_env(tmp_path, TAG, REV)
    notes = tmp_path / "notes.md"
    notes.write_text(notes.read_text().replace('previous_alembic_revision: "0020"\n', ""))
    proc = run_drill(tmp_path, env, "--project", "racket-drill", "--to-previous-tag")
    assert proc.returncode == 2
    assert "previous_alembic_revision" in proc.stdout + proc.stderr


def test_without_a_backup_command_the_backup_service_takes_the_backup(tmp_path: Path) -> None:
    # ST-076a added the `backup` service to compose.yaml, so the drill no longer needs
    # --backup-cmd (decision row 4 in docs/sprints/05/decisions/ST-082.md).
    env = make_env(tmp_path, TAG, REV)
    proc = run_drill(tmp_path, env, "--project", "racket-drill", "--to-previous-tag")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    (backup,) = [c for c in _compose_calls(tmp_path, "run") if "backup" in c["argv"]]
    assert backup["argv"][-3:] == ["--rm", "backup", "--once"]
    assert ["--profile", "ops"] == backup["argv"][backup["argv"].index("--profile") :][:2]


def _inspected(tmp_path: Path) -> set[str]:
    return {c["argv"][2] for c in calls(tmp_path) if c.get("argv", [])[:2] == ["image", "inspect"]}


def test_every_built_service_image_of_the_current_release_is_checked(tmp_path: Path) -> None:
    # PE F2 (PR #224): step 5 redeploys the current set with --no-build and step 1 runs
    # racket-backup:<current>, so step 0 checks every built service, the ops profile included.
    _drill(tmp_path)
    current = {i for i in _inspected(tmp_path) if i.endswith(f":{CURRENT}")}
    assert current == {f"racket-{s}:{CURRENT}" for s in _built()}
    assert f"racket-backup:{CURRENT}" in current


def test_only_the_services_the_redeploy_starts_are_checked_for_the_previous_tag(
    tmp_path: Path,
) -> None:
    # PE F4 (PR #224): step 3 runs `up` without a profile, so it never starts `backup`; the
    # previous release (09d279dd) has no backup service, so racket-backup:<previous> never exists.
    _drill(tmp_path)
    previous = {i for i in _inspected(tmp_path) if i.endswith(f":{TAG}")}
    assert previous == {f"racket-{s}:{TAG}" for s in _started()}
    assert f"racket-backup:{TAG}" not in previous


def test_a_previous_set_without_a_backup_image_is_not_refused(tmp_path: Path) -> None:
    # PE F4: the documented previous-set build (docs/releases/r1-rc.md) has no racket-backup.
    proc = _drill(tmp_path, FAKE_DOCKER_MISSING=f"racket-backup:{TAG}")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert report(tmp_path)["rc"] == 0


def test_a_missing_current_backup_image_refuses_before_any_change(tmp_path: Path) -> None:
    proc = _drill(tmp_path, FAKE_DOCKER_MISSING=f"racket-backup:{CURRENT}")
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert f"racket-backup:{CURRENT}" in proc.stdout + proc.stderr
    assert not _compose_calls(tmp_path, "run")
    assert not [c for c in calls(tmp_path) if c.get("step") == "backup"]


def test_missing_current_images_refuse_before_any_change(tmp_path: Path) -> None:
    proc = _drill(tmp_path, FAKE_DOCKER_MISSING=f"racket-api:{CURRENT}")
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert f"racket-api:{CURRENT}" in proc.stdout + proc.stderr
    assert not _compose_calls(tmp_path, "run")
    assert not [c for c in calls(tmp_path) if c.get("step") == "backup"]


def test_the_backup_service_runs_the_current_release_image(tmp_path: Path) -> None:
    # Without --backup-cmd the project's `backup` service takes the step-1 backup; under a release
    # it must use racket-backup:<current>, never a per-project image built from the working tree.
    env = make_env(tmp_path, TAG, REV)
    proc = run_drill(tmp_path, env, "--project", "racket-drill", "--to-previous-tag")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    (backup,) = [c for c in _compose_calls(tmp_path, "run") if "backup" in c["argv"]]
    assert backup["image_tag"] == CURRENT
    assert str(REPO_ROOT / "infra" / "compose.release.yaml") in backup["argv"]
    assert "--build" not in backup["argv"]


# ------------------------------------------------------------------ the rule 7 order
def test_the_downgrade_runs_with_the_current_image_to_the_previous_revision(tmp_path: Path) -> None:
    proc = _drill(tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    (down,) = _downgrades(tmp_path)
    # PE F1 (PR #224): racket-migrate:<current> through the override, never a per-project build.
    assert down["image_tag"] == CURRENT
    assert str(REPO_ROOT / "infra" / "compose.release.yaml") in down["argv"]
    assert down["argv"][-1] == REV
    assert down["argv"][:4] == ["compose", "-p", "racket-drill", "-f"]


def test_the_redeploy_starts_the_previous_tag_without_building(tmp_path: Path) -> None:
    _drill(tmp_path)
    (up,) = _compose_calls(tmp_path, "up")
    assert up["image_tag"] == TAG
    assert "--no-build" in up["argv"]
    assert "--build" not in up["argv"]
    assert "--wait" in up["argv"]
    assert str(REPO_ROOT / "infra" / "compose.release.yaml") in up["argv"]


def test_a_wrong_revision_after_the_downgrade_fails_and_falls_back(tmp_path: Path) -> None:
    proc = _drill(
        tmp_path, "--restore-cmd", marker_cmd(tmp_path, "restore"), FAKE_DOCKER_REVISION="0021"
    )
    assert proc.returncode == 1
    names = [s["name"] for s in report(tmp_path)["steps"]]
    assert names == [
        "fingerprint-before",
        "backup",
        "downgrade",
        "restore",
        "redeploy",
        "health",
        "fingerprint-after",
    ]


def test_a_failed_downgrade_without_a_restore_command_stops_with_the_runbook(
    tmp_path: Path,
) -> None:
    proc = _drill(tmp_path, FAKE_DOCKER_FAIL="command.downgrade")
    assert proc.returncode == 1
    assert "restore-runbook" in proc.stdout + proc.stderr
    assert not _compose_calls(tmp_path, "up")


def test_a_failed_health_probe_fails_the_drill(tmp_path: Path) -> None:
    proc = _drill(
        tmp_path, "--restore-cmd", marker_cmd(tmp_path, "restore"), FAKE_DOCKER_FAIL="healthz"
    )
    assert proc.returncode == 1
    steps = report(tmp_path)["steps"]
    assert steps[-1]["name"] == "health"
    assert steps[-1]["rc"] != 0


def test_a_failed_backup_stops_before_the_downgrade(tmp_path: Path) -> None:
    env = make_env(tmp_path, TAG, REV)
    proc = run_drill(
        tmp_path, env, "--project", "racket-drill", "--to-previous-tag", "--backup-cmd", "false"
    )
    assert proc.returncode == 1
    assert not _downgrades(tmp_path)
    assert not _compose_calls(tmp_path, "up")


def test_the_report_records_each_step_with_rc_and_seconds(tmp_path: Path) -> None:
    _drill(tmp_path)
    rep = report(tmp_path)
    assert rep["rc"] == 0
    assert rep["to"] == {"tag": TAG, "revision": REV}
    assert [s["name"] for s in rep["steps"]] == [
        "fingerprint-before",
        "backup",
        "downgrade",
        "redeploy",
        "health",
        "fingerprint-after",
    ]
    assert all(s["rc"] == 0 and s["seconds"] >= 0 for s in rep["steps"])


def test_an_explicit_tag_and_revision_override_the_notes(tmp_path: Path) -> None:
    env = make_env(tmp_path, TAG, "0019")
    args = ["--project", "p", "--to", "r1-x", "--revision", "0019"]
    proc = run_drill(tmp_path, env, *args, "--backup-cmd", marker_cmd(tmp_path, "backup"))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert report(tmp_path)["to"] == {"tag": "r1-x", "revision": "0019"}


# --------------------------------------------------------------- NFR-045.3: corrections fingerprint
# Security review F2 (PR #224; T5-RB-4): a rollback that loses or changes confirmed corrections
# must not exit 0. racket-integrity (ST-076b) runs before the backup and after the health check.
def test_the_fingerprint_is_taken_before_the_backup_and_checked_after_health(
    tmp_path: Path,
) -> None:
    proc = _drill(tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    names = [s["name"] for s in report(tmp_path)["steps"]]
    assert names[0] == "fingerprint-before"
    assert names[-2:] == ["health", "fingerprint-after"]
    count, digest = FINGERPRINT.split(":")
    assert report(tmp_path)["corrections"] == {
        "before": {"count": int(count), "sha256": digest},
        "after": {"count": int(count), "sha256": digest},
        "equal": True,
    }


def test_both_fingerprints_run_racket_integrity_in_the_current_release_image(
    tmp_path: Path,
) -> None:
    _drill(tmp_path)
    before, after = _integrity(tmp_path)
    count, digest = FINGERPRINT.split(":")
    for call in (before, after):
        assert call["image_tag"] == CURRENT  # the previous release predates racket-integrity
        assert str(REPO_ROOT / "infra" / "compose.release.yaml") in call["argv"]
        assert "migrate" in call["argv"]
    assert "--expect-count" not in before["argv"]
    assert after["argv"][-4:] == ["--expect-count", count, "--expect-sha256", digest]


def test_a_rollback_that_changes_the_corrections_fails(tmp_path: Path) -> None:
    proc = _drill(tmp_path, FAKE_DOCKER_FINGERPRINT_AFTER="2:" + "b" * 64)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    rep = report(tmp_path)
    assert rep["rc"] == 1
    assert rep["corrections"]["equal"] is False
    assert rep["corrections"]["after"] == {"count": 2, "sha256": "b" * 64}
    assert rep["steps"][-1] == {**rep["steps"][-1], "name": "fingerprint-after", "rc": 1}
    assert "corrections" in proc.stderr


def test_a_failed_fingerprint_before_stops_before_the_backup(tmp_path: Path) -> None:
    proc = _drill(tmp_path, FAKE_DOCKER_FAIL="racket-integrity")
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert [s["name"] for s in report(tmp_path)["steps"]] == ["fingerprint-before"]
    assert not [c for c in calls(tmp_path) if c.get("step") == "backup"]
    assert not _downgrades(tmp_path)


def test_no_fingerprint_after_when_the_health_check_fails(tmp_path: Path) -> None:
    proc = _drill(tmp_path, FAKE_DOCKER_FAIL="healthz")
    assert proc.returncode == 1
    assert len(_integrity(tmp_path)) == 1
    assert report(tmp_path)["corrections"]["after"] is None


# ------------------------------------------------------------------ compose.release.yaml and make
def test_the_release_override_tags_every_built_service_and_nothing_else() -> None:
    built = _built()
    assert built >= BUILT
    release = yaml.safe_load((REPO_ROOT / "infra" / "compose.release.yaml").read_text())
    assert set(release["services"]) == built
    for name, svc in release["services"].items():
        assert set(svc) == {"image", "environment"}, name
        assert svc["image"] == f"racket-{name}:${{IMAGE_TAG:?set IMAGE_TAG}}", name


def test_the_release_override_pins_the_rc_runtime_settings_on_every_service() -> None:
    # Security review F1 (PR #224; T5-RB-3): infra/.env from env.example says APP_ENV=dev and
    # DEV_IDENTITY_ENABLED=true; a release must not inherit either, whatever infra/.env says.
    release = yaml.safe_load((REPO_ROOT / "infra" / "compose.release.yaml").read_text())
    for name, svc in release["services"].items():
        assert svc["environment"] == {"APP_ENV": "staging", "DEV_IDENTITY_ENABLED": "false"}, name


def _make_n(*args: str) -> str:
    res = subprocess.run(
        ["make", "-n", "--no-print-directory", "-C", str(REPO_ROOT), *args],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert res.returncode == 0, res.stderr
    return res.stdout


def test_make_up_without_a_tag_still_builds_the_working_tree() -> None:
    out = _make_n("up")
    assert "up -d --build --wait" in out
    assert "compose.release.yaml" not in out


def test_make_up_with_a_release_tag_starts_that_tag_without_building() -> None:
    out = _make_n("up", "IMAGE_TAG=r1-rc1")
    assert "-f infra/compose.release.yaml" in out
    assert "--no-build" in out
    assert "--build " not in out


def test_make_release_images_builds_the_tagged_set() -> None:
    out = _make_n("release-images", "IMAGE_TAG=r1-rc1")
    assert "-f infra/compose.release.yaml" in out
    assert " build" in out


def test_make_release_images_also_builds_the_ops_profile_backup_image() -> None:
    # `backup` is in profile `ops`; `compose build` skips it without the profile, and step 0 of
    # the drill would then refuse every release for a missing racket-backup:<tag>.
    out = _make_n("release-images", "IMAGE_TAG=r1-rc1")
    assert "--profile ops" in out
