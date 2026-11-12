# CI-NIGHTLY-PERF decisions

Per-ticket decision file (working-agreement §3, "Daily sync"). Ticket: CI-NIGHTLY-PERF "Root-cause the stats/evidence latency tail that failed the nightly 50 RPS gate", story "CI first", NFR-010 "dashboard" (stats and evidence p95 <= 300 ms, p99 <= 800 ms at 50 RPS), NFR-013, NFR-041. Bounded contexts: Match & Scoring (published port `lock_live_sheet`, `owns_match`) serving Analytics (read repair, analytics-snapshots.md §4.2). Owner: senior-backend-engineer. Review tier 1 (ADR 0056): principal-engineer plus the senior-qa-engineer test review plus green CI. No gate threshold changed.

## The failure

Scheduled CI run 43007950254 on `main` b7bf0b7 (2026-11-11), job "Locust baseline 50 RPS" (`.github/workflows/ci.yml`, `backend/tests/perf/locustfile_sprint04.py`, 50 readers at 1 RPS plus 1 correction user, 90 s): `dashboard_p95` false (stats p95 310 ms), `dashboard_p99` false (evidence p99 1200 ms). The next night passed. In the job log the slow requests share one shape: max 1269-1316 ms on `stats`, `evidence`, `correct` and 1016 ms on `score-sheet`, while `match` (max 110 ms) and `corrections` (max 250 ms) never stalled. The four slow routes are exactly the ones that read and re-project the whole scorebook; the two fast ones do not.

## Root cause

| Step | Evidence |
|---|---|
| Every `GET stats` / `GET evidence` of an unchanged match sent **9 statements**: session, the match as a full aggregate plus its participants (only to check ownership), the match row `FOR SHARE`, then the scorebook head, games, rallies and corrections, then the snapshot | `statements()` recorder (`tests/support/statements.py`) around one read; red output below |
| The single uvicorn process is GIL-bound and close to saturation at 50 RPS: API container CPU median 72 %, max 93 % of one core (`docker stats`, run base3); Postgres median 19 % | `.local/perf/base3`, `cpu-base3.txt` |
| py-spy on the API under the CI Locust load: 55 % of sampled thread time inside `sqlalchemy ... execute` / `psycopg wait`; `analytics.api._current` 22 %, `lock_live_sheet` 12-17 %, `get_owned` + `_with_participants` 6.5 % | `py-spy record -r 200 -d 40` (raw profile, local) |
| Postgres is not the bottleneck: `pg_stat_activity` sampled every 0.2 s shows <= 2 active backends and a rare `transactionid` wait; the transactions sit `idle in transaction` (ClientRead) while Python works | `pgsample.sh` during base2 |

So the tail is not a slow query and not an N+1 loop: it is the number of sequential round trips and the projection CPU per dashboard read in one process near saturation. Each round trip gives up the GIL and has to win it back; when the correction user's command and its after-commit recompute land in the same instant, every read that replays the scorebook queues behind them, which is the 1.0-1.3 s cluster on exactly those routes. On a quieter runner the same load passes (the next night), which is why it looked like a flake (judgment, from the evidence above).

## Fix

| Date | Who | Decision | Evidence | Why |
|---|---|---|---|---|
| 2026-11-12 | senior-backend-engineer | **`lock_live_sheet` reads `(owner, version, rules_version)` with the share lock and reuses the sheet projected for an equal key** (`matches/scorebook/memo.py`, `SheetMemo`, per process, LRU 512 matches). A miss reads and projects the scorebook under the same lock, as before | `test_a_stats_read_of_an_unchanged_match_replays_no_scorebook`, `test_an_evidence_read_...`, scenario "Reading the stats and the evidence again replays no scorebook" | The sheet is a pure function of the scorebook and every scorebook command bumps `matches.version` in the transaction that writes the rows (`ScorebookRepository.save`, the only writer of the scorebook tables), so an equal key means an equal sheet; the same argument Coaching's scope memo already relies on (`lock_scope_versions`, SRE-VERIFY04R3-01). The lock and invariant S8 are unchanged |
| 2026-11-12 | senior-backend-engineer | **`owns_match` is one single-column read** (`SELECT matches.id ... WHERE id AND owner_id AND deleted_at IS NULL`) instead of loading the aggregate and its participants | statement budget above; BOLA rows `test_another_account_never_reads_a_match_the_owner_read` and IT-03-05 pass | The check needs a yes/no; the ownership filter (R1) is unchanged |
| 2026-11-12 | senior-backend-engineer | **Memo kept per context, not shared with `coaching/plan/scope.py`** | n/a | Context map rule 1; merging the two into a shared-kernel class is a refactor for its own PR (EP/ENG-04) |
| 2026-11-12 | senior-backend-engineer | **No threshold, Locust shape or workflow change** | `git diff origin/main -- .github scripts/ci backend/tests/perf` is empty | Ticket rule: never loosen a gate |

