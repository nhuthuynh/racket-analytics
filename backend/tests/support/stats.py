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

from collections.abc import Iterable, Sequence
from typing import Any

import httpx
import sqlalchemy as sa

from tests.support import scorebook as sb
from tests.support.api import ApiDriver
from tests.support.contract import Seam

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
