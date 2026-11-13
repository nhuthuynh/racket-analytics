# CI-SCHEDULED-RED decisions (sre-devops-engineer, 2026-11-13)

Ticket CI-SCHEDULED-RED (`ci_fix`, wave 0), story PRC-06, atomic item PRC-9.1. Review tier 1 (ADR 0056). Bounded context: platform/CI.

## Red first

Command: `cd infra && uv run pytest -q -p no:cacheprovider tests/test_scheduled_red.py tests/test_scheduled_red_scenarios.py` on the red-first commit (tests, feature, recorded payloads, stub field; no implementation).

Red: `22 failed, 6 passed`. The failures are for the right reason:
- `scripts/measure/scheduled_red.py` does not exist (`FileNotFoundError` / `can't open file`): the recorded payload of run 43007950254 produces no red line today.
- `merge_ready.py` on a green, approved stubbed PR with the recorded red scheduled CI run 43007950254 on `main` prints `merge-ready: yes (PR #7 at c2c2…)` and exits 0: the red scheduled run does not block the merge today.

The 6 that passed at red: the four "allowed" merge cases (they hold today and must keep holding: green scheduled run, Nightly-only red, dispatched fix) and the "unreadable payload exits 2" case (exits 2 today only because the script is missing; it binds the fail-closed path once the script exists).

## Decisions

| # | Decision | Why | Alternatives |
|---|---|---|---|
| 1 | Only the latest **scheduled CI** run blocks `merge_ready.py`; Nightly quality red is reported, not blocking | PRC-9.1 names "the latest scheduled CI"; Nightly publishes status and runs mutation/flaky trends whose red is a quality signal, not a broken `main` (judgment) | Block on Nightly too: rejected, outside PRC-9.1 |
| 2 | A PR whose head has a current, green `workflow_dispatch` CI run is exempt | `ci.yml`'s scheduled-only jobs also run on `workflow_dispatch` (`if: … schedule … \|\| … workflow_dispatch`); without an exemption the `ci_fix` PR for a red night could never merge (deadlock). The dispatched run proves the fix on the exact head | A label or a ticket-kind waiver: rejected, labels are the PR-policy step's and a waiver proves nothing |
| 3 | `merge_ready.py` reads `actions/workflows/ci.yml/runs?event=schedule&branch=main&status=completed` (one page); the report reads `actions/runs?event=schedule&branch=main&status=completed&per_page=30` for both workflows | Per-workflow listing cannot be crowded out by other workflows; a read error exits 2 (fail closed) | Paging every scheduled run: rejected, unbounded |
| 4 | No completed scheduled CI run listed → no block | A fresh fork or a renamed workflow has none; GitHub errors still fail closed (exit 2) (judgment) | Fail closed on an empty list: rejected, it would block every merge on a new repo |
| 5 | The rule lives in `scripts/measure/scheduled_red.py`; `merge_ready.py` imports `block_reason` | One rule for the status record and the gate, so they cannot disagree | Duplicate the rule: rejected |
| 6 | The recorded payloads are trimmed to the fields the rule reads (`gh api repos/nhuthuynh/racket-analytics/actions/runs/<id> --jq '{id,name,event,status,conclusion,head_branch,head_sha,path,workflow_id,run_attempt,created_at,updated_at,html_url}'`) | The full objects carry repository and actor blobs the rule never reads | Full payload: rejected, noise |
