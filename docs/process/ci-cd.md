# CI/CD, merge gates, agent hooks and the dev environment

- **Owner:** sre-devops-engineer
- **Status:** Sprint 0 (ST-001, ST-002, ST-003). Decisions: ADR 0014 (CI gates), ADR 0013 (agent hooks), ADR 0008 part C (object store; parity note dated 2026-10-03).
- **Citation prefixes:** see `working-agreement.md` §0.

## 1. Dev environment (ST-001)

### 1.1 Docker Compose: the whole stack with one command

```bash
make up            # = cp infra/env.example infra/.env (once), then
                   #   docker compose -f infra/compose.yaml up -d --build --wait
make up-deps       # backing services only: postgres, objectstore (+init), mailpit, tracing
make down          # stop and delete volumes
```

| Service | Image | Host port (127.0.0.1 only) | Purpose |
|---|---|---|---|
| `postgres` | `postgres:16-alpine` | 5432 | Database and job queue (ADR 0008 part B) |
| `objectstore` | `chrislusf/seaweedfs:3.97` | 8333 | S3-compatible store (ADR 0008 part C) |
| `objectstore-init` | same | — | One-shot: creates `S3_BUCKET_MEDIA` |
| `mailpit` | `axllent/mailpit:v1.27` | 8025 (UI), 1025 (SMTP) | Dev email for magic links |
| `tracing` | `jaegertracing/jaeger:2.10.0` | 16686 (UI) | OTLP collector and trace viewer [AQS/OPS-06] |
| `api` | `infra/docker/backend.Dockerfile` target `api` | 8000 | FastAPI app |
| `worker` | same file, target `worker` | — | Job worker, sandboxed |
| `web` | `infra/docker/web.Dockerfile` | 3000 | Next.js PWA |

- **Configuration is environment-only** [AQS/OPS-01]. `infra/env.example` lists every variable with dev-only placeholder values. Compose uses `${VAR:?}` for required values, so a missing variable stops `docker compose` and names the variable. The API also refuses to start without them (ST-005).
- **No SQLite anywhere** [AQS/OPS-05]; `infra/tests/test_compose.py` checks this.
- **Worker sandbox (ST-009, NFR-054).** The worker is only on the `sandbox` network, which is `internal: true`. It reaches Postgres, the object store and the tracing collector, and has no route to the internet. It also runs with a read-only root filesystem, `cap_drop: ALL`, `no-new-privileges`, and CPU and memory limits. Evidence that the network works this way is in §5.
- **Docker Hub rate limits:** set `DOCKERHUB_REGISTRY=mirror.gcr.io` in `infra/.env`.
- **TLS-intercepting proxies:** run `docker build --secret id=extra_ca,src=/path/ca.crt ...`. The backend Dockerfile mounts this secret only when it is present.

**Contracts with other lanes** (change them together with the SRE):

| Contract | Owner |
|---|---|
| ASGI app at `racket.platform.app:app` (override with `API_APP`); `GET /healthz` returns 200 | BE (ST-005) |
| Worker entry point `python -m racket.worker` (override with `WORKER_MODULE`). It touches `/tmp/worker-heartbeat` on every poll loop and returns the in-flight job to the queue on SIGTERM within 10 s | BE (ST-007) |
| Environment variable names as in `infra/env.example` (`DATABASE_URL`, `S3_*`, `APP_ENV`, `DEV_IDENTITY_ENABLED`, `OTEL_*`) | BE (ST-005 Settings) |
| `web/package.json` with a committed `pnpm-lock.yaml` and scripts `build`, `start` (port 3000) and `test:unit` (Vitest) | FE (ST-010) |
| pytest markers `unit`, `integration`, `scenario`, `regression`, `slow`, `red_until` | QA (ST-004) |

### 1.2 Local services without Docker

These scripts are for dev containers and CI runners without a Docker daemon. They start real servers, not mocks.

```bash
eval "$(scripts/dev-postgres.sh start)"      # Postgres 16, free port, random password -> DATABASE_URL
eval "$(scripts/dev-objectstore.sh start)"   # SeaweedFS 3.97 S3, free ports, random keys -> S3_*
scripts/dev-postgres.sh stop; scripts/dev-objectstore.sh stop   # stop and delete the data
```

- `dev-postgres.sh` uses `/usr/lib/postgresql/16/bin` (override with `PG_BIN`). When run as root it runs the server as the `postgres` OS user, because initdb refuses root. TCP auth is scram-sha-256.
- `dev-objectstore.sh` downloads the pinned SeaweedFS release, checks its sha256 (the script refuses a mismatch) and caches it in `.local/bin/`. Set `WEED_BIN` to use another binary.
- State lives in `.local/` (gitignored). Data directories are temp dirs, and `stop` deletes them.

