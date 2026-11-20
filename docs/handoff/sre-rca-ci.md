# RCA: racket-analytics CI keeps failing

Author: principal-engineer. Date: 2026-11-14. Investigation was read-only: nothing was pushed, labelled, reviewed or merged, and no settings were changed.
Method: Google SRE book, ch. 12 "Effective Troubleshooting" (Chris Jones). The steps are problem report, triage, examine, diagnose, test and treat, and cure. "Negative results are magic" is applied in section 3. Quotes from the chapter are marked "SRE12".
Raw data is not in this repository (see `CONTINUE.md` for where it is kept):
- `allruns.tsv`: all 2,479 workflow runs since 2026-10-05, from the REST API.
- `runclass.tsv`: failed runs by failure class.
- `domain_steps.tsv`: 45 timings of the domain-unit step on main.
- Job logs, saved as `j*.log`, `st085.log` and `gl.log`.

## 0. Problem report, restated

SRE12 says a report should give "the expected behavior, the actual behavior, and, if possible, how to reproduce the behavior". The PO's report gives neither the expected nor the actual behaviour, so I restate it:

- **Expected:** a ticket PR goes green on its first ready push. Main stays green. PRs merge within about a day of approval.
- **Actual:**
  - 205 failed runs since 10-05, 202 of them in the `CI` workflow.
  - Today's scheduled CI on main is red (pip-audit flags CVE-2026-126360).
  - The dependency-audit workflow failed.
  - 21 PRs are open, and some have been open since 11-03.
  - Sprint work is stopped.
- **Reproduction:** most failure classes reproduce exactly. Running the CI's own policy and doc scripts on the PR head gives the same verdict (section 3). The exceptions are external outages and timing.

## 1. Triage: stop the bleeding

SRE12: "Stopping the bleeding should be your first priority". It also warns: "Your first response ... may be to start troubleshooting and try to find a root cause as quickly as possible. Ignore that instinct!"

What is bleeding now, and why:

**B1. No PR can merge.** `merge_ready.py` refuses every PR "while the latest scheduled CI run on main is red" (`scheduled_reasons`, merge_ready.py:243). Today's scheduled run 43585233247 is red only on `pip-audit` (opentelemetry-api 1.45.1, CVE-2026-126360). Every PR CI also goes red on the same step until the lock moves.
- **Action:** review and merge **#268** first. It changes only `backend/uv.lock`, 9 lines in each direction. Its branch matches the `s06/ci-fix-*` bootstrap owner (sre-devops-engineer), so it does **not** hit the "no owner row" trap. I checked the owner resolution by reading the code and the owner file.
- **Prove the fix:** merge_ready also accepts a green `workflow_dispatch` CI run on the head. Then dispatch CI on main, so the scheduled-red block clears before the next 03:17 cron.

**B2. Do not restart the sprint runner until it has a circuit breaker for policy failures** (fix R2-a below). PR #226 (ST-085) shows the loop:
- It ran 7 consecutive red CI runs between 11-12 and 11-13.
- Each loop pushed another "re-confirm the PR-policy decision ... escalate the routing loop" docs commit.
- None of those commits could ever turn the gate green.
- Restarting the runner unchanged reproduces this on any PR that fails a gate no label can waive.

**B3. Unblock the two approved merges the user is holding: #236 (owner row), then #235 (domain budget headroom).**
- The 11-12 22:01 merge PUT was denied by the permission system, so a human has to do it.
- Until #235 merges, the domain-unit gate stays marginal (H6).

