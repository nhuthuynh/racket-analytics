# 0034. Deployment edge acceptance criteria (HSTS, forwarded headers, exposed ports)

- **Status:** Proposed
- **Date:** 2026-10-06
- **Deciders:** sre-devops-engineer (author); security-privacy-engineer (reviewer); human product owner (accepts before the first non-dev deployment)
- **Consulted:** security-privacy-engineer (SEC-R1-S1-05, SEC-R5-S1-03, SEC-R6-S1-02), principal-engineer
- **Related:** sprint-02 rows C-29, C-11, C-18, SRE-MEDIA; ADR 0029 (https dev stack; "Follow-ups: the deployment ADR must state how the edge sets `X-Forwarded-For`"); ADR 0018 (CSP); threat model T-ML-8; NFR-055; ST-042 (worker credentials, gate before any non-dev deployment)

## Context and problem statement

No environment except dev and CI exists yet, and the hosting choice is not made. Several Sprint 1 findings were deferred "to the deployment ADR" (SEC-R1-S1-05: no HSTS requirement recorded; ADR 0029 follow-up on `X-Forwarded-For` and trusted hops). Without one place that lists what the public edge must do, each of these can be forgotten when a deployment is built. This ADR does **not** choose a host or a proxy. It fixes the **acceptance criteria** any deployment edge must meet, each with a check that can be run against the public origin.

## Decision drivers

- Findings deferred to a deployment ADR must have a home with a test, not a comment (sprint-02 C-29).
- The dev stack must stay usable: HSTS on `localhost` would pin every developer's browser to https for that host name (judgment).
- Each criterion must be checkable by `curl` or an existing test against the public origin, so the first deployment's smoke can prove it (working-agreement §7 step 1a).

## Considered options

1. **Acceptance criteria now, host choice later (chosen).** Good: the deferred findings get a checkable home today; the host decision is not rushed. Bad: one more Proposed ADR until a deployment exists.
2. **Do nothing until the deployment sprint.** Good: no document to keep. Bad: SEC-R1-S1-05 and the ADR 0029 follow-up stay "deferred to a document that does not exist"; nothing prevents a first deployment without HSTS.
3. **Send HSTS from the dev `web-tls` proxy too.** Good: dev/prod parity for the header. Bad: browsers would remember https-only for `localhost` for the max-age, breaking every other local http service on that name (judgment); the Caddy `tls internal` CA is not trusted by default, so a pinned host with an untrusted certificate cannot be clicked through.

## Decision outcome

Option 1. A deployment edge is accepted only when all of the following hold on the public origin. The check column is what the deployment smoke runs.

| # | Criterion | Check |
|---|---|---|
| E1 | **HSTS** (C-29, SEC-R1-S1-05): every https response from the public origin carries `Strict-Transport-Security: max-age=31536000; includeSubDomains` (at least one year). `preload` only after a separate PO decision, because removal from preload lists is slow (judgment). Never sent from the dev/E2E `web-tls` proxy (option 3). | `curl -sSI https://<origin>/ \| grep -i '^strict-transport-security: max-age=\(3[1-9][0-9]\{6\}\|[4-9][0-9]\{7\}\|[0-9]\{9,\}\)'` |
| E2 | Plain http only redirects to https (308/301), and serves no content | `curl -sS -o /dev/null -w '%{http_code}' http://<origin>/` → 301 or 308 |
| E3 | **Forwarded headers** (ADR 0029 follow-up, T-ML-8): the edge replaces any client `X-Forwarded-For` with the peer address (as `web-tls` does: no `trusted_proxies`), and the API's `TRUSTED_PROXY_HOPS` equals the number of proxies between the client and the API | a request with `X-Forwarded-For: 203.0.113.9` does not reset the per-IP limit (IT-01-02 run against the origin) |
| E4 | **Only the web origin is reachable** (C-11): the API, Postgres, the object store, Mailpit-equivalents and tracing have no public listener | port scan of the public address shows 443 (and 80 for E2) only |
| E5 | **Origin check on** (C-18): `ALLOWED_ORIGINS` = the public web origin; `Settings` already refuses staging/prod without it | `curl -X POST -H 'Origin: https://evil.example' https://<origin>/api/matches` → 403 |
| E6 | **Media through the origin** (SRE-MEDIA, NFR-055): presigned GETs are served under the web origin path, TTL ≤ 900 s, Range → 206, no session token in the URL | IT-02-06 against the origin; G02-01 step 10 |
| E7 | **Worker credentials** (ST-042): the sandboxed worker has its own DB role and S3 key | ST-042 acceptance tests |
| E8 | **Hardening** [AQS/SEC-06]: debug off, no `/docs` or `/openapi.json` outside dev/test, no VCS metadata or directory listing | `curl -sS -o /dev/null -w '%{http_code}' https://<origin>/api/docs` → 404; `…/.git/HEAD` → 404 |

## Consequences

- Good: SEC-R1-S1-05 and the ADR 0029 follow-up now have a checkable criterion (E1, E3). A deployment story copies this table into its acceptance criteria.
- Bad: until a host is chosen, E1-E8 are checked only on paper. The dev stack keeps no HSTS on purpose (option 3), guarded by `infra/tests/test_deployment_edge_adr.py`.
- Follow-up: when the hosting ADR is written, it references this one and adds the concrete edge configuration; this ADR becomes Accepted when the PO accepts that the criteria are complete.

## Evidence

- `grep -n -i 'hsts\|strict-transport' docs/decisions/*.md infra/tls/Caddyfile` before this ADR → only ADR index line 43 ("Deployment ADR adds HSTS at the edge"); no criterion anywhere.
- ADR 0029 lines 49 and 66 (forwarded header and hops deferred here).
- `infra/tests/test_deployment_edge_adr.py` (red before this file, then green).
- HSTS max-age of one year and the `preload` caution are **(judgment)**: the HSTS requirement of OWASP ASVS 5.0 is not in this project's verified source set ([AQS/SEC-06] covers V13 configuration only).
