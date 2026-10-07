"""Sprint 3 flows for integration tests and scenario steps (QA lane, QA-ACC-3).

Routes and field names come from ``scripts/measure/statscontract.py``, the one place the Sprint 3
contract assumptions live until ``docs/architecture/api-sprint-03.md`` exists (PE-1;
decision-log 2026-10-06). The expected stats come from the harness's independent reference
``scripts/measure/statslib.py`` (pinned to the coach's worked example), which imports neither the
product's analytics nor the oracle. A contract change is one edit in ``statscontract.py``.

The purge job and the object store are reached through ``tests.support.contract`` seams, so a
test whose story has not landed fails with "RED until ST-0xx" instead of breaking collection.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from typing import Any

import httpx
import sqlalchemy as sa

from tests.support import scorebook as sb
from tests.support.api import ApiDriver
from tests.support.contract import Seam
from tests.support.paths import REPO

statscontract = sb._load("statscontract")
statslib = sb._load("statslib")

WORKED_EXAMPLE: list[dict[str, Any]] = [dict(t) for t in statslib.STATS_TAGS]
CORRECTED_RALLY: int = statslib.CORRECTED_RALLY
METRICS: tuple[str, ...] = statslib.METRICS
SIDES = ("A", "B")
UNOFFICIAL = sb.taglib.UNOFFICIAL_LABEL
PROPORTIONS = ("AN-01", "AN-02", "AN-05")

# The purge/expiry job (ST-050, ST-038), run once in-process. The CLI name is
# ``statscontract.PURGE_ONCE`` (``python -m racket.platform.purge --once``); PE-3 names it.
PURGE_MAIN = Seam(
    "racket.platform.purge:main",
    "ST-050",
    "main(argv: list[str]) -> int; main(['--once']) runs one purge/expiry pass and returns 0",
)
OBJECT_STORE = Seam("racket.platform.storage:ObjectStore", "ST-008")


# ------------------------------------------------------------------ reference
def reference(tags: Sequence[dict[str, Any]], first_side: str = "A") -> dict[str, Any]:
    """AN-01..AN-07 per side of one game, from the independent reference."""
    games = [{"first_serving_side": first_side, "tags": [dict(t) for t in tags]}]
    stats: dict[str, Any] = statslib.starter_stats(games)
    return stats


# The browser specs' copy of the worked example and its stats (E2E-03-01..06, timing spec).
E2E_REFERENCE = REPO / "web" / "e2e" / "sprint-03" / "worked-example.reference.json"
_TAG_FIELDS = ("winning_side", "ending", "fault_kind", "responsible_player")


def _rounded(x: Any) -> Any:
    if isinstance(x, float):
        return round(x, 4)
    if isinstance(x, dict):
        return {k: _rounded(v) for k, v in x.items()}
    if isinstance(x, list | tuple):
        return [_rounded(v) for v in x]
    return x


def e2e_reference_text() -> str:
    """The exact text of ``E2E_REFERENCE``: worked-example tags and statslib stats (4 places)."""
    source = (
        "generated from scripts/measure/statslib.py (STATS_TAGS, starter_stats) by "
        "backend/tests/support/stats.py write_e2e_reference; never edit by hand "
        "(guard: backend/tests/regression/test_e2e_reference.py)"
    )
    tags = [{k: t[k] for k in _TAG_FIELDS} for t in WORKED_EXAMPLE]
    metrics = _rounded(json.loads(json.dumps(reference(WORKED_EXAMPLE))))

    def one(x: Any) -> str:
        return json.dumps(x, separators=(", ", ": "))

    # One rally per line and one metric-side per line, so a reviewer can read it like the
    # golden scripts (ST-049) and a diff names the metric and side that moved.
    lines = ["{", f' "_source": {one(source)},', ' "tags": [']
    lines += [f"  {one(t)}{',' if i < len(tags) - 1 else ''}" for i, t in enumerate(tags)]
    lines += [" ],", ' "metrics": {']
    for i, (metric, sides) in enumerate(metrics.items()):
        lines.append(f"  {one(metric)}: {{")
        lines += [
            f"   {one(side)}: {one(v)}{',' if j < len(sides) - 1 else ''}"
            for j, (side, v) in enumerate(sides.items())
        ]
        lines.append("  }" + ("," if i < len(metrics) - 1 else ""))
    lines += [" }", "}"]
    return "\n".join(lines) + "\n"


def write_e2e_reference() -> None:
    E2E_REFERENCE.write_text(e2e_reference_text(), encoding="utf-8")


def corrected_example() -> list[dict[str, Any]]:
    tags = [dict(t) for t in WORKED_EXAMPLE]
    tags[CORRECTED_RALLY - 1].update(winning_side="A", responsible_player=None)
    return tags


def stats_diffs(expected: dict[str, Any], body: dict[str, Any]) -> list[str]:
    diffs: list[str] = statslib.compare_stats(expected, body)
    return diffs


# ------------------------------------------------------------------ requests
def request(
    api: ApiDriver, user: str, name: str, *, json_body: Any = None, **ids: str
) -> httpx.Response:
    method, url = statscontract.path(name, **ids)
    if json_body is None:
        return api.request(user, method, url)
    return api.request(user, method, url, json=json_body)


def stats(api: ApiDriver, user: str, match_id: str) -> httpx.Response:
    return request(api, user, "stats", match_id=match_id)


def stats_body(api: ApiDriver, user: str, match_id: str) -> dict[str, Any]:
    response = stats(api, user, match_id)
    assert response.status_code == 200, f"stats: {response.status_code} {response.text[:300]}"
    body: dict[str, Any] = response.json()
    return body


def evidence(
    api: ApiDriver, user: str, match_id: str, metric: str, side: str, *, limit: int | None = None
) -> httpx.Response:
    method, url = statscontract.path("evidence", match_id=match_id, metric_id=metric, side=side)
    if limit is not None:
        url = url.replace("limit=10", f"limit={limit}")
    return api.request(user, method, url)


def delete_match(api: ApiDriver, user: str, match_id: str, body: Any = None) -> httpx.Response:
    return request(
        api,
        user,
        "delete_match",
        json_body=statscontract.CONFIRM_BODY if body is None else body,
        match_id=match_id,
    )


def delete_account(api: ApiDriver, user: str, body: Any = None) -> httpx.Response:
    return request(
        api, user, "delete_account", json_body=statscontract.CONFIRM_BODY if body is None else body
    )


def tagged_example(api: ApiDriver, user: str, title: str = "IT-03") -> str:
    """A doubles match with its video received and the worked example tagged."""
    return sb.ready_tagged_match(api, user, tags=WORKED_EXAMPLE, title=title)


def correct_rally_3(api: ApiDriver, user: str, match_id: str) -> httpx.Response:
    client = api.as_user(user)
    rows = sb.sheet_body(api, user, match_id)["rows"]
    rally_id = rows[CORRECTED_RALLY - 1]["rally_id"]
    version = api.run(sb.version_of(client, match_id))
    return api.run(
        sb.command(
            client,
            "correct",
            version=version,
            body={"field": "winning_side", "value": "A"},
            match_id=match_id,
            rally_id=rally_id,
        )
    )


def run_purge_once() -> None:
    rc = PURGE_MAIN.load()(["--once"])
    assert rc == 0, f"purge --once exit {rc}"


# ------------------------------------------------------------------ inventory (NFR-066 b)
def id_columns(engine: Any) -> list[tuple[str, str]]:
    """Every table column of this schema that can hold a match or account id, plus the roots."""
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text(
                "SELECT table_name, column_name FROM information_schema.columns "
                "WHERE table_schema = current_schema() AND column_name = ANY(:cols) "
                "ORDER BY 1, 2"
            ),
            {"cols": list(statslib.ID_COLUMNS)},
        ).all()
    pairs = [(str(t), str(c)) for t, c in rows]
    return pairs + [p for p in statslib.ROOT_TABLES if p not in pairs]


def rows_holding(engine: Any, ids: Iterable[str]) -> dict[str, int]:
    """``table.column -> rows`` holding any of ``ids`` (as text), over every id column."""
    wanted = [str(i) for i in ids]
    out: dict[str, int] = {}
    with engine.connect() as conn:
        for table, column in id_columns(engine):
            n = conn.execute(
                sa.text(f'SELECT count(*) FROM "{table}" WHERE "{column}"::text = ANY(:ids)'),
                {"ids": wanted},
            ).scalar_one()
            out[f"{table}.{column}"] = int(n)
    return out


def object_keys_of(engine: Any, match_id: str) -> list[str]:
    """Object keys the database knows for a match (originals and upload staging)."""
    keys: list[str] = []
    with engine.connect() as conn:
        for sql in (
            "SELECT object_key FROM media_assets WHERE match_id::text = :m",
            "SELECT object_key FROM upload_sessions WHERE match_id::text = :m",
        ):
            keys += [str(k) for k in conn.execute(sa.text(sql), {"m": match_id}).scalars()]
    return sorted(set(keys))


def keys_still_stored(keys: Iterable[str]) -> list[str]:
    store = OBJECT_STORE.load().from_settings()
    left = []
    for key in keys:
        if store.size_of(key) is not None or any(store.list_keys(prefix=key)):
            left.append(key)
    return left


def me_id(api: ApiDriver, user: str) -> str:
    response = request(api, user, "me")
    assert response.status_code == 200, f"me: {response.status_code} {response.text[:200]}"
    return str(response.json()["id"])


# ------------------------------------------------------------------ dictionary statuses (FR-102)
DICTIONARY = Seam(
    "racket.sports.pickleball.metrics:load_dictionary",
    "ST-043",
    "load_dictionary() (cached) reads METRICS_PATH",
)


def with_statuses(monkeypatch: Any, tmp_path: Any, *, draft: Iterable[str] = ()) -> dict[str, Any]:
    """Point the product's dictionary at a copy where every entry is ``coach-reviewed`` except
    ``draft`` ones. The computation ITs then do not depend on COACH-1's data change; IT-03-03
    and the live scorecard check the shipped statuses. Returns the copy's data."""
    import json

    from racket.sports.pickleball import metrics

    DICTIONARY.load()
    monkeypatch.setattr(metrics, "METRICS_PATH", metrics.METRICS_PATH)  # restored at teardown
    data = json.loads(metrics.METRICS_PATH.read_text(encoding="utf-8"))
    drafts = set(draft)
    for entry in data["entries"]:
        entry["status"] = "draft" if entry["id"] in drafts else "coach-reviewed"
    path = tmp_path / "metrics.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(metrics, "METRICS_PATH", path)
    metrics.load_dictionary.cache_clear()
    return dict(data)