**B4. Freeze the four deadlocked PRs (#218, #220, #238, #239), and #201 and #226.** Do not let the runner retry them. The cause is structural, not code (H8, H9). Retrying spends CI minutes and agent calls and produces red runs. That inflates the failure signal the PO is reacting to.

**Preserve evidence:** SRE12 says "an emphasis on rapid triage doesn't preclude taking steps to preserve evidence". Keep `rca/` and do not delete the branches of #226 and #218-#239.

**Severity: moderate.** Main's code is not broken. The 15 red PR runs on 11-12 and 11-13 are 7 from one loop, plus process gates, plus one budget overrun. Today's red is external. This is a **delivery-pipeline outage** (no merges), not a quality collapse. Section 2 has the numbers.

## 2. Examine: observations and trend

### 2.1 Totals (all workflows, 2,479 runs)

| Workflow | Success | Failure | Cancelled | Skipped |
|---|---|---|---|---|
| CI | 520 | 204 | 238 | 242 |
| Claude review | 572 | 0 | 1 | 219 |
| Scheduled red-run notice | 48 | 0 | 0 | 356 |
| Nightly quality | 39 | 1 | 0 | 0 |
| Dependency audit | 15 | 1 | 0 | 0 |
| E2E repeat (flake triage) | 13 | 2 | 5 | 0 |

How CI breaks down by event:
- **pull_request:** 315 succeeded, 173 failed, 207 cancelled, 242 skipped (drafts).
- **push to main:** 173 succeeded, **6 failed**, 30 cancelled.
- **schedule:** 24 succeeded, 15 failed.
- **workflow_dispatch:** 8 succeeded, 10 failed (sprint-01..03 integration branches, October).

**Observation 1: "CI keeps failing" is about PR runs, not main.**
- 85% of CI failures (173 of 204) are on PRs.
- Main push has failed 6 times out of 179 completed runs.
- The 15 scheduled failures are mostly external: 8 consecutive pip-audit days (10-21 to 10-28), the 11-08 GitHub-releases 504 outage, and today's CVE.

### 2.2 Trend: the failure rate did improve and has been flat since W44

Conclusive CI runs (success + failure), plus first-push pass rate per PR branch:

| ISO week | CI fail rate (excl. cancelled) | PR branches | First-conclusive-run pass rate | Failures per branch | Cancels per branch | Re-attempted runs |
|---|---|---|---|---|---|---|
| W41 (10-05) | 43% | 74 | 42% | 1.26 | 2.0 | 18 |
| W42 (10-12) | 26% | 65 | 66% | 0.69 | 0.5 | 3 |
| W43 | 38% (n=13, idle) | 3 | 100% | 0 | 0 | 1 |
| W44 (10-26) | 14% | 32 | 84% | 0.22 | 0.1 | 0 |
| W45 (11-02) | 14% | 38 | 82% | 0.42 | 0.4 | 2 |
| W46 (11-09) | 18% | 35 | 80% | 0.34 | 0.3 | 2 |

**Observation 2:** the first-push pass rate went from 42% to about 80-84% and has **plateaued since W44**. The October fixes worked:
- dropping sprint integration branches (27,015-line PRs);
- counting only production code for PR size;
- skipping drafts;
- running the local size and immutability checks before push.

What remains is a stable floor of roughly 1 red in 5 PRs. Some of it is chronic (deadlocked PRs), and the rest comes in bursts (loops).

### 2.3 What fails: failure classes by run

From 203 failed CI runs, classified by failing job (`runclass.tsv`):

| Class | Runs where it was the **only** failure | Runs involving it |
|---|---|---|
| PR-policy gates (size, immutability, red-first, ledger, cost table) | **100** | 130 |
| Supply chain (pip-audit, gitleaks, SBOM, pnpm audit) | 17 | 26 |
| E2E / perf (Playwright, Locust) | 14 | 40 |
| Domain/backend unit time budget | 8 | 14 |
| Infra/CI-script tests | 6 | 20 |
| Lint/docs | 5 | 12 |
| Integration | 5 | 30 |

**Observation 3:** **64% of failing runs (130 of 203) involve a PR-policy gate, and in 49% (100) it is the only failing job.** These gates do not test whether the code works. They test the process: size, test immutability, history shape, ledger rows, cost table, decider cells.

### 2.4 "What touched it last": the dominant class each week is the newest gate

PR failure steps by week (`fail-all.tsv`), with the date each gate was added:

| Week | Dominant failure step(s) | Gate added |
|---|---|---|
| W41 | PR size 51, test immutability 24 | 10-03 (sprint 0) |
| W42 | PR size 25, immutability 9, **red-first 8** | red-first 10-17 |
| W45 | **doc check (decider cells, paths) 5, decisions-ledger 4**, infra tests 3 | reconcile_due on PRs, doc-check decider cells |
| W46 | **red-first 6** (one PR loop), doc 2, infra 2 | cost table 11-13 |

The gate machinery changes constantly:
- 66 commits to `ci.yml` and 89 to `scripts/ci/` in 6 weeks.
- 29 commits to `scripts/ci/` in W45-46 alone.

The runner's pre-push instruction still names only **two** of the eight PR-policy and doc checks: `check_pr_size.py` and `check_test_immutability.py` (sprint-runner-v4.js line 90). Red-first, the decisions ledger, the cost table, `check_docs.py`, the infra tests and gitleaks are not in it.

### 2.5 Other measurements

- **Runner loop, PR #226.**
  - The commits show two "test(ST-085)" commits that plant defects in `web/src`. `check_red_first.py` classifies those as code commits without a red step, so CI says "red-first: FAIL, 3 code commit(s) without a red step".
  - The check cannot be waived by label, and the runner forbids rewriting pushed history. So the PR can never pass.
  - The runner kept looping: ci-fix reported `policy_failure`, the policy step pushed a docs commit, a re-review ran, and CI ran again. Five "re-confirm the PR-policy decision" commits followed.
- **Author is also a required reviewer.**
  - `Gate.required()` returns `[principal-engineer, senior-qa-engineer, (+security, +specialists if tier 2)]` for every tier-1 and tier-2 PR. An APPROVE from the author's own role never counts.
  - Tickets owned by those roles: S05 has 6 QA + 2 PE + 4 SEC, and S06 has 5 QA + 2 PE + 1 SEC. That is **about 16% of tickets** (15 of 92) on tier 1 or higher that cannot merge, before counting specialist-owned tier-2 tickets (#218 senior-frontend, #238 coach).
  - `reviewersFor()` in the runner assigns the author's role as a reviewer anyway, and has no substitute.
- **Decider-cell gate (PR #201, PD-5).** CI fails until six *other* roles add dated decider cells to `flows-sprint-05.md`. The author cannot fix this, and #201 has been red and open since 11-03.
- **Labels restart full CI.** CI triggers on `labeled` and `unlabeled`, with `cancel-in-progress`.
  - 120 of 696 non-draft PR runs re-tested a SHA already tested (51 of those were cancelled).
  - Every waiver label restarts all 15 jobs, E2E included.
  - 238 cancelled CI runs in total. They show as grey or red on the PR, which adds to the "keeps failing" perception.
- **Domain-unit 10 s budget, 45 main push and schedule runs since 11-03.**
  - Step wall time: 5 s ×2, 6 s ×6, 7 s ×7, 8 s ×6, 9 s ×16, 10 s ×8.
  - So 24 of 45 runs are within 1-2 s of the kill, and 1 failed (11-12, 1c3b648).
  - Monitor log: the same code runs 5.6 s on fast runners and 9.2-9.9 s on slow ones.
- **External dependencies.**
  - 11-08: GitHub releases returned 504 for the syft and actionlint downloads, and 7 jobs failed in one scheduled run.
  - pip-audit was red for 8 days running in October with the runner idle. Nobody owned it.
  - Today: a new CVE was published overnight. dependency-audit could not open a PR because the "Allow GitHub Actions to create and approve pull requests" setting is off. I could not read it: the proxy blocks `/actions/permissions/workflow`. I am relying on the workflow log and #268's body.
- **Flakiness is now low.**
  - Re-attempted runs: 18 in W41, then 0-3 a week.
  - E2E-failing PR runs: 6 in W41, then 1-2 a week.
  - Only 1 SHA failed and then passed with no code change across all PR history.
- **Review integrity.** Every role posts as one shared GitHub account and is identified by a body line, `Reviewer: <role>`. On 11-12 21:46 one agent authored #236 and posted PE, QA and SPE APPROVE itself (monitor log). merge_ready cannot tell the difference. This does not make CI fail, but it weakens the gate that everything else relies on.
- **WIP leak.** The runner's WIP limit is 4 tickets per wave. A ticket that "fails out" after 5 attempts leaves its PR open. There are now 21 open PRs, each needing rebases, CI and re-reviews.

## 3. Hypotheses: test and treat

SRE12: "perform the tests in decreasing order of likelihood" and "Take clear notes of what ideas you had, which tests you ran, and the results you saw." For each hypothesis I name a test that could **disprove** it.

| # | Hypothesis | Evidence for | Disproving test | Result |
|---|---|---|---|---|
| H1 | Main's code is broken, so CI fails everywhere. | PO report; today's red scheduled run. | If main push runs fail often, or failures are spread across functional suites, H1 stands. **Test:** CI push on main shows 6 failures in 179 runs. Today's red is pip-audit only, on an unchanged lockfile, with an advisory published overnight. | **Ruled out.** A symptom that isn't relevant (SRE12 pitfall 1). |
| H2 | Failures got worse recently (11-12 and 11-13). | 15 failures on 11-12 and 11-13. | Weekly fail rate and first-push pass rate. **Test:** W44-W46 are flat at 14-18% and 80-84%. The 11-12/13 spike is 7 runs from one PR loop. | **Ruled out.** Better than October, flat since W44. |
| H3 | Agents push without running the same checks CI runs (the coordinator's pr-check premise). | Runner line 90 names only 2 policy scripts. Step 3 says "touched area" only. | Run CI's own scripts on the failing heads. If they pass locally, the failures are environmental. **Test:** the logs show deterministic script verdicts: "red-first: FAIL, 3 code commit(s)", "FAIL path: ... backend/.venv does not exist", the gitleaks finding in `infra/tests/test_backup_service_take.py`, and decisions-ledger misses. These reproduce on any machine. | **Confirmed.** In November, about 15 of 23 red PR runs would have been caught by running the CI's own policy, doc and lint scripts before push. |
| H4 | The in-flight `pr-check.sh` (branch s06/ci-fix-pr-check-local, unpushed) is enough. | It covers size, immutability, red-first, ledger, cost table, docs, ruff and unit tests. | Map it against November's failing steps. **Test:** it does **not** run `infra/tests` (20 failures all-time, 4 in November), mypy, gitleaks or the domain budget. The runner prompt never invokes it, and a hook can be bypassed with `--no-verify`. | **Partly ruled out.** Necessary but not sufficient. |
| H5 | PR-policy gates are designed to fail first and be fixed by a label afterwards. Size and immutability go red, a label is added, and the label restarts CI. | 130 of 203 failed runs involve policy. Label events trigger a full rerun. 120 same-SHA reruns. | If labels were applied before ready, policy would rarely fail in CI. **Test:** since the runner added the draft-first local check (W44+), size and immutability fell from 75 (W41) to 3 (W46). | **Confirmed historically, mostly treated.** Residual cost: full-CI reruns on label events. |
| H6 | The domain-unit 10 s wall-clock budget fails because of runner variance, not code. | 1c3b648 red at 10 s; 9.9 s before; 7 s locally. | If step times were tightly grouped well under 10 s, H6 would be false. **Test:** 45 main runs spread 5-10 s, 24 of them at 9 s or more. Same code, 5.6 s vs 9.9 s by runner. | **Confirmed, but a minor contributor** (12 failures all-time, 2 in November). #235 is a valid treatment, but it fixes the symptom. A wall-clock gate on shared runners will drift again. |
| H7 | E2E flakiness drives the failures. | 40 runs involve E2E/perf; the runner forbids calling "flaky" a cause. | If flaky, the same SHA would flip fail to pass. **Test:** 1 flip in all PR history. Re-attempts are 0-3 a week since W42. E2E failures are 1-2 a week. | **Ruled out for now** ("hanging on to past causes", SRE12 pitfall 3). It was real in W41. |
| H8 | The runner has no exit for a failure that cannot be fixed. It loops and pushes useless commits, which makes more red runs. | #226: 7 red runs and 5 "re-confirm" commits. Runner lines 123-125 call the policy step on every attempt, and any push triggers re-review and CI. | If the loop ended after one policy decision, #226 would show 1-2 red runs. **Test:** it shows 7, and the commit log shows the loop. | **Confirmed.** |
| H9 | Some PRs can never merge because the gate design makes them unsatisfiable. | merge_ready says "role never reviews own PR". #218, #220, #238 and #239 are deadlocked, and #201 needs six other roles' cells. | Read `Gate.required()` against the owner files. If no ticket owner were in the required set, H9 would be false. **Test:** QA and PE are always required. About 16% of tickets are owned by them, plus SEC and specialists on tier 2. | **Confirmed.** These do not fail CI often, but they block flow and keep PRs open forever. |
| H10 | The external supply chain causes main to go red: advisories and GitHub release downloads. | 11-08 504s; pip-audit red 8 days in October and today. | If the scheduled failures were in our code, H10 would be false. **Test:** logs show HTTP 504 from github.com/releases and a new CVE on an unchanged lock. | **Confirmed.** The amplifier is gate design: merge_ready blocks every merge on a red schedule, and the audit bot cannot open its PR. |
| H11 | Same-SHA reruns (label, ready, reopen) and `cancel-in-progress` inflate the red and grey count. | 238 cancelled; 120 same-SHA reruns. | Same-SHA reruns would rarely fail. **Test:** 10 of the 120 failed and 51 were cancelled. | **Confirmed as noise and waste.** Not a cause of red, but part of why it "keeps failing" in the UI. |
| H12 | Review integrity is weak: one shared account and self-attested role lines. | Self-approval incident on 11-12. | Can merge_ready tell an agent's own review apart from another role's? **Test:** it trusts the `Reviewer:` line from any trusted-association author, and all roles share one account. | **Confirmed as a risk.** Not a CI-failure cause, so it is outside this RCA's cure. Follow up as security. |

### Negative results (SRE12: "Negative results are magic")

These are recorded so nobody chases them again:
- **Main is not broken (H1).** Do not start a "fix main" hunt in the code.
- **No regression since W44 (H2).** The rate has plateaued, not got worse.
- **E2E flakiness is not the current driver (H7).** Do not spend this sprint on E2E stabilisation.
- **The domain budget is real but small (H6).** #235 helps, but it will not move the headline rate.
- **pr-check alone does not fix the loop (H4, H8).** #226's history was already pushed. A pre-push hook only helps *before* the first push. Unfixable gates still need a runner circuit breaker.

### Pitfalls avoided

- **Correlation vs causation:** "failures rose on 11-12 and 11-13" correlates with the restart after a week's pause and the sprint 6 kickoff. The cause is one PR loop plus newly added gates, not the restart.
- **Latching on to past causes:** E2E flake (an October cause) and the domain budget (the most recent main red) are not what drives the current rate.

## 4. Root causes: five-whys chains

SRE12 notes "there are multiple factors, each of which individually is not the cause, but which taken jointly are causes." Footnote 62 cites Hickam's dictum: "a number of common low-grade problems" can together explain the symptoms. That fits here. There are three causal chains and one shared systemic cause.

### RC1: the pre-push check is not the same as the CI gate

1. **Why** do about 1 in 5 PRs go red on first push? They fail deterministic gates: red-first, ledger, docs paths and decider cells, infra tests, gitleaks.
2. **Why** didn't the author catch them? The agent's pre-push procedure runs 2 of the 8 policy and doc scripts, plus "the suites of the touched area" chosen by each agent.
3. **Why** only 2? The runner prompt was written when only those 2 gates existed. Gates added later (red-first 10-17, ledger on PR, decider cells, cost table 11-13) were added to `ci.yml` but not to the prompt.
4. **Why** were they not added to both? There is no single source of truth that runs "exactly what CI runs" locally. Gates are versioned in the repo, but the agent loop is versioned outside it, in the runner file.
5. **Why** is that a problem now? Gate churn is high: 29 CI-script commits in W45-46. Each new gate creates a new failure class until the prompt catches up, and so far it never has.

**Systemic cause S1: the agents' definition of "ready to push" and CI's definition of "green" can drift apart, and nothing detects the drift.**

### RC2: the runner has no circuit breaker, and some gates cannot be satisfied

1. **Why** did #226 make 7 red runs in a day? Each loop pushed a docs commit, and each push re-ran CI on a head that still failed red-first.
2. **Why** did it keep pushing? The ci-fix and policy steps run on every attempt (up to 5), and any push triggers re-review and CI. The runner does not tell "fixable by a commit" apart from "not fixable by a commit".
3. **Why** was it not fixable? Red-first judges pushed history. No label waives it, and the runner forbids rewriting pushed history. The only fix, a replacement PR, is not a step the runner has.
4. **Why** is the same true of #218, #220, #238, #239 and #201? The gates require an approval from the author's own role, or sign-offs from six other roles. Neither the author nor the runner can produce them, and no substitute rule exists (ADR 0056).
5. **Why** are these not caught at planning? The planner assigns owners "by role fit" without checking them against `Gate.required()`. The gates were designed one at a time, without checking that every ticket shape can reach "mergeable".

**Systemic cause S2: gates and the agent loop are designed separately. Nobody checks that every gate has a reachable pass state for the actor who meets it, and the loop has no stop rule for a failure that cannot be fixed.**

### RC3: an external change freezes the whole pipeline

1. **Why** is main red today? A CVE was published overnight against the locked opentelemetry-api 1.45.1.
2. **Why** did it not self-heal? dependency-audit produced the bump but could not open the PR: the Actions PR-creation setting is off, and the branch `deps/security-audit` has no BOOTSTRAP owner.
3. **Why** does that stop all work? merge_ready blocks every PR while the latest scheduled run is red, and every PR's CI also runs pip-audit.
4. **Why** was the same thing red for 8 days in October? The "CI FIRST" duty only runs inside the sprint runner. When the runner is stopped, nobody owns a red scheduled run.
5. **Why** are external downloads fatal (11-08)? Tools (syft, actionlint) are fetched from GitHub releases at runtime with no cache and no retry.

**Systemic cause S3: gates are fail-closed on things the team does not control, and the automatic remediation and on-call ownership those gates assume do not exist.**

### Systemic cause: one level up

S1-S3 share one pattern. **Every retro adds a new fail-closed gate without designing the matching path that turns it green: the local check, the waiver or substitute rule, the runner step, and the owner.** "Gate added" is treated as done. SRE12's last section says it directly: "Problems in correctly representing the state of reality in a code change or an environment change often lead to a need to troubleshoot. Simplifying, controlling, and logging such changes can reduce the need for troubleshooting."

## 5. Brainstormed fixes, ranked

Impact is the share of red PR runs or blocked merges removed, from section 2. Effort: S is under half a day, M is 1-2 days, L is more.

### For RC1 (pre-push does not match CI)

| Rank | Fix | Impact | Effort | Notes |
|---|---|---|---|---|
| 1-a | **One generated entry point.** `scripts/pr-check.sh` runs every PR-scoped step of `ci.yml` that runs in under 2 minutes: policy ×5, docs, ruff, mypy, unit, **infra/tests**, **gitleaks**. Add a CI test (`infra/tests/test_pr_check_parity.py`, planned) that parses `ci.yml` and fails if a pr-policy, doc-check, infra-tests, lint or secrets step has no pr-check counterpart. | High (about 65% of November red PR runs) | M | This extends the in-flight item 2. The parity test is what stops drift (S1). Adding a gate without its local twin then fails CI on the gate PR itself. |
| 1-b | **The runner calls `make pr-check` and requires exit 0 before any push and before "ready".** Replace step 4 and the "ready" step text. Record the output in the PR body. | High (makes 1-a effective for agents) | S | A pre-push hook alone can be bypassed with `--no-verify`, and an agent may not install hooks. Do both. |
| 1-c | Gate freeze: no new fail-closed gate merges unless its PR includes the local twin, the waiver or substitute path, and the runner step. Make this a DoD row for CI tickets. | Medium (prevents the next class) | S | Process. |
| 1-d | Run the full CI on the draft head before ready, with drafts using a cheap subset. | Medium | M | This costs CI minutes. 1-a and 1-b are cheaper. |

### For RC2 (unsatisfiable gates and loops)

| Rank | Fix | Impact | Effort | Notes |
|---|---|---|---|---|
| 2-a | **Runner circuit breaker.** Classify each failed check as *code-fixable*, *label-decidable* or *structural*. Red-first on pushed history, author-is-required-reviewer and decider cells are structural. On structural, or on the same failing step twice on consecutive heads, stop. Make **no push**, write one escalation to EM/PO, and mark the ticket blocked. Never push a docs-only "re-confirm" commit. | High (removes loop bursts; 7 of the 15 red runs on 11-12/13) | S | Must land **before** the runner restarts (B2). |
| 2-b | **Substitute-reviewer rule** in ADR 0056 and `Gate.required()`. When the author is PE, use another senior plus EM. When the author is QA, use another QA-lens role, for example the senior peer running the QA lens. Also check at **planning**: reject an owner who is in the ticket's required set unless a substitute is named. | High for flow (unblocks #218, #220, #238, #239, about 16% of tickets) | M | Needs a PO decision (Q1). |
| 2-c | **Red-first fix path.** Either let the PR-policy step open a replacement PR from rebuilt history (a runner step), or allow `Red:` evidence in the PR body for test-only tickets that plant and revert defects. | Medium (#226 class) | S-M | Also teach the builder to run red-first locally before the first push (1-a), when history can still be rewritten. |
| 2-d | **Decider cells:** move them out of the PR gate into a non-blocking report, or make them a review-time check owned by the EM, not the author's CI. | Medium (#201, W45 doc failures) | S | |
| 2-e | Stop running full CI on `labeled` and `unlabeled`. Re-run only `pr-policy` on label events, then re-use the code jobs' result for the same SHA (gate on the latest result per job and SHA). | Medium (removes about 120 reruns and cancels; less noise) | M | |
| 2-f | Count WIP as open PRs, not wave tickets. Do not start a new ticket while 4 or more PRs are open. | Medium (flow) | S | |

### For RC3 (external fail-closed)

| Rank | Fix | Impact | Effort | Notes |
|---|---|---|---|---|
| 3-a | Merge #268 now. Turn on "Allow GitHub Actions to create and approve pull requests", or use a bot or GitHub App token with PR scope. Add `deps/security-audit` to BOOTSTRAP_OWNERS (owner: sre-devops-engineer). | High (today's outage; prevents a repeat) | S | The setting is a PO/admin decision (Q3). |
| 3-b | A **fix-forward window** in `scheduled_reasons`: a red scheduled run caused *only* by a newly published advisory on an unchanged lockfile blocks merges only after a 24-hour grace. Meanwhile it opens a P1 issue and lets the fix PR through. | Medium | M | Keeps the security intent and removes the global freeze for external causes. |
| 3-c | Cache or vendor CI tool binaries (syft, actionlint, gitleaks) with a checksum. Add retry with backoff on downloads. | Low-medium (11-08 class) | S | |
| 3-d | **A named owner for a red main outside sprints.** Today the monitor only reports. Give it a scheduled sre-devops task that opens the ci-fix PR within 1 hour. | Medium (stops week-long reds like 10-21 to 10-28) | S | |

### For H6 (domain budget)

- Merge #235 now as a patch.
- Then turn the budget into a ratio, or use the in-process pytest duration (`--durations` total excluding startup) against a 10 s target with warn at 8 s.
- Alternatively pin it to the `--json` elapsed time minus interpreter start. Effort: S.

### What "fixed" means

Measured weekly from the runs API with the script in `rca/`:
1. **First-ready-push CI pass rate for PRs: at least 95%**, from 80% in W46.
2. **Zero PRs with more than 2 consecutive red runs on the same failing step**, from #226's 7.
3. **Main scheduled red for no more than 24 hours.**
4. **Zero open PRs that cannot be merged by design**, from 6. **Median ready-to-merge time under 24 hours.**
5. **Cancelled plus same-SHA reruns under 10% of PR runs**, from about 34%.
6. **Parity test green:** every PR-scoped CI step has a pr-check twin.

## 6. Recommended order of work and owners

| # | Item | Owner role | Reviewer(s) | Done when |
|---|---|---|---|---|
| 1 | Merge #268 (CVE lock bump); dispatch CI on main | sre-devops-engineer (author); human merge | PE, QA, SEC (tier 2 lockfile) | Scheduled run green; merge_ready no longer blocks on schedule |
| 2 | Merge #236, then #235 | human (merge permission), EM | already approved | Domain step has 2 s or more headroom on slow runners |
| 3 | **Runner circuit breaker (2-a)**, plus WIP by open PRs (2-f), plus make the runner call `make pr-check` (1-b) | engineering-manager (owns the runner prompts) with sre-devops-engineer | PE | Replaying #226's history ends in one escalation and no push |
| 4 | Finish `pr-check` with infra/tests, mypy and gitleaks, plus the **parity test (1-a)**; ship the hook | sre-devops-engineer (in-flight branch) | QA, PE | Parity test passes; on the November failures, pr-check flags at least 15 of 23 |
| 5 | Triage the stuck PRs: replacement PR for #226; park #201 pending 2-d; park #218, #220, #238, #239 pending 2-b | engineering-manager | — | No PR open for more than 3 days without a named blocker owner |
| 6 | ADR amendment: substitute reviewer (2-b) plus a planning-time owner check | principal-engineer (author) | EM, QA, SEC, then **PO decision** | merge_ready tests cover the substitute rule |
| 7 | Audit bot: setting or token plus BOOTSTRAP owner (3-a); fix-forward window (3-b); out-of-sprint red-main owner (3-d) | sre-devops-engineer; security-privacy-engineer reviews 3-b | PE, SEC | Next CVE produces a PR automatically within 1 hour |
| 8 | Label events re-run only pr-policy (2-e); cache tool binaries (3-c); decider cells non-blocking (2-d) | sre-devops-engineer; principal-designer for 2-d | PE, QA | Metric 5 under 10% |
| 9 | Gate-change DoD (1-c): each new gate ships with its local twin, its pass path and its runner step | engineering-manager in working-agreement §7 | PE | Next retro gate follows it |
| 10 | Separate review identity (H12): per-role GitHub app or bot accounts, or signed verdicts | security-privacy-engineer | PE | merge_ready can tell roles apart cryptographically |

**Restart rule:** resume sprint work after items 1-4 are merged and the PO says go (`CONTINUE.md`; recommendation, not a PO decision). Items 5-10 run as CI-FIRST tickets in the restarted sprint.

## 7. Open questions for the PO

1. **Author-is-reviewer:** when the ticket owner is principal-engineer, senior-qa-engineer or a required specialist, which role substitutes? Or should those roles stop owning tier-1 and tier-2 code tickets?
2. **Red-first strictness:** may test-only tickets that plant and revert defects carry the red evidence in the PR body, or must the history always show a test-only commit first? Can the policy step open replacement PRs automatically?
3. **Repo settings and tokens:** may we enable "Allow GitHub Actions to create and approve pull requests", or provide a bot or App token, so the dependency audit can open its fix PR?
4. **Security gate scope:** is a 24-hour fix-forward window acceptable for a *newly published* advisory on an unchanged lockfile, instead of an immediate global merge freeze?
5. **Merge authority:** the merge PUT for #236 was denied by the permission system. Should the merge step be allowed to merge automatically when merge_ready exits 0, or does a human merge every PR? Today this is a hidden queue.
6. **Gate budget:** should we freeze new fail-closed process gates for one sprint, while parity and circuit breaker land, and make gate-cost (red runs caused per gate) a retro metric?
7. **Review identity:** do you accept the current shared-account, self-declared-role model, given the 11-12 self-approval incident?

## Limitations

- `merge_ready.py` was not executed against live PRs: the permission classifier denied it. The deadlock and owner conclusions come from reading `review_tiers.py`, `merge_ready.py` and the owner files on main.
- The repo Actions workflow-permission setting cannot be read through the proxy (HTTP 403).
- The 65% catch estimate for pr-check is a step-by-step mapping of the 23 November failed PR runs, not a replay.
