# 0040. Metric snapshots are recomputed after the scoring commit, with read repair as the retry (no outbox in R1)

- **Status:** Accepted (principal-engineer, 2026-10-07, Sprint 3 review round 1, PE-R1S3-03). Design review D3 (BE, QA, coach, security) may amend it before ST-046 merges.
- **Amended by:** ADR 0045 (2026-10-07, review round 2), consequences: snapshot writes need the tombstone-aware `FOR SHARE` read and the purge sweeps orphans (SEC-S3-TM-02).
- **Date:** 2026-10-07
- **Deciders:** principal-engineer
- **Consulted (review D3, open):** senior-backend-engineer, senior-qa-engineer, pickleball-domain-coach, security-privacy-engineer
- **Related:** `docs/architecture/analytics-snapshots.md` §4; ST-046; FR-100; NFR-017 (analogue), NFR-075; context map R6 and CM-2; ddd-guidelines §4.1, §4.6; ADR 0017 (job queue)

## Context and problem statement

ST-046 needs the starter stats of a match to follow every tag and correction (current within 5 s p95, the NFR-017 analogue in G03-02), be idempotent (the same event twice gives one snapshot version, IT-03-02), never refuse or undo a tag when the stats fail (IT-03-02), and stay versioned by `metric_def_version` and `rules_version` (NFR-075). The code has no domain-event infrastructure for scoring today: `grep -rn "RallyScored\|ScoreCorrected" backend/src` finds nothing, scorebook commands commit in `ScorebookService._run`, and the only outbox is `sign_in_requests`, the sign-in mail outbox drained by the mailer stage (ADR 0027). The media worker cannot host a consumer: it runs as `racket_media_worker` with no grant on new tables (ST-042).

## Decision drivers

- One aggregate per transaction (ddd-guidelines §4.1); consumers idempotent (§4.6) [AQS/OPS-02].
- Simplest design that meets the requirement [AQS/ENG-04] (judgment on what "simple" costs).
- No new privileged process (NFR-054).

## Considered options

1. **After-commit in-process consumer + read repair** (chosen). The scorebook service publishes `ScoreSheetChanged(match_id, sheet_version)` after its commit through a small dispatcher in the shared kernel; Analytics recomputes in a new transaction with a guarded upsert (`… WHERE stored.sheet_version < new.sheet_version`). Every read checks the stored `sheet_version` against the sheet and recomputes when behind.
   - Good: no new table, process or identity; idempotent and order-safe by the guard; a lost event (crash, exception) is repaired by the next read, so stats are never stale.
   - Bad: events are not durable; a future consumer that is not driven by reads (Coaching, Dataset) needs something else (CM-2). A read after a failed recompute pays the computation (pure, ≤ 500 rallies).
2. **Transactional outbox + a consumer process.** Good: durable, replayable events for every future consumer. Bad: an outbox table, a poller, a new process and identity, and retry/dead-letter handling, to deliver a computation that option 1 already makes reliable; the media worker cannot be reused (ST-042).
3. **Recompute inside the scoring transaction.** Good: always consistent. Bad: two aggregates in one transaction; a stats bug would refuse a tag (IT-03-02 forbids it).
4. **No snapshot; compute on every read.** Good: simplest. Bad: no stored, versioned output for Coaching (R8) and NFR-075; every read pays the computation.

## Decision outcome

Option 1. Option 4 is its fallback path (read repair), so its simplicity is kept without its drawback. Revisit with CM-2 (outbox) when a second consumer of scoring events appears.

### Consequences

- `racket.platform.events` (dispatcher), `racket.matches.events.ScoreSheetChanged`, `racket.analytics.service.on_sheet_changed` / `current`, the `metric_snapshots` table keyed (`match_id`, `metric_def_version`, `rules_version`) with `sheet_version` (analytics-snapshots.md §2, §6).
- Test seam `racket.analytics.service:replay_latest_event(conn, match_id)` (IT-03-02; TCR row for the seam path).
- SLI: the share of recomputes triggered by reads (`racket_snapshot_compute_seconds{trigger}`) shows a failing after-commit path.

## Evidence

| Claim | Evidence | Type |
|---|---|---|
| No scoring-event code exists; the one outbox is for sign-in mail | `grep -rn "RallyScored\|ScoreCorrected" backend/src --include=*.py` → no match; `grep -rln outbox backend/src --include=*.py` → `players/stages.py` and migrations 0005/0008 only | code |
| The worker cannot write new tables | ST-042 `61dbdd5`/`a1bf473`; IT-03-10 | code, test |
| Same event twice → one snapshot; failing recompute keeps the tag | `backend/tests/integration/test_it_03_02_stats_recompute.py` (red until ST-046) | test |
| Consumers idempotent, one aggregate per transaction | ddd-guidelines §4.1, §4.6; [AQS/OPS-02] | guideline, verified source |
| Choosing option 1 over 2 for R1 | (judgment) | judgment |
