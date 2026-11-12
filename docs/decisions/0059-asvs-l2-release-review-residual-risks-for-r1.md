# 0059. ASVS 5.0 L2 release review: residual risks of R1, accepted for the local prototype only, closed before any deployment or real-user beta

- **Status:** Proposed (draft by the security-privacy-engineer, ST-078c). **The human product owner decides (P19, due 2026-11-12).** Nothing in this ADR is accepted until the PO answers; until then every `Fail` row it lists stays an open risk, and `docs/security/threat-notes-sprint-05.md` keeps "Residual, waiting on P19".
- **Date:** 2026-11-05
- **Deciders:** human product owner (sole decider: accepting a security or privacy risk, ADR README "Risk and cost"; NFR-050.9; working-agreement escalation rules). The engineering-manager records the answer.
- **Proposed by:** security-privacy-engineer
- **Consulted:** principal-engineer (tier 0 reviewer; owner of ADR 0025, ADR 0034 and ADR 0058 text changes), sre-devops-engineer (deployment-edge and Compose items), senior-backend-engineer (mailer, tus checksum, logging items)
- **Related:** story ST-078 (R1 passes an ASVS L2 review, P1); tickets ST-078a, ST-078b, ST-078c (assessment), ST-077 (data classification); NFR-050.1-.9 (`docs/sprints/05/requirements-breakdown.md`); `docs/security/asvs-l2-checklist.md`; `docs/security/threat-notes-sprint-05.md` §8; ADR 0006 (retention), ADR 0025 (magic-link sign-in), ADR 0031 (ASVS 6.3.3 accepted for R1), ADR 0032 (account identity and `AUTH_EMAIL_KEY`), ADR 0034 (deployment-edge criteria), ADR 0051 (R1 is a runnable prototype; privacy flags off), ADR 0057 (SLOs, `obs` profile), ADR 0058 (backups); scorecard goal G05-07 (`docs/sprints/05/goal-scorecard.md`)

## Context and problem statement

NFR-050 makes the ASVS 5.0 L2 review a release gate: every applicable L1/L2 row passes with evidence, or a human accepts its risk in an ADR. ST-078a, ST-078b and ST-078c assessed all 256 rows of `docs/security/asvs-l2-checklist.md` on 2026-11-05. The tool output on that day:

```
python3 docs/security/tools/asvs_status.py docs/security/asvs-l2-checklist.md --level 2 \
  --fail-on not-assessed,fail-without-owner,pass-without-evidence
→ rc 0, "0 problem(s)": 124 Pass, 40 Fail, 92 N/A, 0 not assessed
```

Of the 40 `Fail` rows, 3 are owned by an open fix ticket in this sprint (ST-077: 14.1.1, 14.1.2, 14.2.4), 1 is already accepted (6.3.3, ADR 0031), and **36 need a PO decision**. The threat notes add three more items for the same decision (T5-UT-3, T4-RT-5, the ADR 0031 re-review).

R1 is a runnable prototype on `make up`, not a deployment: no public origin exists (ADR 0034), no real user signs in before the legal review (NFR-070; roadmap §4), and the privacy and quota features run behind default-off flags (ADR 0051 rule 4). Most of the 36 rows are controls that only a deployment can have or prove (TLS at a public edge, a secret store, a log store) or documents that do not exist yet. The question for the PO: **which of these risks may R1 carry, under which conditions, and which must be fixed first?**

## Decision drivers

- NFR-050.9: a residual risk is accepted only by a human decider, in an ADR, with an owner and a closing condition.
- Accepting a risk must not outlive the context that makes it small. R1 has no real users and no public origin; a beta or any deployment changes that (judgment).
- Cheap fixes should not be carried as risk: two rows close with a one-setting or one-line change (judgment).
- Prefer controls proven by a test or a command over documents [AQS/SEC-01]; flag only real risks [EP/ENG-24].
- Legal and privacy-law questions are not decided here; they go to the legal review (P16, NFR-070) [AQS Gaps].

## Considered options

1. **Accept every residual for the local R1 prototype only, with one gate: each must be closed (or re-decided in a new ADR) before any deployment beyond localhost or any real-user beta, whichever comes first.** Good: R1 ships on time; the gates are the moments the risks become real. Bad: two cheap fixes wait; the list is long and must be tracked.
2. **Fix every residual before the R1 release candidate.** Good: a clean L2 review. Bad: about half the rows need a deployment that does not exist (a public origin, a secret store, a log store), so they cannot be closed in Sprint 5 at all; the documentation rows alone are several tickets (judgment).
3. **Option 1, plus fix the two cheap code items in Sprint 6 and the documentation gaps before the first deployment, each as a named ticket (recommended).** Good: the risk register shrinks steadily, every item has an owner and a gate, R1 is not delayed. Bad: more tickets in Sprint 6 refinement.
4. **Do nothing (release R1 without a decision).** Rejected: NFR-050 makes the decision a release gate, and `check_threat_notes.py` fails an "Accepted residual" row without an Accepted ADR id.

## Proposed decision outcome

