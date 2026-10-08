# 0039. Sprint 3 tickets ship as ticket PRs, each reviewed by the principal engineer and a senior engineer before merge

- **Status:** Accepted (engineering-manager is R/A for sprint process, working-agreement §4). The human product owner may change the start date (blockers.md item P13); until they do, this ADR applies.
- **Bases confirmed:** principal-engineer, 2026-10-07, review round 2 (PE-R1S3-01, PE-R2S3-03): the ticket map below replaces the round-1 proposal, built and tested from `main` `259a0a8`.
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

### Ticket map (confirmed by the principal-engineer, 2026-10-07, review round 2; replaces the round-1 proposal)

The round-1 proposal could not be applied as written (PE-R2S3-03): `fee4fa3` (`fix(ST-044)`) changes `analytics/sheet.py`, which `a678a01` (T-ST-045) creates, and it changes the output that T-ST-049 freezes; `e54b754`, `8b451d9`, `15a7551`, `8d805d0`, `921ed53`, `d59d156` and `7a6ffe5` had no row. Almost every code commit also edits the shared record files, and several tests read files that only "docs" commits created (`docs/domain/metric-dictionary.md`, `docs/sprints/03/goal-scorecard.md`). The map below fixes all of this. It was **built and tested**, not only read (Evidence, last four rows).

**How a ticket branch is built (the orchestrator does exactly this).** `git worktree add --detach <dir> <base head>` (no branch switch on `sprint-03`), then, for each entry of the row in order:
- a bare SHA: `git cherry-pick -x -n <sha>`;
- `<sha> (only …)` / `<sha> (all but …)`: the same cherry-pick, then the paths outside (or inside) the list go back to the base state (`git checkout HEAD -- <path>`, or `git rm --cached` plus delete for a new file). This is a **path split** of a commit that spans tickets;
- `<path> as of <sha>`: `git checkout <sha> -- <path>`, committed on its own ("read by this ticket's tests");
- then, for every entry: **record paths** go back to the base state: `docs/sprints/02/**`, `docs/sprints/03/**`, `docs/design/**`, `docs/decisions/README.md`. T-S3-RECORDS carries them. Nothing else is dropped. A cherry-pick that conflicts outside the record paths stops the build: that is a map defect for the principal-engineer, not something to resolve by hand;
- commit with the original message plus `(cherry picked from commit <full sha>)`; an entry left empty (record paths only: `78644f3`, `d0ac61c`, `a200f1a`) is skipped and named in the PR body.

Then `git switch -c s3/<ticket>` **inside the worktree**, push, and open the PR into its base branch (`main`, or `s3/<base ticket>`, a stacked PR). When a base PR merges, GitHub retargets the next PR to `main`.

**Why one long stack.** File and import dependencies chain almost every ticket: the `analytics` pytest marker comes from `c371369` (T-ST-049), which T-QA-ACC-3 needs; `4d8af6d` (T-ST-053) edits `ci.yml` lines from `c7a6443` (T-ST-054); `8b451d9` edits files of `4d8af6d` and `c0fb6ad`; migration `0013` (`e54b754`) needs `0012` (`61dbdd5`), and the new migration `0014` of ST-046a needs both; the FE stories need the C3-03/C3-10/DR-02-FE screen changes and the QA E2E specs. Only four tickets have nothing above them that needs them, and they stay on `main`.

