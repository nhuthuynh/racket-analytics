# 0055. Goal verification starts only after the last build ticket merges; every method is dry-run live in its own configuration first; evidence PRs are merged, never closed unmerged

- **Status:** Accepted (the engineering-manager is R/A for sprint process, working-agreement §4). Applies from Sprint 5 planning. The human product owner may veto it at the Sprint 4 review on 2026-12-11.
- **Date:** 2026-10-29 (Sprint 4 close, retro 4, ticket RETRO-04)
- **Deciders:** engineering-manager
- **Consulted:** senior-qa-engineer and sre-devops-engineer (VERIFY-04-r3 and SMOKE-04 findings), orchestrator (the 2026-10-18 closing comments on #134-#138)
- **Related:** ADR 0033 (rule 2: method authors dry-run every goal method before the verifier), ADR 0047 (rule 1: rounds in series), ADR 0050 (rule 4: a verification round's PR merges before the next round). Retro `docs/retros/2026-12-11-sprint-04.md` (M1, M2, M3).

## Context and problem statement

Sprint 4 ran three verification rounds. Rounds 1 and 2 started on 2026-10-18, while 10 or more build tickets were still unmerged. Both rounds, their smoke PRs and eight FIX-04 PRs were closed unmerged the same day as "premature" (#115-#121, #134-#138). This broke ADR 0050 rule 4, and the only code fix in them (#137, a cheaper `GET /me/plan` read) was lost. G04-02 (c) still fails on that read.

Round 3 ran after every ticket merged. Five of its ten "no" rows (G04-03, -07, -08, -09, -10), and part of G04-11, failed on measurement or configuration while the product behaved correctly:

- `live_privacy.py` was tested only against its own stub, which used a flat error body. The real API nests the code under `error`.
- The flag-on E2E specs were each run with only their own flag on.
- `infra/compose.yaml` forwards no Sprint 4 setting, so no method could start the flag-on stack with `make up`.
- Two method selectors (`junit_rate --require <marker>`, `test_it_04_*` names) do not match how the tests are named.

The scorecard's §6 dry-run table, which ADR 0033 rule 2 requires before verification, has one row: G04-01..03, run on 2026-10-17 with no stack (rc 2, "re-run on an isolated stack before VERIFY-04"). It was never re-run live, and G04-04..G04-12 have no row at all.

## Decision drivers

- PO standing rule: a goal counts only when measured live, so a broken method costs a whole round.
- Each round costs one to two agent hours and a full Compose build on a disk that sits near its 10 GB floor (judgment from the Sprint 4 decision files).
- Evidence that is not merged does not exist for the next round (retro 3 L8).

## Considered options

1. **Gate the first round on the build being merged, require a live dry-run row per method in the configuration it measures, and merge every evidence PR** (chosen).
2. **Keep early rounds and close them when they turn out premature.** Rejected: that is what Sprint 4 did, and it lost a code fix and two rounds of evidence.
3. **Let the verifier fix harness defects during the round.** Rejected: the verifier would then grade its own method (separation of duties). Method defects go to the method author as a FIX ticket.

## Decision outcome

Chosen: option 1.

1. **No goal verification round before the last committed build ticket of the sprint has merged into `main`.** The EM's status step lists the unmerged tickets; the orchestrator starts VERIFY-<nn>-r1 only when that list is empty, or when the PO waives the rule in writing.
2. **Every goal method has a dry-run row in the scorecard's §6 before round 1:** run live by its author against `main`, in the exact configuration it measures (flags on for a flags-on row, started by `make up` with only `infra/.env` changed), with the rc recorded. A method with no row is a blocker for the round, not something the verifier finds.
3. **A verification or smoke PR is never closed unmerged.** If its round turns out premature, its PR still goes through review and merge as history, or the next round's PR merges its commits on the same day. Any FIX PR opened from it either merges or is re-ticketed with a ledger row naming it.
4. **Configuration parity:** each setting added to `infra/env.example` is passed through `infra/compose.yaml` in the same PR. The sre-devops-engineer adds an infra test that checks this.

## Consequences

- Good: round 1 measures the product, not half of it. Method defects show up in the author's dry-run, a day before the verifier's round.
- Good: no evidence and no fix is lost between rounds.
- Bad: verification starts later in the sprint. Accepted: in Sprint 4 the early rounds were thrown away anyway.
- Bad: a few more PR reviews for history-only evidence PRs.

## Confirmation

At the Sprint 5 close: VERIFY-05-r1 starts after the last build merge (EM status-step row). §6 of the Sprint 5 scorecard has one live dry-run row per method. No `VERIFY-05-*` or `SMOKE-05` PR is closed unmerged. The env-to-Compose parity test is in `infra/tests`.

## Evidence

- `list_pull_requests state=closed`: #115-#121 closed 2026-10-18T04:41Z; #134-#138 closed 2026-10-18T16:18-16:19Z, each `merged_at: null`. Comment on #135: "Closing as premature … The smoke test and verification will run again on main once every Sprint 4 ticket has merged."
- `docs/sprints/04/decisions/VERIFY-04-r3.md` rows for G04-03, G04-09/10, G04-07, the Compose gap, and G04-11 (a).
- `docs/sprints/04/decisions/QA-HARNESS-4b.md` row of 2026-10-17: "Dry-run … not yet possible live"; `sed -n '/## 6. Dry-run rows/,$p' docs/sprints/04/goal-scorecard.md` shows one row (G04-01..03, head `64b8f08`, no stack, rc 2).
- `grep -c FEATURE_ infra/compose.yaml` → 0 at `b9d0dc3`.