**Recommended: option 3.** The PO accepts, for the local R1 prototype only, the residuals R-01 to R-19 below except R-05 and R-11, each with its gate; those two "fix" items become Sprint 6 tickets (owner cell: the ticket id); the three threat-note items are decided as stated in R-20 to R-22. On acceptance:

- the engineering-manager sets this ADR to Accepted with the PO's answer per row (accept, fix now, or reject) and the date;
- every checklist owner cell "ADR 0059 draft, P19" becomes "ADR 0059 (accepted residual, gate G-x)"; any row the PO rejects gets a fix ticket id instead;
- the §8 rows of `threat-notes-sprint-05.md` change to "Accepted residual" with this ADR id (and T4-RT-5 in `threat-notes-sprint-04.md`), so `check_threat_notes.py` passes.

### Gates

- **G-DEPLOY:** before any deployment reachable by anyone but the developer (staging, beta, prod). The ADR 0034 deployment check is where most of these are proven.
- **G-BETA:** before any real user signs in (the ADR 0031 re-review point), even on a private deployment.
- **G-S6:** a Sprint 6 ticket; not a carried risk.

### Residual register (ASVS rows; owner cell in the checklist; PO decision per row)

| R-id | ASVS rows | Finding | Risk in R1 (why small now) | Closing action | Gate | Proposed owner | PO decision |
|---|---|---|---|---|---|---|---|
| R-01 | 2.1.3, 15.1.3 | SEC-S5-ASVS-01: no application-wide limits documented (total storage, probe jobs, LLM/GPU spend) | No deployment and no paid GPU/LLM provider exists; per-user and per-IP limits are tested | Document global limits and their alerts (ADR or api-sprint doc) | G-DEPLOY | principal-engineer | |
| R-02 | 3.4.1 | HSTS not sent (dev proxy must not send it) | No public origin | ADR 0034 E1 at the first deployment | G-DEPLOY | sre-devops-engineer | |
| R-03 | 4.1.2 | SEC-S5-ASVS-02: plain-http `/api` calls would be redirected, not refused | No public origin | Amend ADR 0034 E2 so `/api` over http is refused | G-DEPLOY | principal-engineer | |
| R-04 | 4.2.1 | SEC-S5-ASVS-04: no framing (request-smuggling) criterion between the edge and uvicorn | No public origin; one proxy hop on loopback | ADR 0034 criterion and a smuggling probe | G-DEPLOY | sre-devops-engineer | |
| R-05 | 6.5.5 | SEC-S5-ASVS-05: the sign-in link lives 15 min; ASVS caps out-of-band codes at 10 min | Small: single-use link, rate-limited | `MAGIC_LINK_TTL_SECONDS=600` and the FR-001 text (PO owns FR-001) | **G-S6 (fix)** | senior-backend-engineer; PO for FR-001 | |
| R-06 | 5.4.3 | No antivirus scan of uploads (threat-model-v0) | Uploads are only probed by a sandboxed ffprobe and never served as active content (`CSP: sandbox`, `nosniff`); no other user sees them | Decide a scanner or accept for beta in a new ADR | G-BETA | security-privacy-engineer, PO | |
| R-07 | 6.1.1 | SEC-S5-ASVS-07: lockout reasoning not written down | Documentation gap; older links stay valid, so no real lockout (ST-078b) | Text in api-sprint-01 §2.4 or ADR 0025 | G-DEPLOY | principal-engineer | |
| R-08 | 7.1.1 | SEC-S5-ASVS-06: 30 d / 7 d session lifetimes lack a NIST SP 800-63B justification | Documentation gap; ADR 0031 kept these values | Justification or new values in ADR 0025 | G-BETA | principal-engineer | |
| R-09 | 7.4.5 | SEC-S5-ASVS-08: no administrator can end a user's sessions | No real users | Admin CLI `end-sessions --account` or a runbook | G-BETA | senior-backend-engineer | |
| R-10 | 7.5.2 | SEC-S5-ASVS-09: users cannot list or end their other sessions | No real users; product scope | FR for session management, or accept for beta | G-BETA | product-manager, PO | |
| R-11 | 11.4.3 | SEC-S5-ASVS-12: the tus checksum extension accepts SHA-1 | The uploader checksums their own bytes, so a collision helps no attacker; our client sends SHA-256 only | Drop `sha1` from `ALGORITHMS` and api-sprint-01 §6.1 (contract change, tier 2) | **G-S6 (fix)** | senior-backend-engineer | |
| R-12 | 11.1.1, 11.1.2 | SEC-S5-ASVS-11: no key-management policy and no cryptographic inventory | Few keys, all local; the inventory draft is in `docs/sprints/05/decisions/ST-078c.md` | `docs/security/crypto-inventory.md` (planned) with owners, rotation and lifecycle per key | G-DEPLOY | security-privacy-engineer | |
| R-13 | 12.1.1, 12.1.2, 12.2.1, 12.2.2, 12.3.1, 12.3.3, 12.3.4 | SEC-S5-ASVS-13: ADR 0034 has no TLS version, cipher, public-certificate or internal-TLS criteria; backing services are plain text on the Compose network | Everything runs on one host; only `web-tls` is published, on loopback | ADR 0034 criteria (TLS 1.2+ with 1.3 preferred, cipher policy, public certificates, TLS or a private network to managed DB, object store and OTLP) and their checks | G-DEPLOY | sre-devops-engineer, principal-engineer | |
| R-14 | 12.3.1 | SEC-S5-ASVS-14: the mailer speaks plain SMTP only (`smtp://`, no STARTTLS), so a sign-in link would cross a real relay in clear text | Mail goes to a local Mailpit only | `smtps://` or required STARTTLS in `SmtpMailer`, refused in staging/prod without it, with a test | G-DEPLOY | senior-backend-engineer | |
| R-15 | 13.1.1 | SEC-S5-ASVS-15: the communication inventory misses the SMTP relay, purge, backup and off-site targets, and the `obs` profile | Documentation gap | Update threat-model §3 (or a new data-flow doc) | G-DEPLOY | security-privacy-engineer, sre-devops-engineer | |
| R-16 | 13.2.1, 13.2.2, 13.3.1, 13.3.2 | SEC-S5-ASVS-16 (F-1 remainder): API, mailer and purge share the Postgres bootstrap superuser login and the API and purge the `Admin` S3 identity; static passwords; no secret store | One host, no real data; the worker is already least-privilege (ST-042) | Per-service DB roles and S3 identities, a secret store, short-lived credentials where the platform offers them | G-DEPLOY | sre-devops-engineer, senior-backend-engineer | |
| R-17 | 13.2.4, 13.2.5 | SEC-S5-ASVS-17: no egress allowlist for the `edge` services | Outbound hosts come only from configuration, never from a request | Network egress policy at the deployment, or an internal network plus a proxy | G-DEPLOY | sre-devops-engineer | |
| R-18 | 13.4.5 | SEC-S5-ASVS-18 (T-INF-2): `/readyz` is reachable anonymously through `/api` and names the dependencies | Loopback only | Block `/api/readyz` at the edge or move it to an internal port | G-DEPLOY | sre-devops-engineer | |
| R-19 | 15.1.1, 15.3.2, 16.1.1, 16.2.3, 16.3.3, 16.4.2, 16.4.3 | SEC-S5-ASVS-19 (no remediation time frames), -20 (ffprobe sets no redirect limit), -21 (no log inventory or security-event catalogue), -22 (no log store or off-host shipping) | The audit gates already block every known Python and critical npm vulnerability; the worker cannot leave its internal network; logs hold ids only (IT-00-15) | Time frames in ci-cd.md; redirect limit or a test that a 3xx is refused; log inventory and event catalogue; log shipping with access control at the deployment | G-DEPLOY | sre-devops-engineer (19, 22), senior-ml-cv-engineer (20), security-privacy-engineer (21) | |
| R-20 | 6.3.3 | ADR 0031 re-review: single-factor magic link | ADR 0031 is Accepted for R1 | Re-confirm for R1; re-review stays due before the beta | G-BETA | PO | |
| R-21 | — (T4-RT-5) | A signed media URL issued before a purge keeps playing for its TTL (≤ 15 min) | Bearer URL is short-lived, never logged (IT-00-15) | Accept (TTL ≤ 15 min is the design, NFR-055) | — | PO | |
| R-22 | — (T5-UT-3) | Interim consent wording used for recruitment before the legal review | Recording sessions stay blocked until P16 answers | Accept for recruitment wording only; legal review decides the rest | P16 | PO | |

