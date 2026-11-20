# CI-DOMAIN-BUDGET decisions (sprint 5)

Per-ticket decision file (working-agreement §3). Ticket: CI-DOMAIN-BUDGET (sprint 5 reopening), NFR-073 "rules + domain unit suite < 10 s". Owner: sre-devops-engineer. Sprint 3 history: `docs/sprints/03/decisions/CI-DOMAIN-BUDGET.md`, ADR 0049 (parallel workers, Hypothesis cache warm-up, 10 s kept).

## Trigger

Main run 43281846173 (`1c3b648`, merge of #213, 2026-11-12) stopped the step `Domain unit suite < 10 s (NFR-073)` at 10 s (exit 124). #213 changed no domain test or code. The previous main run, 43277394658 (`f46e679`), passed in 9.9 s. ADR 0049's acceptance made 2 overruns on `main` within 7 days the trigger for new work; this is the first, and the margin was already gone.

## Root cause: a two-speed runner pool, and no margin left on the slow one

`budget: finished in` lines of the 15 green `main` runs before the failure, with the two other budgeted steps of the same job (same runner) for comparison. Source: `gh api repos/nhuthuynh/racket-analytics/actions/jobs/<job>/logs`.

| Run (main) | Commit | Date (UTC) | Domain step (budget 10 s) | Property step, serial, `ci` profile (90 s) | Backend unit, serial (60 s) |
|---|---|---|---|---|---|
| 43281846173 | 1c3b648 | 11-12 18:37 | **stopped at 10 s, exit 124** | not run | not run |
| 43277394658 | f46e679 | 11-12 18:12 | 9.9 | 63.7 | 17.6 |
| 43263552673 | 6d61c6e | 11-12 16:53 | 6.8 | 42.7 | 12.2 |
| 43260344444 | 6fc8cdf | 11-12 16:35 | 7.2 | 44.3 | 12.8 |
| 43247887439 | ff519e5 | 11-12 15:26 | 5.9 | 34.3 | 10.3 |
| 42013324102 | b9c2cd2 | 11-05 10:45 | 6.6 | 36.3 | 11.0 |
| 41990011615 | 2ed79c6 | 11-05 07:50 | 7.3 | 43.2 | 13.1 |
| 41988606332 | d3b0580 | 11-05 07:38 | 5.6 | 34.7 | 10.6 |
| 41975999573 | 734d483 | 11-05 05:45 | 9.8 | 62.6 | 17.6 |
| 41969076583 | 61569ae | 11-05 04:38 | 5.9 | 38.7 | 10.7 |
| 41968962881 | abd598e | 11-05 04:37 | 9.3 | 60.7 | 17.0 |
| 41961670952 | d916a97 | 11-05 03:27 | 9.2 | 59.2 | 16.3 |
| 41929624496 | bf0afb1 | 11-04 22:56 | 9.3 | 60.4 | 16.9 |
| 41899431158 | edfd1aa | 11-04 19:41 | 6.2 | 36.5 | 10.9 |
| 41734597825 | 8c37e98 | 11-03 22:53 | 8.6 | 53.0 | 15.0 |
| 41691968128 | 756b387 | 11-03 18:15 | 9.7 | 60.9 | 17.1 |

1. **The runner, not the commit, decides the time.** The domain time moves with the two serial steps of the same job: 5.6-7.3 s when the property step takes 34-44 s, 8.6-9.9 s when it takes 53-64 s. The serial steps run the same tests on one core, so the slow runners are a CPU about 1.6-1.8x slower, not a test that got slower. 7 of the 15 green runs were on slow runners.
2. **The suite grew a little.** 1,837 tests on 11-03..11-05, 1,861 since 11-12 (ST-076b and others). Fast runners 5.6-7.3 s → 5.9-7.2 s; slow runners 8.6-9.8 s → 9.9 s, then over 10 s.
3. **About half of each run is fixed per-process cost.** Locally (4 cores, warm caches, `-n auto --dist worksteal`, per-hook timestamps): controller start-up 0.6 s; worker start-up 0.65 s CPU and collection 1.15-1.35 s CPU each (every worker imports and collects all 1,862 tests); tests 2.3 s CPU per worker; then 0.5-1.0 s from the last worker's `pytest_unconfigure` to the controller's `pytest_sessionfinish`. Serially the tests sum to 7.5 s (junit), 6.7 s of it in 40 Hypothesis property tests; no other test takes more than 0.04 s.
4. **The cyclic garbage collector was 0.8-1.0 s of CPU per worker** (`gc.callbacks` timer): 5 full (generation 2) passes of 0.55-0.79 s in all, each over the ~220,000 objects start-up and collection create and that live until exit, plus young passes. The exit-time passes (pytest's unraisable-exception check) are the 0.5-1.0 s tail above: the controller waits for the slowest worker to exit.
5. **Not the cause.** Hypothesis's constants cache is warm (each worker reads its cache entries and parses no module source; ADR 0049 rule 5 holds). No test pays a first-test penalty: `test_apply_is_total` is 0.11 s serially and 0.44 s on a worker under load; its 1.4 s reading came from a contended host. Only 14 `.pyc` files (xdist, Hypothesis) are written during the timed run.

## Decisions

| Date | Who | Decision | Evidence | Reasoning |
|---|---|---|---|---|
| 2026-11-12 | sre-devops-engineer | **Fix: the backend root conftest (`backend/conftest.py`) freezes the start-up and collection objects out of the cyclic GC (`gc.freeze()` before and after collection, no GC pass during collection).** The collector stays on for every object a test creates; pytest's unraisable-exception check at exit still runs over them | Local A/B, 6 alternating runs each, same tree: CPU (user+sys, all processes) 19.3-20.4 s → 16.5-16.9 s at load ≈ 3; wall 6.7-6.9 s → 5.8 s; last worker exit → controller finish 0.5-1.0 s → 0.06 s. Red: `infra/tests/test_ci_domain_budget_gc_scenarios.py` → `{'enabled': True, 'frozen': 0, 'module_frozen': False}` per worker → green `1 passed` | Cuts CPU the runner spends, not tests or examples. Applies to every backend pytest run (developers' too). In `backend/conftest.py`, not a `-p` flag in ci.yml: `-p` counts as narrowing in the ADR 0049 guards, and `backend/tests/conftest.py` is a protected path |
| 2026-11-12 | sre-devops-engineer | **Kept: budget 10 s, `DOMAIN_TEST_PATHS`, `-m "unit and not red_until"`, default Hypothesis profile, every `max_examples`, `-n auto --dist worksteal`.** No test edited, skipped or moved | `infra/tests/test_ci_domain_budget.py` unchanged and green | The ticket rules and ADR 0049 rules 1-2 |
| 2026-11-12 | sre-devops-engineer | **Rejected for this PR: lazy imports of `alembic` (`racket.platform.db`), `boto3` (`racket.platform.storage`) and `psycopg.errors` (`racket.video_ingest.service`).** Together about 0.19 s of each worker's collection | `python -X importtime` on the domain collection: alembic 36 ms, boto3 81 ms, psycopg 69 ms cumulative | Product code owned by other lanes; `test_migration_failure_rolls_back.py` patches `db.command`, so a lazy alembic import changes a protected test. Worth a backend ticket if more headroom is needed |
| 2026-11-12 | sre-devops-engineer | **Rejected: a higher `DOMAIN_UNIT_BUDGET_S`, fewer examples, fewer workers, `-p no:...` plugins off.** | — | Policy (NFR-073), QA's fuzz depth (QA-R1-07), duplicated collection per worker, ADR 0049 narrowing guard |

## Result on CI (this PR)

Runner speed read from the serial property step of the same job, as in the trend table.

| Run (PR #235) | Commit | Domain step | Property step | Backend unit | Runner | Same-speed runners before (domain step) |
|---|---|---|---|---|---|---|
| 43295511747 | b1089ca | 8.2 s | 57.9 s | 15.1 s | slow | 9.2-9.3 s at 59-61 s |
| 43298772128 | 4aca7b0 | 8.0 s | 57.1 s | 15.4 s | slow | 9.2-9.3 s at 59-61 s |
| 43301588896 | 9c0b604 | 6.4 s | 46.8 s | 13.7 s | middle | 7.2-7.3 s at 43-44 s |

On slow runners the step drops 1.0-1.3 s (about 13%) to 80-82% of the budget; on a middle-speed runner 0.8-0.9 s to 64%; fast runners, scaled by the same CPU cut, land near 5 s (50%). **The ~70% target is met on fast runners and not on slow ones.** What is left is CPU the tests themselves need (Hypothesis generation, 6.7 of 7.5 s of serial test time) and each worker's start-up and collection (about 1.8 s of CPU, every worker collects all 1,862 tests).

| Date | Who | Decision | Evidence | Reasoning |
|---|---|---|---|---|
| 2026-11-12 | sre-devops-engineer | **`DOMAIN_UNIT_BUDGET_S` stays 10; this PR does not raise it.** Whether to buy the rest of the margin on slow runners with product changes (lazy imports, about 0.3 s there) or with a budget change is for the principal-engineer and the product owner (NFR-073 owner), not an SRE edit | Table above; ADR 0049 "Considered options" 5 | A higher budget changes NFR-073, which ADR 0049 rules out; the speed-up in this PR stands on its own |

## Review round 1 (principal-engineer, senior-qa-engineer; PR #235 at `d21558f`)

| Date | Who | Decision | Evidence | Reasoning |
|---|---|---|---|---|
| 2026-11-12 | principal-engineer, senior-qa-engineer | **Collect once when collection ends, then freeze (PE-235-01).** With the collector off during collection, collection's own cyclic garbage was frozen with the live objects: never collected and never finalized, so pytest's unraisable-exception check could not report a finalizer or `ResourceWarning` among it | Probe (unfreeze, collect, freeze at each worker's first test): 21,895 garbage objects frozen per domain worker at `d21558f`, 20 with the fix, on every worker in 2 runs each. One `gc.collect()` at the end of collection: 0.05 s per worker. Local A/B, 4 alternating runs each at load ≈ 4-5: CPU 17.3-17.9 s → 17.2-18.1 s, wall within the host's noise | The speed-up comes from not re-scanning the ~200,000 live objects; collecting the garbage once before the freeze keeps that and hides nothing from the exit-time checks |
| 2026-11-12 | senior-qa-engineer | **The probe scenario checks it (new step "no garbage that start-up or collection left behind is among the frozen objects", fewer than 1,000 per worker) and reads the pass count without an upper bound (QA-235-01, QA-235-02).** `1[0-9]{3} passed` would have failed once the domain suite reached 2,000 tests (1,861 today) | Red on `d21558f`: `assert 21895 < 1000`; green with the fix | A fixed digit count is a time bomb; the floor of 1,000 still proves the whole suite ran |
