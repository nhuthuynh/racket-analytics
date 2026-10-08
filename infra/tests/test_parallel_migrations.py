"""CI-INTEG-BUDGET integration (NFR-073; ADR 0048): parallel test workers on one Postgres cluster
migrate their own databases safely once the integration job's migrate step has run.

Real Postgres 16 (scripts/dev-postgres.sh), the real migration chain plus the 0012-pattern
fixture revision of ``parallel_migrate.py``, the migrate module named by ci.yml. Each test uses
its own fresh cluster, as CI's Compose Postgres is fresh on every run.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from cluster import collides_on, fresh_cluster, migrate_module, run_helper, unique_role

pytestmark = pytest.mark.integration


@pytest.fixture
def base_url(tmp_path: Path) -> Iterator[str]:
    """A fresh cluster per test: the base database's migration head is part of the state."""
    with fresh_cluster(tmp_path / "pg") as url:
        yield url


def _roles(url: str, role: str) -> int:
    with psycopg.connect(url, connect_timeout=5) as conn:
        row = conn.execute("SELECT count(*) FROM pg_roles WHERE rolname = %s", (role,)).fetchone()
        return int(row[0]) if row else 0


def _databases(url: str) -> set[str]:
    with psycopg.connect(url, connect_timeout=5) as conn:
        return {r[0] for r in conn.execute("SELECT datname FROM pg_database").fetchall()}


# ---------------------------------------------------------------- negative case first
def test_without_the_step_the_losing_workers_fail_on_the_cluster_role_only(base_url: str) -> None:
    role = unique_role()

    out = run_helper("workers", base_url, role, "4")

    # One worker creates the role; any worker inside the 1 s window collides. A worker released
    # late sees the committed role and passes, so the count is a range (PE-PR15-03, QA-PR15-02).
    assert 1 <= len(out["failed"]) <= 3, out
    assert all(collides_on(role, f) for f in out["failed"]), out
    assert out["at_head"] == out["workers"] - len(out["failed"]), out
    assert _roles(base_url, role) == 1


# ---------------------------------------------------------------- the migrate step
def test_the_migrate_step_creates_the_cluster_role_on_the_base_database(base_url: str) -> None:
    role = unique_role()

    out = run_helper("step", base_url, role, migrate_module())

    assert out == {"rc": 0, "base_version": "ci_cluster_role"}
    assert _roles(base_url, role) == 1


def test_the_migrate_step_is_harmless_when_run_again(base_url: str) -> None:
    role = unique_role()
    run_helper("step", base_url, role, migrate_module())

    again = run_helper("step", base_url, role, migrate_module())

    assert again == {"rc": 0, "base_version": "ci_cluster_role"}
    assert _roles(base_url, role) == 1


def test_after_the_step_four_workers_reach_head_and_leave_no_database(base_url: str) -> None:
    role = unique_role()
    run_helper("step", base_url, role, migrate_module())
    before = _databases(base_url)

    out = run_helper("workers", base_url, role, "4")

    assert out == {"workers": 4, "failed": [], "at_head": 4}
    assert _roles(base_url, role) == 1
    assert _databases(base_url) == before


def test_the_helper_leaves_no_copy_of_the_migrations_behind(
    base_url: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    monkeypatch.setenv("TMPDIR", str(scratch))  # the helper's tempfile.mkdtemp lands here
    role = unique_role()

    run_helper("step", base_url, role, migrate_module())
    run_helper("workers", base_url, role, "2")

    assert sorted(p.name for p in scratch.iterdir() if p.name.startswith("ra-migrations-")) == []
