"""Binds tests/features/goal_harness_sprint03.feature (HARNESS-03; G03-01 step 8, G03-03).

The purge check (`live_stats.purge_check`) runs against a real Postgres cluster
(scripts/dev-postgres.sh) through the real `psql` client, exactly as the verifier runs it against
the stack; the purge job is a `psql` command. The rally video link is a local HTTP stand-in for
the object store (206 while the object exists, 404 once purged), and Mailpit is the local fake
of test_livehttp_mailpit.py. Standard library plus pytest-bdd; no product imports.
"""

from __future__ import annotations

import importlib.util
import shlex
import sys
import threading
import time
import uuid
from argparse import Namespace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest
from cluster import fresh_cluster
from conftest import SCRIPTS_DIR
from pytest_bdd import given, parsers, scenarios, then, when
from test_livehttp_mailpit import FakeMailpit

pytestmark = pytest.mark.integration
scenarios("goal_harness_sprint03.feature")

MEASURE = SCRIPTS_DIR / "measure"
if str(MEASURE) not in sys.path:
    sys.path.insert(0, str(MEASURE))


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, MEASURE / f"{name}.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


live = _load("live_stats")
lh = sys.modules["livehttp"]

SCHEMA = """
CREATE TABLE accounts (id uuid PRIMARY KEY);
CREATE TABLE matches (id uuid PRIMARY KEY, owner_id uuid NOT NULL);
CREATE TABLE match_rallies (match_id uuid NOT NULL, rally int NOT NULL);
CREATE TABLE metric_snapshots (match_id uuid NOT NULL, metric text NOT NULL);
CREATE TABLE label_sessions (owner_id uuid NOT NULL);
CREATE TABLE sessions (account_id uuid NOT NULL);
"""


class ObjectStore:
    """One stored object: 206 for a Range request while it exists, 404 once purged."""

    def __init__(self) -> None:
        self.present = True
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_: Any) -> None:
                return

            def do_GET(self) -> None:
                if not outer.present:
                    self.send_error(404)
                    return
                self.send_response(206)
                self.send_header("Content-Range", "bytes 0-1/2")
                self.send_header("Content-Length", "2")
                self.end_headers()
                self.wfile.write(b"\x00\x00")

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}/media/rally-1.mp4"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def world() -> dict[str, Any]:
    return {}


@pytest.fixture
def store():
    s = ObjectStore()
    yield s
    s.close()


@pytest.fixture
def mailpit():
    fake = FakeMailpit()
    yield fake
    fake.close()


def _psql_cmd(url: str) -> str:
    return f"psql {shlex.quote(url)} -v ON_ERROR_STOP=1 -At -F|"


def _sql(url: str, sql: str) -> None:
    live._psql(_psql_cmd(url), sql)


def _insert(table: str, *values: str) -> str:
    """Test data only: fixed table names and uuid4 / literal values written by this module."""
    listed = ", ".join(f"'{v}'" for v in values)
    return f"INSERT INTO {table} VALUES ({listed});"  # noqa: S608


def _delete(table: str, column: str, value: str) -> str:
    """Test data only: fixed table and column names and uuid4 values written by this module."""
    return f"DELETE FROM {table} WHERE {column} = '{value}';"  # noqa: S608


# ------------------------------------------------------------------ purge check
@given(
    "a database holding a deleted match, a deleted account and a kept match",
    target_fixture="db",
)
def db(tmp_path: Path, world: dict[str, Any]):
    with fresh_cluster(tmp_path / "pg") as url:
        gone_acc, kept_acc = str(uuid.uuid4()), str(uuid.uuid4())
        gone, kept = str(uuid.uuid4()), str(uuid.uuid4())
        rows = []
        for acc, match in ((gone_acc, gone), (kept_acc, kept)):
            rows += [
                _insert("accounts", acc),
                _insert("matches", match, acc),
                _insert("match_rallies", match, "1"),
                _insert("match_rallies", match, "2"),
                _insert("metric_snapshots", match, "AN-01"),
                _insert("label_sessions", acc),
                _insert("sessions", acc),
            ]
        _sql(url, SCHEMA + "\n".join(rows))
        world.update(gone=gone, gone_acc=gone_acc, kept=kept)
        world["out"] = {"deleted_ids": [gone, gone_acc], "media": []}
        world["psql"] = _psql_cmd(url)
        yield url


