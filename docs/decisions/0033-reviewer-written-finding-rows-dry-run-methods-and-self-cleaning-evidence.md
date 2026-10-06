# 0033. Reviewers write their own finding rows, goal methods are dry-run before handover, and evidence runs clean up after themselves and do not share E2E state

- **Status:** Accepted (engineering-manager is R/A for sprint process, working-agreement §4). Applies from Sprint 2. The human product owner may veto it at the Sprint 1 review on 2026-10-30.
- **Date:** 2026-10-05 (final Sprint 1 close, after goal verification round 3)
- **Deciders:** engineering-manager
- **Consulted:** Sprint 1 sprint-close review rounds 1-3 (principal-engineer, security-privacy-engineer, senior-qa-engineer, principal-designer) and goal verification rounds 1-3 (senior-qa-engineer, sre-devops-engineer)
- **Related:** ADR 0030 (extended, not replaced); ADR 0022; ADR 0014 (fail closed); working-agreement §7; retro `docs/retros/2026-10-30-sprint-01.md` (final close, M10-M14); `docs/sprints/01/goal-scorecard.md`

## Context and problem statement

ADR 0030 made a disposition per finding per round mandatory. Sprint 1's close showed four ways that the review and goal-evidence loop still lets things through:

1. **Findings that never reach the file.** Sprint-close review round 3 (at `fb9e7d6`) raised 16 new findings: 1 blocker, 7 majors and 8 minors. None of them got a row in `review-rounds.md` before goal rounds 1-3 ran. 14 round-2 minors had no row either. `open_defects.py` counts only rows, so G01-11 reported 11 open when the true number was 17 (`open_defects.py` at this close → 17). A rule that the EM reconciles findings against rows (ADR 0030 rule 1) failed because the findings lived only in the orchestrator's output.
2. **Goal methods that could not pass as written.** Four §4 methods had defects. Reviewers found them, not their authors: G01-02(b) ran without the Compose env (F-01, QA-V1-05); G01-09 selected the nightly test and ignored the pytest rc (QA-V1-06); G01-11's awk filter dropped every blocker (QA-V1-07), and the next parser missed `S-07`-style ids (PE-R2-S1-02); the flaky detector collapsed repeats into one outcome (QA-V1-01). Each cost a review round.
3. **Evidence stacks that never clean up.** Each verification round leaves about 4.6 GB of `racket-<round>-*` images. The session may not delete other rounds' images, so a fresh build landed at 6.1 GB free, under the 10 GB floor. G01-05 then measured 541.8 Mbit/s but ended at `disk_free_gb_end 9`, which makes the evidence invalid. G01-05 is the only metric besides G01-11 that is "no" (scorecard §8).
4. **Shared E2E state between concurrent agents.** Concurrent Playwright runs share `web/test-results`, and other agents' Compose up/down changes the host network. Both produced false reds (`ERR_NETWORK_CHANGED`, ENOENT on traces; QA-R3-E2E-02). That makes "0 flaky" unmeasurable while other stacks churn.

## Decision drivers

- A finding that is not in the file cannot be counted, so the default must be "open" (fail closed, ADR 0014).
- A method is only a method once it has run end to end [EP/ENG-24].
- Evidence must reproduce on the same tree (ADR 0030 rule 3).
- Rules should be checkable with `grep`, `git log` or a script (judgment; retro 0 L6).

## Considered options

1. **Four rules:** reviewers write their own Open rows; method authors dry-run every method; evidence runs remove their own images and isolate Playwright output under a lock; the EM status step also refreshes the PO-facing report (chosen).
2. Keep ADR 0030 and ask the EM to reconcile more carefully. Rejected: the reconciliation depends on the EM seeing the orchestrator's output, which is the step that failed.
3. Give every agent permission to prune all Docker images. Rejected: one agent could destroy another agent's running evidence. Removing only your own images is safe (judgment).
4. Run E2E evidence only on CI. Rejected for now: CI has run once in Sprint 1, and the PO standing rule asks for a live local stack.

## Decision outcome

Chosen option: **1**.