def clear_dictionary_cache() -> None:
    from racket.sports.pickleball import metrics

    metrics.load_dictionary.cache_clear()


# ------------------------------------------------------------------ Full Tag (ST-052, FR-150)
# QA proposals until api-sprint-03 (PE-1) names the label routes and the labeller-admin CLI;
# PE-1 then moves the routes into statscontract.py and these names follow (one edit here).
FULLTAG_ROUTES = {
    "label_match": ("GET", "/label/matches/{match_id}"),
    "label_events": ("POST", "/label/matches/{match_id}/events"),
    "label_export": ("GET", "/label/matches/{match_id}/export"),
}
LABELLER_ADMIN = Seam(
    "racket.dataset.admin:main",
    "ST-052",
    "main(argv) -> int: ['grant-labeller', '--account', <id>] sets the labeller role; "
    "['consent', '--match', <id>, '--record', <ref>] writes the team-held consent record",
)
LABEL_SCHEMA = Seam("racket.dataset.labels:validate_labels", "ST-040")


def fulltag(
    api: ApiDriver, user: str, name: str, *, json_body: Any = None, **ids: str
) -> httpx.Response:
    method, template = FULLTAG_ROUTES[name]
    url = template.format(**ids)
    if json_body is None:
        return api.request(user, method, url)
    return api.request(user, method, url, json=json_body)