Result: a dashboard read of an unchanged match sends **4 statements (was 9)** and reads no scorebook table; API CPU under the same load fell from median 72 % to 30-58 % of one core.

## TDD evidence

Red (`83a21be2`), dev Postgres + dev object store (`RA_DEV_STATE=.local/dev`):

```text
$ uv run --no-sync pytest -q -p no:cacheprovider -rfE tests/unit/matches/test_sheet_memo.py tests/integration/test_ci_nightly_perf_stats_read_cost.py tests/features/test_stats_read_cost.py
E   ModuleNotFoundError: No module named 'racket.matches.scorebook.memo'
1 error in 0.17s
$ uv run --no-sync pytest -q -p no:cacheprovider -rfE tests/integration/test_ci_nightly_perf_stats_read_cost.py tests/features/test_stats_read_cost.py
E       AssertionError: assert ['SELECT matc...rrections.at'] == []
E         Left contains 3 more items, first extra item: 'SELECT match_games.match_id, match_games.number, ...
FAILED tests/integration/test_ci_nightly_perf_stats_read_cost.py::test_a_stats_read_of_an_unchanged_match_replays_no_scorebook
FAILED tests/integration/test_ci_nightly_perf_stats_read_cost.py::test_an_evidence_read_of_an_unchanged_match_replays_no_scorebook
FAILED tests/features/test_stats_read_cost.py::test_reading_the_stats_and_the_evidence_again_replays_no_scorebook
3 failed, 4 passed in 6.62s
```

The 4 that passed are the negative guards that must stay true before and after (a correction is read live, a deleted match is 404, another account is 404).

Green (`697a0e8f`): same command, `15 passed in 6.34s`.

## Load evidence: the CI Locust baseline, local

Command: the CI job's (`.github/workflows/ci.yml` "Locust baseline 50 RPS") on an isolated Compose project `perfs05` (ports moved: API 18000, web 13000, Mailpit 18025, because another lane's stack held the defaults; `AUTH_*_LIMIT_PER_IP=1000` as in the job), 4 vCPU shared with other lanes:

```text
uvx --from locust==2.46.7 locust -f backend/tests/perf/locustfile_sprint04.py --headless --host http://127.0.0.1:18000 -u 51 -r 51 -t 90s --csv <run>/perf --only-summary
python3 scripts/ci/perf_verdict.py --stats <run>/perf_stats.csv --state <run>/perf_state.json --rps 50 --json <run>/verdict.json --history <run>/perf_stats_history.csv --users 51 --dashboard-reads stats,evidence
```

| Run | Build | stats p95 / p99 (ms) | evidence p95 / p99 (ms) | requests, failures | rate | verdict |
|---|---|---|---|---|---|---|
| base1 | `main` 2f94797 | 100 / 170 | 98 / 190 | 4537, 0 | 51.01 | ok |
| base2 | `main` | 85 / 170 | 70 / 120 | 4539, 0 | 51.62 | ok |
| base3 | `main` | 110 / 190 | 130 / 250 | 4567, 0 | 51.34 | ok |
| base4 | `main` | 96 / 180 | 94 / 170 | 4586, 0 | 51.60 | ok |
| fix1 | `697a0e8f` | **29** / 55 | 38 / **110** | 4539, 0 | 51.61 | ok |
| fix2 | `697a0e8f` | **54** / 130 | 60 / **110** | 4555, 0 | 51.80 | ok |
| fix3 | `697a0e8f` | **44** / 110 | 43 / **100** | 4558, 0 | 51.82 | ok |
| fix4 | `697a0e8f` | **240** / 590 | 70 / **180** | 4553, 0 | 51.75 | ok |
| fix5 | `697a0e8f` | **91** / 180 | 250 / **580** | 4566, 0 | 51.92 | ok |

Acceptance (stats p95 <= 250 ms and evidence p99 <= 800 ms, 5 consecutive runs): **met, 5 of 5**. The local baseline did not reproduce the CI failure itself (all four `main` runs passed here too), so the before/after evidence is the statement count, the API CPU and the medians, not a red-to-green Locust run.

## Residual risk and follow-ups (not in this ticket)

- fix4 and fix5 each show one tail event (stats p99 590 ms, evidence p99 580 ms) while other lanes ran suites on the same 4 vCPUs. The remaining cost on these routes is the correction itself: `PATCH`/`undo` hold the match row `FOR UPDATE` (p95 110-290 ms here), and every read's `FOR SHARE` queues behind it, then the after-commit recompute misses the memo once per version. Options for the principal-engineer: a lock-free read when the stored snapshot equals the head version (changes the S8 reading of analytics-snapshots.md §4.2), more than one API worker process (SRE lane, compose/Dockerfile), or `pool_pre_ping` off for the API engine (one round trip per request).
- `GET score-sheet` (1016 ms max in the failing run) has the same replay cost; `ScorebookService.sheet` could use the same memo (Match & Scoring ticket).
