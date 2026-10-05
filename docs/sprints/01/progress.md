# Sprint 1 progress

- **Owner:** engineering-manager (with the product-manager for scope and PO items). Machine-readable status: [`status.json`](status.json) (ADR 0010 units; `implemented_units` and `dod_done_units` tracked separately per retro 0).
- **Plan:** [`../sprint-01.md`](../sprint-01.md). **Created:** 2026-10-05, on D1 (retro 0 action M2: the progress file exists from the first day).
- **Branch:** `sprint-01`. **Remote:** `nhuthuynh/racket-analytics` (created by the PO, 2026-10-05).
- **Process changes in force (ADR 0022, Accepted 2026-10-05):** one story = one commit (over 400 changed lines needs an EM waiver row in `decision-log.md`); review findings routed to their owner role; an integrated Compose + E2E smoke runs before review round 1; threat-model controls are story acceptance criteria.

## Preconditions (sprint-01 header)

| Precondition | Status | Evidence |
|---|---|---|
| PO ratified ADR 0002 and ADR 0007 (OQ-02) | Met | [ADR 0023](../../decisions/0023-product-owner-decisions-2026-10-05.md), 2026-10-05 |
| PO ratified ADR 0009 | Met | ADR 0023. Rules stories proceed under the (a)/(b) split; the only preset stays `PROVISIONAL-UNVERIFIED` and provisional rows stay `@needs-verification` because the rulebook files (OQ-01) are not yet supplied |
| Sprint 0 DoD met, or carry-over re-sized | Open | Carry-over listed in `status.json` `carry_over_from_sprint_00` (sprint-report §8); not counted in the 32 committed units |

## Committed stories and planned units (ADR 0010: XS 0.5, S 1, M 2, L 4)

Priority confirmed by the product-manager on 2026-10-05 (Sprint 1 DoR item P1): every committed story is P1 for this sprint; MoSCoW is taken from the FRs in sprint-01 §14.1 (all Must, except FR-004 inside ST-015, which is Should). ST-019 is stretch (Should).

| Story | Lanes (size → units) | Planned units | Status | Implemented units | DoD-done units | External evidence (owner) |
|---|---|---|---|---|---|---|
| ST-013 | BE M 2, FE S 1 | 3 | implemented | 3 | 0 | CI run (SRE); security + design reviews; SEC-R4-S1-01 (ADR 0032, ST-013b) and ASVS 6.3.3 (ADR 0031, PO) open |
| ST-014 | FE S 1 | 1 | implemented | 1 | 0 | CI run; security review; WebKit PD-R1-04 (S-09) |
| ST-015 | FE M 2 | 2 | implemented | 2 | 0 | CI run; design review; WebKit PD-R1-02 (S-09). Coach sign-off done |
| ST-016 | FE L 4, BE S 1 | 5 | implemented | 5 | 0 | CI run; design review; participant-model doc P4 (PE) |
| ST-017 | BE M 2, FE M 2 | 4 | implemented | 4 | 0 | CI run; WebKit/iOS run (OQ-17); BE counted in review round 2 (TCR 32 decided; 157/157 upload tests green, isolated run at `351488e`) |
| ST-018 | BE M 2, FE S 1 | 3 | implemented | 3 | 0 | CI run; security review; caps from ST-025 (P11) |
| ST-020 | BE L 4 | 4 | implemented | 4 | 0 | CI run; PE review |
| ST-021 | BE S 1 | 1 | implemented | 1 | 0 | CI run; PE review |
| ST-022 | QA M 2 | 2 | implemented | 2 | 0 | CI run; first nightly oracle run (S-08). Mutation baseline 0.8654 (`33e6146`); property/oracle tests 28/28 green |
| ST-023 | QA M 2 | 2 | implemented | 2 | 0 | CI run; coach review |
| ST-024 | SRE M 2 | 2 | implemented | 2 | 0 | CI run; nightly workflow ran on GitHub |
| ST-025 | ML M 2 | 2 | blocked | 0 | 0 | Real phone clips from the PO (blockers.md); security review |
| SPIKE-06 | FE S 1 | 1 | partial | 0 | 0 | Real iOS Safari / Android Chrome devices (not in sandbox) |
| **Committed** | BE 12, FE 12, QA 4, SRE 2, ML 2 | **32** | | **29** | **0** | Capacity 12.8 per lane at load factor 0.8 |
| ST-019 (stretch) | FE S 1 | 1 | implemented | 1 | 0 | CI run; design review (scenario bound in 073d3f3) |

