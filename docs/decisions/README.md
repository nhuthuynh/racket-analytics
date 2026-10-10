# Decision Log (Architecture Decision Records)

Every significant decision made by the agent team or the human product owner is recorded here as an ADR,
together with the **evidence** behind it and the **alternatives** considered.

## Why

- An ADR records **one** decision, its rationale, the options with their pros and cons, and timestamps [EP/ENG-09].
- This project uses the MADR structure (Markdown Architectural Decision Records). MADR files live in
  `docs/decisions/` and are named `nnnn-title-with-dashes.md` [EP/ENG-10].
- Design docs and decision logs live in the repo and are reviewed as PRs [DPA/DESIGN-15].

The citation prefixes (EP, AQS, DPA, DOM) are explained in `docs/process/working-agreement.md` §0.

## What counts as "significant" (judgment)

Write an ADR for any of the following:

- **Technology and architecture:** a choice of technology, library, model, dataset or licence; a change to
  architecture, a context boundary, an API contract or the data schema; or an NFR target such as an SLO,
  a coverage threshold or an eval tolerance.
- **Domain:** an interpretation of a pickleball rule or of coaching content.
- **Process:** a change to the working agreement, DoD or DoR.
- **Risk and cost:** accepting a risk (security, privacy, quality) or a cost commitment.
- **Changing course:** reversing or superseding an earlier decision.
- **Escalations:** anything escalated to the human product owner, together with their answer.

## Rules

1. Number ADRs sequentially with four digits and never reuse a number: `0001-...`, `0002-...` [EP/ENG-10].
2. **Evidence is mandatory.** Every claim cites one of the following:
   - a verified research source, e.g. `[AQS/SEC-09]`;
   - data, such as eval metrics or benchmarks with their dataset version;
   - test results, given as the command and its output, or a CI link.

   Anything else is labelled **(judgment)**. Never invent URLs.
3. **Alternatives are mandatory.** List at least two considered options, including "do nothing" where it
   applies, each with pros and cons.
4. **Do not rewrite history.** Once an ADR is Accepted, only dated notes may be appended. A changed
   decision gets a new ADR, and the old one becomes `Superseded by NNNN` [EP/ENG-09].
5. The **deciders** are named by role (agent name, or "human product owner").
6. An ADR from a read-only agent (security-privacy-engineer) is returned as a draft and saved by the
   engineering-manager.
7. Statuses: `Proposed`, `Accepted`, `Rejected`, `Deprecated`, `Superseded by NNNN`.

## Template

Copy this into `docs/decisions/NNNN-short-title.md`:

```markdown
# NNNN. <Short title of the decision>

- **Status:** Proposed | Accepted | Rejected | Deprecated | Superseded by NNNN
- **Date:** YYYY-MM-DD
- **Deciders:** <agent roles / human product owner>
- **Consulted:** <agent roles>
- **Related:** <story IDs, FR/NFR IDs, other ADRs>

## Context and problem statement
<What is the situation and what question must be answered? 2-5 sentences.>

## Decision drivers
- <driver, e.g. "NFR-SEC-01 BOLA on every resource ID">
- <driver, e.g. "GPU cost <= 2 GPU-min per match-min (spec §8)">

## Considered options
1. <Option A>
2. <Option B>
3. <Option C / do nothing>

## Decision outcome
Chosen option: "<Option X>", because <justification tied to drivers>.

## Pros and cons of the options
### Option A
- Good, because ...
- Bad, because ...
### Option B
- ...

## Consequences
- Good: ...
- Bad / trade-offs accepted: ...
- Follow-up work: ...

## Evidence
| Claim | Evidence | Type |
|---|---|---|
| <claim> | [AQS/SEC-09] | verified source |
| <claim> | `pytest tests/integration/test_bola.py` -> 42 passed (CI run link) | test result |
| <claim> | HOTA 61.2 on gold-set v3 (docs/evals/2026-11-01.md) | data |
| <claim> | (judgment) | judgment |

## Confirmation
<How will we know the decision is implemented and working? e.g. test, eval gate, metric, review.>

## Notes
<Dated notes appended after acceptance; never edit the sections above once Accepted.>
```

