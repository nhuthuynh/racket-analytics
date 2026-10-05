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

# ================================================================== Sprint 1 (sprint-01 §5)
# QA proposals written before ST-020/ST-021 (sprint-01 §3 "ST-023 tests first"). The shapes come
# from sprint-01 §5 and §14.1 and QD §2.1 (QD-RE-01..11). Module paths not fixed by the plan are
# QA proposals, logged in docs/sprints/01/decision-log.md; BE confirms or amends them at story
# start, and every amendment is a QA edit here (ADR 0012).
#
# Rules engine (ST-020), module racket.sports.pickleball.rules, pure (no I/O, clock, randomness):
#   Side            Enum with members A and B; Side.A.other is Side.B.
#   ScoringSystem   StrEnum: SIDE_OUT = "side_out", RALLY = "rally" (RALLY may be refused, FR-043).
#   MatchFormat     reuse of "doubles"/"singles" strings; Sprint 1 scores doubles only (ST-035).
#   RulesConfig(*, rules_version: str, scoring_system: str, format: str, points_to_win: int,
#               win_by: int, first_service_single_server: bool)
#       frozen value object. Out-of-range values raise InvalidRulesConfig whose ``field``
#       attribute and message name the field ("points_to_win", "win_by", "scoring_system", ...).
#   PRESETS         Mapping[str, RulesConfig]; only "PROVISIONAL-UNVERIFIED" ships (ADR 0009).
#   GameState       frozen value object (== by value) with score_a, score_b: int,
#                   serving_side: Side, server_number: int | None (None in singles),
#                   winner: Side | None, and is_over: bool.
#                   Doubles positions (SOD-05/SOD-06, @needs-verification; QD-RE-03 names):
#                   server_player: str (one of "A1", "A2", "B1", "B2") and
#                   right_court_player: Mapping[Side, str], the player standing in the
#                   right-hand court of each side. A new or declared state puts A1 and B1 in the
#                   right-hand court, and the serving side's right-court player serves at
#                   server 1 (its partner at server 2). Sprint 1 per sprint-01 §7.8 / ST-023
#                   (SOD-01..SOD-12); docs/architecture/scoring-engine.md §2.4 defers it to
#                   Sprint 2, routed to the principal-engineer (docs/sprints/01/decision-log.md).
#   new_game(config, first_server: Side) -> GameState
#       0-0 with first_server serving at server 2 when config.first_service_single_server,
#       else at server 1. The first server is an input, never inferred (QD-RE-11).
#   declare_state(config, *, serving_side, serving_score, receiving_score, server_number)
#       -> GameState | DomainError   (IllegalState for server_number outside {1, 2} in doubles
#       or a score that already meets the game-over condition; QD-RE-06, sprint-01 §5 GameState).
#   RallyOutcome    value object with constructors
#       RallyOutcome.won_by(side: Side)                 rally won outright by ``side``
#       RallyOutcome.fault(by: Side, kind: FaultKind)   ``by`` faulted, i.e. lost the rally
#       RallyOutcome.replay()                           replayed rally (QD-RE-08)
#   FaultKind       StrEnum: SERVE "serve", FOOT "foot", TWO_BOUNCE "two_bounce", NVZ "nvz",
#                   OTHER "other" (glossary "Rally ending").
#   apply(state, outcome, config) -> GameState | DomainError     never raises (QD-RE-05)
#   fold(outcomes, config, start: GameState) -> GameState | DomainError
#       equals sequential apply from ``start``; stops at the first DomainError (P6).
#   DomainError     base type (NOT an Exception subclass required) with a ``message: str``;
#                   subclasses GameOver ("game already over") and IllegalState.
RULES_MODULE = Seam("racket.sports.pickleball.rules", "ST-020", "the pure rules engine module")
RULES_SIDE = Seam("racket.sports.pickleball.rules:Side", "ST-020")
RULES_CONFIG = Seam("racket.sports.pickleball.rules:RulesConfig", "ST-020")
INVALID_RULES_CONFIG = Seam("racket.sports.pickleball.rules:InvalidRulesConfig", "ST-020")
RULES_PRESETS = Seam("racket.sports.pickleball.rules:PRESETS", "ST-020")
GAME_STATE = Seam("racket.sports.pickleball.rules:GameState", "ST-020")
NEW_GAME = Seam("racket.sports.pickleball.rules:new_game", "ST-020")
DECLARE_STATE = Seam("racket.sports.pickleball.rules:declare_state", "ST-020")
RALLY_OUTCOME = Seam("racket.sports.pickleball.rules:RallyOutcome", "ST-020")
FAULT_KIND = Seam("racket.sports.pickleball.rules:FaultKind", "ST-020")
RULES_APPLY = Seam("racket.sports.pickleball.rules:apply", "ST-020")
RULES_FOLD = Seam("racket.sports.pickleball.rules:fold", "ST-020")
DOMAIN_ERROR = Seam("racket.sports.pickleball.rules:DomainError", "ST-020")
GAME_OVER = Seam("racket.sports.pickleball.rules:GameOver", "ST-020")
ILLEGAL_STATE = Seam("racket.sports.pickleball.rules:IllegalState", "ST-020")
PROVISIONAL_PRESET = "PROVISIONAL-UNVERIFIED"
RULES_PACKAGE_DIR = "src/racket/sports/pickleball/rules"  # module or package (IT-01-12/13)

