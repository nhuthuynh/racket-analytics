# CI-TIERS-a-R3 decisions

Per-ticket decision file (working-agreement §3). Ticket: CI-TIERS-a-R3, the follow-up to PR #188 (CI-TIERS-a) for the post-merge security/privacy review finding SEC-188-R3-01 (review 5875615911). Story PRC-05, atomic items PRC-2.1 and PRC-2.3 (kickoff SEC-1). Owner: sre-devops-engineer. Review tier 2 (ADR 0056): the change set includes `scripts/ci/review_tiers.py`, so `python3 scripts/ci/review_tiers.py --base origin/main --head HEAD` prints `review-tier: 2`.

PR #188 had already merged (2026-11-03, merge commit `cdd1f6a9`) when the finding was posted, so the fix goes in this new PR into `main` instead of a push to the merged branch. CI-TIERS-b (tier enforcement in `merge_ready.py`) is already on `main`, so until this lands the six paths below merge on a tier 1 verdict set without a security review.

## Decisions

| Date | Who | Decision | Evidence | Why |
|---|---|---|---|---|
| 2026-11-12 | sre-devops-engineer | **Six consent, access-control and security-header files are tier 2** (SEC-188-R3-01): `backend/src/racket/dataset/api.py`, `backend/src/racket/dataset/manifest.py`, `backend/src/racket/platform/http.py`, `backend/src/racket/platform/app.py`, `backend/src/racket/platform/errors.py`, `web/next.config.ts`. They are exact paths, not globs, so other `dataset/**` files stay tier 1 | `test_a_tier_2_path_is_tier_2[<each path>]`; scenario Examples "consent, access control and security headers are never tier 1 (SEC-188-R3-01)", one row per path; `test_every_tier2_glob_matches_a_tracked_path` | `dataset/api.py` enforces the labeller role, the owner filter and the consent check (409 `no_consent`); `manifest.py` is the training-consent manifest; `http.py` and `next.config.ts` set the security headers and CSP (NFR-061/067); `app.py` wires the middleware and `errors.py` shapes the error envelope. All fall under SEC-1 "consent" and "client security". `errors.py` was not in the reviewer's suggested list but is in the finding; an error envelope can leak internals, so tier 2 is the stricter reading |
| 2026-11-12 | sre-devops-engineer | **The specialist flags are unchanged.** `dataset/**` still flags senior-ml-cv-engineer and `web/next.config.ts` still flags senior-frontend-engineer | `test_a_path_flags_its_specialist` (unchanged, green) | Tier and specialist are separate rules; only the tier moves |
| 2026-11-12 | sre-devops-engineer | **Branch `s05/ci-tiers-a-r3-...` uses the CI-TIERS-a owner row** in `docs/sprints/05/ticket-owners.json` (`merge_ready.py` matches `<row branch>-<slug>`), so no owner-file change is needed in this PR | `scripts/ci/merge_ready.py` `_owner_rows` | Ticket PRs do not edit the owner file; the engineering-manager can add a dedicated row through an `s05/owners-*` PR if wanted |
| 2026-11-12 | sre-devops-engineer | **SEC-188-R3-02, -03 and -04 are out of scope here** (minor and nit, not blocking) | review 5875615911 | They need separate decisions (R3-02 per path), a CI-TIERS-b gate-source test (R3-03) and a CLI decode fix (R3-04); left for the security-privacy-engineer and the engineering-manager to schedule |

## Test change request (TCR)

None. The PR only adds parametrize cases to `test_a_tier_2_path_is_tier_2` and a new Examples block to `tests/features/review_tiers.feature`; no existing case is changed, weakened or removed.

## Evidence

- Red (commit `542f9778`, tests before the fix): `cd infra && uv run pytest tests/test_review_tiers.py tests/test_review_tiers_scenarios.py -q -p no:randomly` → `12 failed, 205 passed`. 6 × `test_a_tier_2_path_is_tier_2[<path>]` `assert 1 == 2`; 6 scenarios `AssertionError: {'tier': 1, ...}` (for example `{'tier': 1, 'specialists': ['senior-frontend-engineer'], 'files': {'web/next.config.ts': 1}}`).
- Green: `cd infra && uv run pytest tests/test_review_tiers.py tests/test_review_tiers_scenarios.py tests/test_merge_ready_tiers.py tests/test_merge_tiers_scenarios.py -q -p no:randomly` → `311 passed`.