Counting rule (2026-10-05 sprint close, QA-R3-04; same text as `status.json` `counting_rule`): a lane counts as implemented when its code is committed, review rounds have been held, and its own tests are green in the latest **isolated** run (ADR 0030) without depending on an undecided test-change row. Backend at `cf8cd19` on its own `RA_DEV_STATE` Postgres and object store: `3 failed, 1060 passed, 6 skipped` (nightly x1, phone fixtures x2, both open blockers). Lanes by total: BE 10/12, FE 11/12, QA 2/4, SRE 2/2, ML 0/2. Not counted: ST-017 BE (green only through Pending TCR row 32(a), disputed in QA-R3-01), ST-022 (no mutation baseline, no nightly run), ST-025 (real phone clips), SPIKE-06 (real devices). DoD-done stays 0: there is no green CI run on any head with the Sprint 1 fixes. Sprint report: [`sprint-report.md`](sprint-report.md).

## Open items that need the human product owner (ADR 0023)

| Item | Effect while open | Need-by |
|---|---|---|
| OQ-01: supply the 2026 USAP rulebook and change-document PDFs | Presets stay `PROVISIONAL-UNVERIFIED`; rows `@needs-verification`; "unofficial scoring" label | Sprint 3 planning, 2026-11-16 |
| OQ-05: jurisdictions named 2026-10-05 (US and AU, ADR 0023 note); legal review covering both recorded as an ADR | No real-user beta (none planned) | Before any real-user beta |
| OQ-13: name the monthly beta budget amount | NFR-022 alerts have no base | Sprint 2 review |
| OQ-20: recruit testers, interviewees and a second coach | NFR-036 and QD-AN-03 cannot be tested | Sprint 3 planning |
| Retro A1: branch protection on `ci-gate`, labels, `ANTHROPIC_API_KEY` secret | No story can reach full DoD without a green GitHub run | 2026-10-14 |

## Log

