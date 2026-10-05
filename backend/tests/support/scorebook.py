"""Sprint 2 scorebook flows for integration tests and scenario steps (QA lane).

Routes and field names come from ``scripts/measure/tagcontract.py`` (the one place the Sprint 2
contract assumptions live until ``api-sprint-02.md`` exists, decision-log 2026-10-05), so a
contract change is one edit there. The reference rows come from the harness's independent
stepper ``scripts/measure/taglib.py``, which imports neither the product engine nor the oracle.
"""

from __future__ import annotations

import importlib.util
import sys
from types import ModuleType
from typing import Any

import httpx
import sqlalchemy as sa

from tests.support import tus
from tests.support.api import ApiDriver
from tests.support.paths import REPO, SYNTHETIC_CLIP


def _load(name: str) -> ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    path = REPO / "scripts" / "measure" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None, path
    assert spec.loader is not None, path
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


tagcontract = _load("tagcontract")
taglib = _load("taglib")

DOUBLES_PEOPLE = (("A1", "Ivy"), ("A2", "Dana"), ("B1", "Carlos"), ("B2", "Sam"))

# Every table a request could write to; "no row written" compares these counts.
TABLES = (
    "accounts",
    "sessions",
    "sign_in_links",
    "sign_in_requests",
    "rate_limit_events",
    "jobs",
    "matches",
    "match_participants",
    "match_games",
    "match_rallies",
    "match_corrections",
    "media_assets",
    "upload_sessions",
)


def row_counts(engine: Any) -> dict[str, int]:
    """Row count of every table of ``TABLES`` that exists in this schema."""
    with engine.connect() as conn:
        present = [
            t for t in TABLES if conn.execute(sa.text("SELECT to_regclass(:t)"), {"t": t}).scalar()
        ]
        return {
            t: int(conn.execute(sa.text(f"SELECT count(*) FROM {t}")).scalar_one()) for t in present
        }


def path(name: str, **ids: str) -> tuple[str, str]:
    method, url = tagcontract.path(name, **ids)
    return str(method), str(url)


def doubles_body(title: str = "Saturday doubles") -> dict[str, Any]:
    return {
        "title": title,
        "format": "doubles",
        "participants": [
            {"slot": slot, "nickname": name, "is_me": slot == "A1"} for slot, name in DOUBLES_PEOPLE
        ],
    }


async def create_doubles(client: httpx.AsyncClient, title: str = "Saturday doubles") -> str:
    response = await client.post("/matches", json=doubles_body(title))
    assert response.status_code == 201, f"create match: {response.status_code} {response.text}"
    return str(response.json()["id"])


async def receive_video(client: httpx.AsyncClient, match_id: str) -> None:
    data = SYNTHETIC_CLIP.read_bytes()
    upload = await tus.start(client, match_id, len(data))
    await tus.send_all(client, upload, data, chunks=2)
    status = (await client.get(f"/matches/{match_id}")).json()["status"]
    assert status == "video_received", status


async def version_of(client: httpx.AsyncClient, match_id: str) -> int:
    method, url = path("sheet", match_id=match_id)
    response = await client.request(method, url)
    assert response.status_code == 200, response.text
    return int(response.headers["ETag"].strip('"'))


async def command(
    client: httpx.AsyncClient,
    name: str,
    *,
    version: int | None,
    body: Any = None,
    raw: bytes | None = None,
    **ids: str,
) -> httpx.Response:
    method, url = path(name, **ids)
    headers = {} if version is None else {tagcontract.VERSION_HEADER: f'"{version}"'}
    if raw is not None:
        headers["Content-Type"] = "application/json"
        return await client.request(method, url, content=raw, headers=headers)
    if body is None:
        return await client.request(method, url, headers=headers)
    return await client.request(method, url, json=body, headers=headers)


async def start_game(client: httpx.AsyncClient, match_id: str, side: str = "A") -> int:
    response = await command(
        client,
        "start_game",
        version=await version_of(client, match_id),
        body={"first_serving_side": side, "ends_switched": False},
        match_id=match_id,
    )
    assert response.status_code == 201, response.text
    return int(response.json()[tagcontract.VERSION_KEY])


async def tag_all(
    client: httpx.AsyncClient, match_id: str, tags: list[dict[str, Any]]
) -> list[httpx.Response]:
    """Tag each rally in turn with the version the previous answer carried."""
    version = await version_of(client, match_id)
    out = []
    for tag in tags:
        response = await command(client, "tag", version=version, body=tag, match_id=match_id)
        assert response.status_code == 201, f"tag {tag}: {response.status_code} {response.text}"
        version = int(response.json()[tagcontract.VERSION_KEY])
        out.append(response)
    return out


async def sheet(client: httpx.AsyncClient, match_id: str) -> httpx.Response:
    method, url = path("sheet", match_id=match_id)
    return await client.request(method, url)


def canonical(value: Any) -> bytes:
    """The bytes the byte-identical checks compare (sorted keys, no spaces, no floats)."""
    data: bytes = taglib.canonical_bytes(value)
    return data


def ready_tagged_match(
    api: ApiDriver, user: str, tags: list[dict[str, Any]] | None = None, title: str = "IT-02"
) -> str:
    """A doubles match with its video received, game 1 started by side A, ``tags`` tagged
    (the 6-rally journey by default)."""
    client = api.as_user(user)
    match_id = api.run(create_doubles(client, title))
    api.run(receive_video(client, match_id))
    api.run(start_game(client, match_id))
    api.run(tag_all(client, match_id, list(taglib.JOURNEY_TAGS if tags is None else tags)))
    return match_id


def reference_rows(tags: list[dict[str, Any]], first_side: str = "A") -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = taglib.expected_rows(tags, first_serving_side=first_side)
    return rows


def rows_of(body: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = taglib.normalise_sheet(body)
    return rows


def row_diffs(expected: list[dict[str, Any]], body: dict[str, Any]) -> list[str]:
    diffs: list[str] = taglib.compare_rows(expected, rows_of(body))
    return diffs