1. **Reviewer-written rows.** At the end of a review or verification round, each reviewer appends one row per finding to `docs/sprints/<nn>/review-rounds.md` under its own heading, with the disposition **Open**. The owner later adds a new row with the disposition. Because the reviewer's row says "Open", a finding with no owner row counts as open in G01-11. The EM status step (ADR 0030 rule 2) runs `open_defects.py` and states the count.
2. **Dry-run before handover.** The author of every goal-scorecard method runs it once end to end on an isolated stack before the scorecard goes to the verifier. The author records the rc and the would-be number in the sprint decision-log row that introduces the method. A method that cannot reach "yes" as written is fixed or explicitly waived before handover. A harness parser gets a red test for each id or report shape it must accept.
3. **Self-cleaning, isolated evidence.** Every evidence stack is torn down with `docker compose -p <own project> down -v --rmi local`. Every Playwright evidence run passes `--output <run dir>/pw-out`. Playwright evidence runs and Compose up/down for evidence take the lock `flock .local/evidence-e2e.lock` (SRE implements it, sprint-02 row C-05). Run `scripts/disk-precheck.sh` before any E2E evidence run (row C-23).
4. **PO-facing report in the status step.** The EM status step also updates `sprint-report.md` §1 (scorecard result, open count, PO items) whenever the scorecard or the open count changes. A dated note is not enough: the verdict section is rewritten (PE-R3R-04, QA-R3-DOC-01).

## Pros and cons of the options

### Option 1
- Good: each rule targets a defect seen at the Sprint 1 close, and each can be checked (`grep`, `open_defects.py`, `docker image ls`).
- Bad: reviewers spend a little more time writing rows; method authors need one extra stack run (judgment: about 30 minutes per sprint).

### Option 2
- Good: no new rule.
- Bad: the same failure mode stays.

### Option 3
- Good: maximum free disk.
- Bad: one agent could destroy another agent's running evidence.

### Option 4
- Good: perfect isolation.
- Bad: no local evidence, which is against the PO standing rule; CI availability has been 1 run per sprint.

## Consequences

- **Good:** G01-11 can no longer undercount through missing rows. Methods reach the verifier already able to pass. Disk use stays bounded per round. E2E flake measurements stop depending on other agents.
- **Trade-offs accepted:** E2E evidence runs are serialised, so goal rounds take longer in wall-clock time.
- **Follow-up work:** working-agreement §7 (steps 1a, 2 and 3c) and the engineering-manager role file are amended with dated notes (done with this ADR). The SRE implements the lock and the teardown in the scorecard template and in `docs/ops/disk-and-prune.md` (sprint-02 rows C-05, C-15, C-23).

## Evidence

| Claim | Evidence | Type |
|---|---|---|
| 16 new round-3 findings had no row | `grep -n 'PE-R3R-01\|SEC-R6-S1-01\|PD-R3V-01\|QA-R3-GATE-01' docs/sprints/01/review-rounds.md` at `6f6e44e` → no match | data |
| G01-11 undercounted | `open_defects.py` at `6f6e44e` → open 11. After this close's EM rows → open 17 | test result |
| The round-3 blocker is still in the code | `normalise_email('a\x00b@example.com')` → `'a\x00b@example.com'` (accepted); `git diff fb9e7d6 6f6e44e --stat -- backend/src web/src` → empty | test result |
| Methods failed as written | QA-V1-01, QA-V1-05, QA-V1-06, QA-V1-07, PE-R2-S1-02 (review-rounds sprint-close rounds 1-2) | data |
| G01-05 invalid on disk | goal-scorecard §8: 541.8 Mbit/s, `disk_free_gb_end 9`; image removal of other rounds denied; `racket-gv3-*` 4.6 GB left | test result |
| Shared Playwright state caused false reds | QA-R3-E2E-02: ENOENT under `web/test-results`; `net::ERR_NETWORK_CHANGED`; the same tests passed alone with `--output` (6/6) | test result |
| Evidence before claims | [EP/ENG-24] | verified source |

## Confirmation

At the Sprint 2 close, the EM checks all four rules:
- every reviewer heading in `review-rounds.md` has an Open row per finding;
- each scorecard method has a decision-log dry-run row;
- `docker image ls 'racket-*'` shows no image of a finished round;
- every E2E evidence command line shows `--output` and the lock.