## 2. CI pipeline and merge gates (ST-002)

`.github/workflows/ci.yml` runs on every PR, on pushes to `main`, nightly at 03:17 UTC and on manual dispatch. **Every gate fails closed.** A missing project, lockfile, manifest or report is a red gate, never a silent skip (ADR 0014).

| Job | Gate (sprint-00 §8) | Threshold |
|---|---|---|
| `pr-policy` | Test and gold immutability; PR size | No unapproved change under protected paths; > 400 lines needs `size-waiver` |
| `workflow-lint` | actionlint + shellcheck on workflows | 0 findings |
| `python-lint` | `ruff check`, `ruff format --check` | 0 errors [AQS/STACK-05] |
| `python-types` | mypy, strict on `scoring`, `analytics`, `coaching`, `sports`, `dataset` | 0 errors (NFR-077) |
| `python-unit` | Domain unit suite; backend unit suite | 100% pass; < 10 s; ≤ 60 s (NFR-073) |
| `integration` | IT-00-16 object-store parity; unit + integration + scenario + regression suites on Compose services, with coverage; changed-lines coverage | 100% pass; < 10 min; ≥ 85% on changed lines (testing-strategy §8) |
| `fixture-integrity` | `racket-manifest-check` on every `fixtures/**/manifest.json`, against the merge-base manifest | Intact (FR-151, NFR-078) |
| `infra-tests` | Tests for hooks, CI scripts, launchers and compose | 100% pass |
| `web-checks` | ESLint, `tsc --noEmit`, Vitest coverage, changed-lines coverage, `next build`, first-route JS | 0 errors; ≥ 80%; ≤ 200 KB gzipped (NFR-015) |
| `e2e` | Playwright (Chromium + WebKit projects) on the full Compose stack, with axe-core | 0 serious or critical violations (NFR-027) |
| `secrets-and-audit` | gitleaks 8.28.0 (pinned, sha256-checked) over the git history; pip-audit; `pnpm audit --prod --audit-level critical` | 0 secrets; 0 known vulnerabilities (Python); 0 critical (npm) |
| `sbom-licences` | CycloneDX SBOMs of the **shipped** graph (backend `--no-dev` venv, web `--prod` node_modules) via Syft; `scripts/ci/check_licences.py` | 0 AGPL, non-commercial, SSPL or BUSL (NFR-062) |
| `flaky-report` (nightly) | Suites run 3 times; `scripts/ci/flaky_report.py` | Report only (NFR-074); quarantine within 1 day |
| `ci-gate` | Aggregates every job above except `flaky-report` | The single required status check |

**Expected red until code exists:** `python-unit`, `integration` (coverage, red-first QA suites), `web-checks`, `e2e`, the web part of `secrets-and-audit` and `sbom-licences` stay red until ST-005..ST-010 land. This is intended: QA's red-first suites (ST-012) must fail until their stories turn them green.

### 2.1 Repository settings a human admin must apply (not possible from code)

1. **Branch protection on `main`:** require the `ci-gate` check, require PRs, and dismiss stale approvals.
2. **Labels:** create `qa-approved-test-change` (applied only by the senior-qa-engineer), `size-waiver` (EM only) and `skip-claude-review`. GitHub cannot restrict who applies a label. Limit triage/write access, and audit label events in the PR timeline at review (judgment; ADR 0014).
3. **Secret `ANTHROPIC_API_KEY`** (Settings → Secrets and variables → Actions → New repository secret) for the review bot (§4). Without it, the review job logs a notice and passes.
4. **Actions → General:** set "Workflow permissions" to "Read repository contents" (the workflows request what they need per job).

## 3. Agent hooks (ST-003, DPA/AI-10)

Wired in `.claude/settings.json`; scripts in `.claude/hooks/`; tests in `infra/tests/test_hook_*.py`.

