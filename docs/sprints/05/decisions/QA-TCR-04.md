# QA-TCR-04 decisions

Per-ticket decision file (working-agreement §3, "Daily sync"). Ticket: QA-TCR-04 "Decide TCR rows 11 and 14 (retro F2/E2)", story PRC-05 (carry-over F2), sprint-05 §4.1. Owner: senior-qa-engineer. Review tier 0 (ADR 0056).

"Rows 11 and 14" are the file lines the retro names (`awk -F'|' 'NR==11||NR==14{print $(NF-1)}' docs/sprints/04/test-change-requests.md`, retro 4 §12 E2/F2): the CI-DRAFT-SKIP row and the ST-062-part2 review-round-2 row, both dated 2026-10-18 and both `Pending (senior-qa-engineer)` at `origin/main` `6df095b5`. Both changes are already on `main`; these are after-the-fact decisions. Only the "QA decision" cell of each row is filled in (the file's append-only rule).

## Why TDD does not apply

This ticket changes two Markdown files and no code or test. Nothing executable is added, so there is no red test to write. The evidence is the re-run of the tests each row is about (below) and the doc checks.

## Decisions

| Date | TCR row (line) | Ticket | Change commits / merge | Decision | Evidence (command → result, at `origin/main` `6df095b5`) |
|---|---|---|---|---|---|
| 2026-11-03 | 11 | CI-DRAFT-SKIP | `cc896f59` (red commit), merged in #122 `48fb908c` | **Accepted** | `git diff cc896f59^ cc896f59 -- infra/tests/test_workflows.py` → the `== "always()"` assertion becomes a `startswith("always()&&(")` prefix check plus one comment; the `needs` assertion is unchanged. The prefix check alone is weaker, but the same PR added `test_ci_gate_stays_always_for_every_non_draft_event` (evaluates the whole condition with `workflow_if.evaluate` on ready PR, push, schedule and dispatch) and `test_every_ci_job_is_skipped_on_a_draft_pull_request`, so the check as a whole is stronger. `cd infra && uv run pytest -q tests/test_workflows.py tests/test_ci_draft_skip.py tests/test_ci_draft_skip_scenarios.py` → `37 passed, 1 skipped` (actionlint not installed). Mutation probe of `jobs.ci-gate.if` in `.github/workflows/ci.yml` (reverted after each run), `uv run pytest -q tests/test_workflows.py tests/test_ci_draft_skip.py`: `always()` → 3 failed; `always() && (github.event_name == 'push')` → 3 failed; `success() && (<draft guard>)` → 4 failed |
| 2026-11-03 | 14 | ST-062-part2 (review round 2: PE-062P2-R2-01, SQA-062P2-R2-01) | `3740583e` (red), `9877bb46` (green), merged in #128 `d7bce34f` | **Accepted** | `git diff --numstat 3740583e^ origin/main -- backend/tests/integration/test_it_02_10_json_string_fuzz.py backend/tests/unit/coaching/test_follow_through_schemas.py` → `39 2`, `57 0`; no change to either file after `9877bb46`. The only removed lines are the 2-line module docstring sentence, rewrapped into 3 (the row says "1 line rewrapped into 3"; immaterial). No existing `FIELDS` row, strategy, assertion or test changed; `_check_refused` adds `target.swap_url()` only under `route == "swap"`. Live on `scripts/dev-postgres.sh` + `scripts/dev-objectstore.sh`: `cd backend && uv run pytest -q tests/unit/coaching/test_follow_through_schemas.py tests/integration/test_it_02_10_json_string_fuzz.py` → `219 passed in 201.27s` (IT-02-10: 179, as the row states); `-k swap` on IT-02-10 → `9 passed`. The red commit `3740583e` records "IT-02-10 7 failed" before the fix, so the new row bites |

## Doc checks

| Check | Command | Result |
|---|---|---|
| No Pending row left | `grep -c Pending docs/sprints/04/test-change-requests.md` | `0` |
| Paths named in the decisions exist | `ls` of each path above | all exist |
| Commits named resolve | `git cat-file -t <sha>` for `cc896f59 48fb908c 3740583e 9877bb46 d7bce34f 6df095b5` | `commit` each |
| Table shape kept | every data row of the TCR file has 8 cells | yes |
