"""ST-076c unit tests: the restore drill's verdict, RPO, set checks and drill settings
(NFR-045.1-.4; ADR 0058 rules 3, 4 and 6; goal G05-03).

``scripts/ops/restore_drill.py`` is standard-library Python run on the host. These tests import
it and call its pure functions, and run its ``--check`` mode on recorded drill reports
(``fixtures/restore_drill/*.json``). No Docker: the live drill is
``test_restore_drill_scenarios.py``. Red first: the planted drill's report exits 1 naming
``corrections``. Negative cases first in each group.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from conftest import REPO_ROOT

pytestmark = pytest.mark.unit

SCRIPT = REPO_ROOT / "scripts" / "ops" / "restore_drill.py"
FIXTURES = Path(__file__).parent / "fixtures" / "restore_drill"
EXAMPLE = REPO_ROOT / "infra" / "env.example"


def load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("ops_restore_drill", SCRIPT)
    assert spec, f"missing {SCRIPT}"
    assert spec.loader, f"missing {SCRIPT}"
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ops_restore_drill"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def rd() -> ModuleType:
    return load()


def report(name: str = "clean") -> dict[str, Any]:
    return json.loads((FIXTURES / f"{name}.json").read_text())


def check(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--check", str(path)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


# ---------------------------------------------------------------- --check on recorded reports
def test_the_planted_drill_report_exits_1_naming_corrections() -> None:
    proc = check(FIXTURES / "planted.json")
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "corrections" in proc.stderr
    assert "objects" not in proc.stderr


def test_a_report_that_is_not_json_exits_2(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    assert check(bad).returncode == 2


def test_the_clean_drill_report_exits_0() -> None:
    proc = check(FIXTURES / "clean.json")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert json.loads(proc.stdout) == {"failures": [], "ok": True}


# ---------------------------------------------------------------- failures(): each target
@pytest.mark.parametrize(
    ("path", "value", "named"),
    [
        (("rpo_hours",), 24.01, "rpo"),
        (("rto_minutes",), 240.01, "rto"),
        (("corrections", "equal"), False, "corrections"),
        (("objects", "equal"), False, "objects"),
        (("objects", "manifest_equal"), False, "objects"),
        (("alembic_revision", "equal"), False, "alembic_revision"),
        (("dangling_object_refs",), ["matches/x/review.mp4"], "dangling_object_refs"),
        (("healthz",), 503, "healthz"),
    ],
)
def test_each_missed_target_is_named(
    rd: ModuleType, path: tuple[str, ...], value: Any, named: str
) -> None:
    r = report()
    node = r
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    assert named in rd.failures(r)


@pytest.mark.parametrize(
    "drop", ["rpo_hours", "rto_minutes", "corrections", "objects", "dangling_object_refs"]
)
def test_a_missing_measurement_fails_closed(rd: ModuleType, drop: str) -> None:
    r = report()
    del r[drop]
    assert rd.failures(r), f"no failure without {drop}"


def test_a_corrections_check_without_equal_true_fails(rd: ModuleType) -> None:
    r = report()
    r["corrections"]["equal"] = "true"  # only the boolean true counts
    assert "corrections" in rd.failures(r)


def test_a_drill_that_stopped_with_an_error_fails(rd: ModuleType) -> None:
    r = report()
    r["error"] = "restore: pg_restore exited 1"
    assert "error" in rd.failures(r)


def test_the_targets_themselves_pass(rd: ModuleType) -> None:
    r = report()
    r["rpo_hours"], r["rto_minutes"] = 24.0, 240.0
    assert rd.failures(r) == []


def test_the_clean_fixture_passes_and_the_planted_one_only_names_corrections(
    rd: ModuleType,
) -> None:
    assert rd.failures(report("clean")) == []
    assert rd.failures(report("planted")) == ["corrections"]


# ---------------------------------------------------------------- RPO (NFR-045.1)
def test_rpo_is_the_backup_age_at_drill_start_in_hours(rd: ModuleType) -> None:
    start = datetime(2026, 11, 12, 11, 0, 0, tzinfo=UTC)
    assert rd.rpo_hours("2026-11-11T10:00:00Z", start) == 25.0
    assert rd.rpo_hours("2026-11-12T10:30:00Z", start) == 0.5


def test_a_25_hour_old_backup_fails_the_rpo(rd: ModuleType) -> None:
    r = report()
    r["rpo_hours"] = rd.rpo_hours("2026-11-11T10:00:00Z", datetime(2026, 11, 12, 11, tzinfo=UTC))
    assert rd.failures(r) == ["rpo"]


# ---------------------------------------------------------------- objects (NFR-045.4)
def test_the_object_digest_changes_with_any_byte_and_ignores_order(rd: ModuleType) -> None:
    a = {"key": "matches/a/review.mp4", "size": 3, "sha256": "aa"}
    b = {"key": "matches/b/review.mp4", "size": 4, "sha256": "bb"}
    changed = {**b, "sha256": "bc"}
    assert rd.object_digest([a, b]) == rd.object_digest([b, a])
    assert rd.object_digest([a, b]) != rd.object_digest([a, changed])
    assert rd.object_digest([a, b])["count"] == 2
    assert rd.object_digest([]) == {"count": 0, "sha256": hashlib.sha256(b"").hexdigest()}


def test_dangling_refs_are_live_keys_missing_from_the_bucket(rd: ModuleType) -> None:
    inventory = [{"key": "matches/a/review.mp4", "size": 1, "sha256": "x"}]
    refs = ["matches/a/review.mp4", "matches/b/review.mp4"]
    assert rd.dangling(refs, inventory) == ["matches/b/review.mp4"]
    assert rd.dangling(refs[:1], inventory) == []


# ---------------------------------------------------------------- the set (rules 3 and 4)
def plant_set(root: Path, *, status: str = "complete", taken: str = "20261112T101500Z") -> Path:
    d = root / taken
    d.mkdir(parents=True)
    artefacts = {}
    for name in ("globals.sql.age", "db.dump.age", "objects.tar.age"):
        data = b"age-encryption.org/v1\n" + name.encode()
        (d / name).write_bytes(data)
        artefacts[name] = {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    meta = {"status": status, "taken_at": f"{taken[:4]}-{taken[4:6]}-{taken[6:8]}T10:15:00Z",
            "artefacts": artefacts, "alembic_revision": "0021"}  # fmt: skip
    (d / "backup.json").write_text(json.dumps(meta))
    return d


def test_a_set_that_is_not_complete_is_refused(rd: ModuleType, tmp_path: Path) -> None:
    d = plant_set(tmp_path, status="running")
    with pytest.raises(rd.SetRefused, match="complete"):
        rd.verify_set(d)


def test_a_changed_artefact_is_refused_before_decrypting(rd: ModuleType, tmp_path: Path) -> None:
    d = plant_set(tmp_path)
    (d / "db.dump.age").write_bytes(b"age-encryption.org/v1\nchanged")
    with pytest.raises(rd.SetRefused, match=r"db\.dump\.age"):
        rd.verify_set(d)


def test_a_missing_artefact_is_refused(rd: ModuleType, tmp_path: Path) -> None:
    d = plant_set(tmp_path)
    (d / "objects.tar.age").unlink()
    with pytest.raises(rd.SetRefused, match=r"objects\.tar\.age"):
        rd.verify_set(d)


def test_a_verified_set_returns_its_metadata(rd: ModuleType, tmp_path: Path) -> None:
    meta = rd.verify_set(plant_set(tmp_path))
    assert meta["alembic_revision"] == "0021"


def test_no_complete_set_is_refused(rd: ModuleType, tmp_path: Path) -> None:
    plant_set(tmp_path, status="failed")
    with pytest.raises(rd.SetRefused, match="no complete"):
        rd.newest_complete(tmp_path)


def test_the_newest_complete_set_is_chosen(rd: ModuleType, tmp_path: Path) -> None:
    plant_set(tmp_path, taken="20261110T101500Z")
    newest = plant_set(tmp_path, taken="20261111T101500Z")
    plant_set(tmp_path, taken="20261112T101500Z", status="failed")
    assert rd.newest_complete(tmp_path) == newest


# ---------------------------------------------------------------- globals (rule 4 step 4)
def test_only_the_owner_create_role_line_is_dropped(rd: ModuleType) -> None:
    sql = (
        "CREATE ROLE racket;\nALTER ROLE racket WITH SUPERUSER LOGIN;\n"
        "CREATE ROLE racket_media_worker;\nCREATE ROLE racketeer;\n"
    )
    out = rd.strip_owner_role(sql, "racket")
    assert "CREATE ROLE racket;" not in out.splitlines()
    assert "ALTER ROLE racket WITH SUPERUSER LOGIN;" in out
    assert "CREATE ROLE racket_media_worker;" in out
    assert "CREATE ROLE racketeer;" in out


# ---------------------------------------------------------------- drill settings
def test_the_drill_env_remaps_every_host_port_and_turns_the_flags_on(
    rd: ModuleType, tmp_path: Path
) -> None:
    example = EXAMPLE.read_text()
    ports = iter(range(41000, 41100))
    env = rd.drill_env(example, flags="on", backups=tmp_path, port=lambda: next(ports))
    host_ports = [k for k in rd.parse_env(example) if k.endswith("_HOST_PORT")]
    assert host_ports, "env.example names no host ports"
    assert {env[k] for k in host_ports} == {str(41000 + i) for i in range(len(host_ports))}
    assert all(env[k] == "true" for k in rd.parse_env(example) if k.startswith("FEATURE_"))
    assert env["BACKUP_HOST_DIR"] == str(tmp_path)


def test_flags_off_keeps_every_feature_off(rd: ModuleType, tmp_path: Path) -> None:
    example = EXAMPLE.read_text()
    env = rd.drill_env(example, flags="off", backups=tmp_path, port=lambda: 42000)
    flags = [k for k in rd.parse_env(example) if k.startswith("FEATURE_")]
    assert flags
    assert all(env[k] == "false" for k in flags)


def test_the_planted_option_is_recorded_in_the_arguments(rd: ModuleType) -> None:
    args = rd.parse_args(["--project", "racket-drill05b", "--plant-delete-correction"])
    assert args.plant_delete_correction is True
    assert args.flags == "on"
    assert rd.parse_args(["--project", "p"]).plant_delete_correction is False


def test_a_project_name_compose_would_refuse_is_rejected(rd: ModuleType) -> None:
    with pytest.raises(SystemExit):
        rd.parse_args(["--project", "Racket Drill"])


def test_fixtures_are_independent_copies(rd: ModuleType) -> None:
    r = report()
    before = copy.deepcopy(r)
    rd.failures(r)
    assert r == before, "failures() must not change the report"


# ---------------------------------------------------------------- Compose commands
def test_up_never_starts_the_ops_profile(rd: ModuleType, tmp_path: Path) -> None:
    """The `backup` service (profile ops) has a 1 h start period: `up --wait` with the profile
    waited on it (live run 2026-11-12). Only the backup's own calls and `down` name it."""
    st = rd.Stack("racket-drill-u", {"POSTGRES_USER": "racket"}, tmp_path)
    assert "--profile" not in st.cmd("up", "-d", "--build", "--wait")
    assert "--profile" not in st.cmd("run", "--rm", "--no-deps", "db-roles")
    for args in (("run", "--rm", "backup", "--once"), ("build", "backup"), ("down", "-v")):
        cmd = st.cmd(*args)
        assert cmd[cmd.index("--profile") + 1] == "ops", args
    assert "--profile" in st.cmd(*st.decrypt(tmp_path / "db.dump.age"))
