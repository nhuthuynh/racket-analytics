# Evidence runs: isolated, locked, self-cleaning

Owner: sre-devops-engineer. Rule: ADR 0033 rule 3 (with ADR 0030 rule 3). Sprint 2 rows C-05, C-15, C-23. Findings: QA-R3-E2E-02, PD-R2R-10, G01-05 goal round 3.

## Why

At the Sprint 1 close, concurrent Playwright runs shared `web/test-results` (ENOENT on traces) and other agents' Compose up/down changed the host network (`net::ERR_NETWORK_CHANGED`). Both produced false reds, so "0 flaky" could not be measured (QA-R3-E2E-02). Each verification round also left about 4.6 GB of images, which pushed the next build under the 10 GB disk floor (G01-05).

## The evidence browser: `scripts/dev-chrome.sh` (ADR 0036, C3-04)

Bundled Chromium cannot decode H.264, so the goal rows that play the real upload (G02-05, G02-06 (c), G02-10 V family and their Sprint 3 successors) run in Chrome for Testing 141.0.7390.54 at `/opt/google/chrome`, with `PW_CHROMIUM_CHANNEL=chrome`.

| Command | What it does | Exit codes |
|---|---|---|
| `bash scripts/dev-chrome.sh` | Installs the pinned CfT zip after a sha256 check (`5023ec2b…23ed01`, ADR 0036) and checks the version inside before it replaces anything. A matching install is left as it is (no download); any other version is replaced | 0 installed or already there; 1 download failed, sha256 mismatch, or wrong version in the zip (nothing installed) |
| `bash scripts/dev-chrome.sh check` | Prints the version if the pinned build is installed | 0 present; 1 missing or another version |

Run `check` before a goal run that needs the evidence browser; a run without it is not the evidence for those rows (ADR 0036, fail closed).

## The wrapper: `scripts/ci/evidence.sh`

| Command | What it does | Exit codes |
|---|---|---|
| `bash scripts/ci/evidence.sh e2e RUN_DIR [playwright args]` | `scripts/disk-precheck.sh /` first (C-23), then from `web/`: `pnpm exec playwright test --output RUN_DIR/pw-out [args]` while holding the lock | Playwright's rc; 2 usage (no `RUN_DIR`, or a caller-supplied `--output`); 3 below the disk floor; 4 lock not taken in time |
| `bash scripts/ci/evidence.sh up PROJECT ENV_FILE` | Build floor `RA_UP_MIN_FREE_GB` (default 16: a fresh build of the app images takes about 6 GB), then under the lock `docker compose -p PROJECT -f infra/compose.yaml [-f extra…] --env-file ENV_FILE up -d --build --wait`, then the 10 GB run floor | compose's rc; 2 usage or a refused project/env file; 3 below a floor; 4 lock |
| `bash scripts/ci/evidence.sh down PROJECT ENV_FILE` | Under the lock: `df -h /`, `… down -v --rmi local --remove-orphans` (C-15), `df -h /`, then a check that no `PROJECT-*` image is left | compose's rc; 2; 4; 5 an image of the project survived |

- **Lock:** `.local/evidence-e2e.lock` (`flock`), shared by every agent and the verifier. A run waits up to `RA_EVIDENCE_LOCK_WAIT_S` seconds (default 3600) and then exits 4. Nothing runs without the lock.
- **Disk floor (C-23, PD-R2R-10):** every E2E evidence run starts with the precheck, floor `RA_MIN_FREE_GB` (default 10). The `df -h /` line it prints is the disk evidence of the run. Below the floor Playwright never starts (rc 3): a run on a full disk would not be valid evidence.
- **Output:** always `RUN_DIR/pw-out`. A relative `RUN_DIR` is resolved against the caller's directory. Passing `--output` yourself is refused, so a run can never fall back to the shared `web/test-results`.
- **Own project only (C-15):** `PROJECT` must match `racket-<lower-case id>` and is never `racket-analytics` (the developer stack, `compose.yaml` `name:`). The wrapper therefore cannot tear down someone else's default stack. Use one project per round (`racket-goal02`, `racket-sre02`, …).
- **Self-cleaning (C-15, ADR 0033 rule 3):** `down` removes the project's containers, volumes and locally built images, and fails with rc 5 if any `PROJECT-*` image is still present. Shared base images (`mirror.gcr.io/...`) stay; they are not the project's.
- **Extra compose files:** `RA_EVIDENCE_COMPOSE_EXTRA="a.yaml b.yaml"` (space-separated) follow `infra/compose.yaml`, for a sandbox-only build-CA override that is never committed. A missing file is refused (rc 2).
- **Smaller web image (C-15, disk):** `.dockerignore` keeps `**/test-results`, `**/playwright-report`, `**/blob-report`, `**/coverage` and `reports` out of every build context (`web/test-results` alone was 809 MB, measured 2026-10-06), and the web build stage deletes `.next/cache` after `pnpm build`. Dev dependencies stay in the runtime: `next start` transpiles `next.config.ts` and needs TypeScript.
- Environment for Playwright (`BASE_URL`, `MAILPIT_API_URL`, `PW_PROJECTS`, `PLAYWRIGHT_BROWSERS_PATH`, reporter output names) passes through unchanged.

Example (the goal scorecard G02-05 run, same effect as its `flock … --output "$GOAL/pw-out"` line):

```bash
MAILPIT_API_URL=$MAILPIT PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers BASE_URL=$WEB PW_PROJECTS=chromium \
  PLAYWRIGHT_JUNIT_OUTPUT_NAME="$GOAL/e2e.xml" PLAYWRIGHT_JSON_OUTPUT_NAME="$GOAL/e2e.json" \
  bash scripts/ci/evidence.sh e2e "$GOAL" --workers=1 --reporter=line,junit,json; echo rc=$?
```

Stack example (goal scorecard §4.0, same effect as its `flock … $DC up/down` lines):

```bash
bash scripts/ci/evidence.sh up racket-goal02 "$RA_DEV_STATE/goal.env"; echo rc=$?
# ... methods ...
bash scripts/ci/evidence.sh down racket-goal02 "$RA_DEV_STATE/goal.env"; echo rc=$?   # rc 0 = nothing left
```

Tests: `cd infra && uv run pytest -q tests/test_evidence_wrapper.py tests/test_web_dockerfile_round2.py`.
