# SMOKE-04 decisions (per-ticket file, PO rule 2026-10-07)

| Date | Who | Decision | Evidence | Why |
|---|---|---|---|---|
| 2026-10-18 | sre-devops-engineer | **Own Compose project `smoke04` instead of `make up`** (`make up` uses the default project `racket-analytics`, which a stale stack from `/home/user/wt/mvp-final` still holds) | `docker inspect racket-analytics-worker-1` → working dir `/home/user/wt/mvp-final/infra` | Never touch another lane's project; clean state for this run only |
| 2026-10-18 | sre-devops-engineer | **Backend suites run with only CI's exported variables**; the first run that sourced all of `infra/env.example` is discarded | `smoke.md` "Environment faults" 1 | Same environment as CI's integration job; the discarded run's reds were the harness |
| 2026-10-18 | sre-devops-engineer | **Pruned build cache (steps 2-4 of docs/ops/disk-and-prune.md) before the journeys; left other lanes' images and the stale stack in place** | `docker builder prune -af` → 2.556 GB; `df -h /` 7.2G → 9.1G | Owner of the prune procedure; other lanes' state is not this run's to remove |
| 2026-10-18 | senior-qa-engineer | **Docs-only ticket: no scenario, integration or unit test**; the relevant check is the commands and results in `smoke.md` | `git diff --name-status origin/main...HEAD` → 2 `A` docs files | Definition of done for docs-only tickets |