# Match structure (ST-021), Match & Scoring context:
#   MatchState.start(*, best_of: int, config: RulesConfig) -> MatchState   (best_of in {1, 3})
#   ms.start_game(*, first_server: Side, ends_switched: bool) -> MatchState | DomainError
#       opens the next game; MatchOver once the match is decided (M-05, M-08).
#   ms.record_rally(game_number: int, outcome: RallyOutcome) -> MatchState | DomainError
#       MatchOver when the match is decided or game_number is beyond the format.
#   ms.games -> tuple of game records with number, first_server, ends_switched, state: GameState
#   ms.games_won(side) -> int; ms.winner -> Side | None; ms.is_over -> bool
#   ms.rules_version -> str (a match keeps the preset it was scored under, QD-RE-02)
MATCH_STATE = Seam("racket.matches.domain:MatchState", "ST-021")
MATCH_OVER = Seam("racket.matches.domain:MatchOver", "ST-021", "a DomainError subclass")

# ------------------------------------------------------------------ HTTP contract, Sprint 1
# docs/architecture/api-sprint-01.md (Accepted 2026-10-05). Routes are relative to the API root.
AUTH_LINKS = "/auth/links"  # POST {"email"} -> 202 always (no account oracle, D-4)
AUTH_EXCHANGE = "/auth/exchange"  # POST {"token"} -> 200 + session cookie; 401 link_expired
AUTH_SIGN_OUT = "/auth/sign-out"  # POST -> 204 + Clear-Site-Data: "cache"
ME = "/me"
UPLOAD_POLICY = "/upload-policy"  # GET -> caps and chunk bounds (§6.1)
UPLOAD_OPTIONS = "/uploads"  # OPTIONS -> Tus-Extension: creation,checksum,expiration
SESSION_COOKIE_TEST = "racket_session"  # test env name (prod: __Host-racket_session)
SIGN_IN_LINK = r"/auth/callback#token=(?P<token>[A-Za-z0-9_-]{43})"  # in the email body
# Auth events are JSON log lines whose ``msg`` is one of these, with ``ts`` (UTC),
# ``request_id`` and ``user_id`` (pseudonymous) or ``email_key`` (HMAC); never the address or
# token (NFR-057, T-ML-9). Names are a QA proposal matching the racket.auth.links outcomes.
AUTH_LOG_EVENTS = ("auth.link_requested", "auth.link_exchanged", "auth.link_refused")
SEND_SIGN_IN_LINK_STAGE = "send_sign_in_link"  # queued job that sends the email (§2.1)
MAILPIT_API_ENV = "MAILPIT_API_URL"  # e.g. http://127.0.0.1:8025 (Compose `mailpit` UI port)
CHECKSUM_MISMATCH = 460  # tus checksum extension status (§6.5)
# Configuration the tests set before the app is built (§8). ``api``/``committed_app`` build
# the app from the environment, so a test sets these with monkeypatch before using them.
UPLOAD_EXPIRY_ENV = "UPLOAD_EXPIRY_SECONDS"
UPLOAD_MAX_BYTES_ENV = "UPLOAD_MAX_BYTES"
UPLOAD_MAX_DURATION_ENV = "UPLOAD_MAX_DURATION_MS"
PROVISIONAL_CAP_BYTES = 10_000_000_000  # 10 GB (FR-023, provisional until ST-025)
PROVISIONAL_CAP_DURATION_MS = 9_000_000  # 150 min