| Date | Step | Outcome | Evidence |
|---|---|---|---|
| 2026-10-05 | PO answer: "accept all recommendations, repo created …, push and start sprint 1" | ADR 0023 written; ADRs 0001, 0002, 0003, 0004, 0006, 0007, 0009, 0015, 0022 set to Accepted with dated notes; ADR 0010 PO-time note; `open-questions.md` statuses updated; decision-log index updated | `git show --stat` of the product-manager commit (see `git log -- docs/decisions/0023-product-owner-decisions-2026-10-05.md`) |
| 2026-10-05 | Sprint 1 started on branch `sprint-01`; this file and `status.json` created | 32 units committed (BE 12, FE 12, QA 4, SRE 2, ML 2) + 1 stretch | `python3 -m json.tool docs/sprints/01/status.json` → valid; unit sums asserted when generated |
| 2026-10-05 | senior-qa-engineer: Sprint 0 carry-over and Sprint 1 tests first | 6 Sprint 0 test-change rows decided, weak IT-00-10 probe and 21 stale `red_until` markers retired, test report rewritten and signed; Sprint 1 red-first tests for ST-013..ST-025 committed (ST-023 tables first), status in `test-plan-status.md` | `env -u APP_ENV uv run pytest -q -m "not red_until" tests` → `503 passed` (Compose, 0 skipped); `-m red_until` → `113 failed, 9 passed, 1 skipped, 8 errors`; Playwright Sprint 0 `7 passed`, Sprint 1 `37 failed, 6 skipped` |
| 2026-10-05 | senior-backend-engineer (stream B): ST-016, ST-013 (+ ST-014 BE), ST-017, ST-018, R3-04 | Commits `bcdc7d0` (ST-016 participants, 422 `fields`), `deea4e3` (ST-013 magic link, rolling rate limits, `send_sign_in_link` stage, ADR 0027 Proposed, `Clear-Site-Data` on sign-out), `78902e0` (ST-017 checksum/expiration/quota, read-model `upload`, `/upload-policy`), `1d099e5` (ST-018 `UploadPolicy`, 413/415, probe refusal, `rejection`), `efbe3a9` (R3-04 `Tus-Resumable` on 405/500). Every story's own IT and scenarios are green except test defects filed for QA. **Next/open:** 8 test-change rows Pending (QA); EM waivers for 3 commits >400 lines (decision-log); SRE Compose wiring for the mail worker and new env vars (blockers.md); PE amendments for §2.4 (rolling window), §6.5 (check order), §8 (dev defaults) | `env -u APP_ENV uv run pytest -q tests` (private Postgres, SeaweedFS, Mailpit) → `19 failed, 963 passed, 6 skipped, 9 errors`: 4 failures are other lanes (nightly `status.json`, phone fixtures), the other 15 failures + 9 errors are the filed test-change rows (error-body keys, allowlist, Tus-Extension, quota vs multi-upload tests, `flows.percent`, non-video payloads in Sprint 0 tus tests). `uv run ruff check src tests` → all passed; `uv run ruff format --check src tests` → 217 files formatted; `uv run mypy` → no issues in 75 files |
| 2026-10-05 | engineering-manager: status refresh (QA-R1-03) | `status.json` and this table updated from the commits and a fresh local run: 23 of 32 committed units implemented, 1 stretch unit, 0 DoD-done | `cd backend && env -u APP_ENV uv run pytest -q` → `18 failed, 1020 passed, 16 skipped, 9 errors` (all Pending TCR rows or open blockers, same set as smoke.md); `cd web && pnpm exec vitest run` → `244 passed`; `python3 -m json.tool docs/sprints/01/status.json` → valid; `cd infra && uv run pytest -q tests/test_nightly_quality.py` → `15 passed` |
| 2026-10-05 | engineering-manager: sprint close (review round 3 was the last iteration) | 25 of 32 committed units implemented (78%), 1 stretch unit, 0 DoD-done. 16 round-3 findings open (2 blockers, 14 majors) and escalated to the PO. Sprint report, retro and ADR 0030 written | Isolated backend run at `cf8cd19` → `3 failed, 1060 passed, 6 skipped in 139.76s`; `cd web && pnpm exec vitest run` → `251 passed`; `cd infra && uv run pytest -q` → `245 passed`; `list_workflow_runs` → total_count=2, no run after `2390e9a` |
| 2026-10-05 | engineering-manager: status step, sprint-close review round 2 (ADR 0030; PE-R2-S1-03, QA-R2V-09) | `status.json` and this table re-derived from the round-1 fix commits (`17c850d`..`afb0e23`) and an isolated run at `351488e` (`RA_DEV_STATE=.local/em-r2`: backend 3 failed (PO-blocked S-07 x2, S-08), 1075 passed, 6 skipped; web 269 passed; infra 292 passed). 29 of 32 committed units implemented (ST-017 BE and ST-022 now counted), 1 stretch unit, **0 DoD-done: no story is Done** (no green CI run on any head with the Sprint 1 fixes). Stale `open` items removed (PD-R1-01/03/05/07, TCR 32, PE-R3-01/02/03, PD-R3-01/02/03, SEC-R3-S1-02/03, mutation baseline). Sprint goal not demonstrated |
