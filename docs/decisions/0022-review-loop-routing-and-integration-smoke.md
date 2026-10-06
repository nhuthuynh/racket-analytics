# 0022. Review loop: route findings to their owner role, smoke-test the integrated stack before review, one story per commit

- **Status:** Accepted (engineering-manager R/A for sprint process). The human product owner did not veto it and accepted it on 2026-10-05 (ADR 0023); it applies from Sprint 1 onward.
- **Date:** 2026-10-03
- **Deciders:** engineering-manager
- **Consulted:** findings and lane reports from senior-qa-engineer, senior-backend-engineer, sre-devops-engineer and security-privacy-engineer (review rounds 1-3)
- **Related:** working-agreement §5 and §7; ADR 0001; ADR 0010; ADR 0014; retro `docs/retros/2026-10-16-sprint-00.md` (M1, M2, M3, M4, M6)

## Context and problem statement

Sprint 0 used all 3 fix iterations and still ended with 4 blockers. Every one of them was a non-code item: sprint artifacts, QA approval of test changes, CI evidence, and the contract. These had been raised since round 1. Working-agreement §7.3 sends every finding to "the owning engineer", and that engineer cannot close artifacts owned by the EM, QA, the PE or a human.

Round 1 also found 3 blockers that appear only when the stack is integrated. Each lane had been green on its own private stack.

Finally, the work landed in two commits of about 15,000 lines each, so the PR-size and per-PR gates never applied.

## Decision drivers

- Small changes of about 100 lines; about 1000 lines is too large [EP/ENG-04].
- After two failed corrections, restart with a better prompt; do not repeat the loop unchanged [EP/ENG-24].
- Delegation briefs must not overlap and must name the done-check [EP/ENG-26].
- Deterministic gates over advisory prompts [DPA/AI-10].
- Sprint 0 data (Evidence table).

## Considered options

1. **Do nothing.** Keep §7 as written and let the EM chase non-code findings by hand.
2. **Owner routing plus an integration smoke plus a story-sized commit unit** (chosen).
3. **Add a fourth fix iteration** for non-code items.

## Decision outcome

Chosen option: **2**, because it removes the root causes M1, M2, M3 and M6 without raising the iteration limit.

1. **Routing (§7.3).** Each finding is routed by type, in the same round:
   - code goes to the owning engineer;
   - API contract and ADR amendments go to the principal-engineer;
   - test-change approval goes to the senior-qa-engineer;
   - sprint artifacts go to the engineering-manager;
   - environment, repo admin or legal items go to the human product owner via the EM.

   A finding that its addressee marks "not my lane" counts as an unrouted finding. That is an EM defect, not a fix-loop iteration.
2. **Integration smoke (§7.1a).** Before review round 1, the orchestrator runs these on the integrated tree and attaches the output:
   - a fresh-volume `docker compose up --wait`;
   - the full Playwright suite;
   - the backend suite with no ambient service variables.
3. **Commit unit (§5).** The orchestrator commits one story, or one PR-sized slice of a story, at a time. Anything over 400 changed lines needs an EM waiver recorded in the decision log.
4. **Threat controls as acceptance criteria (§7.3 note).** A threat-model control that names a story becomes an acceptance criterion with a red test in that story.

## Pros and cons of the options

### Option 1
- Good: no process change.
- Bad: Sprint 0 shows the outcome: 3 rounds spent, the same 4 items still open.

### Option 2
- Good: each finding reaches someone who can close it. Integration defects show up before review. The size gate and per-PR review become meaningful.
- Bad: more agent invocations per round (QA, PE and EM as fixers), at roughly 15x the tokens of chat for multi-agent work [DPA/AI-02]. The smoke needs Docker and costs minutes.

### Option 3
- Good: simple.
- Bad: it repeats a loop that failed twice, against [EP/ENG-24].

## Consequences

- Good: fewer repeated findings, and earlier detection of cross-lane breaks.
- Trade-offs accepted: higher token cost per round; more commits for the orchestrator.
- Follow-up: the Sprint 1 retro measures the share of repeated findings across rounds (target: 0) and how many integration defects round 1 still finds.

## Evidence

| Claim | Evidence | Type |
|---|---|---|
| The 4 round-3 blockers were non-code items open since round 1 | Round-3 findings R3-01, R3-02, QA-R3-01, QA-R3-02; round 1 QA-R1-08; review-rounds.md marks R2-03, R2-04 and QA-R2-01 "Not fixed (not my lane)" | data |
| Integration-only blockers in round 1 | QA-R1-01 (`PATCH /uploads/{id}` 404 on the web origin), QA-R1-02 (`up --wait` rc=1, worker `relation "jobs" does not exist`), QA-R1-03 (IT-00-10 in a job with no worker) | test result |
| Commit size | `git log --shortstat`: 1d10ec8 → 173 files, +15,020; 3492042 → 138 files, +15,280 | data |
| ~100-line PRs | [EP/ENG-04] | verified source |
| Restart after two failed corrections | [EP/ENG-24] | verified source |
| Routing table, smoke step, 400-line waiver | (judgment) | judgment |

## Confirmation

- The Sprint 1 review rounds contain no finding marked "not my lane".
- Every round-1 review input includes the smoke output.
- `git log --shortstat` for Sprint 1 shows no commit over 400 changed lines without a logged waiver.

## Notes
- **2026-10-05 (product-manager, recording the human product owner):** PO accepted ("accept all recommendations"); the "Sprint 1 only / may veto" qualifier is removed. Previous status line: "Accepted for Sprint 1 (engineering-manager is R/A for sprint process). The human product owner may veto it at the Sprint 0 review on 2026-10-16.". See ADR 0023.
