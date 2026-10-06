# Sprint 2 progress

- **Owner:** engineering-manager (with the product-manager for scope and PO items). Machine-readable status: [`status.json`](status.json) (ADR 0010 units; `implemented_units` and `dod_done_units` tracked separately).
- **Plan:** [`../sprint-02.md`](../sprint-02.md). **Goal scorecard:** [`goal-scorecard.md`](goal-scorecard.md). **Created:** 2026-10-05, at planning.
- **Branch:** `sprint-02`, based on `sprint-01` at `2b97fa0`. **Remote:** `nhuthuynh/racket-analytics`.
- **Process in force:** ADR 0022 (one story = one commit, owner-routed findings, smoke before review), ADR 0030 (a disposition per finding, EM status step, isolated evidence, slices planned and waivers before the commit), ADR 0033 (reviewer-written Open rows, dry-run every goal method, self-cleaning evidence, sprint-report §1 rewritten when the scorecard or the open count changes).

## Planning, 2026-10-05 (engineering-manager with product-manager, principal-engineer, business-analyst, senior-qa-engineer)

| Item | Result | Evidence |
|---|---|---|
| Branch | `sprint-02` created from `sprint-01` | `git checkout -b sprint-02` at `2b97fa0` |
| Retro 1 actions reviewed first | A1-A5 mapped into the plan (sprint-02 §0.3) | `docs/retros/2026-10-30-sprint-01.md` §9 |
| PO decisions applied | ADR 0023 and `po-input-2026-10-05.md`: accept all; US + AU; https dev stack, no insecure cookie; rules stay PROVISIONAL-UNVERIFIED, the sheet says "unofficial" (sprint-02 §0.2) | ADR 0023 note 2026-10-05 |
| Preconditions | ADR 0009 met; match-aggregate design not approved (D1); no api-sprint-02 (D2); no Sprint 2 flows (D2); DR-01 not held (D1) | sprint-02 §0.1; blockers.md row 2 |
| Capacity | Load factor 0.8, 12.8 units/lane. Committed BE 12.5, FE 12.0, QA 11.5, SRE 8.0, ML 2.0 = 46.0 units; stretch ST-035, ST-034, ST-038, ST-028b, ST-025, ST-033, ST-036; ST-042 to Sprint 3 | sprint-02 §2; decision-log rows 1-4 |
| Carried findings | 17 open Sprint 1 blocker/major families carried as Open rows | `python3 scripts/measure/open_defects.py docs/sprints/02/review-rounds.md` → rc=1, `open 17` |
| PO list | P1-P9 with dates sent on day 1 | blockers.md row 1 |
| Goal scorecard | 12 metrics G02-01..G02-12 with targets and live methods | `docs/sprints/02/goal-scorecard.md` |
| Harness | `taglib.py`, `tagcontract.py`, `live_tagging.py`, `tag_latency.py`, `pw_timings.py` with tests, red first | `cd infra && uv run pytest -q tests/test_measure_sprint02.py tests/test_measure_scripts.py` → 81 passed; commit `15c8836` (late size waiver, decision-log) |
| C-24 (EM) | Scorecard §4.0 documents the host-port remap for isolated stacks | goal-scorecard §4.0 |
| Disk | 11 GB free on `/` (floor 10 GB) | `df -h /` → `252G 28G 11G 73%`; blockers.md row 3 |

## Lane status

| Lane | Committed units | Implemented | DoD-done | Next |
|---|---|---|---|---|
| BE | 12.5 | 0 | 0 | C-01, C-02 red first |
| FE | 12.0 | 0 | 0 | C-03 |
| QA | 11.5 | 0 | 0 | QA-FUZZ (red before C-01), C-04, ST-041 |
| SRE | 8.0 | 0 | 0 | C-05, C-15, C-23, then W-01 |
| ML | 2.0 | 0 | 0 | ST-040 |
| **Total** | **46.0** | **0** | **0** | |

## Daily log

