# Sprint 3 review rounds

Every reviewer appends one row per finding under its own heading, with the disposition **Open**, as soon as it states the finding (ADR 0033 rule 1; working-agreement §7 step 2). Owners add a later row with the new disposition (fixed with evidence, deferred to a named backlog row, or rejected with a reason the reviewer accepts). The last row naming an id wins. After every review or verification round the engineering-manager reconciles the reviewers' returned ids against this file and writes an Open row for any id that has none, before the next step starts (ADR 0037 rule 1; working-agreement §7 step 3d). Count: `python3 scripts/measure/open_defects.py docs/sprints/03/review-rounds.md` (goal scorecard G03-12).

## Owner dispositions: senior-backend-engineer (Sprint 3 build, 2026-10-06)

| Finding | Severity | Disposition | Files | Test evidence |
|---|---|---|---|---|
| SEC-RV3-02 | minor | Fixed, pending the security-privacy-engineer's re-check. A staging or prod process refuses an `AUTH_EMAIL_KEY` that contains `dev-only` (any case), with a message that never echoes the key. Before, the env.example key `dev-only-email-key-not-a-secret-0000` (36 characters) passed the 32-character rule | `backend/src/racket/platform/settings.py`, `backend/tests/unit/platform/test_settings_sprint03.py` | Red: `cd backend && env -u APP_ENV uv run pytest -q tests/unit/platform/test_settings_sprint03.py` → `6 failed, 3 passed` (the 3 dev keys × staging/prod accepted). Green: same → `9 passed`; `tests/unit/platform` → `101 passed`; ruff clean |
