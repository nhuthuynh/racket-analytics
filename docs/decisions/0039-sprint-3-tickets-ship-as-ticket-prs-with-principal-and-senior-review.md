# 0039. Sprint 3 tickets ship as ticket PRs, each reviewed by the principal engineer and a senior engineer before merge

- **Status:** Accepted (engineering-manager is R/A for sprint process, working-agreement §4). The human product owner may change the start date (blockers.md item P13); until they do, this ADR applies.
- **Date:** 2026-10-07 (review round 1, Sprint 3)
- **Deciders:** engineering-manager
- **Consulted:** review round 1 findings PE-R1S3-01 (principal-engineer) and QA-R1S3-04 (senior-qa-engineer); `po-input-2026-10-05.md` addendum "Ticket-level PRs and reviews"
- **Related:** ADR 0022 (one story = one commit), ADR 0030 (dispositions, slices and waivers before the commit), ADR 0037 (human-gated items); `docs/sprints/sprint-03.md` §9; `docs/sprints/03/review-rounds.md` review round 1

## Context and problem statement

The PO's request, in their words: "each ticket in a sprint needs to have a PR, and each PR need to be reviewed by principle and senior engineers before merge and tested scenarios with integration and unit tests, and the ticket needs to be developed using TDD and DDD". It names no start sprint.

Commit `94cdb99` (author: the agent session, not the PO) recorded the rule in `po-input-2026-10-05.md` and added a row "Effective from | **Sprint 4.** Sprint 3 … ships as one sprint PR". That date is not in the PO's sentence, and nothing in the repository shows that the PO agreed to it (PE-R1S3-01, QA-R1S3-04). An agent cannot grant itself a deferral of a PO rule.

At `94cdb99`, Sprint 3 has no ticket PR: `mcp__github__list_pull_requests state=all` returns only #1 (`sprint-01`), #2 (`sprint-02`) and #3 (`hotfix/gitleaks-ignore`), all closed. All 68 Sprint 3 commits since `ce91984` went straight to `sprint-03`, with tickets interleaved.

## Decision drivers

- The PO's words are the rule. An agent-written start date does not count as PO consent.
- Nothing from Sprint 3 has reached `main` yet. Ticket PRs are still possible without rewriting history, because new branches from `main` take cherry-picks and `sprint-03` stays as it is.
- A review on a PR has to cover the code that merges. Review rounds on the sprint branch did not check each ticket's diff against `main`.

## Considered options

1. **Ship Sprint 3 as ticket PRs into `main`, each with a principal-engineer and a senior-engineer verdict before merge, and no sprint-wide PR** (chosen).
2. Keep the "Sprint 4" date and ship Sprint 3 as one sprint PR. Rejected: the PO did not give that date, and the EM may not defer a PO rule on its own. This option stays open to the PO only (blockers.md P13). If the PO confirms it in their own words, the EM records it and this ADR is superseded for Sprint 3.
3. Retroactively label the sprint review rounds as "the ticket reviews". Rejected: no reviewer saw a ticket's diff against `main`, and the rule says "PR … reviewed … before merge".

## Decision outcome

Chosen option: **1**.

1. **No sprint-wide merge.** `sprint-03` is not merged into `main` as one PR. It stays as the integration and evidence branch. Its history is not rewritten and it is not force-pushed.
2. **One branch and PR per ticket.** For each ticket in the table below, the owner (or the orchestrator for them) creates `s3/<ticket>` from current `main`, cherry-picks that ticket's commits in order (`git cherry-pick -x`, so each commit names its `sprint-03` original), runs the ticket's unit and integration tests and the CI jobs, and opens a PR into `main`. When a ticket needs another ticket's code, its PR is based on that ticket's branch (a stacked PR). Before any PR opens, the principal-engineer confirms the bases in the table.
3. **Reviews before merge.** Each PR gets a GitHub review from the **principal-engineer** and from a **senior engineer** in a different role from the author, each starting "Verdict: APPROVE" or "Verdict: CHANGES REQUESTED" (PO addendum). Each reviewer checks TDD (a test commit, or a red run, before the implementation), DDD (bounded context, ubiquitous language, a framework-free domain), and the Gherkin, integration and unit tests for the ticket. A PR merges only when both latest verdicts approve its current head SHA and `ci-gate` is green. Merging is done by the orchestrator or the human PO.
4. **Size.** A ticket PR over 400 changed lines needs a waiver row in the sprint decision log **before the PR opens** (ADR 0030 rule 4). The EM writes those rows with this ADR (decision log, 2026-10-07). A ticket that was already built in slices opens one stacked PR per slice group of at most 400 lines (T-ST-053, T-QA-ACC-3, T-ST-049), so the ticket is still reviewed as a whole: the last PR of the stack names the ticket and links the others.
5. **Secret-scan fingerprint.** A cherry-pick gets a new commit hash, so the `.gitleaksignore` fingerprint for `9ca52fe` does not match the cherry-picked copy. The `T-SEC-RV3-02` PR carries the synthetic key and an ignore entry for **its own** commit hash, guarded by `infra/tests/test_gitleaks_ignore.py` (which requires the commit to exist in the scanned repository). This is also what ends the red nightly on `main` (QA-R1S3-02): it merges first.
6. **Work that is not built yet** (ST-046/047/048/050/051/038, ST-052 b/c and the rest) is built on a ticket branch from `main` and opened as a PR from the start, not committed to `sprint-03` first.

