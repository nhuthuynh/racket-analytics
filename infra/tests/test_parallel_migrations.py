"""CI-INTEG-BUDGET integration (NFR-073; ADR 0048): parallel test workers on one Postgres cluster
migrate their own databases safely once the integration job's migrate step has run.

Real Postgres 16 (scripts/dev-postgres.sh), the real migration chain plus the 0012-pattern
fixture revision of ``parallel_migrate.py``, the migrate module named by ci.yml. Each test uses
its own cluster-wide role, so one cluster serves the module.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from cluster import fresh_cluster, migrate_module, run_helper, unique_role

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def base_url(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    state: Path = tmp_path_factory.mktemp("pg")
    with fresh_cluster(state) as url:
        yield url


def _roles(url: str, role: str) -> int:
    with psycopg.connect(url, connect_timeout=5) as conn:
        row = conn.execute("SELECT count(*) FROM pg_roles WHERE rolname = %s", (role,)).fetchone()
        return int(row[0]) if row else 0


def _collides_on(role: str, failure: str) -> bool:
    """Both ways Postgres reports two CREATE ROLE of one name: the unique index, or the catalog
    check when the other transaction committed first."""
    return "pg_authid_rolname_index" in failure or f'role "{role}" already exists' in failure


def _databases(url: str) -> set[str]:
    with psycopg.connect(url, connect_timeout=5) as conn:
        return {r[0] for r in conn.execute("SELECT datname FROM pg_database").fetchall()}


# ---------------------------------------------------------------- negative case first
def test_without_the_step_the_losing_workers_fail_on_the_cluster_role_only(base_url: str) -> None:
    role = unique_role()

    out = run_helper("workers", base_url, role, "4")

    assert len(out["failed"]) == 3, out  # one worker creates the role, the other three collide
    assert all(_collides_on(role, f) for f in out["failed"]), out
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
