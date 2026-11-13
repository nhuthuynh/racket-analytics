# CI-SCHEDULED-RED decisions (sre-devops-engineer, 2026-11-13)

Ticket CI-SCHEDULED-RED (`ci_fix`, wave 0), story PRC-06, atomic item PRC-9.1. Review tier 1 (ADR 0056). Bounded context: platform/CI.

## Red first

Command: `cd infra && uv run pytest -q -p no:cacheprovider tests/test_scheduled_red.py tests/test_scheduled_red_scenarios.py` on the red-first commit (tests, feature, recorded payloads, stub field; no implementation).

Red: `22 failed, 6 passed`. The failures are for the right reason:
- `scripts/measure/scheduled_red.py` does not exist (`FileNotFoundError` / `can't open file`): the recorded payload of run 43007950254 produces no red line today.
- `merge_ready.py` on a green, approved stubbed PR with the recorded red scheduled CI run 43007950254 on `main` prints `merge-ready: yes (PR #7 at c2c2…)` and exits 0: the red scheduled run does not block the merge today.

The 6 that passed at red: the four "allowed" merge cases (they hold today and must keep holding: green scheduled run, Nightly-only red, dispatched fix) and the "unreadable payload exits 2" case (exits 2 today only because the script is missing; it binds the fail-closed path once the script exists).