| Ticket PR | `sprint-03` commits (in order) | Base | Reviewers |
|---|---|---|---|
| T-SEC-RV3-02 | `9ca52fe`, `e7e86ef` | `main` | principal-engineer + security-privacy-engineer |
| T-HARNESS-3 | `75338b9` | `main` | principal-engineer + senior-qa-engineer |
| T-C3-01 | `1c1535d` | `main` | principal-engineer + senior-backend-engineer |
| T-C3-02 | `bd770f8` | `main` | principal-engineer + senior-frontend-engineer |
| T-ST-043 | `bd7593c` | T-HARNESS-3 | principal-engineer + senior-backend-engineer |
| T-ST-044 | `783cfd2` | T-ST-043 | principal-engineer + senior-qa-engineer |
| T-ST-045 | `a678a01` | T-ST-044 | principal-engineer + senior-qa-engineer |
| T-ST-044-b | `fee4fa3` | T-ST-045 | principal-engineer + senior-qa-engineer |
| T-COACH-1 | `d59d156` | T-ST-044-b | principal-engineer + senior-qa-engineer |
| T-ST-043-b | `921ed53`, `7a6ffe5` (only `test_metric_dictionary.py`) | T-COACH-1 | principal-engineer + senior-qa-engineer |
| T-ST-049 | `c371369`, `39f624a`, `7a6ffe5` (only 7 paths: `gm1-two-games.json`, `gm2-three-games.json`, `gm3-corrections-needs-decision.json`, `manifest.json`, `test_golden_an.py`, `statslib.py`, `test_measure_sprint03.py`) | T-ST-043-b | principal-engineer + senior-backend-engineer |
| T-QA-ACC-3 | `79ad8c3`, `979b23c`, `8880b55`, `5ffce1c`, `152c57c`, `de1b894`, `00430c4`, `8745dd5`, `ab0c279`, `20ad39e`, `5421ce7`, `99a711f`, `39eb73c`, `7a6ffe5` (only 4 paths: `test_it_03_02_stats_recompute.py`, `test_it_03_11_full_tag.py`, `full-tag.spec.ts`, `worked-example.reference.json`) | T-ST-049 | principal-engineer + senior-backend-engineer |
| T-ST-054 | `78644f3`, `d0ac61c`, `9c64d79`, `c7a6443`, `docs/sprints/03/goal-scorecard.md` as of `6f3bfce`, `6f3bfce` | T-QA-ACC-3 | principal-engineer + sre-devops-engineer |
| T-ST-053 | `70fa33f`, `1955d74`, `2408bff`, `bac3d81`, `b5cd5ac`, `f493c02`, `4d8af6d` | T-ST-054 | principal-engineer + senior-backend-engineer |
| T-ST-052a | `98f4c7c`, `8d805d0` | T-ST-053 | principal-engineer + senior-backend-engineer |
| T-QA-R1S3-11 | `15a7551` | T-ST-052a | principal-engineer + senior-backend-engineer |
| T-C3-04 | `c0fb6ad`, `8b451d9`, `09f1f67` | T-QA-R1S3-11 | principal-engineer + senior-qa-engineer |
| T-ST-048-tests | `47c34e8` | T-C3-04 | principal-engineer + senior-frontend-engineer |
| T-SRE-PURGE-a | `ecee023` | T-ST-048-tests | principal-engineer + senior-backend-engineer |
| T-ST-042 | `61dbdd5`, `a1bf473`, `e54b754` | T-SRE-PURGE-a | principal-engineer + sre-devops-engineer |
| T-C3-03 | `6059930`, `975338e`, `c5f7049` | T-ST-042 | principal-engineer + senior-qa-engineer |
| T-C3-10 | `954e7bd`, `984d1d4`, `3f13b05`, `e5324cc` | T-C3-03 | principal-engineer + senior-frontend-engineer |
| T-DR-02-FE | `a200f1a`, `1265966`, `9c18697`, `c2be16e` | T-C3-10 | principal-engineer + senior-qa-engineer |
| T-PE-DESIGN-3 | `86d7839`, `38b5da4`, `99d08e9` | T-DR-02-FE | author: principal-engineer; reviewers: senior-backend-engineer + security-privacy-engineer (a design PR cannot be approved by its author) |
| T-S3-RECORDS (last) | every commit not listed above (30 `docs(...)` commits, `ccc2fe9` first, all record or docs-only paths), plus the record-path parts of every commit above | `main` after every PR above has merged | principal-engineer + senior-qa-engineer |

**T-S3-RECORDS** is one commit made last: `git checkout <sprint-03 head> -- $(git diff --name-only main <sprint-03 head>)`, except `docs/sprints/02/test-change-requests.md`, where `main` has the QA decisions of `c4c66b1` for the same rows 24-28 that `1c1535d` decided on `sprint-03`. Those rows are merged by hand: keep `main`'s rows and append any sentence only `sprint-03` has. Confirmation: after it merges, `git diff main <sprint-03 head> --stat` lists only that file.

