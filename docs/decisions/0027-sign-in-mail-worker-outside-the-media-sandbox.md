# 0027. Sign-in emails are sent by a worker outside the media sandbox (`WORKER_STAGES`)

- **Status:** Proposed (senior-backend-engineer; needs principal-engineer and security-privacy-engineer review, sre-devops-engineer to wire Compose)
- **Date:** 2026-10-05
- **Deciders:** senior-backend-engineer (proposer); principal-engineer, security-privacy-engineer (approvers)
- **Consulted:** sre-devops-engineer (Compose), senior-ml-cv-engineer (probe sandbox owner)
- **Related:** ST-013; ADR 0017 (job runtime), ADR 0020 (probe sandbox), ADR 0025 (magic link); api-sprint-01 §2.1; NFR-054

## Context and problem statement

ADR 0025 sends the sign-in email from a queued job (`send_sign_in_link`), so `POST /auth/links` answers 202 at once for every address (no existence oracle, T-ML-6). The only worker today is the media worker, which runs ffprobe on untrusted files inside a sandbox whose only network is the internal `sandbox` network (ADR 0020, NFR-054); Mailpit (and later the email provider) sits on `edge`. Which process sends the email?

## Decision drivers

- The probe sandbox must not gain a route to any service it does not need (NFR-054; ADR 0020).
- One job runtime (ADR 0017): no second queue technology.
- In tests and CI the in-process `run_until_idle` must still run every stage.

## Considered options

1. **Stage selection per worker process (`WORKER_STAGES`)** (chosen): the same `python -m racket.worker` entry point runs only the listed stages. The sandboxed media worker runs `probe`; a second worker service on `edge` (the API image is enough, no ffprobe needed) runs `send_sign_in_link`. Empty means all stages (tests, local dev).
2. **Put Mailpit (SMTP) on the sandbox network**: the media worker sends the email.
3. **Send from the API request** (no job): `POST /auth/links` talks SMTP inline.

## Decision outcome

Chosen option: **1**, because it keeps the probe sandbox unchanged and reuses the job runtime.

- `Settings.worker_stages` from `WORKER_STAGES` (comma-separated). An unknown name stops the worker at start (exit 2), like any configuration error.
- `racket.worker.stages.selected(STAGES, names)` builds the stage map; `Runner.claim` already filters by stage name, so a worker never claims another worker's jobs.
- The email address waits in the `sign_in_requests` outbox only until the job sends it; the stage deletes the row in the transaction that stores the link's SHA-256 (or on failure).

### Pros and cons of the options

- **Option 1.** Good: sandbox unchanged; one runtime; same code path in tests. Bad: one more Compose service (SRE work); two worker deployments to keep in step.
- **Option 2.** Good: no new service. Bad: gives the process that parses untrusted media a route to an SMTP relay (spam/exfiltration path if ffprobe is ever exploited); violates ADR 0020's "internal network only for what the probe needs".
- **Option 3.** Good: simplest. Bad: response time depends on SMTP and on whether the job ran, which reopens the timing oracle (T-ML-6) and couples API availability to the mail server (ADR 0025 rejected it).

## Consequences

- SRE adds a `mailer` service to `infra/compose.yaml` (API image, `command: ["python", "-m", "racket.worker"]`, `WORKER_STAGES=send_sign_in_link`, networks `[edge]`) and sets `WORKER_STAGES=probe` on the sandboxed `worker`. Until then, in Compose the sandboxed worker would claim `send_sign_in_link` jobs and fail them with `mail_failed` (no route to Mailpit). Tracked in `docs/sprints/01/blockers.md`.
- The production email provider (Sprint 4 ADR) changes only `racket.players.mailer`.

## Evidence

| Claim | Evidence | Type |
|---|---|---|
| The worker sandbox has only the internal network | `infra/compose.yaml` `worker.networks: [sandbox]`; IT-00-10 strict (`worker → BLOCKED dns`) | repo / test |
| Mailpit is on `edge` only | `infra/compose.yaml` `mailpit.networks: [edge]` | repo |
| Stage selection works and refuses unknown names | `uv run pytest tests/unit/test_worker_stage_selection.py` → `3 passed` | test |
| IT-01-01..03 pass with the in-process worker running every stage | `env -u APP_ENV uv run pytest tests/integration/test_it_01_01_magic_link.py tests/features/test_sign_in.py` → green (see ST-013 commit) | test |
| SMTP from the media sandbox widens its attack surface | (judgment) | judgment |
