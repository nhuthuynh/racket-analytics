# Design: `MetricSnapshot` (Analytics), recompute on scoring events, versions, low-sample source

- **Status:** Accepted for build (principal-engineer, author and chair, 2026-10-07, Sprint 3 review round 1, PE-R1S3-03 / task PE-2). **Design review D3 is open:** senior-backend-engineer, senior-qa-engineer, pickleball-domain-coach and security-privacy-engineer write their comments as rows under "Design review D3 (analytics-snapshots.md)" in `docs/sprints/03/review-rounds.md`. A blocking comment amends this file before ST-046 merges (its ticket PR is reviewed against this file, ADR 0039). Nothing here changes code that exists at `6f07640`.
- **Amended 2026-10-07 (review round 2, principal-engineer), SEC-S3-TM-02 / T-DL-4:** a snapshot is written only under a tombstone-aware `FOR SHARE` lock on the match (§4.2 step 2, invariant S8), and the purge sweeps orphan snapshot rows (`deletion-and-purge.md` §4.2). Decision: ADR 0045, which amends ADR 0040's consequences.
- **Decisions recorded as ADRs:** ADR 0040 (recompute after commit with read repair, no outbox in R1; amended by ADR 0045), ADR 0041 (the metric dictionary is the single source of the low-sample thresholds).
- **Stories:** ST-043 (dictionary file, done in `bd7593c`), ST-044 (pure stats, done), ST-045 (conservation, done), **ST-046** (this design), ST-047 (evidence). HTTP contract: `api-sprint-03.md` §2-§3.
- **Canvas:** `contexts/analytics.md`. **Context map:** R5 (dictionary, Published Language), R6 (scoring events), R8 (snapshots to Coaching, later).
- **Requirements:** FR-100..FR-103, FR-109; NFR-004, NFR-010, NFR-017 (analogue: current within 5 s p95), NFR-051, NFR-075; ADR 0003, ADR 0005, ADR 0009, ADR 0023.

## 1. The decision in one paragraph

A `MetricSnapshot` is the starter stats of **one match** computed from **one version of its score sheet** under **one metric-dictionary version** and **one rules version**. It is a recomputable read model, never a source of truth: deleting every snapshot loses nothing (NFR-075). Match & Scoring publishes `ScoreSheetChanged(match_id, sheet_version)` after every committed scorebook command; the Analytics consumer recomputes in **its own transaction after the scoring commit** and upserts the snapshot only if it is newer. A consumer failure never undoes the tag. Every read (`GET …/stats`, `GET …/evidence`) compares the stored `sheet_version` with the current one and recomputes on the spot when it is behind (read repair), so a lost event is retried by the next read and the stats are never stale. The low-sample thresholds come only from the metric dictionary (ADR 0041), so the `min_sample` a card shows is the one that set the flag.

## 2. Model

```
MetricSnapshot  (aggregate root; one row per key)
  key:            SnapshotKey(match_id, metric_def_version, rules_version)
  owner_id        (ddd-guidelines §4.9; copied from the match, used only by the owner filter)
  sheet_version   int, the scorebook version the stats were computed from (monotonic)
  stats           {metric_id: {side: fields}}  — every AN entry of that dictionary version,
                  draft ones included (status is applied on read, §5.3)
  computed_at     timestamp
```

- **Identity and idempotency key.** The table key is (`match_id`, `metric_def_version`, `rules_version`); `sheet_version` is the version guard. The upsert writes only when the incoming `sheet_version` is greater than the stored one:
  `INSERT … ON CONFLICT (match_id, metric_def_version, rules_version) DO UPDATE SET … WHERE metric_snapshots.sheet_version < EXCLUDED.sheet_version`.
  So the same event twice, an event delivered late (older version) and two consumers racing all leave exactly one row with the newest version (IT-03-02 "the same event twice gives one snapshot version"). This is the PE-R1S3-03 key "(match, metric_def_version, rules_version, sheet version)": the first three name the row, the fourth decides whether a write happens.