### Ticket map (proposal; the principal-engineer confirms the bases before the first PR)

| Ticket PR | `sprint-03` commits (in order) | Base | Reviewers (principal + senior) |
|---|---|---|---|
| T-SEC-RV3-02 (first; ends the red nightly) | `9ca52fe`, `e7e86ef` (fingerprint re-made for the new hash) | `main` | principal-engineer + security-privacy-engineer |
| T-HARNESS-3 | `75338b9` | `main` | principal-engineer + senior-qa-engineer |
| T-C3-01 | `1c1535d` | `main` | principal-engineer + senior-backend-engineer |
| T-C3-02 | `bd770f8` | `main` | principal-engineer + senior-frontend-engineer |
| T-C3-03 | `6059930`, `975338e`, `c5f7049` | `main` | principal-engineer + senior-qa-engineer |
| T-C3-04 | `c0fb6ad` | `main` | principal-engineer + senior-qa-engineer |
| T-C3-10 | `954e7bd`, `984d1d4`, `3f13b05`, `e5324cc` | `main` | principal-engineer + senior-frontend-engineer |
| T-DR-02-FE | `a200f1a`, `1265966`, `9c18697`, `c2be16e` | `main` | principal-engineer + senior-qa-engineer |
| T-ST-042 | `61dbdd5`, `a1bf473` | `main` | principal-engineer + sre-devops-engineer |
| T-ST-043 | `bd7593c` | `main` | principal-engineer + senior-backend-engineer |
| T-ST-044 | `783cfd2` | `main` | principal-engineer + senior-qa-engineer |
| T-ST-045 | `a678a01` | T-ST-044 | principal-engineer + senior-qa-engineer |
| T-ST-053 | `70fa33f`, `1955d74`, `2408bff`, `bac3d81`, `b5cd5ac`, `4d8af6d`, `f493c02` | `main` | principal-engineer + senior-backend-engineer |
| T-ST-052a | `98f4c7c` | `main` | principal-engineer + senior-backend-engineer |
| T-SRE-PURGE-a | `ecee023` | `main` | principal-engineer + senior-backend-engineer |
| T-QA-ACC-3 (red-first tests) | `79ad8c3`, `979b23c`, `8880b55`, `5ffce1c`, `152c57c`, `de1b894`, `00430c4`, `8745dd5`, `ab0c279`, `20ad39e`, `5421ce7`, `99a711f` | T-HARNESS-3 | principal-engineer + senior-backend-engineer |
| T-ST-049 | `c371369`, `39f624a` | T-ST-044 | principal-engineer + senior-backend-engineer |
| T-ST-054 (so far) | `78644f3`, `d0ac61c`, `c7a6443`, `9c64d79` | T-QA-ACC-3 | principal-engineer + sre-devops-engineer |
| T-S3-RECORDS (plan, scorecard, smoke, records) | every `docs(...)` commit not listed above, `ccc2fe9` first | `main` | principal-engineer + senior-qa-engineer |

Commits made after `94cdb99` go into the ticket their message names.

## Pros and cons of the options

### Option 1
- Good: it follows the PO's words, and each merged diff is reviewed against `main` by the two roles the PO named.
- Bad: about 19 PRs, cherry-pick work, and a CI run for each one. The red nightly ends only when T-SEC-RV3-02 merges.

### Option 2
- Good: one merge and less work.
- Bad: it relies on a start date the PO never gave.

### Option 3
- Good: no extra work.
- Bad: it misstates what was reviewed.

## Consequences

- **Good:** Sprint 3 meets the PO rule before anything merges, and the record no longer claims a PO date the PO did not give.
- **Trade-offs accepted:** sprint-DoD-done stays 0 until ticket PRs merge. Each cherry-pick may conflict on shared record files (decision log, blockers, scorecard). Those files go in T-S3-RECORDS, which merges last.
- **Follow-up work:** the principal-engineer confirms the bases (EM brief, blockers row 2026-10-07). The orchestrator opens the PRs in the table's order. The EM tracks each PR's verdicts in `status.json` (`ticket_prs`). Retro 3 counts the missed rule.

## Evidence

| Claim | Evidence | Type |
|---|---|---|
| The start date was written by the agent | `git show 94cdb99` → Author: Claude; the row "Effective from \| **Sprint 4.**" | data |
| No Sprint 3 ticket PR exists | `mcp__github__list_pull_requests state=all` (2026-10-07) → #1 `sprint-01`, #2 `sprint-02`, #3 `hotfix/gitleaks-ignore`, all closed | data |
| Commits are interleaved on one branch | `git log --reverse --format='%h %s' ce91984..HEAD` | data |
| A cherry-picked fingerprint needs its commit in the repo | blockers.md row 2026-10-07 (PR #3, CI run 37629664958, `test_every_entry_names_a_commit_in_this_repository`) | test result |

## Confirmation

- `list_pull_requests state=all` shows one PR per ticket in the table, each with two "Verdict:" reviews (principal-engineer and a senior engineer) on its merged head SHA.
- `git log main` shows no merge of `sprint-03` itself.
