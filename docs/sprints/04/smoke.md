# Sprint 4 integration smoke (ADR 0022, ADR 0033 rule 3; SMOKE-04)

## Smoke of `main` after the Sprint 4 merges so far, 2026-10-18 (sre-devops-engineer with senior-qa-engineer; SMOKE-04)

- **Tree:** `origin/main` at `3c4be05` (merge of PR #114, PD-4b, the last merge at the time), in a fresh worktree (`git -C <repo> worktree add -b s04/smoke-04-integration-smoke-of-main-3c4be05 /home/user/wt/smoke-04 origin/main`). Dependencies come from the lock files only: `uv sync --locked` (backend, infra) and `pnpm install --frozen-lockfile` (web). CI on that SHA: run 39090166506, `push`, **`success`** (every job, including `ci-gate`).
- **What `main` holds at this SHA:** 27 Sprint 4 PRs are merged (`git log --merges --oneline c170ef0..3c4be05 | grep -c 'Merge pull request'` → 27): PLAN-04, the six C4 carry-over tickets, the gate tickets (PE-4, PD-4, PD-4b, SEC-4, COACH-4, PM-4), ST-055/056/057/058a-c/059/060/061a/067/073, QA-HARNESS-4a/b and CI-SIGNIN-HYDRATION. **Not merged yet:** ST-061b (PR #111, open: `POST`/`GET /me/plan`), and ST-062, ST-063a-c, ST-064-066, ST-068-072, VERIFY-04 and RETRO-04 (no PR yet). So this run is a **regression and platform smoke**, not the Sprint 4 goal measurement: the plan journey cannot pass until the plan API and UI land.
- **Disk and prune:** `df -h /` was `252G 29G 11G 74%` at the start (10.5 GiB by `df -Pk`). Prune by `docs/ops/disk-and-prune.md` steps 2-3, with no build running: `docker builder prune -af` (2.44 GB reclaimed) and `docker image prune -f` (0 B) gave `252G 27G 13G 69%`. The other lane's running `racket-analytics-*` containers and the stale images of earlier rounds were left alone. `bash scripts/disk-precheck.sh` → `ok, 12 GB free on / (floor 10 GB)`. At the end: `252G 27G 12G 70%`.
- **Why no Compose image build:** there were two reasons. (1) 12 GiB free is under the 16 GB build floor (`RA_UP_MIN_FREE_GB`, `docs/ops/disk-and-prune.md`). (2) The Docker daemon in this sandbox has a stale build proxy: `docker info` → `HTTPS Proxy: http://127.0.0.1:34223`, and that port is closed (`connection refused`), while the session proxy is now on another port. So the daemon cannot pull or resolve any image it does not already have. Restarting `dockerd` would have killed another lane's running stack, so it was not restarted. The stack therefore used the SMOKE-03 topology, from a clean state, with Compose for every pulled service (next bullet).
- **Stack under test (project `racket-smoke04`, `<scratch>/stack.sh up|down`, env = `infra/env.example` with only the host ports changed to 60xxx and `DOCKERHUB_REGISTRY=mirror.gcr.io`; every `FEATURE_*` flag off, the default):**
  - Compose from `infra/compose.yaml`, no build: `up -d --wait postgres objectstore mailpit`, `run --rm objectstore-init`, and `run --rm --no-deps db-roles` after the migrate step. All volumes fresh.
  - `python -m racket.platform.migrate` from the worktree; `alembic_version` → `0018` (ST-061a plan persistence).
  - App services as local processes with the Compose environment:
    - `api`: uvicorn with `--proxy-headers`, `TRUSTED_PROXY_HOPS=1` and sign-in per-IP limits of 1000, as in the CI E2E job.
    - `worker`: `WORKER_STAGES=probe`, DB login `racket_worker`, the worker's own S3 key.
    - `mailer`: `send_sign_in_link`, no S3 key.
    - `purge`: `infra/docker/purge_schedule.py … racket.platform.purge --once`.
    - `web`: `pnpm build`, then `next start`.
  - Jaeger `2.10.0` and `caddy:2.10.2-alpine` come from images already on disk. Caddy runs the **committed `infra/tls/Caddyfile`**, with only its upstreams and ports rewritten by `sed`, read-only and with `cap_drop ALL`. The stack is at https://localhost:60300 and was up in 62 s.

### Verdict

**Green on what is merged; no new red in the product.**

- The Sprint 2 and Sprint 3 goal journeys pass live over HTTPS on `main`, and so does the privacy flags-off check.
- **Every Playwright journey passed** on Chromium (Chrome for Testing): **133 passed, 6 skipped, 0 failed, 0 flaky**. There is no `@red-until-` tag in `web/e2e`.
- Backend CI selection: 3444 passed, 0 failed. Web: 712 passed. Drill lint, coverage and the plan eval are green (32 of 32 cases at pass^3).
- **Two things are not green, and neither is a product defect:**
  1. The Sprint 4 plan journey (`live_plan.py`) fails closed, because `POST /me/plan` is 404 on `main`. The ST-061b PR #111 is not merged.
  2. 4 infra tests (`test_compose_extra_ca*.py`, C4-CA) need a real `docker compose build`. Here they fail on the sandbox daemon's stale proxy, and they pass in CI on the same SHA.
- The Sprint 3 ledger still has 2 open rows (G04-12 c), although C4-G12 has merged.

### Suites

| Suite | Command | Result |
|---|---|---|
| Web types, lint | `pnpm exec tsc --noEmit`; `pnpm exec eslint --max-warnings=0 .` | rc 0; rc 0 |
| Web unit | `pnpm exec vitest run` | **83 files, 712 passed** in 35 s (SMOKE-03: 78 files, 672) |
| Web build | `pnpm build` (stack step, `API_INTERNAL_URL=http://127.0.0.1:60800`) | rc 0 |
| Infra | `cd infra && DOCKERHUB_REGISTRY=mirror.gcr.io uv run --no-sync pytest -q -p no:cacheprovider -rfEs -m "unit or integration"` (the CI `infra-tests` selection) | rc 1 in 488 s: **4 failed, 1550 passed, 7 skipped** (SMOKE-03: 936 passed). **The 4 failures are environment-only:** `test_compose_extra_ca.py::test_it_04_14_a_build_without_extra_ca_file_mounts_nothing`, `::test_it_04_14_a_build_with_a_throwaway_ca_reads_it_and_no_layer_has_it`, `test_compose_extra_ca_scenarios.py::test_no_extra_ca__no_secret_no_ca_in_image` and `::test_extra_ca_configured`. Each one stops at `resolve image config for docker-image://mirror.gcr.io/docker/dockerfile:1.7: … proxyconnect tcp: dial tcp 127.0.0.1:34223: connect: connection refused` (the daemon proxy; see Disk). The same tests are in the `infra-tests` job of CI run 39090166506, which is `success`. **The 7 skips:** `demo_live.py` 3 (`RA_DEMO_BASE_URL` not set), `GITLEAKS_BIN` not set 3, and `test_repo_visibility.py:169` 1 (live GitHub call, opt-in) |
| Backend, CI integration-job selection, on the stack's Compose Postgres and object store | `env (DATABASE_URL, S3_*, MAILPIT_API_URL, APP_ENV=test) uv run --no-sync pytest -q -p no:cacheprovider -n auto -m "(unit or integration or scenario or regression) and not nightly and not red_until" --ignore=…worker_sandbox.py --ignore=…worker_sandbox_strict.py --ignore-glob='tests/integration/harness/test_ci_objstore_*.py'` | **3444 passed, 1 skipped, 0 failed** in 251 s (SMOKE-03: 3048). The skip is `test_rules_properties.py:66` (P3 rally scoring, blocked on FR-043 / OQ-01) |
| Object store write floor (CI-OBJSTORE-SLOW) | `… pytest -q tests/integration/harness/test_ci_objstore_throughput.py` | 2 passed in 4.1 s |
| Backend `red_until` rows (listed, not gated) | `… pytest -q -m "red_until and not nightly" -o timeout=30 --session-timeout=90 --junitxml=…`; `python3 ../scripts/ci/red_until_report.py --junit … --root . --expected-rows 21` | pytest 21 failed (expected), 21 rows collected. Report rc 0, **"No stale markers."**: ST-024 1, ST-025 2, ST-035 18. This is the same as SMOKE-03, so Sprint 4 added no `red_until` row |
| Drill lint (ST-053) | `cd backend && uv run --no-sync racket-drill-lint ../content/drills` | `ok, 0 problem(s), metric dictionary v0.1`, rc 0 |
| Drill coverage (ST-059; G04-05 c, d) | `uv run --no-sync racket-drill-coverage ../content/drills`; the same on `tests/fixtures/drills-coverage-gap` | rc 0: `library: 23 reviewed drill(s), 3 warm-up(s)`, `ok, 0 problem(s)`. The gap fixture gives rc 1: `FAIL AN-05 × beginner: players ≤ 2: 0` |
| Code-grader plan eval (ST-060; G04-04) | `uv run --no-sync racket-plan-eval --runs 3 --json …` | rc 0, `pass^3: 32 of 32 cases passed all 3 runs (100%)` |

### Live checks (stack `racket-smoke04`, https://localhost:60300)

| Check | Command | Result |
|---|---|---|
| Stack up | `bash <scratch>/stack.sh up` | rc 0 in 62 s; `created bucket racket-media`; `migrate: database is at head`; `db-roles: worker login racket_worker ready (member of racket_media_worker)` |
| Migration head | `psql -U racket -Atc 'select version_num from alembic_version'` | `0018` |
| TLS front door (ADR 0029) | `curl http://localhost:60300/`; `curl --cacert root.crt https://localhost:60300/` (the root is copied from the caddy data volume) | 400; 200 |
| API health, direct and through TLS | `curl http://127.0.0.1:60800/healthz`; `curl --cacert root.crt https://localhost:60300/api/healthz` | 200 `{"status":"ok"}`; 200 |
| Flags and coaching config (ST-067) | `curl --cacert root.crt https://localhost:60300/api/config/public` | `{"features":{"age_gate":false,"retention_setting":false,"training_consent":false,"quotas":false},"coaching":{"weakness_unit":"rallies_lost_per_game"}}` |
| ST-042 DB grants | `PGPASSWORD=… psql -U racket_worker -c 'select count(*) from sessions'` / `accounts` / `jobs` | permission denied; permission denied; `0` (allowed) |
| Probe stage under the narrowed grants | `grep -c probe.done` in the worker log, after all runs | 77; 0 `permission denied` |
| Purge scheduler (SRE-PURGE) | the purge log at start | `purge.pass` (0/0/0, `failed` 0); `purge.run` `status ok`, `next_run_in_s 86400` |
| C-13 and error lines | over the api, worker, mailer, purge and web logs after all runs: `grep -ciE 'permission denied\|Traceback\|"level": *"error"'`, then `grep -ci 'failed to export'` | 0 and 0 in each |
| Sprint 2 journey (G02-01 method, regression) | `python3 scripts/measure/live_tagging.py --api https://localhost:60300/api --origin https://localhost:60300 --mailpit http://127.0.0.1:60025 --cacert root.crt --file fixtures/clips/synthetic-60s/clip.mp4 --runs 1 --json …` | rc 0, `runs_passed 1/1`, `ok true`. Tag→sheet p50 14.0 / p95 15.0 ms (n 6, target ≤ 5,000). Tag server p50 33.5 / p95 38.8 ms (n 8) |
| Sprint 3 journey (G03-01..03 method, regression) | `PGPASSWORD=… python3 scripts/measure/live_stats.py <same args> --runs 1 --psql "psql -h 127.0.0.1 -p 60432 -U racket -d racket -At -F\|" --purge-cmd "bash <scratch>/stack.sh purge-once" --json …` | **rc 0, `runs_passed 1/1`, `ok true`.** Tag→stats p50 18.4 / p95 22.9 ms (n 14). Correction→stats 17.3 ms. Delete match: hidden in 19.7 ms (target ≤ 60,000). Purge ok: 0 rows left in all 26 checked columns, **including the new Sprint 4 tables** (`training_plans`, `plan_sessions`, `plan_assignments`, `plan_citation_rallies`, `plan_source_matches`, `plan_done_ops`); media 404 |
| **Sprint 4 plan journey (G04-01..03 method; informative)** | `python3 scripts/measure/live_plan.py --base-url https://localhost:60300 --cacert root.crt --mailpit http://127.0.0.1:60025 --file fixtures/clips/synthetic-60s/clip.mp4 --runs 1 --json …` | **rc 1, `runs_passed 0/1`: fails closed, as expected.** `setup` ok, `stats` ok, `reference` 9 comparisons with 0 mismatches. Then `generate`: "4 of 4 not 201". Cross-check: `curl -X POST https://localhost:60300/api/me/plan` → 404, and `grep -rn '"/me/plan' backend/src` finds nothing. It waits on ST-061b (PR #111) and the plan UI tickets |
| Privacy, flags off (G04-09 a method; informative) | `python3 scripts/measure/live_privacy.py --flags off --api https://localhost:60300/api --origin https://localhost:60300 --mailpit http://127.0.0.1:60025 --cacert root.crt --file … --runs 1 --json …` | rc 0, `ok true`; `flags_off` codes 404, 404, 404, 404 (no privacy route is served while the flags are off). The full G04-09 (a) also needs a G04-01 run, so this row is not the scorecard value |
| Playwright, every spec, Chromium (Chrome for Testing 141.0.7390.54, ADR 0036; `scripts/dev-chrome.sh check`) | `PW_CHROMIUM_CHANNEL=chrome PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers BASE_URL=https://localhost:60300 MAILPIT_API_URL=http://127.0.0.1:60025 PW_PROJECTS=chromium E2E_ADMIN_CMD="bash <scratch>/stack.sh admin" bash scripts/ci/evidence.sh e2e <run> --project=chromium --workers=1 --global-timeout=2400000 --reporter=list,json,junit` | **rc 0 in 10.8 min: 133 passed, 6 skipped, 0 failed, 0 flaky.** JSON `stats`: expected 133, skipped 6, unexpected 0, flaky 0. By folder: root specs 7, `sprint-01` 53 (+ the 6 skips, each naming its API binding), `sprint-02` 35, `sprint-03` 38 (SMOKE-03: 34). `grep -rn "@red-until-" web/e2e` → nothing, so this is every journey. **There is no `e2e/sprint-04/` yet:** E2E-04-01..08 come with ST-063a-c, ST-065 and ST-068b-072b |
| Self-cleaning (C-15) | `bash <scratch>/stack.sh down` | rc 0. The `racket-smoke04_pgdata` and `_s3data` volumes and the networks were removed. That leaves 0 `racket-smoke04` containers, 0 volumes and 0 stack processes; `df -h /` 12 GB free |

### Problems routed (ADR 0022 rule 1)

| Owner | Issue | Evidence |
|---|---|---|
| senior-backend-engineer (ST-061b) | The Sprint 4 goal journey cannot run on `main`: there is no plan API | `live_plan.py` rc 1, `generate` "4 of 4 not 201"; `POST /api/me/plan` → 404; PR #111 open |
| senior-backend-engineer | EM-PR27-01 (major, Sprint 3 ledger) is still Open after C4-G12 merged. There is still no senior-engineer `Verdict:` on PR #27's merged head `52582fd`: the reviews on #27 are by the principal-engineer and the sre-devops-engineer only | `python3 scripts/measure/open_defects.py docs/sprints/03/review-rounds.md` → rc 1, `open 2` (PD-R1S3-01/QA-R3S3-06, EM-PR27-01); `pull_request_read get_reviews 27` |
| engineering-manager | The Fixed row for PD-R1S3-01 / QA-R3S3-06 is not written. The chair's part is done (`flows-sprint-03.md` v0.3, "held 2026-10-17"; `decisions/C4-G12.md` row 22 hands the Fixed rows to the EM). G04-12 (c) stays "no" until both rows are closed | Same `open_defects.py` output; `docs/design/flows-sprint-03.md:3` and `:292` |
| human / environment owner (via EM) | The sandbox Docker daemon has a stale build proxy (`127.0.0.1:34223`, closed). No image build or pull works on this host: G04-06 (`make up` from a fresh checkout) and the 4 C4-CA infra tests cannot run here. A `dockerd` restart with the current proxy is needed, at a time when no lane's stack is running | `docker info` → `HTTPS Proxy: http://127.0.0.1:34223`; `(echo > /dev/tcp/127.0.0.1/34223)` → closed; infra failures above |

### Not covered by this run

- **The Sprint 4 goal rows.** G04-01/02/03 (d) wait on the plan API. G04-06 needs `make up` (an image build, see Disk) and `make demo` with a plan (ST-064). G04-07/08 Sprint 4 ids: there are no E2E-04 specs yet. G04-09 (b-d) and G04-10 need a flags-on stack and the ST-068..072 routes. These belong to VERIFY-04 once the tickets merge.
- **Container hardening of the app services and the worker sandbox IT-00-10** (no Compose image build). These are covered by `infra/tests/test_compose_*.py` (green above, apart from the 4 build-only C4-CA tests) and by the CI E2E job on Compose (run 39090166506, success).
- **WebKit:** there is no WebKit build in `/opt/pw-browsers`. CI runs the WebKit leg (run 39090166506, success).
- **Locust on stats and evidence** (C4-LOCUST): this runs in the CI `perf-baseline` job (run 39090166506, success), not in this smoke.
- **Human-gated goal items** (P6, P7, P8, P10, P11, P15, P16): there is nothing for a smoke to run. Their rows stay "not met: waiting on P-n" (PO P12).
