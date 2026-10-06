# Evidence runs: isolated, locked, self-cleaning

Owner: sre-devops-engineer. Rule: ADR 0033 rule 3 (with ADR 0030 rule 3). Sprint 2 rows C-05, C-15, C-23. Findings: QA-R3-E2E-02, PD-R2R-10, G01-05 goal round 3.

## Why

At the Sprint 1 close, concurrent Playwright runs shared `web/test-results` (ENOENT on traces) and other agents' Compose up/down changed the host network (`net::ERR_NETWORK_CHANGED`). Both produced false reds, so "0 flaky" could not be measured (QA-R3-E2E-02). Each verification round also left about 4.6 GB of images, which pushed the next build under the 10 GB disk floor (G01-05).

## The wrapper: `scripts/ci/evidence.sh`

| Command | What it does | Exit codes |
|---|---|---|
| `bash scripts/ci/evidence.sh e2e RUN_DIR [playwright args]` | From `web/`: `pnpm exec playwright test --output RUN_DIR/pw-out [args]` while holding the lock | Playwright's rc; 2 usage (no `RUN_DIR`, or a caller-supplied `--output`); 4 lock not taken in time |

- **Lock:** `.local/evidence-e2e.lock` (`flock`), shared by every agent and the verifier. A run waits up to `RA_EVIDENCE_LOCK_WAIT_S` seconds (default 3600) and then exits 4. Nothing runs without the lock.
- **Output:** always `RUN_DIR/pw-out`. A relative `RUN_DIR` is resolved against the caller's directory. Passing `--output` yourself is refused, so a run can never fall back to the shared `web/test-results`.
- Environment for Playwright (`BASE_URL`, `MAILPIT_API_URL`, `PW_PROJECTS`, `PLAYWRIGHT_BROWSERS_PATH`, reporter output names) passes through unchanged.

Example (the goal scorecard G02-05 run, same effect as its `flock … --output "$GOAL/pw-out"` line):

```bash
MAILPIT_API_URL=$MAILPIT PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers BASE_URL=$WEB PW_PROJECTS=chromium \
  PLAYWRIGHT_JUNIT_OUTPUT_NAME="$GOAL/e2e.xml" PLAYWRIGHT_JSON_OUTPUT_NAME="$GOAL/e2e.json" \
  bash scripts/ci/evidence.sh e2e "$GOAL" --workers=1 --reporter=line,junit,json; echo rc=$?
```

Tests: `cd infra && uv run pytest -q tests/test_evidence_wrapper.py`.
