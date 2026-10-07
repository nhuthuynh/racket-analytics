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

import logging
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from botocore.exceptions import ClientError

from racket.analysis_jobs import public as analysis_jobs
from racket.analytics import public as analytics
from racket.matches import public as matches
from racket.platform.logs import user_id_var
from racket.video_ingest import public as video_ingest

log = logging.getLogger("racket.purge")
ORPHAN_PAGE = 500


def _now() -> datetime:
    return datetime.now(UTC)


class ContextPorts:
    """Each step through the owning context's published port (context map rule 1)."""

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


@dataclass
class PassResult:
    matches: int = 0
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
    ) -> None:
        self.session_factory = session_factory
        self.store = store
        self.ports = ports or ContextPorts()
        self.clock = clock
        self.batch = batch

    def _failed(self, kind: str, item: uuid.UUID, stage: str, exc: BaseException) -> None:
        log.error(
            "purge item failed",
            extra={"event": "purge.failed", "kind": kind, f"{kind}_id": str(item),
                   "stage": stage, "error": type(exc).__name__},
        )  # fmt: skip

    def run_once(self) -> PassResult:
        started = time.perf_counter()
        result = PassResult()
        with self.session_factory() as session:
            due = list(self.ports.due_matches(session, self.batch))
            session.rollback()
        for item in due:
            self._purge_match(item.match_id, item.owner_id, result)
        log.info(
            "purge pass",
            extra={"event": "purge.pass", "matches": result.matches, "failed": result.failed,
                   "duration_ms": round((time.perf_counter() - started) * 1000)},
        )  # fmt: skip
        return result

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