**Bases for the work not built yet** (the EM's slice brief, decision-log round 2): ST-046a, ST-050a and ST-052b start from **T-PE-DESIGN-3**, not from T-ST-045, `main` or T-ST-052a. Only that branch has the contracts and designs (ADR 0045), the coach's statuses, `longest_by_game`, QA's red-first ITs that the slices turn green, and migration `0013`. Their stacks are unchanged: ST-046a → ST-046b → ST-047-API; ST-050a → ST-050b → ST-051-API; ST-052b → ST-052c. FE stories (ST-047 UI, ST-048) start from the top of whichever backend stack they call, for their E2E.

**Commits after `99d08e9`.** Each one names exactly one ticket of this map, or a new ticket whose base row the principal-engineer adds here **before** the commit. A commit that edits a file another ticket created goes into a ticket stacked above that one. A commit that spans tickets is path-split here, as `7a6ffe5` is. A new build is committed on its `s3/<ticket>` branch (rule 6), not on `sprint-03`.

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
- **Follow-up work:** the principal-engineer confirmed the bases (review round 2, ticket map above). New size waivers are needed before the PRs open: T-COACH-1 (1,530 lines; 1,166 of them the coach's hand-count JSON), T-PE-DESIGN-3 (898), T-ST-042 (894; 797 waived), T-ST-054 (642, with the scorecard snapshot), T-ST-049 (641), T-ST-052a (466). Measured with the slice-brief command; the EM decides them. The orchestrator opens the PRs in the table's order. The EM tracks each PR's verdicts in `status.json` (`ticket_prs`). Retro 3 counts the missed rule.

## Evidence

| Claim | Evidence | Type |
|---|---|---|
| The start date was written by the agent | `git show 94cdb99` → Author: Claude; the row "Effective from \| **Sprint 4.**" | data |
| No Sprint 3 ticket PR exists | `mcp__github__list_pull_requests state=all` (2026-10-07) → #1 `sprint-01`, #2 `sprint-02`, #3 `hotfix/gitleaks-ignore`, all closed | data |
| Commits are interleaved on one branch | `git log --reverse --format='%h %s' ce91984..HEAD` | data |
| Every ticket branch builds from `main` (`259a0a8`) with no conflict outside record paths | `<scratch>/build.sh <scratch> 259a0a8` (the procedure above over this table) → all 24 rows `conflicts=[]`; empty entries only `78644f3`, `d0ac61c` (T-ST-054) and `a200f1a` (T-DR-02-FE) | test result |
| Every non-record path reaches its `sprint-03` state | `git diff --name-only <T-PE-DESIGN-3 head> 7a6ffe5 -- . ':!docs/sprints' ':!docs/design' ':!docs/decisions/README.md'` → only the files of T-SEC-RV3-02, T-C3-01 and T-C3-02 (checked equal blob by blob) and the docs of records-only commits (ADR 0039, 0043, `functional-requirements.md`, `po-input-2026-10-05.md`, `threat-model-sprint-03.md`) | data |
| Each ticket is green on its own (unit) | per worktree `cd backend && env -u APP_ENV uv run pytest -q -m unit` and `cd infra && uv run pytest -q -m unit`: every row passes, from T-SEC-RV3-02 (backend 1475 passed, infra 466) to T-PE-DESIGN-3 (backend 1670 passed, infra 567). `cd web && npx vitest run` on T-SEC-RV3-02 (458), T-C3-03 (465), T-C3-10 (472), T-DR-02-FE (477), T-PE-DESIGN-3 (477): all pass. `tests/regression/test_golden_an.py` on T-ST-049 → 31 passed | test result |
| The top of the stack is green with integration tests | isolated services (`RA_DEV_STATE=<scratch>/iso-top`, `dev-postgres.sh` + `dev-objectstore.sh`), T-PE-DESIGN-3: `uv run pytest -q -m "(unit or integration or scenario or regression) and not nightly and not red_until"` → 2349 passed, 24 skipped (Mailpit 18, Compose 5, P3 1) | test result |
| A cherry-picked fingerprint needs its commit in the repo | blockers.md row 2026-10-07 (PR #3, CI run 37629664958, `test_every_entry_names_a_commit_in_this_repository`) | test result |

## Confirmation

- `list_pull_requests state=all` shows one PR per ticket in the table, each with two "Verdict:" reviews (principal-engineer and a senior engineer) on its merged head SHA.
- `git log main` shows no merge of `sprint-03` itself.