| Event | Script | Behaviour |
|---|---|---|
| PreToolUse `Write\|Edit\|MultiEdit\|NotebookEdit\|Bash` | `pre_tool_use.py` | Denies writes (exit 2) to `.env*`, `*.pem`, `*.key`, `infra/secrets/**`, including through `..` and symlinks. Also denies Bash redirection, `tee`, `cp`, `mv` and `install` into those paths. Appends every Bash command to `.claude/logs/bash-audit.jsonl` |
| PostToolUse `Write\|Edit\|MultiEdit` | `post_tool_use.py` | Python: `ruff check --fix`, `ruff format`, then `ruff check`. Exit 2 reports what is left to Claude. TS/JS: `eslint --fix` from `web/node_modules` |
| Stop | `stop.py` | Runs `scripts/test-unit.sh` (unit, not slow, not `red_until`). Exit 2 with the failure tail blocks the end of the turn. Skips when `stop_hook_active` (loop guard), under GitHub Actions (CI is the gate), or when the tree and command are unchanged since the last green run |

`permissions.deny` also blocks *reading* `.env*`, keys and `infra/secrets/**`.

**Defensive rules (ADR 0013):** stdlib only, and no network. Malformed input or an internal hook error allows the call and warns on stderr, so a hook bug never wedges a session. Missing linters skip with a note, because CI is the gate. The Stop hook's time budget is 180 s (internal) inside a 240 s hook timeout.

**Human-only overrides** for debugging (environment of the Claude Code process): `RA_UNIT_TEST_CMD`, `RA_STOP_TIMEOUT_S`, `RA_RUFF`, `RA_ESLINT`.

### 3.1 Test-immutability guard (EP/ENG-28, NFR-078)

`scripts/ci/check_test_immutability.py` (job `pr-policy`) fails a PR that **modifies, deletes or renames** an existing file under `backend/tests/`, `web/e2e/`, `fixtures/gold/` or `tests/features/`. The PR passes when it carries the `qa-approved-test-change` label. Adding new files is always allowed. The job re-runs on `labeled`/`unlabeled` events. Only changes since the merge base count.

## 4. Claude review bot

`.github/workflows/claude-review.yml` uses `anthropics/claude-code-action`, pinned to the commit of tag `v1.0.240` (`ed670b4c…`, resolved with `git ls-remote` on 2026-10-03; licence MIT, fetched). The research names `@v1` [DPA/AI-11, DPA/AI-13]. We pin the commit behind the newest `v1.x` tag.

- **Requires** the `ANTHROPIC_API_KEY` repository secret (§2.1 step 3).
- **Guards:**
  - job-level token permissions `contents: read`, `pull-requests: write`, `issues: read`; workflow default `{}`;
  - skips drafts, forks (no secrets there), PRs opened by bots, and PRs labelled `skip-claude-review`;
  - `--max-turns 12`, `timeout-minutes: 15`, one run per PR with cancel-in-progress;
  - tool allowlist: read the repo, read the PR diff, comment.
- **Bot-loop protection:** the action posts with `GITHUB_TOKEN`. Events created with `GITHUB_TOKEN` do not start new workflow runs, and the `allowed_bots` input is left empty (no bots).
- **Review content:** the prompt points at the DoD, working-agreement §6-§7, testing-strategy and ddd-guidelines. It asks only for correctness and requirement gaps, labelled Blocking, Nit or Optional [DPA/AI-08].

## 5. Evidence (2026-10-03, dev container)

| Claim | Command | Result |
|---|---|---|
| Lane test suite (hooks, CI scripts, launchers, compose, workflows, parity) | `cd infra && uv run pytest -q` | `171 passed in 54.63s` |
| Workflows valid | `actionlint -color=false` | exit 0 (shellcheck integration active) |
| Compose backing services start healthy | `docker compose -f infra/compose.yaml --env-file <env.example with DOCKERHUB_REGISTRY=mirror.gcr.io> up -d --wait postgres objectstore objectstore-init mailpit tracing` | all `healthy`, `objectstore-init` exited 0, 24 s |
| SeaweedFS parity on Compose (IT-00-16) | `S3_ENDPOINT_URL=http://127.0.0.1:58333 ... uv run pytest tests/test_object_store_parity.py` | `7 passed` |
| Worker sandbox network | `docker run --network racket-analytics_sandbox racket-api:dev python -c ...` | `objectstore:8333/healthz 200`; postgres:5432 reachable; `pypi.org` name resolution failure; `1.1.1.1` network unreachable |
| Image runs non-root | `docker run --rm --entrypoint id racket-api:dev` | `uid=999(app)` |
| Hooks on the real repo | see `docs/sprints/00/decision-log.md` rows of 2026-10-03 | `.env` write → exit 2; format-on-edit; failing unit test → Stop exit 2 |

Not yet shown: a CI run on GitHub. This repo has no remote in this session. The sprint DoD item "a deliberately failing sample PR shows each gate blocking" needs the first push.
