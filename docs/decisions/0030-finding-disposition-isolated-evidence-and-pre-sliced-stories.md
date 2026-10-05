# 0030. Review loop: every finding gets a disposition each round, evidence comes from isolated runs, and M/L stories are sliced before they are built

- **Status:** Accepted (engineering-manager is R/A for sprint process, working-agreement §4). Applies from Sprint 2. The human product owner may veto it at the Sprint 1 review on 2026-10-30.
- **Date:** 2026-10-05 (written at the end of Sprint 1's compressed session; the retro keeps the planned date 2026-10-30)
- **Deciders:** engineering-manager
- **Consulted:** Sprint 1 review-round findings from principal-engineer, security-privacy-engineer, senior-qa-engineer and principal-designer (rounds 1-3); lane reports
- **Related:** ADR 0022 (which this extends and does not replace); ADR 0010; working-agreement §5 and §7; retro `docs/retros/2026-10-30-sprint-01.md` (M1-M5); `docs/sprints/01/sprint-report.md`

## Context and problem statement

ADR 0022 fixed Sprint 0's routing problem: in Sprint 1, findings went to their owner role and no finding was marked "not my lane". Sprint 1 still used all 3 fix iterations and ended with 2 blocker and 13 major findings open (`docs/sprints/01/review-rounds.md` round 3). Four causes repeat across the rounds:

1. **Findings without a disposition came back, or were silently dropped.** The round-1 and round-2 tables in `review-rounds.md` hold 11 of 31 and 10 of 16 findings. Five round-1 design **blockers** (PD-R1-01..05) never got a row and are still open at `cf8cd19`. For example, `MatchDetail.tsx` still has `!!file` in `showUpload`, so M-02 can show 'Video received' and 'Checking video…' together. Working-agreement §7.4 had reviewers re-check "only the changed lines and their findings". Code that was never changed therefore never got a second look. Round-1 minors that nobody fixed or deferred returned as round-3 majors: T-ML-5 and T-UV-10 had no tests (SEC-R1-S1-02/03, then SEC-R3-S1-03), the probe deleted the object before the commit (PE-R1-08, then PE-R3-02), the upload error had no support reference (PD-R1-08, then PD-R3-04). The contract §2.4 amendment, routed in the decision log, was never made (PE-R3-07).
2. **The EM's own status file was stale three rounds running** (QA-R1-03, QA-R2-04/PD-R2-05, QA-R3-04). The EM refreshed it only when a reviewer complained.
3. **Evidence from shared services was not reproducible.** Agents ran the backend suite on one shared dev Postgres and object store. The `db` fixture truncates every table and some tests compare the whole bucket, so identical runs gave different counts (PE-R2-03: 25 failed then 19 failed on the same tree; QA-R3-02; SEC-R3-S1-04). The sandbox disk reached 99% and SeaweedFS refused writes; review round 3 lost its E2E run to that (QA-R3-03, PD-R3-07).
4. **Commits over 400 lines were waived late or not at all.** 12 of 82 Sprint 1 commits exceed 400 changed lines. The EM recorded one waiver at commit time; six were requested and left undecided; four were never requested. ST-020 shows the alternative works: four slices, each under 400 lines and green on its own.

## Decision drivers

- A finding that is neither fixed nor explicitly deferred costs a later round more than it would have cost now (judgment, from the repeats above).
- Evidence must reproduce: the same command on the same tree gives the same result [EP/ENG-24].
- Small changes review better [EP/ENG-04].
- Rules must be checkable from the repo, not from memory (judgment; retro 0 L6).

## Considered options

1. **Extend the loop with four checkable rules: per-round disposition, an EM status step, isolated evidence with a disk check, and slicing at briefing time** (chosen).
2. Raise the iteration limit to 4. Rejected: round 3 had repeats, not new depth. A fourth round would repeat them again (judgment).
3. Let reviewers report only new findings in later rounds. Rejected: the repeats were real defects. Hiding them would have shipped them.
4. Drop the 400-line rule for whole stories. Rejected: [EP/ENG-04]. ST-020 shows that slicing works.

## Decision outcome

Chosen option: **1**.

1. **Disposition per finding, per round.** Every finding of round *n* has a row in `docs/sprints/<nn>/review-rounds.md` before round *n+1* starts. Each row has exactly one disposition: **fixed** (with evidence), **deferred** (to a named backlog row with an owner and a sprint), or **rejected** (with a reason the reviewer accepts). A finding that comes back without a row is an EM defect. Minors and nits may be deferred, never left blank. Reviewers re-check every earlier finding of theirs that is not fixed, deferred or rejected, not only the changed lines (working-agreement §7.4).
2. **EM status step.** Each fix round's last step is the EM refreshing `status.json` and `progress.md` from that round's commits and runs. Re-review starts only after that step.
3. **Isolated evidence.** A suite count used as evidence (smoke, review, status) must come from an isolated run: own `RA_DEV_STATE` Postgres and object store, or a fresh Compose project. The command line must show this. The smoke and every reviewer run start with `df -h /`, and need at least 10 GB free. If not, the SRE prunes stale images and build cache first.
4. **Slice at briefing time.** The EM's brief for an M or L story names its slices, each planned at 400 changed lines or less and green on its own. A waiver is decided **before** the commit and must already be in the decision log. An undecided waiver means the commit waits or is split.

## Pros and cons of the options

### Option 1
- Good: each rule targets a repeat seen in Sprint 1, and each can be checked with `grep` or `git log`.
- Bad: more EM bookkeeping per round (judgment).

### Option 2
- Good: more room to converge.
- Bad: the extra round would go to the same repeats; the cost is 1 round of 4 reviewers.

### Option 3
- Good: shorter reports.
- Bad: real defects would stay hidden.

### Option 4
- Good: fewer waivers.
- Bad: contradicts [EP/ENG-04]; Sprint 0's 15k-line commits were the result.

## Consequences

- **Good:** findings converge or are visibly deferred. Suite counts reproduce. Commit size is decided before code lands.
- **Trade-offs accepted:** each fix round gets one more EM step, and each M/L brief needs a slicing plan.
- **Follow-up work:** working-agreement §5 and §7 get dated notes (done with this ADR). The engineering-manager role file names the status step. The SRE adds the disk and isolation precheck to the smoke procedure (retro 1 action A5). QA makes tests assert only their own rows and keys (retro 1 action A2).

## Evidence

| Claim | Evidence | Type |
|---|---|---|
| 2 blocker and 13 major findings open after round 3 | `docs/sprints/01/review-rounds.md` round 3; the orchestrator's unresolved list (15 rows) | data |
| Round-1 blockers dropped without a row | `review-rounds.md` round 1 table: 11 rows of 31 findings; PD-R1-01..05 absent; code check at `cf8cd19` (`MatchDetail.tsx:84-89`, `globals.css` `.error-summary__list a`) | data |
| Round-1 minors returned in round 3 | SEC-R1-S1-02/03 → SEC-R3-S1-03; PE-R1-08 → PE-R3-02; PD-R1-08 → PD-R3-04; decision-log row 35 → PE-R3-07 | data |
| EM status stale in each round | QA-R1-03, QA-R2-04, PD-R2-05, QA-R3-04 | data |
| Identical runs differ on shared services | PE-R2-03: same tree `961648e`, 25 failed/15 errors vs 19 failed/9 errors; isolated DB → 3 failed, 1060 passed (SEC-R3-S1-04) | test result |
| Disk exhaustion broke E2E | QA-R3-03: `df -h /` → 99%; objectstore log `No more free space left` (46,908 lines) | test result |
| Commit sizes | EM, 2026-10-05: per-commit `git show --shortstat` over `c32b878^..HEAD` → 82 commits, median 152.5 changed lines, 12 over 400, maximum 2,111 (`722f0c5`) | data |
| Slicing works | ST-020: `77a5082`, `5999097`, `52953f0`, `131dcb7`, each under 400 lines, each green in a detached worktree (lane report) | data |
| Small PRs review better | [EP/ENG-04] | verified source |
| Evidence before claims | [EP/ENG-24] | verified source |

## Confirmation

- In Sprint 2, `review-rounds.md` has one disposition row per finding for every round, and no finding returns without a row.
- `git log --shortstat` for Sprint 2 shows no commit over 400 lines without a waiver row dated on or before the commit.
- Every suite count in `smoke.md` and `status.json` names an isolated run and a `df -h /` result.

## Notes
