# 0046. Red-first E2E specs carry a `@red-until-<story>` tag; CI runs them in a listed, non-gating step with a stale-tag check

- **Status:** Proposed (sre-devops-engineer, 2026-10-07, Sprint 3 review round 2). The engineering-manager accepts or rejects it (blockers.md row of 2026-10-07, "The E2E job cannot be green on `sprint-03`…"). The senior-qa-engineer decides the TCR row that tags the specs.
- **Date:** 2026-10-07
- **Deciders:** engineering-manager (accept), senior-qa-engineer (TCR: the specs are QA-owned)
- **Consulted:** principal-engineer (PE-R1S3-07), senior-qa-engineer (QA-R1S3-07, the tag proposal in blockers.md)
- **Related:** sprint-02 §8 ("rows `red_until` a stretch story listed separately"); `scripts/ci/red_until_report.py` (W-01, the backend twin); retro 1 A2 (stale markers); ADR 0014 (test immutability); ADR 0022 (smoke before review); NFR-074 (no silent retries or skips)

## Context and problem statement

The backend gate selects `not red_until` and lists the red-until rows in a separate step whose report fails on a stale marker. Playwright has no such marker. QA writes the Sprint 3 E2E specs red first (E2E-03-01..06 and the timing spec), so they fail until their stories land. The CI `e2e` job therefore fails at every Sprint 3 head (24 failures across Chromium and WebKit in runs 37639459765 and 37640321145; 12 failed of 115 in Chromium at the pre-review smoke). As a result:

1. `ci-gate` cannot be green on any intermediate head (DoD "CI green at the head");
2. a real Sprint 0-2 E2E regression would be hidden in a job that is red anyway.

## Decision drivers

- Fail closed. A red-first test must not join the gate before its story lands, and it must not stay out of the gate after it.
- Same model as the backend (one rule for the team; `red_until_report.py` is already reviewed and tested).
- QA owns the specs (ADR 0014). SRE owns the pipeline.

## Considered options

1. **A Playwright tag `@red-until-<story>` (on the `test` or its `describe`); the gated step runs `--grep-invert "@red-until-"`; a second step runs `--grep "@red-until-"` with the JSON reporter; `scripts/ci/e2e_red_until_report.py` lists the results per story and fails closed** (chosen).
2. **`test.fail()` on the red-first specs.** Pros: built in, and a passing `test.fail()` already turns red. Cons: an expected failure counts as a pass in the gated run, so it hides *why* a test fails (a regression in the same spec looks the same). It also has no story id to list, and it is in effect `xfail`, which `pyproject.toml` forbids for the backend twin ("Never xfail").
3. **`test.skip()` until the story lands.** Rejected: a silent skip (NFR-074) with no stale check.
4. **A separate, non-required `e2e-red-first` job.** Pros: no tag. Cons: it needs a list of files kept in the workflow, and that list goes stale (a spec file mixes gated and red-first tests: `fe-minors.spec.ts`, `focus-after-decision.spec.ts`). It also has no stale check.
5. **Do nothing** (wait until every Sprint 3 story lands). Rejected: `ci-gate` stays red for the whole sprint and hides Sprint 0-2 regressions (the problem above).

## Decision outcome

Chosen option: **1**.

1. **Tag.** A red-first test, or its `describe`, has `{ tag: '@red-until-<id>' }`, where `<id>` is the story or finding it waits on (`ST-047`, `COACH-1`, `QA-R1S3-01`; pattern `[A-Z][A-Z0-9]*(-[A-Z0-9]+)+`). Only QA adds or removes tags, each change with a TCR row.
2. **Gated step.** `pnpm exec playwright test --grep-invert "@red-until-"`. Every other spec, Sprint 0-2 included, gates as before.
3. **Listed step.** `--grep "@red-until-" --reporter=json` (`PLAYWRIGHT_JSON_OUTPUT_NAME=../reports/e2e-red-until.json`). Playwright's rc is ignored there.
4. **Report** (`scripts/ci/e2e_red_until_report.py`, not ignored). It writes a per-story table to the step summary. It **fails** the job when a tagged test passes in any project (a stale tag: the story landed, so QA removes the tag and the test joins the gate), when nothing is selected, when a selected test has no story tag, when the report has top-level errors (for example a spec that does not compile), and with rc 2 when the report is missing or unreadable.
5. **Local runs** (smoke and E2E evidence) use the same two selections, so a local verdict and the CI verdict mean the same thing.

### Consequences

- Good: `ci-gate` can be green on an intermediate head, and a Sprint 0-2 E2E regression turns the job red on its own.
- Good: a story cannot land without its E2E test joining the gate, because the stale-tag check fails the job.
- Bad: the tagged tests run a second time (≈ 4 min of the 10 min Chromium run at the pre-review smoke). Accepted, the job has a 30 min timeout (judgment).
- Bad: as with the backend `red_until`, a tagged test that fails for a different reason (a regression inside a red-first spec) is not gated. That is the price of red-first, and the listed table makes it visible.
- **Until QA tags the specs,** the report fails closed ("no red-until E2E tests were selected"), and the gated step still runs the untagged red-first specs. The `e2e` job is therefore red until the TCR row is made. That is intended: no change to a QA-owned spec without a QA decision.

## Evidence

- Unit tests, red first: `cd infra && uv run --no-sync pytest -q -p no:cacheprovider tests/test_e2e_red_until.py` → `8 failed, 2 passed` before the script and workflow change (the two that passed are the rc-2 cases, which passed only because the script file was missing); `10 passed` after.
- `actionlint .github/workflows/ci.yml` → rc 0.
- Real Playwright 1.56.1, scratch spec (one gated test, a `describe` tagged `@red-until-ST-047` that fails, a test tagged `@red-until-ST-048` that passes, two projects): gated run `--grep-invert` → `2 passed`, rc 0. Listed run → rc 1. Report → table `ST-047 | 2 | 0 | 0`, `ST-048 | 0 | 2 | 0`, two "stale tag" lines, rc 1. After the stale tag is removed → "No stale tags.", rc 0, and the gated run has `4 passed`.
- Today's specs (`web/e2e`, no tags yet): `playwright test --list --grep "@red-until-" --reporter=json` → "No tests found"; report → "no red-until E2E tests were selected (fail closed)", rc 1.
