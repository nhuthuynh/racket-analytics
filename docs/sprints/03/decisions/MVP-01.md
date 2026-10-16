# MVP-01 decisions

Per-ticket decision file (PO rule 2026-10-07). Ticket: README "Run it locally" quick start (PO MVP goal 2026-10-15: the app runs locally and a new developer can use it).

| Date | Who | Decision | Why |
|---|---|---|---|
| 2026-10-16 | sre-devops-engineer | The quick start is a `## Run it locally` section right after the README's one-line pitch; the existing link list moves under `## Documentation` | The PO asked for it "near the top"; a new developer reads the README first |
| 2026-10-16 | sre-devops-engineer | Guarded by `scripts/ci/check_readme_quickstart.py`, tested by `infra/tests/test_readme_quickstart*.py` and `tests/features/readme_quick_start.feature` (picked up by the existing `infra-tests` CI job; no workflow change) | Ticket: "a test that the commands named in the README exist as Makefile targets". The checker also rejects a `VAR=... make` setting that `infra/compose.yaml` does not read, so the Docker Hub mirror tip cannot rot. The integration test resolves each named target with real `make -n` and proves `DOCKERHUB_REGISTRY=mirror.gcr.io` moves every pulled image to the mirror via `docker compose config --images` |
| 2026-10-16 | sre-devops-engineer | No section on changing host ports | Not verified live in this ticket (changing `WEB_HOST_PORT` also needs `PUBLIC_WEB_ORIGIN` and `DEMO_URL`); the README only states what was run. Troubleshooting says to free the port instead |
| 2026-10-16 | sre-devops-engineer | TDD applies to the checker (red at `e63a9fd`: collection fails, `ModuleNotFoundError: No module named 'check_readme_quickstart'`; scenarios 3 failed on `can't open file .../check_readme_quickstart.py`). After the checker, before the README: 3 failed, 10 passed (`README has no '## Run it locally' section`). Green at `65f0626`: 13 passed | PO rule: tests first, seen failing for the right reason |

## Live run on a clean clone (2026-10-16)

`git clone /home/user/racket-analytics mvp01-clean && git checkout f8b8d50` (origin/main), Docker 29.6.2, Compose v5.3.1, GNU Make 4.3. Run with `COMPOSE_PROJECT_NAME=mvp01` only so as not to touch another agent's containers of the default project `racket-analytics`; ports were the defaults (checked free with `ss -ltnp`).

| Command (as in the README) | Result |
|---|---|
| `make help` | lists `up`, `demo`, `ps`, `logs`, `down` among 18 targets |
| `DOCKERHUB_REGISTRY=mirror.gcr.io make up` | `cp infra/env.example infra/.env`; base images resolved from `mirror.gcr.io/...`; all 13 services Healthy/Exited(0); `rc=0 elapsed=115s` (warm build cache) |
| `make ps` | api, mailer, mailpit, postgres, purge, web, web-tls, worker `(healthy)`; migrate, db-roles, objectstore-init exited `(0)`; ports 3000, 8000, 5432, 8025, 1025, 8333, 16686 on 127.0.0.1 |
| `make demo` | `Demo match: created with 12 tagged rallies; 7 published metrics.` `Open https://localhost:3000/matches/596fffb8-.../stats` `Sign in as Ivy`; rc=0 |
| `curl --cacert .local/demo/root.crt https://localhost:3000/` | `200 ssl_verify=0` (trusting the dev root works) |
| `curl https://localhost:3000/` (no CA) | rc=60: certificate not trusted, hence the click-through note |
| `curl https://localhost:3000/api/dev/users` | `Ivy`, `Carlos`, `Dana` |
| Chromium (`/opt/pw-browsers`, `--ignore-certificate-errors` = click-through): open `/`, click "Sign in as Ivy", open the demo stats link | landed on `/matches`, then the stats page (h1 `Stats`, "Demo match", 7 metric cards with ranges and "Show me" buttons) |
| `POST /api/auth/links {"email":"newdev@example.com"}`, then Mailpit `http://localhost:8025/api/v1/messages` | `202`; Mailpit: 1 message to `newdev@example.com`, subject `Your sign-in link`; `http://localhost:8025/` -> 200 |
| `timeout 5 make logs` | `docker compose -f infra/compose.yaml logs -f --tail=100`, JSON log lines from `purge-1` |
| `make down` | containers, network and volumes `mvp01_pgdata`, `mvp01_s3data`, `mvp01_caddy-data` removed; rc=0; afterwards 0 volumes and 0 containers for the project |

The rest of the journey (wizard, upload, score sheet, corrections, delete) was measured live on main `6c666b9` in the PO finding that opened this ticket; the README only lists it.
