# SMOKE-04 decisions

Per-ticket decision file (PO rule 2026-10-07). Ticket: integration smoke of `origin/main` after the Sprint 4 merges. Results go to `docs/sprints/04/smoke.md`. Owner: sre-devops-engineer with senior-qa-engineer. Docs-only. No product, test or harness file is changed.

| Date | Role | Decision | Evidence | Why |
|---|---|---|---|---|
| 2026-10-29 | sre-devops-engineer | **The 16 GB build floor was kept. There was no Compose image build.** The stack used the SMOKE-03 topology: Compose for the pulled services, the app as local processes behind the committed Caddyfile | `df -h /` 14G free after the prune (steps 2-3) | A fresh build takes about 6 GB and would push the host under the 10 GB run floor that other agents share (`docs/ops/disk-and-prune.md`) |
| 2026-10-29 | sre-devops-engineer | **Flag-on runs restarted the app processes with the four `FEATURE_*=true` exported**, because `infra/compose.yaml` does not forward them (SMOKE-04-04) | `grep -c FEATURE_ infra/compose.yaml` → 0; `GET /api/config/public` after the restart → all `true` | Without this, the flag-on harness and E2E could not run at all |
| 2026-10-29 | senior-qa-engineer | **The three Sprint 4 measurement failures (SMOKE-04-01..03) are routed and not worked around.** The harness and specs are not edited in this PR. A debug copy that printed the 409 body stayed in scratch | `smoke.md` Verdict items 1-3 | Scorecard §3 rule 4: no edits to make a row pass. A test or harness change needs a TCR row decided by QA |
| 2026-10-29 | sre-devops-engineer | **The backend suite ran on its own `RA_DEV_STATE` Postgres and object store and its own Mailpit, with `-n 2`,** at the same time as the Playwright run | `3818 passed, 1 skipped`; Playwright `145 passed`, 0 flaky | This keeps the suites from writing into the stack under E2E test and leaves CPU for the single Playwright worker on a 4-core host |
