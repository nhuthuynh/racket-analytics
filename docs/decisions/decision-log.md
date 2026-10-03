# Decision log: index of all ADRs

- **Maintained by:** engineering-manager (A for log completeness, working-agreement §4). Last updated 2026-10-03, after Sprint 0 review round 3.
- **Rules and template:** [README.md](README.md). This page is an index with a one-line evidence summary per ADR; the ADR file is authoritative.
- **Small decisions:** [Sprint 0 decision log](../sprints/00/decision-log.md) (dated rows: who, decision, evidence, reasoning).
- **Reviews:** [review-log.md](review-log.md) (adversarial review of docs and agent definitions) and [Sprint 0 review rounds](../sprints/00/review-rounds.md) (code review findings, fixes and evidence for rounds 1-2; round-3 findings are summarised in [sprint-report.md](../sprints/00/sprint-report.md) §6).
- **Blockers:** [Sprint 0 blockers](../sprints/00/blockers.md).

## Index

All dates are 2026-10-03. "PO" means the human product owner.

| # | Title | Status | Evidence summary | Needs |
|---|---|---|---|---|
| [0001](0001-adopt-adrs-and-agent-team.md) | Adopt ADRs and an AI agent team with a working agreement | Accepted (pending PO ratification) | MADR and ADR practice [EP/ENG-09, EP/ENG-10]; agent-team practices [DPA/AI-*]; 17 evidence rows | PO ratifies at the Sprint 0 review |
| [0002](0002-mvp-scope-walking-skeleton-release-slicing.md) | MVP scope: walking-skeleton R1 on manual tagging, then automation by release | Proposed | Spec milestones vs research gaps; 11 evidence rows | PO decision OQ-02 |
| [0003](0003-weakness-ranking-by-rallies-lost.md) | Rank weaknesses by rallies lost per game, split serve/receive | Proposed | Depends on an unverified rule [DOM G1]; 6 rows | PO (OQ-08); coach verification |
| [0004](0004-accuracy-target-definitions-m2-m3.md) | Measurable M2/M3 accuracy target definitions | Proposed | Metric definitions from research; 8 rows | PO (OQ-09) |
| [0005](0005-low-sample-and-efficacy-claim-rules.md) | Low-sample flagging and efficacy claims with Wilson intervals | Proposed | Statistical method plus thresholds (judgment); 5 rows | Coach review at the first analytics retro |
| [0006](0006-retention-and-deletion-defaults.md) | Interim retention, expiry and deletion defaults | Proposed | Legal adequacy unverified [AQS Gaps]; 8 rows | PO (OQ-07), legal review |
| [0007](0007-delivery-sequencing-vertical-slices.md) | Sprint 0 foundations, then one vertical slice per sprint | Proposed | Sequencing rationale; 15 rows | PO ratifies at the Sprint 0 review |
| [0008](0008-stack-confirmation-for-sprint-0.md) | Stack confirmation: spec stack, Postgres queue, Apache-licensed S3 store, MIT/Apache test tooling | Accepted (Sprint 0) | 24 rows. Dated notes: package `racket`; SeaweedFS 3.97 parity green locally and in Compose (`test_object_store_parity.py` 7 passed; IT-00-16 4 passed); SPIKE-09 504-888 jobs/s with 0 double claims | CV stack waits for SPIKE-01 / OQ-12 |
| [0009](0009-rules-engine-readiness-split.md) | Rules-engine split: parameterised engine Ready now; USAP-2026 preset waits for verification | Proposed | Rulebook fetch → 403 (blockers.md); 10 rows | PO ratifies before Sprint 1 planning |
| [0010](0010-estimation-and-capacity-model.md) | Estimation: t-shirt sizes → units, 2 streams per lane, load factor | Accepted | 8 rows (mostly judgment). Retro-0 note: 19 of 28 units implemented, 0 meet the full DoD; Sprint 2 rule uses the DoD ratio | PO confirms the PO-time assumption |
| [0011](0011-tus-server-fastapi-core.md) | tus 1.0.0 core inside FastAPI, not a tusd sidecar | Accepted (Sprint 0) | tusd docs fetched and hashed (hooks, locks, S3 backend); IT-00-06/07/08 and the tus regression suites are green | — |
| [0012](0012-red-first-test-seam-contract.md) | Red-first tests reach production code through one QA-owned seam contract | Proposed | 74 tests red with "RED until ST-xxx", then green after ST-005..009 (backend 439 passed) | Accept at the Sprint 0 review (BE confirmed the seams unchanged) |
| [0013](0013-agent-hooks-design.md) | Agent hooks: deterministic gates that never wedge a session | Proposed | Hook tests 86 passed; live demo (`.env` write → exit 2; Stop on a failing test → exit 2) | Security and QA review |
| [0014](0014-ci-merge-gates-fail-closed.md) | CI gates fail closed, one required check, SHA-pinned actions, SBOM licence gate | Proposed | `actionlint` rc=0; workflow tests green; SHAs from `git ls-remote`. **Never run on GitHub** | First CI run (QA-R3-02); QA and security review |
| [0015](0015-cv-licence-posture.md) | CV licence posture: MIT/Apache code by default, weights judged by training data, no AGPL | Proposed | 26 repo licence fetches (21 hit), sha256 hashed; non-GitHub sources egress-blocked and marked unverified | **PO decides OQ-12**; PE and security review |
| [0016](0016-design-tokens-and-contrast-proof.md) | Design tokens in JSON with an executable contrast proof | Proposed | `contrast_check.py` → 55/55 pairs pass (after a real 1.07:1 focus-ring defect was fixed) | Design review at the ST-010 PR |
| [0017](0017-job-runtime-skip-locked-queue-with-leases.md) | Job runtime: hand-written `SKIP LOCKED` queue with leases, not procrastinate | Proposed | procrastinate docs fetched and hashed (no SIGTERM requeue); SPIKE-09 numbers; worker crash suites green | Accept at the ST-007 review (PE) |
| [0018](0018-web-csp-per-request-nonce.md) | Web CSP: per-request nonce, no inline-script allowance | Proposed | Playwright CSP probe: no violations; security-header spec green | Security review of ST-010 |
| [0019](0019-web-api-rewrite-limits.md) | Next.js `/api` rewrite is dev/CI only; 8 MiB upload chunks | Proposed | 64 MiB PATCH through the rewrite → 500 "Request body exceeded 10MB"; 8 MiB → 200 | **PE accepts and amends api-sprint-00 §8/§9 (R3-03)** |
| [0020](0020-probe-sandbox-and-lgpl-ffprobe.md) | Probe sandbox: pinned LGPL ffprobe, rlimits, internal-network container | Proposed | sha256 check OK; no `--enable-gpl`; IT-00-10 on Compose 2 passed (later 12 with the strict file) | Security confirms the LGPLv3 reading |
| [0021](0021-probe-input-format-allowlist.md) | ffprobe demuxes only the MP4/MOV family | Proposed | DASH canary fetch reproduced, then blocked by `-format_whitelist`; the fixture still probes. Evidence is in a section rather than the template's table | Security accepts (round-1 review) |
| [0022](0022-review-loop-routing-and-integration-smoke.md) | Review loop: owner routing, integration smoke before review, one story per commit | Accepted for Sprint 1 | Round-3 blockers were non-code items open since round 1; 3 integration-only blockers in round 1; two ~15k-line commits | PO may veto at the review |

## Gaps found in this pass (2026-10-03)

- ADRs 0016 and 0017 were missing from the README index. The EM added them.
- 17 of 22 ADRs are still Proposed. The ones that block Sprint 1 are 0002, 0007 and 0009 (PO), and 0019 (PE).
- ADR numbers had collisions while lanes worked in parallel (0012/0013/0014, with 0011 reserved). Lanes resolved them by checking the folder; the fix is recorded in the Sprint 0 decision log.
