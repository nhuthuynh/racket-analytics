# 0046. Red-first E2E specs carry a `@red-until-<story>` tag; CI runs them in a listed, non-gating step with a stale-tag check

- **Status:** **Accepted with one amendment** (engineering-manager, 2026-10-08, Sprint 3 close; PE-R3S3-05 / QA-R3S3-03; see Notes and the Amendment section, which PR #12 round 1 corrected). Proposed by the sre-devops-engineer on 2026-10-07 (review round 2). The senior-qa-engineer still decides TCR row 30.
- **Date:** 2026-10-07
- **Deciders:** engineering-manager (accept), senior-qa-engineer (TCR: the specs are QA-owned). **Consulted:** principal-engineer (PE-R1S3-07, PE-R3S3-05, PR #12 M1/M2), senior-qa-engineer (QA-R1S3-07, QA-R3S3-03, QA-PR12-01/03)
- **Related:** sprint-02 §8 ("rows `red_until` a stretch story listed separately"); `scripts/ci/red_until_report.py` (W-01, the backend twin); retro 1 A2 (stale markers); ADR 0014 (test immutability); ADR 0022 (smoke before review); NFR-074 (no silent retries or skips)

## Context and problem statement

The backend gate selects `not red_until` and lists the red-until rows in a separate step whose report fails on a stale marker. Playwright has no such marker. QA writes the Sprint 3 E2E specs red first (E2E-03-01..06 and the timing spec), so they fail until their stories land. The CI `e2e` job therefore fails at every Sprint 3 head (24 failures across Chromium and WebKit in runs 37639459765 and 37640321145). As a result, (1) `ci-gate` cannot be green on any intermediate head (DoD "CI green at the head"), and (2) a real Sprint 0-2 E2E regression would be hidden in a job that is red anyway.

## Decision drivers

- Fail closed. A red-first test must not join the gate before its story lands, and it must not stay out of the gate after it.
- Same model as the backend (one rule for the team; `red_until_report.py` is already reviewed and tested). QA owns the specs (ADR 0014); SRE owns the pipeline.

## Considered options

1. **A Playwright tag `@red-until-<story>`; the gated step runs `--grep-invert "@red-until-"`; a listed step runs `--grep "@red-until-"` with the JSON reporter; `scripts/ci/e2e_red_until_report.py` lists the results per story and fails closed** (chosen).
2. **`test.fail()`**: an expected failure counts as a pass in the gated run, so it hides *why* a test fails, has no story id to list, and is `xfail` by another name (`pyproject.toml`: "Never xfail").
3. **`test.skip()`** until the story lands: a silent skip (NFR-074) with no stale check.
4. **A separate, non-required `e2e-red-first` job**: a file list in the workflow that goes stale (`fe-minors.spec.ts` mixes gated and red-first tests), and no stale check.
5. **Do nothing**: `ci-gate` stays red for the whole sprint and hides Sprint 0-2 regressions.

## Decision outcome

Chosen option: **1**.

1. **Tag.** A red-first test, or its `describe`, has `{ tag: '@red-until-<id>' }`, where `<id>` is the story or finding it waits on (`ST-047`, `ST-047b`, `COACH-1`, `QA-R1S3-01`; pattern `[A-Z][A-Z0-9]*(-[A-Z0-9]+)+[a-z]?`, the backend twin's optional sub-story suffix). Only QA adds or removes tags, each change with a TCR row.
2. **Gated step.** `pnpm exec playwright test --grep-invert "@red-until-"`. Every other spec, Sprint 0-2 included, gates as before.
3. **Listed step.** `--grep "@red-until-" --reporter=json` (`PLAYWRIGHT_JSON_OUTPUT_NAME=../reports/e2e-red-until.json`). Playwright's rc is ignored there.
4. **Report** (`--specs web/e2e`, not ignored). It writes a per-story table to the step summary. It **fails** when a tagged test passes in any project (a stale tag: QA removes the tag and the test joins the gate), when nothing is selected (except under the amendment below), when a selected test has no story tag, and on top-level report errors (for example a spec that does not compile); rc 2 when the report is missing or unreadable. Failed, timed-out and skipped tagged tests are listed, not failed.
5. **Local runs** (smoke and E2E evidence) use the same two selections, so a local verdict and the CI verdict mean the same thing.

### Amendment (2026-10-08; PE-R3S3-05, QA-R3S3-03; corrected by PR #12 review round 1, M1 and QA-PR12-01)

When no spec carries a tag, the listed step selects nothing and the original rule 4 kept the `e2e` job red with nothing to wait on. Now the report counts `@red-until-` in every source file under `--specs` (specs **and** helpers, so a tag built from a helper constant counts). With 0 tags, a report that selected nothing and whose only error is Playwright's "No tests found" passes. The report is **always read**: a missing report is still rc 2, any selected test follows rule 4 (a passing one is a stale tag), and any other report error fails. With 1 or more tags an empty selection still fails (a broken grep or a renamed tag). Limit: a tag assembled at run time from pieces (no literal `@red-until-` in any file) is only caught when Playwright selects it, which rule 4 then checks.

### Consequences

- Good: `ci-gate` can be green on an intermediate head, and a Sprint 0-2 E2E regression turns the job red on its own. A story cannot land without its E2E test joining the gate (stale-tag check).
- Bad: the tagged tests run twice (≈ 4 of the 10 min Chromium run at the pre-review smoke; the job has a 30 min timeout, judgment). A tagged test that fails for another reason is not gated; the listed table makes it visible.
- Open (QA-PR12-05, senior-qa-engineer to decide): a skipped tagged test is listed in its own column and does not fail the job, as in the backend twin, so it can never turn stale.

## Evidence

- Unit tests, red first: `cd infra && uv run --no-sync pytest -q -p no:cacheprovider tests/test_e2e_red_until.py` → `8 failed, 2 passed` before the script (07); `3 failed, 11 passed` before the amendment; at the PR #12 round-1 fix, the new cases on the `797cfb3` script → `6 failed, 10 passed`; after → `16 passed`. `actionlint .github/workflows/ci.yml` → rc 0.
- Real Playwright 1.56.1, scratch project: a `describe` tagged `@red-until-ST-047` that fails and a test tagged `@red-until-ST-048` that passes → table `ST-047 | 2 | 0 | 0`, `ST-048 | 0 | 2 | 0`, two "stale tag" lines, rc 1. A passing test tagged through `helpers/tags.ts` → `797cfb3` report rc 0 (fail open), fixed report "stale tag, the test passes: ST-048", rc 1. Today's `web/e2e` (no tags): listed step → rc 1, report errors `['Error: No tests found']`; report with `--specs web/e2e` → "0 `@red-until-` tags … and none selected", rc 0.

## Notes

- **2026-10-08 (engineering-manager, Sprint 3 close): accepted, with one amendment.** The model is right: it is the twin of the reviewed backend `red_until` gate, and the alternatives (`test.fail()`, skips, a separate job) hide why a test fails or go stale. But the fail-closed rule on an empty selection has no exit: once every red-first spec lands, nothing carries a tag, the listed step selects nothing, and `ci-gate` is red by construction. That is the state at `c1fba6a` (`grep -rn '@red-until' web/e2e | wc -l` → 0; every E2E-03 spec passed in VR3). **Amendment:** the listed step first counts `@red-until-` tags in the spec files (a static grep). With 0 tags it prints "no red-first E2E spec is waiting on a story" and exits 0. With 1 or more tags and an empty selection it still fails closed, which is the case the rule exists for (a broken grep or a renamed tag). Owner: sre-devops-engineer, red first in `infra/tests/test_e2e_red_until.py` (a 0-tag case that passes and a tagged-but-unselected case that fails). TCR row 30 stays QA's to decide; with no red-first spec left, the expected decision is "no tag needed now" (judgment).