def grant_labeller(api: ApiDriver, user: str) -> None:
    rc = LABELLER_ADMIN.load()(["grant-labeller", "--account", me_id(api, user)])
    assert rc == 0, f"grant-labeller exit {rc}"


def record_consent(match_id: str, ref: str = "CONSENT-TEAM-SYNTHETIC-001") -> None:
    rc = LABELLER_ADMIN.load()(["consent", "--match", match_id, "--record", ref])
    assert rc == 0, f"consent exit {rc}"


# ------------------------------------------------------------------ scenario scripts (QA-ACC-3)
def _win(side: str) -> dict[str, Any]:
    return {
        "winning_side": side,
        "ending": "winner",
        "fault_kind": None,
        "responsible_player": None,
    }


def receive_script(n: int, won: int, receiver: str = "A") -> list[dict[str, Any]]:
    """Games (``[{"first_serving_side", "tags"}]``) where ``receiver`` receives serve in exactly
    ``n`` counted rallies and wins ``won`` of them (FR-101 examples). The receiver never scores:
    on its own serve it loses at once (a side-out under side-out scoring), so the server keeps
    the points and a new game starts only when the server's side reaches 11."""
    from tests.support.scorebook import taglib

    if not 0 <= won <= n:
        raise ValueError("won must be between 0 and n")
    server = "B" if receiver == "A" else "A"
    games: list[dict[str, Any]] = []
    tags: list[dict[str, Any]] = []
    state = taglib.new_doubles_game(server)
    wins_left, losses_left = won, n - won
    while wins_left or losses_left:
        if state.serving_side == receiver:
            pick = server  # the receiver loses its own serve: side-out, nobody scores
        elif wins_left and (not losses_left or wins_left * (n - won) >= losses_left * won):
            pick, wins_left = receiver, wins_left - 1
        else:
            pick, losses_left = server, losses_left - 1
        tags.append(_win(pick))
        state = taglib.step_doubles(state, pick, target=11)
        if state.winner is not None:
            games.append({"first_serving_side": server, "tags": tags})
            if len(games) == 2:
                raise ValueError("needs more than two games; the match would be over")
            tags, state = [], taglib.new_doubles_game(server)
    if tags:
        games.append({"first_serving_side": server, "tags": tags})
    return games