- **Why one row per key, not one per sheet version.** History of stats is not a requirement (the score sheet and its audit are the history, FR-052); a row per tag would grow with every command for no reader (judgment, [AQS/ENG-04]). A dictionary bump or a rules change creates a **new** key, so old snapshots keep the meaning they were computed under (NFR-075) until the match is deleted.
- **`metric_def_version`** is the dictionary's top-level `version` (`metrics.json` `"version"`, today `0.1`), which the lock test forces up whenever any entry's definition changes (`metrics.lock.json`, ST-043). Each entry also keeps its own `version`, shown on the card.
- **`rules_version`** is the sheet's `rules_version` (today `PROVISIONAL-UNVERIFIED`, ADR 0023). Every metric that reads the score sequence inherits that status; the response carries `unofficial` and the label (api-sprint-03 §2.1).
- **Code layout** (DDD; enforced by `backend/tests/unit/test_architecture_sprint03.py`, QA-R1S3-11):

| Module | Layer | Holds |
|---|---|---|
| `racket/analytics/snapshot.py` | domain (pure) | `SnapshotKey`, `MetricSnapshot.compute(sheet, sheet_version, dictionary, owner_id, now)`, `MetricSnapshot.is_behind(current_version)`, `published_view(dictionary)` |
| `racket/analytics/starter_stats.py`, `uncertainty.py`, `attribution.py`, `sheet.py` | domain (pure) | unchanged (ST-044/045); `LowSamplePolicy.from_dictionary` added (§5.2) |
| `racket/analytics/repository.py` | adapter | the `metric_snapshots` table, the guarded upsert, `delete_for_match` |
| `racket/analytics/service.py` | application | `on_sheet_changed(event)` (the consumer), `current(match, session)` (read repair), `replay_latest_event(conn, match_id)` (test seam, §4.3) |
| `racket/analytics/api.py` | adapter | `GET …/stats`, `GET …/stats/{metric_id}/evidence` |
| `racket/analytics/public.py` | port | `purge_match(session, match_id)` for the purge job (deletion-and-purge.md §4) |

`service.py` calls `starter_stats` through the module (`from racket.analytics import starter_stats as stats_module`; `stats_module.starter_stats(...)`), so IT-03-02's failure injection (which patches the module attribute) reaches it.

## 3. Invariants

| # | Invariant | Guard | Test |
|---|---|---|---|
| S1 | A snapshot is a pure function of (sheet at `sheet_version`, dictionary version, rules version) | `MetricSnapshot.compute` has no I/O, clock passed in | unit: same inputs → equal snapshot; golden GS-AN-1 (ST-049) |
| S2 | `sheet_version` never goes down for a key | guarded upsert (§2) | unit (repository fake) + IT-03-02 (replay twice, out-of-order) |
| S3 | Attribution conservation holds for every snapshot written (FR-109) | `check_conservation` inside `starter_stats` raises; nothing is written | ST-045 property suite; unit: a violating sheet writes no row |
| S4 | A read never returns stats older than the sheet it reads | read repair (§4.2) | IT-03-01 (after every tag), IT-03-02 (failure then read) |
| S5 | Draft entries never leave the API (FR-102) | `published_view` filters by the live dictionary status | IT-03-03 |
| S6 | The flag on a metric uses that metric's `min_sample` from the same dictionary version the response names | `LowSamplePolicy.from_dictionary` (§5.2) | unit: dictionary with AN-05 n=30 → AN-05 flagged at n=25, AN-01 not; card `min_sample.n` = 30 |
| S7 | Only the owner reads a snapshot (NFR-051) | the match is loaded through the R1 owner filter before the snapshot | IT-03-05 BOLA |
| S8 | No `metric_snapshots` row outlives its match (SEC-S3-TM-02, T-DL-4; NFR-066 b) | every upsert runs in a transaction that holds the match row `FOR SHARE` through `matches.public.lock_live_sheet`, which returns nothing for a missing or tombstoned match; the purge's orphan sweep is the second net | unit (fake port returns `None` → no repository write); IT: recompute replayed after `DELETE` + purge → no row; seeded orphan → one pass → gone |

