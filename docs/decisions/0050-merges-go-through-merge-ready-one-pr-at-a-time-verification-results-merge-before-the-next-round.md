# 0050. Merges go through `merge_ready.py` one PR at a time and are audited after merge; each verification round's PR merges before the next round; finding ids use the ledger's id format

- **Status:** Accepted (the engineering-manager is R/A for sprint process, working-agreement §4). Applies from now (Sprint 4 planning at the latest). The human product owner may veto it at the Sprint 3 review on 2026-11-27.
- **Date:** 2026-10-15 (Sprint 3 close, retro 3, ticket RETRO-03)
- **Deciders:** engineering-manager
- **Consulted:** principal-engineer (findings F1/F2 in `docs/sprints/03/decisions/PE-R3S3-04.md`; root cause of PE-PR24-01 in `decisions/FIX-03-2b.md`), senior-qa-engineer and sre-devops-engineer (VERIFY-03-r1..r3 findings VM-R2-02, VM-R3-01, VM-R3-02)
- **Related:** ADR 0039 (rule 3: principal-engineer + senior-engineer verdicts on the head), ADR 0047 (rule 1: rounds in series), ADR 0037 (rule 1: reconciliation), ADR 0033; CI-PR-GATE (#5, `scripts/ci/merge_ready.py`); FIX-03-2b (#77, `scripts/measure/merged_verdict.py`); retro `docs/retros/2026-11-27-sprint-03.md` (M9, M10, M13)

## Context and problem statement

Sprint 3 shipped as 71 ticket PRs. Three process misses kept G03-12 from reaching 0 for five days after the product was done:

1. **Three PRs merged without the review rule on their merged head** (retro 3 M10). #24, #26 and #27 merged in one batch, 2026-10-08 20:12-20:14 UTC, about six hours after `merge_ready.py` reached `main`. #24 had the principal-engineer's latest verdict CHANGES REQUESTED (its round-2 review stayed PENDING); #26 had both APPROVE verdicts on the head before a docs-only commit; #27 had a principal-engineer and an sre-devops-engineer verdict, but no senior engineer. `merge_ready.py` would have refused each one.
2. **Verification results never reached `main`** (M9). VERIFY-03-r1 (#69), -r2 (#76) and -r3 (#81) each opened a docs PR that rewrote the same 12 scorecard cells. None was reviewed or merged, so each round's findings sat outside the ledger, and the PRs conflicted with each other.
3. **Verifier ids could not be counted** (M13). `V03R1-01` and its siblings do not match `measurelib._FINDING_ID`, and a ledger row without a parseable id makes `open_defects.py` exit 2. So nobody wrote the rows, and the major V03R1-01 stayed out of the count.

## Decision drivers

- The PO rules: merge only with both verdicts on the head and every CI job green (2026-10-07, 2026-10-08); separation of duties (orchestrator, 2026-10-09).
- A gate that a person or agent can skip will be skipped under time pressure (ADR 0047 context). The check has to run inside the merge step and again in the status step.
- Keep the cost low: both scripts exist and run in seconds.

## Considered options

1. **Merge step runs `merge_ready.py` per PR, status step audits with `merged_verdict.py`, verification PRs merge first, one id format** (chosen).
2. **GitHub branch protection with required reviews.** Not possible as the only control: all agents post through one account, so GitHub cannot tell the roles apart; the role is in the review body. Branch protection still requires `ci-gate` (CI-PR-GATE).
3. **Let the verifier write to `main` directly.** Rejected: the verifier would then merge its own result (separation of duties).

## Decision outcome

Chosen: option 1.

1. **One PR at a time through `merge_ready.py`.** The merge step runs `python3 scripts/ci/merge_ready.py --repo nhuthuynh/racket-analytics --pr N --sha <head>` immediately before each merge and merges only on rc=0. No batch merges: the next PR's check starts after the previous merge returns.
2. **Post-merge audit in every EM status step.** The EM runs `python3 scripts/measure/merged_verdict.py --repo nhuthuynh/racket-analytics --pr N --role principal-engineer --role <the senior role>` for every PR merged since the last status step, and writes an Open ledger row (major) for any rc=1, owned by the missing reviewer.
3. **The "senior engineer" of ADR 0039 rule 3 is a `senior-*` role.** The sre-devops-engineer, principal-designer and other roles may review too, but they do not replace the senior verdict. This is what `merge_ready.py` already checks.
4. **A verification round's PR is reviewed and merged before the next verification round starts** (extends ADR 0047 rule 1). The EM's reconciliation row of the round is part of that PR or of the next EM status step.
5. **Finding ids use the ledger's id format.** Every role writes ids that `open_defects.py` parses (for example `VM-R1-01`, `PE-PR24-01`); the EM rewrites a non-parseable id as an alias in brackets when reconciling, as RETRO-03 did.

## Consequences

- Good: the review rule holds on every merged head, and a miss is found within one status step instead of five days later.
- Good: each verification round's evidence is on `main` before the next round reads it, so rounds do not conflict.
- Bad: merges are serial (about one minute each). Accepted: 71 merges took seven days for other reasons.
- Bad: a verification PR needs reviewers. Its review is a docs review (one principal-engineer and one senior verdict), as for any ticket.

## Confirmation

At the Sprint 4 close: `merged_verdict.py` rc=0 for every Sprint 4 PR; every verification round has a merged PR before the next round's start time; `open_defects.py` never exits 2 on the Sprint 4 ledger.

## Evidence

- `python3 scripts/measure/merged_verdict.py --repo nhuthuynh/racket-analytics --pr 27 --role principal-engineer --role senior-backend-engineer` → "senior-backend-engineer: no verdict review on PR #27", rc=1 (2026-10-15).
- `--pr 26 --role principal-engineer --role senior-qa-engineer` → both "APPROVE on b3ec328…, not APPROVE on 7974a9b…", rc=1.
- Merge times from `list_pull_requests state=all`: #26 20:12:33Z, #24 20:13:21Z, #27 20:14:02Z on 2026-10-08; PR #5 (CI-PR-GATE) merged 13:57:46Z the same day.
- Open verification PRs before RETRO-03: #69 (2026-10-10), #76, #81 (2026-10-15), each changing the same 12 rows of `goal-scorecard.md` §2.
- `open_defects.py` on a row whose first cell is `V03R1-01` → "severity row with no finding id", rc=2 (RETRO-03 decision row).
