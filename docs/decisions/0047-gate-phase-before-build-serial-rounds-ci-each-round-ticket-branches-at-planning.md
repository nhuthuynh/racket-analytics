# 0047. Gates run before the build; review and verification rounds never overlap; CI runs at every round head; ticket branches exist from planning; agents never write PO decisions

- **Status:** Accepted (the engineering-manager is R/A for sprint process, working-agreement §4). Applies from Sprint 4 planning. The human product owner may veto it at the Sprint 3 review on 2026-11-27.
- **Date:** 2026-10-08 (Sprint 3 close, retro 3)
- **Deciders:** engineering-manager
- **Consulted:** Sprint 3 review rounds 1-3 (principal-engineer, security-privacy-engineer, senior-qa-engineer, principal-designer), verification rounds 1-3 (senior-qa-engineer, sre-devops-engineer), the lane results and blocker rows of every role
- **Related:** ADR 0037 (rule 1 hardened, rule 2 made a phase), ADR 0039 (rule 6 made workable), ADR 0033, ADR 0030, ADR 0022, ADR 0046; working-agreement §3, §5, §7; retro `docs/retros/2026-11-27-sprint-03.md` (M1-M6); `docs/sprints/03/sprint-report.md` §1.2

## Context and problem statement

Sprint 3's product works live: VR3 met 10 of 12 goal metrics on a fresh HTTPS stack, with every player-facing promise shown in real time. The goal still fails, for process reasons only:

1. **Review round 3 was never reconciled** (retro 3 M1). It ran at `fdeeb53` in parallel with verification round 1. Its 25 new ids had no row until the sprint close, so three goal rounds counted 3 open findings when the true count was 8. ADR 0037 rule 1 exists to prevent exactly this (retro 2 M1). It failed again because a round that runs in parallel with another one has no "before the next step" moment for the EM to act on.
2. **The gates ran after the build, not before it** (M2, M3). The 17 decider and design tasks were due D1-D3. PE-1/2/3, SEC-1, PD-1 and COACH-1 landed only in review round 1; the BA and PM DR-03 cells landed at the very end (`1433a92`). The build lanes stopped on 26 of 43 units, and the UI was then built in a goal round before DR-03 was held, with no PO waiver (ADR 0037 rule 2 breached; FE decision-log row of 2026-10-07).
3. **CI never ran at a head that the verifier measured** (M5). The push and dispatch belong to the orchestrator and SRE, but no round step contained them, so G03-09 (c) failed on that alone. The ADR 0046 stale-tag step would also fail at the close head by construction.
4. **The ticket-PR rule was adopted mid-sprint, but nobody operated it** (M6). ADR 0039 rule 6 says unbuilt work goes on `s3/<ticket>` branches from their base. The bases did not exist, so the goal-round slices went onto `sprint-03`. 0 ticket PRs were opened, and DoD-done is 0 for the third sprint in a row.
5. **An agent wrote a PO decision** (M7). The "Effective from Sprint 4" row in the PO record (`94cdb99`) was the agent session's text. It was retracted, but only after two reviewers found it.

## Decision drivers

- The PO standing rule: a goal counts only when it is demonstrated, and that includes the open-defect metric.
- Retro 2 already wrote rules for items 1 and 2. They failed at the points where the workflow had no step for them, so this ADR adds steps and checks rather than more advice (judgment).
- Keep the cost low: one extra phase at the start and one push per round.

## Considered options

1. **Five workflow rules with an enforcement point each** (chosen; Decision outcome).
2. **Restate ADR 0037 more strongly.** Rejected: it was already explicit, and it failed twice at the same point.
3. **A script that blocks the next round when the reconciliation is missing.** Wanted, but it needs the orchestrator to save the returned ids in a file the script can read. That is retro 3 action A5. Rule 1 below is the manual form until then.

## Decision outcome

Chosen: option 1.

1. **Rounds run one at a time.** A review round and a verification round never run on the same head at the same time. The EM's reconciliation row for a round (ADR 0037 rule 1) is the entry condition of the next round, and the verifier's brief includes the reconciliation log. A verifier that finds a finished round with no log row reports the open-defect metric as **not measurable**, not as a number.
2. **Gate phase before the build.** Sprint planning lists the gate tasks (design, contract, threat notes, decider cells, coach review), and the orchestrator runs them first, each with its brief. A build lane is briefed only on stories whose Definition of Ready is met, plus the stories that need no gate. A goal round may not route a story whose DoR gate is still open. It escalates to the PO for a waiver instead, and the waiver is recorded before the work starts.
3. **CI at every round head.** The EM status step of every fix round, and the step before every verification round, includes a fast-forward push of the sprint branch and a CI dispatch (PO P1 allows this for `sprint-*` branches). The run id goes in `ci-status.md`. A verification round with no CI run at its head reports the CI parts of the scorecard as not met, and it names the missing run in its first line.
4. **Ticket branches exist from planning.** When a sprint plan ships tickets as PRs (ADR 0039), the plan's ticket map names each ticket's base, and the orchestrator creates every base and ticket branch at planning. Lanes commit on their ticket branch. The sprint branch only takes merges from ticket branches. The ticket PR opens when its first commit is pushed. The principal-engineer keeps the map current at each round's status step.
5. **Agents never write PO decisions.** In `docs/requirements/po-input-*.md` and in ADR 0023 notes, a PO decision is quoted verbatim from the PO. Any agent text there sits under a heading that names the role and says "not a PO decision".

## Consequences

- Good: the open-defect count is true at every step, so the PO sees the real state, not a number that changes at the close.
- Good: the build starts on settled designs, so there is less rework and the "built before review" findings stop.
- Bad: the first day of a sprint is gates only, so some lanes idle for one step. This is accepted: in Sprint 3 they idled for more than one step anyway, while waiting on gates that ran late (judgment).
- Bad: more pushes and CI runs. Each takes 30-45 minutes of runner time (runs 37639459765: 31 min; 37643676432: 44 min).

## Confirmation

At the Sprint 4 close:

- `open_defects.py` equals the verifier's count in every round, and every round has a reconciliation log row before the next one starts.
- No Sprint 4 story is committed before its DoR gate is met, unless a PO waiver row comes first.
- `ci-status.md` has one run per round head.
- Every Sprint 4 ticket has a branch and a PR from its first commit.

## Evidence

- Review round 3: 25 new ids with 0 rows until the close; `open_defects.py` went from 3 to 8 after reconciliation (`docs/sprints/03/review-rounds.md`, "Sprint close: engineering-manager").
- Gate dates: `86d7839` (PE-1/2/3), `af3dd99` (SEC-1), `dc9e73a` (PD-1), `d59d156` (COACH-1) were all committed during review round 1. The DR-03 BA and PM cells landed in `1433a92` (2026-10-07 23:29 UTC). The UI landed in `d83ee1b`, `96044d9`, `1040cfb` and `cd8856f`, before DR-03 was held.
- CI: `actions_list` → the newest `ci.yml` run on `sprint-03` is 37643676432 at `09f1f67` (failure); origin `sprint-03` is `723bb7f`, while the local head is `c1fba6a`.
- Ticket PRs: `list_pull_requests state=all` → #1-#3 only; `list_branches` → no `s3/*`.
- The PO record: `git show 94cdb99` (author Claude) and the correction in `po-input-2026-10-05.md`.