## 4. Event consumption

### 4.1 The event

`racket.matches.events.ScoreSheetChanged(match_id: UUID, sheet_version: int, owner_id: UUID, kind: str)`, past tense, raised by `ScorebookService._run` after `session.commit()` succeeds. `kind` is the command (`rally_tagged`, `rally_corrected`, `rally_withdrawn`, `rally_resolved`, `game_started`, `change_undone`). It stands for the EventStorming events `RallyScored` (a tag) and `ScoreCorrected` (a correction, withdrawal, resolution or undo); one event type is enough because every one of them changes the sheet and the consumer does the same thing for each (judgment). The event carries ids and a version only, never sheet content (the consumer reads the sheet through the port, so it always reads a committed state).

### 4.2 Delivery: in-process, after commit; read repair as the retry (ADR 0040)

1. **Publish.** `racket.platform.events` (shared kernel) holds a tiny in-process dispatcher: `subscribe(event_type, handler)` at the composition root (`racket.platform.app`), `publish(event)` called by the scorebook service after its commit. Match & Scoring imports nothing from Analytics (context-map rule 1; R6 direction).
2. **Consume.** `analytics.service.on_sheet_changed` opens **a new session** (one aggregate per transaction, ddd-guidelines §4.1) and reads the sheet through `racket.matches.public.lock_live_sheet(session, match_id) → (version, sheet) | None`, which runs `SELECT … FROM matches WHERE id = :id AND deleted_at IS NULL FOR SHARE` and then reads the sheet in the same transaction. `None` (gone or tombstoned) → write nothing, roll back, log `analytics.snapshot_skipped` (`match_id`, `reason=deleted`) at DEBUG. Otherwise compute, upsert (§2), commit; the lock is held until that commit. Why this closes T-DL-4: the tombstone (`DELETE /matches`, `DELETE /me`, the §3.3 sweep of `deletion-and-purge.md`) takes the match row `FOR UPDATE` and the purge deletes that row, and both conflict with `FOR SHARE`. So either the recompute commits first and its row exists **before** the tombstone, and the purge removes it with `analytics.public.purge_match`; or the tombstone commits first and the recompute, re-checking the row under READ COMMITTED, finds `deleted_at` set and writes nothing. Matching on `sheet_version` alone (ADR 0040 as first written) did not stop an **insert** when no row existed (threat model E6). Shared lock: two recomputes of one match do not block each other. A scorebook command takes the same match row `FOR UPDATE` (`ScorebookRepository.load(lock=True)`, IT-02-04), so a command and a recompute of one match run one after the other; the wait is one pure computation over at most 500 rallies (§4.2 step 4). BE measures it in ST-046 with the IT-03-02 timing and the G03-05 run (judgment until then). `FOR KEY SHARE` would not conflict with a plain `UPDATE … SET deleted_at` and is therefore not enough.
3. **Failure.** Any exception in the handler is caught by the dispatcher, logged at ERROR (`analytics.snapshot_failed`, `match_id`, `sheet_version`, the exception class; no sheet content) and counted (`racket_snapshot_failures_total`). The scorebook response is already decided: the tag stays committed and the client gets its 201/200 (IT-03-02 "a failing recompute keeps the tag").
4. **Retry = read repair.** `GET …/stats` and `GET …/evidence` call `analytics.service.current(match)`: read the current sheet version through the same `lock_live_sheet` port (a tombstoned match is already 404 at the owner filter; the lock covers a delete that commits between the filter and the upsert); load the snapshot for (match, current dictionary version, the sheet's rules version); if there is none or `snapshot.is_behind(version)`, compute from that sheet now, upsert (same guard), and answer from the freshly computed value. The work is a pure computation over at most `SCOREBOOK_MAX_RALLIES` (500) rallies, measured in ST-044's unit run at well under the NFR-010 budget (BE confirms with the G03-05 run).
5. **Freshness.** With the after-commit consumer the snapshot is normally current before the client reads; with read repair, a read is never behind. NFR-017's 5 s p95 (analogue) is therefore met by construction; G03-02 measures it live.
6. **Dictionary or rules change.** A new dictionary version (deploy) means no snapshot exists for the new key: the next read computes it. No backfill job in R1 (judgment; matches are few and the computation is cheap). Old-key rows stay until the match is deleted.

### 4.3 Test seam

`racket.analytics.service:replay_latest_event(conn, match_id) -> None` delivers `ScoreSheetChanged(match_id, <current version>)` to the consumer again, inside the caller's connection/transaction (IT-03-02). The QA proposal named `racket.analytics.snapshot:replay_latest_event`; `snapshot.py` is the pure domain module, so the seam moves to `service.py` (one-line change in `backend/tests/integration/test_it_03_02_stats_recompute.py`, raised as a TCR row for QA, 2026-10-07).

### 4.4 Options considered (summary; detail in ADR 0040)

| Option | Verdict |
|---|---|
| **After-commit in-process consumer + read repair** | **Chosen.** No new infrastructure; idempotent by the guarded upsert; a lost event costs one recompute on the next read |
| Transactional outbox table + a consumer process | Rejected for R1: a new table, a poller and a new process identity (the media worker is sandboxed, ST-042) for a computation that read repair already makes reliable. Revisit with CM-2 when a second consumer (Coaching R8, Dataset R9) needs the events durably |
| Compute in the scoring transaction | Rejected: two aggregates in one transaction (ddd-guidelines §4.1); a stats bug would refuse a tag |
| No snapshot, compute on every read | Rejected: R8 (Coaching) and the weakness ranking need a stored, versioned snapshot (NFR-075); fine as the fallback, which read repair is |

## 5. Versions and the low-sample source

### 5.1 What each version means

| Field | Source | Changes when | Effect |
|---|---|---|---|
| `metric_def_version` | `metrics.json` `version` | any entry's definition fields change (lock test forces the bump), or the dictionary-level low-sample rule changes (§5.2) | new snapshot key; next read recomputes |
| entry `version` | `metrics.json` entry | that entry's definition changes | shown on the card ("How is this measured?") |
| entry `status` | `metrics.json` entry | the coach reviews it | **no** recompute: status is outside the digest and applied on read (S5) |
| `rules_version` | the sheet | a match with a different preset | new snapshot key |
| `sheet_version` | scorebook `version` | every committed command | upsert on the same key |

### 5.2 The single source of the low-sample thresholds (ADR 0041)

Today there are two: `metrics.json` `min_sample` per entry (versioned, digested, shown to users by `MetricEntry.public()`), and `LowSamplePolicy` defaults (`min_proportion_n=20`, `min_service_turns=10`, `min_games=2`, `max_interval_width=0.30`), which `uncertainty.py` says "come from settings". If an operator could change the policy, the card would show a `min_sample` that disagrees with the flag applied (PE-R1S3-03). Decision:

1. **The metric dictionary is the only source.** At the composition root the service builds the policy with `LowSamplePolicy.from_dictionary(dictionary)`; each metric's flag uses **its own entry's** `min_sample.n` (AN-01, AN-02, AN-05, AN-07: rallies; AN-03: service turns; AN-04: games; AN-06: `null`, never flagged). The policy refuses a dictionary whose `min_sample.unit` does not fit the metric (start-up fails closed, like `InvalidDictionary`).
2. **The interval-width rule moves into the dictionary** as a top-level, digested field `"low_sample": {"max_interval_width": 0.30}` (metric-dictionary.md rule 0.3 already states it). Changing it bumps the dictionary `version`. `MetricEntry.public()` keeps `min_sample`; the stats response adds `low_sample_rule: {"max_interval_width": 0.30}` once at the top (api-sprint-03 §2.1) so the card can say "or the range is wider than 30 points".
3. **No environment setting** for any threshold. FR-101's and ADR 0005's "thresholds live in config" is met by the dictionary file, which is configuration as versioned data; an env override would break NFR-075 (two snapshots with the same `metric_def_version` could carry different flags).
4. `LowSamplePolicy()` defaults stay for pure unit calls only. A unit test (ST-046) asserts `LowSamplePolicy.from_dictionary(load_dictionary())` equals the ADR 0005 values for the shipped dictionary, so a drift between the two shows as a red test, not as a wrong card.
5. Owners: senior-backend-engineer (loader field, `from_dictionary`, the test; ST-046); pickleball-domain-coach confirms the `low_sample` field's value with the COACH-1 review (it restates rule 0.3, no new judgment).

### 5.3 Read model (what `GET …/stats` shows)

`published_view(dictionary)` returns, for every entry with status `coach-reviewed` or `verified` **in the loaded dictionary whose version equals the snapshot's `metric_def_version`**: the entry's `public()` and the two sides' fields without the `rallies` lists (those are served by the evidence route). Draft and deprecated entries are absent from the whole body (IT-03-03). Shape: api-sprint-03 §2.1.

### 5.4 Evidence (ST-047)

The snapshot keeps each metric-side's `rallies` (match-wide sheet `number`s, FR-103). `GET …/evidence` takes the **same sheet** the read repair used, maps each number to the sheet row (`rally_id`, `game`, `start_ms`, `end_ms`), orders by `start_ms` (the sheet's `number` order is the video order, api-sprint-02 §2.1), and pages it (api-sprint-03 §3). Numbers and rally ids therefore always come from one sheet version.

