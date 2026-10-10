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
5. deleted accounts with no match row left are purged.

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
from racket.matches import public as matches
from racket.platform.logs import configure_logging, user_id_var
from racket.players import public as players
from racket.video_ingest import public as video_ingest

log = logging.getLogger("racket.purge")
ORPHAN_PAGE = 500


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

    def expire_uploads(self, session: Any, store: Any, now: datetime) -> int:
        return 0

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
        rows += analysis_jobs.purge_match(session, match_id)
        rows += video_ingest.purge_match(session, match_id)
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
        players.purge_account(session, account_id)


@dataclass
class PassResult:
    matches: int = 0
    accounts: int = 0
    uploads: int = 0
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
    ) -> None:
        self.session_factory = session_factory
        self.store = store
        self.ports = ports or ContextPorts()
        self.clock = clock
        self.batch = batch
        self.alert_after = alert_after

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
        self._step("upload", lambda s: self._expire(s, now, result), result)
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
        log.info(
            "purge pass",
            extra={"event": "purge.pass", "matches": result.matches, "accounts": result.accounts,
                   "uploads": result.uploads, "failed": result.failed,
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

    def _expire(self, session: Any, now: datetime, result: PassResult) -> None:
        result.uploads += self.ports.expire_uploads(session, self.store, now)

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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m racket.platform.purge", exit_on_error=False)
    parser.add_argument("--once", action="store_true", required=True)
    try:
        parser.parse_args(sys.argv[1:] if argv is None else argv)
    except (argparse.ArgumentError, SystemExit):
        return 2
    try:
        from racket.platform.db import engine_for, session_factory
        from racket.platform.settings import Settings
        from racket.platform.storage import ObjectStore

        settings = Settings.from_env()
        configure_logging(settings.log_level)
        job = PurgeJob(
            session_factory(engine_for(settings.database_url)),
            ObjectStore.from_settings(settings),
            batch=_env_int("PURGE_BATCH", 100, 1),
            alert_after=timedelta(seconds=_env_int("PURGE_ALERT_AFTER_S", 518_400, 1)),
        )
    except Exception as exc:  # noqa: BLE001 - configuration problems are exit 2
        log.error(
            "purge not configured", extra={"event": "purge.config", "error": type(exc).__name__}
        )
        return 2
    return job.run_once().exit_code


if __name__ == "__main__":
    raise SystemExit(main())