Not in this register: 14.1.1, 14.1.2, 14.2.4 are owned by ST-077 (PR #213, open), a fix ticket in this sprint; if ST-077 does not merge before VERIFY-05, the engineering-manager adds them here as R-23.

## Consequences

- Good: the release gate has one decision with an owner and a gate per risk; nothing is accepted silently or forever.
- Good: the list is a ready-made deployment checklist: 13 of the 17 accepted items close at G-DEPLOY (most through ADR 0034), the other 4 at G-BETA.
- Bad: R1's L2 review is "pass with 34 rows accepted as residual risk" (plus 6.3.3 under ADR 0031 and the 2 rows fixed in Sprint 6), not a clean pass; the release notes (ST-082) must say so.
- Bad: the gates rely on people remembering them. Mitigation: the ADR 0034 deployment check lists every G-DEPLOY row, and the beta-entry review lists every G-BETA row (judgment).

## Evidence

- Checklist and counts: the `asvs_status.py` command above, run 2026-11-05 on the ST-078c branch (base `2ed79c68`).
- Each row's evidence command or test: `docs/security/asvs-l2-checklist.md`; the runs are in `docs/sprints/05/decisions/ST-078a.md`, `ST-078b.md` and `ST-078c.md`.
- Threat-note items: `docs/security/threat-notes-sprint-05.md` §8.
- R1 context: ADR 0051 rule 4 (flags off), ADR 0034 (no public origin), ADR 0031 (6.3.3 accepted for R1).

## PO answer

_(to be filled by the engineering-manager with the PO's own words, date and the per-row decisions)_
