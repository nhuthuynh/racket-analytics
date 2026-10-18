"""The purge job: ``python -m racket.platform.purge --once`` (ST-050, ST-051, ST-038;
deletion-and-purge.md §4; ADR 0038, 0042, 0045).

A composition root: no domain rule lives here. One pass:

1. abandoned uploads expire (ST-038);
2. live matches of a deleted account are tombstoned (SEC-S3-TM-05 second net);
3. each tombstoned match, oldest first, is claimed (``SKIP LOCKED``), its typed object refs are
   built (fail closed, SEC-S3-TM-01), the objects are deleted, then every row in one
   transaction, the match root last (objects before rows: a failure leaves rows that still
   name every object left, so there is no orphan and the next pass finishes the job);
4. orphan snapshot rows are swept (SEC-S3-TM-02);
5. deleted accounts with no match row left are purged (their training-plan rows, then the
   account row; ST-061a);
6. with ``FEATURE_RETENTION_SETTING`` on, each review video past its owner's own deletion date
   is deleted, its object first, then its media row; tags, stats and plans stay (ST-069;
   FR-008; ADR 0006 user rule, ADR 0042). Flag off: this step does nothing.

Dev/test only (api-sprint-04 §5; SEC-4 T4-RT-3): ``--now RFC3339`` or ``--now-offset-days N``
moves the clock of step 6 only (the other steps keep the real clock), and is refused with exit 2
when ``APP_ENV`` is ``staging`` or ``prod``.

Exit 0: every due item done; 1: an item failed and stays due; 2: usage or configuration.
Log lines hold ids and the pseudonymous account id only (NFR-057).
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from botocore.exceptions import ClientError

from racket.analysis_jobs import public as analysis_jobs
from racket.analytics import public as analytics
from racket.coaching import public as coaching
from racket.dataset import public as dataset
from racket.matches import public as matches
from racket.platform.logs import configure_logging, user_id_var
from racket.players import public as players
from racket.video_ingest import public as video_ingest

log = logging.getLogger("racket.purge")
ORPHAN_PAGE = 500
UPLOAD_PAGE = 500
REVIEW_PAGE = 500
CLOCK_ENVS = ("dev", "test")  # where the dev clock option is honoured (T4-RT-3)


def _now() -> datetime:
    return datetime.now(UTC)


def _env_int(name: str, default: int, minimum: int, maximum: int | None = None) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    if not raw.isascii() or not raw.isdigit():
        raise ValueError(f"{name} must be a whole number")
    value = int(raw)
    if value < minimum or (maximum is not None and value > maximum):
        raise ValueError(f"{name} is out of range")
    return value


class ContextPorts:
    """Each step through the owning context's published port (context map rule 1)."""

    def __init__(self, upload_idle: timedelta = timedelta(hours=24)) -> None:
        self.upload_idle = upload_idle

    def abandoned_uploads(self, session: Any, now: datetime, limit: int) -> list[uuid.UUID]:
        """ST-038: up to ``limit`` abandoned uploads of live matches, unlocked. Pages through
        every candidate by id, so uploads of deleted matches (the match purge's, refs checked
        fail-closed, §4.6) never fill a batch (PE-038-01). The composition root does the set
        difference; neither context reads the other's table (context-map rule 1)."""
        found: list[uuid.UUID] = []
        after = None
        while len(found) < limit:
            page = video_ingest.abandoned_upload_ids(
                session, now, self.upload_idle, after=after, limit=UPLOAD_PAGE
            )
            if not page:
                break
            live = matches.live_ids(session, [match_id for _, match_id in page])
            found += [upload_id for upload_id, match_id in page if match_id in live]
            after = page[-1][0]
        return found[:limit]

    def claim_upload(
        self, session: Any, upload_id: uuid.UUID, now: datetime
    ) -> video_ingest.AbandonedUpload | None:
        """The upload row locked until commit, if still abandoned and its match still live."""
        upload = video_ingest.claim_abandoned_upload(session, upload_id, now, self.upload_idle)
        if upload is None or upload.match_id not in matches.live_ids(session, [upload.match_id]):
            return None
        return upload

    def forget_upload(self, session: Any, upload_id: uuid.UUID) -> None:
        video_ingest.forget_upload(session, upload_id)

    def tombstone_deleted_accounts(self, session: Any, now: datetime) -> list[uuid.UUID]:
        """SEC-S3-TM-05 second net: a live match of a deleted account becomes due now."""
        caught: list[uuid.UUID] = []
        for account_id in players.tombstoned_account_ids(session):
            for match_id in matches.tombstone_owned_by(session, account_id, now):
                caught.append(match_id)
                log.info(
                    "match deleted",
                    extra={"event": "match.deleted", "match_id": str(match_id),
                           "user_id": str(account_id)},
                )  # fmt: skip
        return caught

    def due_matches(self, session: Any, limit: int) -> list[matches.DueMatch]:
        return matches.due_for_purge(session, limit)

    def claim(self, session: Any, match_id: uuid.UUID) -> bool:
        return matches.claim_for_purge(session, match_id)

    def object_refs(self, session: Any, match_id: uuid.UUID) -> list[video_ingest.ObjectRef]:
        return video_ingest.object_refs(session, match_id)

    def purge_rows(self, session: Any, match_id: uuid.UUID) -> int:
        rows = analytics.purge_match(session, match_id)
        rows += dataset.purge_match(session, match_id)
        rows += analysis_jobs.purge_match(session, match_id)
        rows += video_ingest.purge_match(session, match_id)
        rows += coaching.purge_match(session, match_id)  # ST-061b: plan rows naming the match
        return rows + matches.purge_match(session, match_id)  # root last; FKs cascade

    def orphan_snapshot_ids(self, session: Any) -> list[uuid.UUID]:
        orphans: list[uuid.UUID] = []
        after = None
        while True:
            page = list(analytics.snapshot_match_ids(session, after, ORPHAN_PAGE))
            if not page:
                return orphans
            alive = matches.existing_ids(session, page)
            orphans += [m for m in page if m not in alive]
            after = page[-1]

    def purge_orphan_snapshot(self, session: Any, match_id: uuid.UUID) -> None:
        analytics.purge_match(session, match_id)

    def due_accounts(self, session: Any, limit: int) -> list[uuid.UUID]:
        """Deleted accounts with no match row left (their matches are purged first)."""
        ids = players.tombstoned_account_ids(session, limit)
        return [a for a in ids if not matches.owner_has_matches(session, a)]

    def claim_account(self, session: Any, account_id: uuid.UUID) -> bool:
        return players.claim_for_purge(session, account_id) and not matches.owner_has_matches(
            session, account_id
        )

    def purge_account(self, session: Any, account_id: uuid.UUID) -> None:
        coaching.purge_account(session, account_id)  # ST-061a: plan rows before the account row
        players.purge_account(session, account_id)

    def _due(
        self,
        session: Any,
        videos: list[video_ingest.ReviewVideo],
        now: datetime,
        default_days: int | None,
    ) -> list[video_ingest.ReviewVideo]:
        """Each video against its own owner's choice (T4-RT-1), live matches only: a deleted
        match goes through the match purge."""  # fmt: skip
        days = players.review_video_days(session, sorted({v.owner_id for v in videos}),
                                         default_days)  # fmt: skip
        live = matches.live_ids(session, [v.match_id for v in videos])
        return [
            v for v in videos
            if v.match_id in live
            and video_ingest.ReviewVideoSchedule(days[v.owner_id]).is_due(v.analysed_at, now)
        ]  # fmt: skip

    def due_review_videos(
        self, session: Any, now: datetime, default_days: int | None, limit: int
    ) -> list[video_ingest.ReviewVideo]:
        """ST-069: up to ``limit`` review videos past their deletion date, unlocked."""
        found: list[video_ingest.ReviewVideo] = []
        after = None
        while len(found) < limit:
            page = video_ingest.probed_review_videos(session, after=after, limit=REVIEW_PAGE)
            if not page:
                break
            found += self._due(session, page, now, default_days)
            after = page[-1].match_id
        return found[:limit]

    def claim_review_video(
        self, session: Any, match_id: uuid.UUID, now: datetime, default_days: int | None
    ) -> video_ingest.ReviewVideo | None:
        """The video locked until commit, if still due under its owner's current choice (a
        choice changed since the listing wins, T4-RT-4)."""
        video = video_ingest.claim_review_video(session, match_id)
        if video is None or not self._due(session, [video], now, default_days):
            return None
        return video

    def forget_review_video(self, session: Any, video: video_ingest.ReviewVideo) -> None:
        video_ingest.forget_review_video(session, video)


