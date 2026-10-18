"""The review video step of the purge pass and its dev clock (ST-069; FR-008; ADR 0042;
api-sprint-04 §5; SEC-4 T4-RT-2, T4-RT-3), with fakes.

Negative cases first: ``--now``/``--now-offset-days`` with ``APP_ENV`` staging or prod exit 2
before any job is built; with the flag off (no rule) the step asks for nothing; a store failure
keeps the media row (objects first, ADR 0042) and the next video still goes. Then: object, then
row, one transaction each; the dev clock moves only this step's "now"."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from racket.platform import purge
from racket.platform.purge import PurgeJob, RetentionRule, main
from racket.video_ingest.public import OriginalKey, ReviewVideo

pytestmark = [pytest.mark.unit]

NOW = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)
A, B = uuid.UUID(int=1), uuid.UUID(int=2)
OWNER = uuid.UUID(int=9)
HEX_A, HEX_B = "a" * 32, "b" * 32


class FakeSession:
    def __init__(self, log: list[str]) -> None:
        self.log = log

    def commit(self) -> None:
        self.log.append("commit")

    def rollback(self) -> None:
        self.log.append("rollback")

    def __enter__(self) -> FakeSession:
        return self

    def __exit__(self, *exc: Any) -> None:
        pass


def _video(match_id: uuid.UUID, hex_: str) -> ReviewVideo:
    return ReviewVideo(match_id, OWNER, uuid.uuid4(), NOW - timedelta(days=40),
                       OriginalKey(f"originals/{hex_}"))  # fmt: skip


class Ports:
    """Every other step is empty; the review video step is recorded."""

    def __init__(self, log: list[str], videos: list[ReviewVideo]) -> None:
        self.log, self.videos = log, videos
        self.asked_at: list[datetime] = []

    def abandoned_uploads(self, session: Any, now: datetime, limit: int) -> list[uuid.UUID]:
        return []

    def tombstone_deleted_accounts(self, session: Any, now: datetime) -> list[uuid.UUID]:
        return []

    def due_matches(self, session: Any, limit: int) -> list[Any]:
        return []

    def orphan_snapshot_ids(self, session: Any) -> list[uuid.UUID]:
        return []

    def due_accounts(self, session: Any, limit: int) -> list[uuid.UUID]:
        return []

    def due_review_videos(
        self, session: Any, now: datetime, default_days: int | None, limit: int
    ) -> list[ReviewVideo]:
        self.asked_at.append(now)
        self.log.append(f"due default={default_days}")
        return self.videos[:limit]

    def claim_review_video(
        self, session: Any, match_id: uuid.UUID, now: datetime, default_days: int | None
    ) -> ReviewVideo | None:
        return next((v for v in self.videos if v.match_id == match_id), None)

    def forget_review_video(self, session: Any, video: ReviewVideo) -> None:
        self.log.append(f"row {video.match_id.int}")


class Store:
    def __init__(self, log: list[str], fail_on: str | None = None) -> None:
        self.log, self.fail_on = log, fail_on

    def delete(self, key: str) -> None:
        if self.fail_on and self.fail_on in key:
            raise ConnectionError("store down")
        self.log.append(f"delete {key}")


def _job(ports: Ports, store: Store, log: list[str], rule: RetentionRule | None) -> PurgeJob:
    return PurgeJob(lambda: FakeSession(log), store, ports=ports, clock=lambda: NOW, retention=rule)


@pytest.mark.parametrize("app_env", ["staging", "prod"])
@pytest.mark.parametrize("option", [["--now-offset-days", "31"], ["--now", "2027-01-01T00:00:00Z"]])
def test_the_dev_clock_is_refused_outside_dev_and_test(
    monkeypatch: pytest.MonkeyPatch, app_env: str, option: list[str]
) -> None:
    def never(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("no job may be built")

    monkeypatch.setenv("APP_ENV", app_env)
    monkeypatch.setattr(purge, "PurgeJob", never)
    assert main(["--once", *option]) == 2


@pytest.mark.parametrize(
    "option",
    [["--now-offset-days", "x"], ["--now", "yesterday"], ["--now", "2027-01-01T00:00:00"],
     ["--now-offset-days", "1", "--now", "2027-01-01T00:00:00Z"]],
)  # fmt: skip
def test_a_malformed_or_doubled_dev_clock_is_a_usage_error(
    monkeypatch: pytest.MonkeyPatch, option: list[str]
) -> None:
    monkeypatch.setattr(purge, "PurgeJob", lambda *a, **k: (_ for _ in ()).throw(AssertionError))
    assert main(["--once", *option]) == 2


def test_with_the_flag_off_the_step_asks_for_nothing() -> None:
    log: list[str] = []
    ports = Ports(log, [_video(A, HEX_A)])
    result = _job(ports, Store(log), log, None).run_once()
    assert ports.asked_at == []
    assert not any(e.startswith(("delete", "row")) for e in log)
    assert (result.review_videos, result.failed) == (0, 0)


def test_a_store_failure_keeps_the_row_and_the_next_video_still_goes() -> None:
    log: list[str] = []
    ports = Ports(log, [_video(A, HEX_A), _video(B, HEX_B)])
    result = _job(ports, Store(log, fail_on=HEX_A), log, RetentionRule(90)).run_once()
    assert "row 1" not in log
    assert log.index("row 2") > log.index(f"delete originals/{HEX_B}")
    assert (result.review_videos, result.failed, result.exit_code) == (1, 1, 1)


def test_objects_then_rows_and_the_dev_clock_moves_only_this_step() -> None:
    log: list[str] = []
    ports = Ports(log, [_video(A, HEX_A)])
    rule = RetentionRule(90, offset=timedelta(days=31))
    result = _job(ports, Store(log), log, rule).run_once()
    i = log.index(f"delete originals/{HEX_A}")
    assert log[i + 1 : i + 3] == ["row 1", "commit"]
    assert "due default=90" in log
    assert ports.asked_at == [NOW + timedelta(days=31)]
    assert (result.review_videos, result.failed) == (1, 0)
