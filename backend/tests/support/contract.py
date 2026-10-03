"""The seams the QA-written tests use to reach production code (ST-004, ST-012).

Tests were written before the code (sprint-00 §3.1 ST-012), so they name the intended public
API here, in ONE place. Names come from sprint-00 §5/§6 where the plan names them; module
paths and HTTP routes not fixed by the plan are QA proposals (decision-log 2026-10-03) to be
confirmed with the implementing lane at story start. Changing a seam is a test change: it
goes through the senior-qa-engineer (working-agreement, test immutability).

Every lookup is lazy. A missing seam makes the *individual test* fail with a message naming
the story that will provide it ("RED until ST-xxx"), instead of breaking collection.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any

import pytest


@dataclass(frozen=True)
class Seam:
    target: str  # "module.path:attribute"
    story: str
    note: str = ""

    def load(self) -> Any:
        module_name, _, attr = self.target.partition(":")
        try:
            module = importlib.import_module(module_name)
            return getattr(module, attr) if attr else module
        except (ImportError, AttributeError) as exc:
            reason = f"{type(exc).__name__}: {exc}"
        pytest.fail(
            f"RED until {self.story}: seam {self.target!r} is not implemented yet "
            f"({reason}). {self.note}".rstrip(),
            pytrace=False,
        )


# ------------------------------------------------------------------ platform (ST-005)
APP_FACTORY = Seam(
    "racket.platform.app:create_app",
    "ST-005",
    "create_app(settings: Settings | None = None) -> FastAPI",
)
SETTINGS = Seam("racket.platform.settings:Settings", "ST-005", "Settings.from_env(environ)")
MISSING_SETTING_ERROR = Seam("racket.platform.settings:MissingSettingError", "ST-005")
CONFIGURATION_ERROR = Seam("racket.platform.settings:ConfigurationError", "ST-005")
DB_MIGRATE = Seam(
    "racket.platform.db:upgrade_to_head",
    "ST-005",
    "upgrade_to_head(database_url) applies the Alembic migrations",
)
DB_SESSION_DEPENDENCY = Seam(
    "racket.platform.db:get_session",
    "ST-005",
    "FastAPI dependency yielding a SQLAlchemy Session; tests override it to a rolled-back one",
)
OBJECT_STORE = Seam(
    "racket.platform.storage:ObjectStore",
    "ST-001/ST-008",
    "ObjectStore.from_settings() (reads env) with list_keys(prefix='') -> Iterable[str] "
    "and get_bytes(key) -> bytes",
)

# ------------------------------------------------------------------ queue and worker (ST-007)
JOB_KEY = Seam("racket.analysis_jobs.domain:JobKey", "ST-007")
JOB_QUEUE = Seam(
    "racket.analysis_jobs.queue:JobQueue",
    "ST-007",
    "JobQueue(session): enqueue(key) -> job_id (idempotent per key), "
    "claim(worker_id) -> Job | None, get(job_id) -> Job, for_match(match_id) -> list[Job]; "
    "Job has id, key, status "
    "('queued'|'running'|'done'|'failed'), attempts, failure_reason",
)
WORKER_MODULE = "racket.worker"  # `python -m racket.worker` is the worker entry point (ST-007)
STAGE_REGISTRY = Seam("racket.worker.stages:STAGES", "ST-007", "mapping stage name -> callable")
WORKER_RUN_UNTIL_IDLE = Seam(
    "racket.worker.runner:run_until_idle",
    "ST-007",
    "run_until_idle(max_jobs: int = 100) -> int; claims and runs jobs in-process until none left",
)
# Fault injection for the worker (honoured ONLY when APP_ENV=test; ST-007). Values:
#   "probe:sleep=<seconds>"            the probe stage sleeps before writing anything
#   "probe:fail_after_partial_write"   the probe stage writes part of its result, then raises
FAULT_INJECTION_ENV = "RACKET_FAULT_INJECTION"

# ------------------------------------------------------------------ media (ST-009)
PROBE_STAGE_NAME = "probe"
COUNT_MEDIA_FACTS = Seam(
    "racket.video_ingest.repository:count_media_facts",
    "ST-009",
    "count_media_facts(session, match_id) -> int; rows of MediaAsset facts for a match",
)

# ------------------------------------------------------------ errors and security log (ST-005/006)
MATCH_SERVICE_DEPENDENCY = Seam(
    "racket.matches.api:get_match_service",
    "ST-006",
    "FastAPI dependency returning the match application service used by the /matches routes",
)
SECURITY_LOGGER = "racket.security"  # authorisation failures are logged here without personal data
DEV_IDENTITY_ENV = "DEV_IDENTITY_ENABLED"  # "true" enables the dev identity provider

# ------------------------------------------------------------------ HTTP contract (ST-006, ST-008)
# GET /matches/{id} -> {"id", "title", "format", "status", "media": null | {
#     "duration_ms", "fps", "width", "height", "has_audio", "vfr", "container", "video_codec"}}
# The dev identity provider (ST-006) signs a user in and sets a session cookie.
DEV_SIGN_IN = ("POST", "/dev/sign-in")  # json {"username": "ivy" | "carlos" | "dana"}
MATCHES = "/matches"
MATCH = "/matches/{match_id}"
MATCH_MEDIA = "/matches/{match_id}/media"  # media facts of a match (204 until probed)
# tus 1.0.0 core (ST-008). The creation URL may change with ADR 0011 (tusd vs FastAPI core).
UPLOAD_CREATE = "/matches/{match_id}/uploads"
UPLOAD_RESOURCE = "/uploads/{upload_id}"  # tus HEAD/PATCH target returned in Location
TUS_VERSION = "1.0.0"

# Match status codes in the API and the labels the UI shows (sprint-00 §7 wording).
STATUS_LABELS = {
    "awaiting_upload": "Awaiting upload",
    "uploading": "Uploading",
    "video_received": "Video received",
    "probe_failed": "We could not read this video",
}