@dataclass(frozen=True)
class RetentionRule:
    """FEATURE_RETENTION_SETTING on (ST-069): the default days for an owner who chose none and
    the dev clock of this step (``at`` or ``offset``; T4-RT-3)."""

    default_days: int | None
    at: datetime | None = None
    offset: timedelta = timedelta(0)

    def now(self, real: datetime) -> datetime:
        return (self.at or real) + self.offset


@dataclass
class PassResult:
    matches: int = 0
    accounts: int = 0
    uploads: int = 0
    review_videos: int = 0
    failed: int = 0

    @property
    def exit_code(self) -> int:
        return 1 if self.failed else 0


def _delete(store: Any, ref: Any) -> None:
    """One typed ref; a missing object, folder or multipart upload is a success."""
    try:
        if isinstance(ref, video_ingest.MultipartRef):
            store.abort_multipart(ref.key, ref.upload_id)
        elif isinstance(ref, video_ingest.StagingPrefix):
            store.delete_prefix(ref.prefix)
        elif isinstance(ref, video_ingest.OriginalKey):
            store.delete(ref.key)
        else:  # never a raw string: only typed refs reach the store (§4.6)
            raise video_ingest.UnsafeObjectRef("not a typed ref")
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code not in ("404", "NoSuchKey", "NoSuchUpload", "NotFound"):
            raise