## Index

| # | Title | Status | Date |
|---|---|---|---|
| 0001 | [Adopt ADRs and an AI agent team with a defined working agreement](0001-adopt-adrs-and-agent-team.md) | Accepted (PO ratified 2026-10-05) | 2026-10-03 |
| 0002 | [MVP scope: walking skeleton and release slicing](0002-mvp-scope-walking-skeleton-release-slicing.md) | Accepted (PO 2026-10-05) | 2026-10-03 |
| 0003 | [Weakness ranking by rallies lost](0003-weakness-ranking-by-rallies-lost.md) | Accepted (PO 2026-10-05) | 2026-10-03 |
| 0004 | [Measurable definitions for the M2 and M3 accuracy targets](0004-accuracy-target-definitions-m2-m3.md) | Accepted (PO 2026-10-05) | 2026-10-03 |
| 0005 | [Low-sample and efficacy-claim rules](0005-low-sample-and-efficacy-claim-rules.md) | Proposed | 2026-10-03 |
| 0006 | [Retention and deletion defaults](0006-retention-and-deletion-defaults.md) | Accepted as interim (PO 2026-10-05) | 2026-10-03 |
| 0007 | [Delivery sequencing in vertical slices](0007-delivery-sequencing-vertical-slices.md) | Accepted (PO 2026-10-05) | 2026-10-03 |
| 0008 | [Stack confirmation for Sprint 0](0008-stack-confirmation-for-sprint-0.md) | Accepted (Sprint 0) | 2026-10-03 |
| 0009 | [Rules-engine readiness split](0009-rules-engine-readiness-split.md) | Accepted (PO 2026-10-05) | 2026-10-03 |
| 0010 | [Estimation and capacity model](0010-estimation-and-capacity-model.md) | Accepted | 2026-10-03 |
| 0011 | [tus server: tus 1.0.0 core inside FastAPI, not a tusd sidecar](0011-tus-server-fastapi-core.md) | Accepted (Sprint 0) | 2026-10-03 |
| 0012 | [Red-first tests reach production code through one QA-owned seam contract](0012-red-first-test-seam-contract.md) | Proposed | 2026-10-03 |
| 0013 | [Agent hooks: deterministic gates that never wedge a session](0013-agent-hooks-design.md) | Proposed | 2026-10-03 |
| 0014 | [CI merge gates: fail closed, one required check, pinned actions, SBOM-based licence gate](0014-ci-merge-gates-fail-closed.md) | Proposed | 2026-10-03 |
| 0015 | [CV licence posture: MIT/Apache code by default, pretrained weights judged by their training data, no AGPL](0015-cv-licence-posture.md) | Accepted (PO 2026-10-05, OQ-12) | 2026-10-03 |
| 0016 | [Design tokens are a JSON source of truth with an executable contrast proof](0016-design-tokens-and-contrast-proof.md) | Proposed | 2026-10-03 |
| 0017 | [Job runtime: a hand-written `SKIP LOCKED` queue with leases, not procrastinate](0017-job-runtime-skip-locked-queue-with-leases.md) | Proposed | 2026-10-03 |
| 0018 | [Web CSP: per-request nonce in middleware, no inline-script allowance](0018-web-csp-per-request-nonce.md) | Proposed | 2026-10-03 |
| 0019 | [The Next.js `/api` rewrite is for dev and CI only; uploads use 8 MiB chunks](0019-web-api-rewrite-limits.md) | Accepted (amended 2026-10-05) | 2026-10-03 |
| 0020 | [Probe stage sandbox: a pinned LGPL ffprobe, per-process limits inside an internal-network container](0020-probe-sandbox-and-lgpl-ffprobe.md) | Proposed | 2026-10-03 |
| 0021 | [ffprobe may demux only the MP4/MOV family (input-format allowlist)](0021-probe-input-format-allowlist.md) | Proposed | 2026-10-03 |
| 0022 | [Review loop: route findings to their owner role, smoke-test the integrated stack before review, one story per commit](0022-review-loop-routing-and-integration-smoke.md) | Accepted (PO 2026-10-05) | 2026-10-03 |
| 0023 | [Product-owner decisions 2026-10-05: accept all open-question recommendations](0023-product-owner-decisions-2026-10-05.md) | Accepted | 2026-10-05 |
| 0024 | [Match participants are per-match nickname slots inside the `Match` aggregate](0024-match-participants-as-per-match-nicknames.md) | Accepted | 2026-10-05 |
| 0025 | [Magic-link sign-in: token in the URL fragment, exchanged by POST; 30-day/7-day sessions](0025-magic-link-sign-in-design.md) | Accepted (Sprint 1; 6.3.3 residual risk needs PO) | 2026-10-05 |
| 0026 | [Nightly quality results and SLI metrics](0026-nightly-quality-results-and-sli-metrics.md) | Proposed (Sprint 1, ST-024) | 2026-10-05 |
| 0027 | [Sign-in emails are sent by a worker outside the media sandbox (`WORKER_STAGES`)](0027-sign-in-mail-worker-outside-the-media-sandbox.md) | Proposed (Sprint 1, ST-013) | 2026-10-05 |
| 0028 | [Phone-browser uploads: "resume on return", no background-upload promise](0028-phone-browser-upload-resume-on-return.md) | Proposed (SPIKE-06, partial data) | 2026-10-05 |
| 0029 | [The dev and E2E stack is served over https (`web-tls`), not given an insecure cookie](0029-dev-and-e2e-stack-served-over-https.md) | Accepted (Sprint 1, WebKit sign-in blocker) | 2026-10-05 |
| 0030 | [Review loop: a disposition per finding, isolated evidence, M/L stories sliced before they are built](0030-finding-disposition-isolated-evidence-and-pre-sliced-stories.md) | Accepted (EM, retro 1) | 2026-10-05 |
| 0031 | [ASVS 6.3.3: residual risk of the single-factor magic link, or passkeys in R1](0031-asvs-6-3-3-single-factor-magic-link-residual-risk.md) | Accepted (human PO, 2026-10-06: option 1, re-review before any real-user beta) | 2026-10-05 |
| 0032 | [Account identity is the normalised address, not the HMAC `email_key` (amends 0025)](0032-account-identity-is-the-address-not-the-email-key.md) | Accepted (security-privacy-engineer sign-off recorded 2026-10-05; code is ST-013b, gate before any non-dev deployment) | 2026-10-05 |
| 0033 | [Reviewers write their own finding rows, goal methods are dry-run, evidence cleans up after itself](0033-reviewer-written-finding-rows-dry-run-methods-and-self-cleaning-evidence.md) | Accepted (EM, retro 1 final close) | 2026-10-05 |
| 0034 | [Deployment edge acceptance criteria (HSTS, forwarded headers, exposed ports)](0034-deployment-edge-acceptance-criteria.md) | Proposed (sre-devops-engineer; PO accepts before the first non-dev deployment) | 2026-10-06 |
| 0035 | [Gold-set manifest v1 and Full Tag labels v1, checked by racket-manifest-check](0035-gold-set-manifest-v1-and-full-tag-labels-v1.md) | Proposed (senior-ml-cv-engineer, ST-040) | 2026-10-06 |
| 0036 | [Local goal evidence runs in Chrome for Testing, a browser that decodes H.264](0036-local-h264-evidence-browser-chrome-for-testing.md) | Accepted (EM, review round 2, SRE-S2-05 / QA-RV1-07) | 2026-10-06 |
| 0039 | [Sprint 3 tickets ship as ticket PRs, each reviewed by the principal engineer and a senior engineer before merge](0039-sprint-3-tickets-ship-as-ticket-prs-with-principal-and-senior-review.md) | Accepted (EM, review round 1, PE-R1S3-01 / QA-R1S3-04; PO may change the start via P13) | 2026-10-07 |
| 0038 | [The purge/expiry job runs as its own scheduled Compose service with the app identity](0038-purge-job-runs-as-its-own-scheduled-compose-service.md) | Accepted (principal-engineer, PE-3; proposed by sre-devops-engineer) | 2026-10-07 |
| 0040 | [Metric snapshots are recomputed after the scoring commit, with read repair as the retry](0040-metric-snapshots-recompute-after-commit-with-read-repair.md) | Accepted (principal-engineer, PE-2; review D3 open) | 2026-10-07 |
| 0041 | [The low-sample thresholds have one source: the versioned metric dictionary](0041-low-sample-thresholds-come-from-the-metric-dictionary.md) | Accepted (principal-engineer, PE-2; amends ADR 0005's "config" clause) | 2026-10-07 |
| 0042 | [Deletion hides with a tombstone; the purge deletes objects before rows, in idempotent passes](0042-deletion-tombstones-now-purge-objects-before-rows.md) | Accepted (principal-engineer, PE-3; SEC-1 may amend) | 2026-10-07 |
| 0043 | [Sprint 3 UX: deletion confirmed in a dialog without a typed word; "Show me" rallies open on the score sheet; a Full Tag rally is saved only with its ending](0043-sprint-3-ux-deletion-dialog-evidence-opens-score-sheet-full-tag-ending-saves.md) | Proposed (principal-designer, PD-1; Accepted when DR-03 holds) | 2026-10-07 |
| 0045 | [Purge deletes only shape-checked keys of the claimed match; owned writes lock the live account; snapshot writes lock the live match](0045-purge-keys-fail-closed-owned-writes-lock-the-account-snapshots-lock-the-match.md) | Accepted (principal-engineer, review round 2; amends 0040 and 0042; SEC-S3-TM-01/-02/-05) | 2026-10-07 |
| 0037 | [A review round closes only when every finding has a row; decider roles get scheduled briefs; human-gated goal items agreed with the PO at planning](0037-review-round-reconciliation-decider-roles-and-human-gated-goal-items.md) | Accepted (EM, retro 2) | 2026-10-06 |
| 0044 | [`coach-reviewed` means the coach's hand count equals the product; the second recompute and the κ check gate `verified`](0044-coach-reviewed-means-hand-count-equals-product-second-recompute-gates-verified.md) | Accepted (pickleball-domain-coach, COACH-1) | 2026-10-07 |
| 0046 | [Red-first E2E specs carry a `@red-until-<story>` tag; CI lists them in a non-gating step with a stale-tag check](0046-red-first-e2e-specs-are-tagged-red-until-and-listed-not-gated.md) | Accepted with one amendment (EM, Sprint 3 close; proposed by sre-devops-engineer) | 2026-10-07 / 2026-10-08 |
| 0047 | [Gates run before the build; review and verification rounds never overlap; CI at every round head; ticket branches from planning; agents never write PO decisions](0047-gate-phase-before-build-serial-rounds-ci-each-round-ticket-branches-at-planning.md) | Accepted (EM, retro 3; PO may veto at the 2026-11-27 review) | 2026-10-08 |
| 0048 | [The integration suite runs in parallel workers on one cluster, with the base database migrated first](0048-integration-suite-runs-in-parallel-workers-with-the-base-database-migrated-first.md) | Accepted (2026-10-08, principal-engineer, PR #15 review r1) | 2026-10-08 |
| 0049 | [The domain unit suite runs in parallel workers inside its 10 s budget](0049-domain-unit-suite-runs-in-parallel-workers-inside-its-10-s-budget.md) | Proposed | 2026-10-09 |

Adversarial review findings and their fixes are logged in [review-log.md](review-log.md). An index with evidence summaries is in [decision-log.md](decision-log.md). Index rows 0016 and 0017 were added by the engineering-manager on 2026-10-03; they had been missing.