## 6. Persistence

Migration `0014_metric_snapshots` (the next free number when ST-046 starts; BE checks), owned by `racket.analytics`:

```
metric_snapshots(
  match_id uuid NOT NULL, metric_def_version varchar(16) NOT NULL, rules_version varchar(64) NOT NULL,
  owner_id uuid NOT NULL, sheet_version integer NOT NULL CHECK (sheet_version >= 0),
  stats jsonb NOT NULL, computed_at timestamptz NOT NULL,
  PRIMARY KEY (match_id, metric_def_version, rules_version))
```

- **No foreign key to `matches`** (context-map rule 1: Analytics owns its table; the purge removes it through `analytics.public.purge_match`, deletion-and-purge.md §4). The generic purge inventory (IT-03-06, G03-03) finds it by its `match_id` column. What a foreign key would have guaranteed comes from invariant S8: the `FOR SHARE` write rule, plus the purge's orphan sweep (`analytics.public.snapshot_match_ids` against `matches.public.existing_ids`, deletion-and-purge.md §4.2), which also removes rows left by any older code path.
- Grants: the app role only. The media worker role (ST-042) gets nothing on it (IT-03-10 lists the worker's tables).
- No personal data: ids, versions and counts only. Nicknames never enter the snapshot (by-player counts are keyed by slot `A1`…`B2`).

## 7. Observability

One log line per recompute at DEBUG (`analytics.snapshot_computed`, `match_id`, `sheet_version`, `metric_def_version`, `duration_ms`, `trigger` = `event` | `read`), ERROR on failure (§4.2). Histogram `racket_snapshot_compute_seconds{trigger}`; counter `racket_snapshot_failures_total`. A rising `trigger="read"` share means the after-commit path is failing (SRE dashboard, judgment).

## 8. DDD guard

`backend/tests/unit/test_architecture_sprint03.py` scans every `racket/analytics/*.py` except the adapter names `api.py`, `repository.py`, `service.py`, `schemas.py`, `public.py`, `worker.py`. `snapshot.py` is therefore checked framework-free from the day it lands.

## 9. Not decided here

| Item | Owner | When |
|---|---|---|
| Per-player snapshot rows (AN-04 by player is inside the side's fields today) | principal-engineer with BE | when Coaching (R8) needs per-player reads |
| Outbox / durable events (CM-2) | principal-engineer | when a second consumer appears |
| Backfill of snapshots after a dictionary bump | BE | only if read-repair latency shows in G03-05 |
| Whether forced/unforced merge below κ 0.6 (K8) changes AN-04/AN-07 | pickleball-domain-coach | COACH-1 |