class PurgeJob:
    def __init__(
        self,
        session_factory: Callable[[], Any],
        store: Any,
        *,
        ports: Any = None,
        clock: Callable[[], datetime] = _now,
        batch: int = 100,
        alert_after: timedelta = timedelta(seconds=518_400),
        retention: RetentionRule | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.store = store
        self.ports = ports or ContextPorts()
        self.clock = clock
        self.batch = batch
        self.alert_after = alert_after
        self.retention = retention  # None: FEATURE_RETENTION_SETTING off, step 6 does nothing

    def _failed(self, kind: str, item: uuid.UUID, stage: str, exc: BaseException) -> None:
        log.error(
            "purge item failed",
            extra={"event": "purge.failed", "kind": kind, f"{kind}_id": str(item),
                   "stage": stage, "error": type(exc).__name__},
        )  # fmt: skip

    def run_once(self) -> PassResult:
        started = time.perf_counter()
        result = PassResult()
        now = self.clock()
        self._expire_uploads(now, result)
        self._step("account", lambda s: self.ports.tombstone_deleted_accounts(s, now), result)
        with self.session_factory() as session:
            due = list(self.ports.due_matches(session, self.batch))
            session.rollback()
        for item in due:
            age = now - item.deleted_at
            if age > self.alert_after:
                log.error(
                    "purge overdue",
                    extra={"event": "purge.overdue", "kind": "match",
                           "match_id": str(item.match_id), "age_s": int(age.total_seconds())},
                )  # fmt: skip
            self._purge_match(item.match_id, item.owner_id, result)
        self._step("snapshot", self._sweep_orphans, result)
        self._purge_accounts(result)
        if self.retention is not None:
            self._purge_review_videos(self.retention, now, result)
        log.info(
            "purge pass",
            extra={"event": "purge.pass", "matches": result.matches, "accounts": result.accounts,
                   "uploads": result.uploads, "review_videos": result.review_videos,
                   "failed": result.failed,
                   "duration_ms": round((time.perf_counter() - started) * 1000)},
        )  # fmt: skip
        return result

    def _step(self, kind: str, work: Callable[[Any], Any], result: PassResult) -> None:
        with self.session_factory() as session:
            try:
                work(session)
                session.commit()
            except Exception as exc:  # noqa: BLE001 - one failed step never stops the pass
                session.rollback()
                result.failed += 1
                log.error(
                    "purge step failed",
                    extra={"event": "purge.failed", "kind": kind, "stage": "rows",
                           "error": type(exc).__name__},
                )  # fmt: skip

    def _expire_uploads(self, now: datetime, result: PassResult) -> None:
        """ST-038, one upload at a time (ST038-QA-1): its own transaction and row lock, bytes
        first, then the row. A failure rolls back that upload only (its row and bytes stay, the
        next pass retries it), logs ``purge.failed`` with its id, and the next upload goes on
        (deletion-and-purge.md §4.3, §4.5)."""
        due: list[uuid.UUID] = []
        self._step("upload", lambda s: due.extend(self.ports.abandoned_uploads(s, now, self.batch)),
                   result)  # fmt: skip
        for upload_id in due:
            with self.session_factory() as session:
                stage = "objects"
                try:
                    upload = self.ports.claim_upload(session, upload_id, now)
                    if upload is None:  # a request or another pass holds it, or it moved on
                        session.rollback()
                        continue
                    for ref in upload.refs:
                        _delete(self.store, ref)
                    stage = "rows"
                    self.ports.forget_upload(session, upload_id)
                    session.commit()
                except Exception as exc:  # noqa: BLE001 - the upload stays due; next one
                    session.rollback()
                    result.failed += 1
                    self._failed("upload", upload_id, stage, exc)
                    continue
            result.uploads += 1
            log.info(
                "upload expired",
                extra={"event": "upload.expired", "upload_id": str(upload.upload_id),
                       "match_id": str(upload.match_id), "user_id": str(upload.owner_id)},
            )  # fmt: skip

    def _purge_match(self, match_id: uuid.UUID, owner_id: uuid.UUID, result: PassResult) -> None:
        token = user_id_var.set(str(owner_id))
        try:
            with self.session_factory() as session:
                if not self.ports.claim(session, match_id):
                    session.rollback()  # another pass has it, or it is already gone
                    return
                stage = "objects"
                try:
                    refs = self.ports.object_refs(session, match_id)  # all refs before any call
                    for ref in refs:
                        _delete(self.store, ref)
                    stage = "rows"
                    rows = self.ports.purge_rows(session, match_id)
                    session.commit()
                except Exception as exc:  # noqa: BLE001 - the match stays due; next one
                    session.rollback()
                    result.failed += 1
                    self._failed("match", match_id, stage, exc)
                    return
            result.matches += 1
            log.info(
                "match purged",
                extra={"event": "match.purged", "match_id": str(match_id),
                       "objects": len(refs), "rows": rows},
            )  # fmt: skip
        finally:
            user_id_var.reset(token)

    def _sweep_orphans(self, session: Any) -> None:
        for match_id in self.ports.orphan_snapshot_ids(session):
            self.ports.purge_orphan_snapshot(session, match_id)
            log.info(
                "orphan swept",
                extra={"event": "purge.orphan_swept", "kind": "snapshot",
                       "match_id": str(match_id)},
            )  # fmt: skip

    def _purge_accounts(self, result: PassResult) -> None:
        with self.session_factory() as session:
            due = list(self.ports.due_accounts(session, self.batch))
            session.rollback()
        for account_id in due:
            token = user_id_var.set(str(account_id))
            try:
                with self.session_factory() as session:
                    try:
                        if not self.ports.claim_account(session, account_id):
                            session.rollback()
                            continue
                        self.ports.purge_account(session, account_id)
                        session.commit()
                    except Exception as exc:  # noqa: BLE001 - the account stays due
                        session.rollback()
                        result.failed += 1
                        self._failed("account", account_id, "rows", exc)
                        continue
                result.accounts += 1
                log.info("account purged", extra={"event": "account.purged"})
            finally:
                user_id_var.reset(token)

    def _purge_review_videos(self, rule: RetentionRule, real: datetime, result: PassResult) -> None:
        """ST-069, one video at a time: its own transaction and asset row lock, object first,
        then the media row (ADR 0042). A failure rolls back that video only (the row still names
        the object, the next pass retries it) and the next video goes on."""
        now = rule.now(real)
        due: list[video_ingest.ReviewVideo] = []
        self._step("review_video",
                   lambda s: due.extend(self.ports.due_review_videos(s, now, rule.default_days,
                                                                     self.batch)),
                   result)  # fmt: skip
        for item in due:
            token = user_id_var.set(str(item.owner_id))
            try:
                with self.session_factory() as session:
                    stage = "objects"
                    try:
                        video = self.ports.claim_review_video(
                            session, item.match_id, now, rule.default_days
                        )
                        if video is None:  # another pass has it, it is gone, or no longer due
                            session.rollback()
                            continue
                        _delete(self.store, video.ref)
                        stage = "rows"
                        self.ports.forget_review_video(session, video)
                        session.commit()
                    except Exception as exc:  # noqa: BLE001 - the video stays due; next one
                        session.rollback()
                        result.failed += 1
                        self._failed("match", item.match_id, stage, exc)
                        continue
                result.review_videos += 1
                log.info(
                    "review video purged",
                    extra={"event": "review_video.purged", "match_id": str(item.match_id)},
                )
            finally:
                user_id_var.reset(token)


def _dev_clock(raw_now: str | None, offset_days: str | None) -> tuple[datetime | None, timedelta]:
    """``--now`` (RFC 3339 with a zone) and ``--now-offset-days`` (whole days); ValueError on a
    malformed value or both at once."""
    if raw_now is not None and offset_days is not None:
        raise ValueError("--now and --now-offset-days are exclusive")
    at = None
    if raw_now is not None:
        at = datetime.fromisoformat(raw_now.replace("Z", "+00:00"))
        if at.tzinfo is None:
            raise ValueError("--now needs a time zone")
    days = 0
    if offset_days is not None:
        if not offset_days.lstrip("-").isascii() or not offset_days.lstrip("-").isdigit():
            raise ValueError("--now-offset-days takes whole days")
        days = int(offset_days)
    return at, timedelta(days=days)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m racket.platform.purge", exit_on_error=False)
    parser.add_argument("--once", action="store_true", required=True)
    parser.add_argument("--now", default=None)  # dev/test only (T4-RT-3)
    parser.add_argument("--now-offset-days", default=None)  # dev/test only (T4-RT-3)
    try:
        args = parser.parse_args(sys.argv[1:] if argv is None else argv)
        at, offset = _dev_clock(args.now, args.now_offset_days)
    except (argparse.ArgumentError, SystemExit, ValueError):
        return 2
    if (args.now is not None or args.now_offset_days is not None) and os.environ.get(
        "APP_ENV", ""
    ) not in CLOCK_ENVS:
        log.error("purge dev clock refused", extra={"event": "purge.config", "error": "dev_clock"})
        return 2
    if at is not None or offset:
        log.warning("purge dev clock", extra={"event": "purge.dev_clock",
                                               "offset_days": offset.days})  # fmt: skip
    try:
        from racket.platform.db import engine_for, session_factory
        from racket.platform.settings import Settings
        from racket.platform.storage import ObjectStore

        settings = Settings.from_env()
        configure_logging(settings.log_level)
        job = PurgeJob(
            session_factory(engine_for(settings.database_url)),
            ObjectStore.from_settings(settings),
            ports=ContextPorts(upload_idle=timedelta(seconds=settings.upload_expiry_seconds)),
            batch=_env_int("PURGE_BATCH", 100, 1),
            alert_after=timedelta(seconds=_env_int("PURGE_ALERT_AFTER_S", 518_400, 1)),
            retention=RetentionRule(settings.retention_default_days, at, offset)
            if settings.feature_retention_setting
            else None,
        )
    except Exception as exc:  # noqa: BLE001 - configuration problems are exit 2
        log.error(
            "purge not configured", extra={"event": "purge.config", "error": type(exc).__name__}
        )
        return 2
    return job.run_once().exit_code


if __name__ == "__main__":
    raise SystemExit(main())