@given("a rally video link of the deleted match taken before deletion")
def video_link(world: dict[str, Any], store: ObjectStore) -> None:
    world["out"]["media"].append({"url": store.url, "valid_until": time.time() + 600})


def _purge_sql(world: dict[str, Any], *, keep_snapshot: bool) -> str:
    m, a = world["gone"], world["gone_acc"]
    sql = [
        _delete("match_rallies", "match_id", m),
        _delete("label_sessions", "owner_id", a),
        _delete("sessions", "account_id", a),
        _delete("matches", "id", m),
        _delete("accounts", "id", a),
    ]
    if not keep_snapshot:
        sql.append(_delete("metric_snapshots", "match_id", m))
    return " ".join(sql)


@given('a purge job that leaves 1 "metric_snapshots" row of the deleted match and the video')
def leaky_purge(db: str, world: dict[str, Any]) -> None:
    sql = _purge_sql(world, keep_snapshot=True)
    world["purge_cmd"] = f"{_psql_cmd(db)} -c {shlex.quote(sql)}"


@given("a purge job that removes every row and object of the deleted match and account")
def full_purge(db: str, world: dict[str, Any], store: ObjectStore) -> None:
    sql = _purge_sql(world, keep_snapshot=False)
    world["purge_cmd"] = f"{_psql_cmd(db)} -c {shlex.quote(sql)}"
    world["store"] = store


@given("a purge job that removes the deleted match and its video but keeps the deleted account")
def purge_keeps_account(db: str, world: dict[str, Any], store: ObjectStore) -> None:
    m = world["gone"]
    sql = " ".join(
        _delete(table, column, m)
        for table, column in (
            ("match_rallies", "match_id"),
            ("metric_snapshots", "match_id"),
            ("matches", "id"),
        )
    )
    world["purge_cmd"] = f"{_psql_cmd(db)} -c {shlex.quote(sql)}"
    world["store"] = store


@given("a psql command that cannot reach the database")
def broken_psql(world: dict[str, Any]) -> None:
    world["psql"] = "psql postgresql://nobody@127.0.0.1:1/none -At -F|"


@when("the purge check runs")
def purge_runs(world: dict[str, Any]) -> None:
    args = Namespace(psql=world["psql"], purge_cmd=world["purge_cmd"])
    if "store" in world:  # the full purge also deletes the stored object (object-store side)
        world["store"].present = False
    world["result"] = live.purge_check(args, None, world["out"])


@then("the purge check fails")
def purge_fails(world: dict[str, Any]) -> None:
    assert world["result"]["ok"] is False, world["result"]


@then("the purge check passes")
def purge_passes(world: dict[str, Any]) -> None:
    assert world["result"]["ok"] is True, world["result"]
    assert world["result"]["problems"] == []


@then(parsers.parse('it names "{text}"'))
def names(world: dict[str, Any], text: str) -> None:
    assert any(p.startswith(text) for p in world["result"]["problems"]), world["result"]


@then('every inventoried column counts 0 rows, "matches.id" and "accounts.id" among them')
def zero_rows(world: dict[str, Any]) -> None:
    rows = world["result"]["rows"]
    expected = {
        "matches.id",
        "accounts.id",
        "matches.owner_id",
        "match_rallies.match_id",
        "metric_snapshots.match_id",
        "label_sessions.owner_id",
        "sessions.account_id",
    }
    assert expected <= set(rows), rows
    assert all(n == 0 for n in rows.values()), rows


@then("the video link answered 404")
def video_404(world: dict[str, Any]) -> None:
    assert world["result"]["media"] == [404]