# Participants (ST-016, ADR 0024): pure predicate shared by client and domain (§5.4).
PARTICIPANTS = Seam(
    "racket.matches.domain:Participants",
    "ST-016",
    "Participants.looks_like_contact_details(nickname: str) -> bool",
)
# Upload policy (ST-018): pure check of probe facts (§6.6).
UPLOAD_POLICY_DOMAIN = Seam(
    "racket.video_ingest.domain:UploadPolicy",
    "ST-018",
    "UploadPolicy(max_bytes, max_duration_ms, ...).check(facts) -> None | rejection code",
)

# ------------------------------------------------------------------ Sprint 1 operations (ST-024)
# Nightly results in docs/sprints/01/status.json under "nightly" (QA proposal, SRE confirms):
#   {"run_date": "YYYY-MM-DD", "run_url": str,
#    "oracle": {"sequences": int, "disagreements": int, "passed": bool},
#    "mutation": {"score": float (0..1), "scope": "sports/pickleball/rules"}}
STATUS_NIGHTLY_KEY = "nightly"
# SLI arithmetic (api-sprint-01 §10), pure functions so the dashboard formula is unit-tested:
#   upload_completion(events) -> (good, base): events are per-upload lifecycles such as
#     ("created", "completed"), ("created", "rejected"), ("created", "cancelled");
#     good = completed; base = created - rejected - cancelled (cancel ships with DELETE, ST-038).
#   availability(status_codes) -> float: non-5xx / all, 429 excluded from both (NFR-041).
SLI_UPLOAD_COMPLETION = Seam("racket.platform.slis:upload_completion", "ST-024")
SLI_AVAILABILITY = Seam("racket.platform.slis:availability", "ST-024")

# ------------------------------------------------------------------ phone fixtures (ST-025)
# fixtures/clips/phones-v1/manifest.json: the ST-011 manifest plus one "clips" entry per video
# (QA proposal, ML confirms): {"path", "device_model", "fps", "vfr": bool,
#  "shows_people": bool, "consent_record": str | null}. racket-manifest-check fails, naming the
# file, when "shows_people" is true and "consent_record" is null (OQ-06).
PHONES_V1_DIR = "clips/phones-v1"

# ================================================================== Sprint 2 (sprint-02 §5)
# Seams QA uses for the Sprint 2 golden tables (ST-041). Scorebook names follow the code the BE
# lane committed for ST-026..ST-032 (`racket.matches.scorebook.domain`); the singles preset
# seam is a QA proposal for ST-035 (BE-D1-05: presets keyed by rules version and format).
#   Scorebook.new(*, rules_version, format, best_of) -> Scorebook          (pure, versioned)
#   book.start_game(*, first_serving_side, ends_switched, ready, expected_version, ctx)
#   book.tag(times, outcome, *, ready, expected_version, ctx) -> (Scorebook, Rally)
#   book.correct(rally_id, field, value, *, expected_version, ctx) -> Scorebook
#   book.undo(*, expected_version, ctx) -> Scorebook
#   project(book) -> dict (the score sheet; rows carry "marker": "needs_decision" for C-02/C-03)
#   canonical_bytes(sheet) -> bytes (sorted keys, no spaces: the C-04 / NFR-075 comparison)
#   preset_for(rules_version, format) -> RulesConfig | None   (ST-035; singles preset)
#   score_call(state) -> str   ("S-R-n" in doubles, "S-R" in singles; FR-048 provisional)
SCOREBOOK = Seam("racket.matches.scorebook.domain:Scorebook", "ST-026")
SCOREBOOK_CONTEXT = Seam("racket.matches.scorebook.domain:CommandContext", "ST-026")
OUTCOME_INPUT = Seam("racket.matches.scorebook.domain:OutcomeInput", "ST-027")
RALLY_TIMES = Seam("racket.matches.scorebook.domain:RallyTimes", "ST-027")
PROJECT = Seam("racket.matches.scorebook.domain:project", "ST-026")
CANONICAL_BYTES = Seam("racket.matches.scorebook.domain:canonical_bytes", "ST-026")
NEEDS_DECISION = "needs_decision"
SCORE_CALL = Seam("racket.sports.pickleball.rules:score_call", "ST-029")
PRESET_FOR = Seam(
    "racket.sports.pickleball.rules:preset_for",
    "ST-035",
    "preset_for(rules_version, format) -> RulesConfig | None; singles under the provisional preset",
)