| Date | Agent | Did | Next | Blockers |
|---|---|---|---|---|
| 2026-10-05 | engineering-manager | Planning: sprint plan refined, scorecard and harness, carried findings, PO list | D1 briefs per lane (§3.2 order, slices) | P1-P9; design preconditions (D1-D2) |
| 2026-10-05 | senior-frontend-engineer | C-03 + C-35 fixed (live native run green). FE code for ST-027 (slices 1-3e), ST-028a, ST-029, ST-030, ST-031, ST-032 (corrections and decisions), ST-037, stretch ST-028b and minors C-20, C-21, C-30, C-36, C-37 (in part); WebKit family analysed (8/8 test defects, TCR row). Live native-stack runs (own Postgres/object store, production `next build`, Chromium): 6 rallies by taps and keys → sheet equals the reference rows; axe 0 serious/critical on T-01, K-01, S-01, H-01; no sideways scroll at 320/360 px; tag buttons ≥ 48 px; optimistic call 16-70 ms (n=6); correction confirmed 161 ms; undo restores the identical sheet; C-02 conflict rows kept and removable. Vitest 398 passed, lines 90.95%; lint, typecheck, build clean; first-route JS 110.9 KB | QA's E2E-02-0n specs and the Compose https stack for the goal evidence; ST-033/ST-034/ST-036 UI if BE and design land | SRE-MEDIA (playback), whole-match video route (PE/BE), `api-sprint-02.md` and `flows-sprint-02.md` not yet written (blockers.md) |
| 2026-10-06 | senior-backend-engineer | C-01 (`9bf41f0`) and C-02 (`4ba6f99`) red-first and "Fixed" before any new story; ST-013b (`019c551`, migration 0008); ST-026 (`292b417`, `e78e161`, migration 0009), ST-027 API (`423de28`¹, `54539a5`, `477c3bb`), ST-030 API (`477c3bb`), ST-031 (`af9837f`, `072d82f`, migration 0010 append-only trigger), ST-032 (`af9837f`, `9ebb848`), ST-037 API (`c949d70`, `ac5ca2c` whole-match `/video`). Minors: C-07, C-08, C-09, C-14, C-16, C-19, C-26, C-28, BE-PL-01 (migration rollback), QA-S2-FUZZ-01. Evidence: `tests/unit` 1253 passed (7.6 s); `tests/integration tests/regression` (dev-postgres, dev-objectstore, Mailpit) 405 passed, 2 skipped (Compose-only sandbox); QA Sprint 2 scenarios 28 passed; IT-02-01..12 and BOLA 229 passed (one flaky fuzz run, BE-QA-02); scorebook domain coverage 99% line. Live (local uvicorn, http): `live_tagging.py --runs 5 --corrections 50` 10/13 steps per run, all 13 with the harness `_code()` fix (BE-D1-01), corrections p95 15.9 ms; `tag_latency.py` 50 RPS p95 13.2 ms. ¹ slice 1a landed inside FE commit `423de28` (decision-log) | Stretch ST-035 (SOS rows now written by QA), ST-034, ST-038 after review round 1 (sprint-02 §3 stretch rule); C-25 after its TCR; C-17 with ST-038 | Design review D1 and `api-sprint-02.md` not done (blockers.md); BE-D1-01 (harness) and SRE-MEDIA for G02-01 step 10 over https |
| 2026-10-06 | engineering-manager | Planning re-check on the orchestrator's re-entry: `sprint-02` already exists (no new branch); plan (`4ef518c`), scorecard G02-01..G02-12 and lanes L1-L5 (sprint-02 §15) unchanged and confirmed; harness tests `cd infra && uv run pytest -q tests/test_measure_sprint02.py tests/test_measure_scripts.py` → 81 passed. Uncommitted SRE files in the tree (`.dockerignore`, `infra/docker/web.Dockerfile`, `scripts/ci/evidence.sh`, infra tests) and QA/EM `blockers.md` edits left to their owners | Lanes continue per §3.2 order | As above (D1 design review, `api-sprint-02.md`) |