# ------------------------------------------------------------------ deleted ids (PE-1)
def _sign_in_again(world: dict[str, Any], again_id: str) -> None:
    """G03-01 step 8 as the harness judges it: DELETE /me accepted, old session 401, empty list."""
    world["step"] = live.judge_account_deletion(
        deleted_id=world["gone_acc"],
        status=204,
        old_session=401,
        back=True,
        items=[],
        again_me={"id": again_id},
    )


@when("signing in again with the same address resolves to the deleted account's id")
def again_same_id(world: dict[str, Any]) -> None:
    _sign_in_again(world, world["gone_acc"])


@when("signing in again with the same address resolves to a new account id")
def again_new_id(world: dict[str, Any]) -> None:
    _sign_in_again(world, str(uuid.uuid4()))


@then(parsers.parse('the account deletion step fails, naming "{text}"'))
def deletion_step_fails(world: dict[str, Any], text: str) -> None:
    assert world["step"]["ok"] is False, world["step"]
    assert any(p.startswith(text) for p in world["step"]["problems"]), world["step"]


@then("the account deletion step passes")
def deletion_step_passes(world: dict[str, Any]) -> None:
    assert world["step"]["ok"] is True, world["step"]
    assert world["step"]["problems"] == []


@then("the purge check inventoried exactly the deleted match and the deleted account")
def inventoried_exactly(world: dict[str, Any]) -> None:
    assert world["result"]["ids"] == [world["gone"], world["gone_acc"]], world["result"]
    assert world["step"]["again_id"] not in world["result"]["ids"]


@given("a fresh run of the goal journey")
def fresh_run(world: dict[str, Any]) -> None:
    world["out"] = {"deleted_ids": [], "media": []}
    world["match"] = str(uuid.uuid4())


@when("GET /me answers without an account id")
def me_without_id(world: dict[str, Any]) -> None:
    world["setup_problems"] = live.record_run_ids(world["out"], world["match"], {"email": "x"})


@then(parsers.parse('the run\'s setup fails, naming "{text}"'))
def setup_fails(world: dict[str, Any], text: str) -> None:
    assert any(p.startswith(text) for p in world["setup_problems"]), world["setup_problems"]


@then("no id is recorded for the purge check")
def nothing_recorded(world: dict[str, Any]) -> None:
    assert world["out"]["deleted_ids"] == []


# ------------------------------------------------------------------ sign-in link (BE-GR1-01)
ADDRESS = "harness-03@example.com"


def _token() -> str:
    """A fresh 43-character link token: the helper remembers every token it returned."""
    return (uuid.uuid4().hex + uuid.uuid4().hex)[:43]


@given("a mailbox whose only sign-in link the harness already used")
def spent_link(mailpit: FakeMailpit, world: dict[str, Any]) -> None:
    world["spent"], world["fresh"] = _token(), _token()
    mailpit.deliver(world["spent"])
    assert lh.mailpit_token(mailpit.url, ADDRESS, timeout_s=2) == world["spent"]


@when("the harness asks for a sign-in link and no new mail arrives")
def ask_no_mail(mailpit: FakeMailpit, world: dict[str, Any]) -> None:
    world["token"] = lh.mailpit_token(mailpit.url, ADDRESS, timeout_s=0.6)


@when("a new sign-in mail arrives while the harness waits")
def ask_new_mail(mailpit: FakeMailpit, world: dict[str, Any]) -> None:
    timer = threading.Timer(0.8, mailpit.deliver, args=(world["fresh"],))
    timer.start()
    try:
        world["token"] = lh.mailpit_token(mailpit.url, ADDRESS, timeout_s=5)
    finally:
        timer.cancel()


@then("it gets no link")
def no_link(world: dict[str, Any]) -> None:
    assert world["token"] is None


@then("it gets the new link, not the spent one")
def new_link(world: dict[str, Any]) -> None:
    assert world["token"] == world["fresh"]
