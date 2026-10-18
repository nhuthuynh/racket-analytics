# Sprint 4 review rounds

Every reviewer appends one row per finding under its own heading, with the disposition **Open**, as soon as it states the finding (ADR 0033 rule 1; ADR 0050 rule 5: ids in the ledger format `<ROLE>-<TICKET>-<nn>`, e.g. `PE-ST055-01`). Owners add a later row with the new disposition (Fixed with evidence, Deferred to a named backlog row, or Rejected with a reason). The engineering-manager writes the reconciliation row of each round before the next round starts (ADR 0037 rule 1, ADR 0047 rule 1). G04-12 counts the open blocker/major rows of this file **and** of `docs/sprints/03/review-rounds.md` (`scripts/measure/open_defects.py docs/sprints/03/review-rounds.md docs/sprints/04/review-rounds.md`).

## Carried from Sprint 3 (engineering-manager, planning, 2026-10-17)

The two Sprint 3 rows still open stay in the Sprint 3 ledger (they close there, in ticket C4-G12); they are listed here so the Sprint 4 count starts from the true number. `python3 scripts/measure/open_defects.py docs/sprints/03/review-rounds.md` → rc 1, `open 2` at `c170ef0`.

| Finding | Severity | Disposition | Owner (Sprint 4) | Waits on |
|---|---|---|---|---|
| PLAN-04-CARRY-01 | minor | Open (pointer row, not a defect): PD-R1S3-01 / QA-R3S3-06 (blocker) and EM-PR27-01 (major) are open in `docs/sprints/03/review-rounds.md` lines 524-525 and are counted there; ticket C4-G12 closes them | engineering-manager | C4-G12 |

## PLAN-04 (PR #87), review round 1

| Finding | Severity | Disposition | Owner (Sprint 4) | Waits on |
|---|---|---|---|---|
| PE-PLAN04-01 | major | Fixed (engineering-manager, 2026-10-17): OQ-05..OQ-08 recorded as PO-accepted (ADR 0023) in `po-input-2026-10-05.md`, ADR 0051, sprint-04, scorecard, blockers and roadmap; P16 is now the NFR-070 legal review; S4-DoD-P7 added for the side-out rule check; `decisions/PLAN-04.md` row | engineering-manager | — |
| QA-PLAN04-01 | major | Fixed (engineering-manager, 2026-10-17): scorecard §4 G04-03, G04-06, G04-07/08 and G04-11 rewritten to the scripts' real flags; each new form run at `c8ca483` (`decisions/PLAN-04.md` row) | engineering-manager | — |

## PLAN-04 (PR #87), review round 2

| Finding | Severity | Disposition | Owner (Sprint 4) | Waits on |
|---|---|---|---|---|
| QA-PLAN04-05 | major | Fixed (engineering-manager, 2026-10-17): scorecard §4 common setup is `GOAL=$PWD/reports/goal04`; `../$GOAL` dropped in G04-03 and G04-04; the `cd web` / `cd backend` sequence re-run at the fix (`decisions/PLAN-04.md` row) | engineering-manager | — |

## VERIFY-04 round 1 (goal verification on `main` at `3c4be05`, 2026-10-18)

Verifiers: senior-qa-engineer with sre-devops-engineer. Scorecard result: met 1 / 12 (`goal-scorecard.md` §7).

| Finding | Severity | Disposition | Owner (Sprint 4) | Waits on |
|---|---|---|---|---|
| SRE-V04R1-01 | major | Open: the verifier host cannot build the Compose stack (Docker daemon HTTPS proxy stale at `127.0.0.1:34223`; `docker compose … up -d --build --wait` → rc=1, `failed to resolve source metadata for docker.io/docker/dockerfile:1.7 … connection refused`); every live row of round 1 not run | sre-devops-engineer | orchestrator: daemon restart window (other agents' stacks run; live-restore off) |
| QA-V04R1-01 | minor | Open: scorecard §4 G04-03 `--require weakness_golden` / `--require plan_property` never match a JUnit test name, so `junit_rate.py` exits 1 although 9 of 9 and 1 of 1 pass | senior-qa-engineer | — |
| QA-V04R1-02 | minor | Open: G04-05 (e) safety grep → `pb.volley.line-volleys-no-step-in` (coach-reviewed, skill `footwork`, `safety_notes` empty) plus 5 draft `pb.fixture.*` drills; coach decides C5 and the method drops drafts | pickleball-domain-coach | — |
| QA-V04R1-03 | major | Open: domain suite with `tests/unit/coaching` 20.5-21.3 s > 10 s (NFR-073; `run_with_budget.py 10` → rc=124); `test_property_assembled_plans_keep_every_rule` 16.3 s; `ci.yml` `DOMAIN_TEST_PATHS` lacks `tests/unit/coaching` | senior-backend-engineer | sre-devops-engineer (`DOMAIN_TEST_PATHS`) |
| QA-V04R1-04 | major | Open: `mutation_score.py --target src/racket/coaching/plan --min-score 0.80` → 0.7036 (148 survived, 227 no tests), rc=1 | senior-backend-engineer | — |

