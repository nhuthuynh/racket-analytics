# Sprint 2 integration smoke (ADR 0022, ADR 0033 rule 3; SRE-SMOKE)

- **Date:** 2026-10-06
- **Run by:** sre-devops-engineer
- **Tree:** `sprint-02` at `bddd3c7`, as a clean detached worktree (`git worktree add --detach … HEAD`), so no lane's uncommitted file is in the run. `git diff --stat ffce41d bddd3c7 -- . ':(exclude)docs'` is empty: the CI head `ffce41d` has the same code.
- **Isolation:** own `RA_DEV_STATE=.local/sre02-smoke` Postgres and object store, own Mailpit container `sre02-smoke-mailpit` (ports 59025/51125); the Compose part ran on a fresh GitHub runner (fresh volumes by construction).
- **Disk:** `df -h /` 15G free at the start, 13G at the end (other agents' stacks running). See "Not run locally".

## Verdict

**Ready for review round 1 for the platform; not ready overall.** Every platform gate is green, and the live checks of the SRE stories hold. The remaining reds all have an owner outside the platform and an Open row in `review-rounds.md`: the 21 `red_until` rows (stretch ST-035 and PO-blocked ST-024/ST-025), five stale `red_until` markers (SRE-S2-04), H.264 in CI Chromium (SRE-S2-05), five Sprint 2 specs that fail in WebKit only (SRE-S2-07), and two Chromium-only timing tests that run in WebKit (SRE-S2-08).

## Suites

| Suite | Where | Command | Result |
|---|---|---|---|
| Infra (incl. hooks, CI scripts, evidence wrapper, perf verdict, red-until report) | worktree | `cd infra && uv run pytest -q -p no:cacheprovider` | **454 passed** in 69.3 s |
| Web types, lint | worktree | `pnpm exec tsc --noEmit`; `pnpm exec eslint --max-warnings=0 .` (with `pipefail`) | rc 0, rc 0 |
| Web unit | worktree | `pnpm exec vitest run --coverage` | **51 files, 406 passed**; lines 91.02% |
| Backend, full | worktree, own Postgres/object store/Mailpit, no ambient service variables | `env -u APP_ENV uv run pytest -q tests --ignore=…worker_sandbox*.py` | **21 failed, 1876 passed, 1 skipped** in 395 s; the 21 are exactly the `red_until` rows: ST-035 SOS-01..18 (18), ST-025 phone fixtures (2), ST-024 nightly (1) |
| Fresh Compose stack, `up --wait` | CI run 37438997898 (`ffce41d`) | E2E job "Start the full stack" | success (1m43s); worker sandbox IT-00-10 against the running worker: success |
| Playwright, Chromium + WebKit, https | same | `pnpm exec playwright test` | **161 passed, 9 failed, 12 skipped** (14.0 min); failures in `ci-status.md` (SRE-S2-05, -07, -08) |
| Backend gate selection on Compose services | same | integration job | success (`not red_until`); the red-until step fails on SRE-S2-04 as designed |
| Locust baseline, 50 RPS | same | `perf-baseline` job | success: 0 failures, correction p95 410 ms, restored byte-identical |

## Live checks of the platform stories (own stack `racket-sre02`, https://localhost:53000)

Stack built from the tree at `7bb971f` plus the then-uncommitted SRE-MEDIA change (`03ab524`), with `scripts/ci/evidence.sh up` (rc 0, 17 → 12 GB free).

| Story | Check | Result |
|---|---|---|
| TLS front door | `curl http://localhost:53000/`; `curl --cacert root.crt https://localhost:53000/` | 400; 200 |
| C-18 | POST with `Origin: https://evil.example` through the web; same on the API port; POST with the web origin | 403; 403; passes the check (404 route) |
| SRE-MEDIA | `live_tagging.py --runs 1` step `media_link`; unsigned, listing, PUT, DELETE on the bucket path; cross-origin GET | ok (206, tampered 403, TTL 300 s); 403 each; 206 with no `Access-Control-*`, no `Server` (docs/ops/media-serving.md) |
| C-13 | api, worker, mailer logs > 60 s after the change | 0 export errors; traces still in Jaeger |
| ST-039 | Locust run + `perf_verdict.py` | verdict ok (numbers in decision-log; host contended, so reads not a baseline) |
| G02-01 (one run, informative) | `live_tagging.py --runs 1` | 10 of 13 steps; the 3 failing steps are BE-D1-01 (harness `_code()`, owner EM), not platform |
| C-15 | `scripts/ci/evidence.sh down racket-sre02 …` | rc 0, "removed with its volumes and images", 0 `racket-sre02` images and 0 volumes left |

## Not run locally (disk)

A local fresh-volume Compose run of the smoke tree needs 16 GB free before `up --build` (`docs/ops/evidence-runs.md`); this host had 13-15 GB, held by other agents' running stacks and object stores, which the SRE does not remove (`disk-and-prune.md`). The SRE pruned its own state and the build cache (3.2 GB). The Compose part of this smoke therefore comes from CI run 37438997898 at the same code, a fresh runner with fresh volumes. To re-run locally once 16 GB are free: `bash scripts/ci/evidence.sh up racket-smoke02 <env>` from the worktree, Playwright with `evidence.sh e2e`, then `evidence.sh down`.

## Sprint-close head

To be filled by the SRE at the sprint-close head (C-12 rule; Sprint 1 §7): tree, stack, suites, verdict.