def no_score_script(rallies: int) -> list[dict[str, Any]]:
    """One game in which the serving side always loses: nobody scores, the game never ends,
    and each side wins every rally it receives (rallies/2 each)."""
    from tests.support.scorebook import taglib

    state = taglib.new_doubles_game("A")
    tags: list[dict[str, Any]] = []
    for _ in range(rallies):
        pick = "B" if state.serving_side == "A" else "A"
        tags.append(_win(pick))
        state = taglib.step_doubles(state, pick, target=11)
    return [{"first_serving_side": "A", "tags": tags}]


def lost_split_script(on_serve: int, on_receive: int, side: str = "A") -> list[dict[str, Any]]:
    """One game where ``side`` loses ``on_serve`` rallies on its serve and ``on_receive`` on the
    other side's serve, and wins every other rally it receives (to get the serve back)."""
    from tests.support.scorebook import taglib

    other = "B" if side == "A" else "A"
    state = taglib.new_doubles_game(side)
    tags: list[dict[str, Any]] = []
    serve_left, receive_left = on_serve, on_receive
    while serve_left or receive_left:
        if state.serving_side == side:
            if serve_left:
                pick, serve_left = other, serve_left - 1
            else:
                pick = side  # (only when every serve loss is used) a point for the side
        elif receive_left:
            pick, receive_left = other, receive_left - 1
        else:
            pick = side
        ending = "unforced_error" if pick == other and len(tags) % 2 else "winner"
        tags.append({**_win(pick), "ending": ending})
        state = taglib.step_doubles(state, pick, target=11)
        assert state.winner is None, "the script ended the game; change the numbers"
    return [{"first_serving_side": side, "tags": tags}]


def timed(games: list[dict[str, Any]], duration_ms: int = 59_000) -> list[dict[str, Any]]:
    """Give every rally of every game its own slot on the 60 s fixture video, in play order."""
    from tests.support.scorebook import taglib

    flat = [t for g in games for t in g["tags"]]
    spread = taglib.with_times(flat, duration_ms=duration_ms)
    out, i = [], 0
    for g in games:
        out.append({**g, "tags": spread[i : i + len(g["tags"])]})
        i += len(g["tags"])
    return out


def tag_games(api: ApiDriver, user: str, games: list[dict[str, Any]], title: str) -> str:
    """A received doubles match with ``games`` started and tagged in order."""
    client = api.as_user(user)
    match_id = api.run(sb.create_doubles(client, title))
    api.run(sb.receive_video(client, match_id))
    for game in timed(games):
        api.run(sb.start_game(client, match_id, game["first_serving_side"]))
        api.run(sb.tag_all(client, match_id, game["tags"]))
    return match_id
