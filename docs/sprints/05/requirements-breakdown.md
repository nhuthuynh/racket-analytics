# Sprint 5 requirements breakdown (atomic items)

- **Written:** 2026-11-03 at Sprint 5 planning (ticket PLAN-05) by the engineering-manager, from the business-analyst's kickoff breakdown advice and the per-role advice in [`kickoff.md`](kickoff.md). The business-analyst owns this file from here: ticket **BA-5** re-checks every row against the Definition of Ready and records the DoR verdict per story (§5).
- **Rules applied:** `docs/process/definition-of-ready.md` "Atomic breakdown (stories pulled from Sprint 5 on)" [ASB/REQ-01, ASB/REQ-12, ASB/REQ-19, ASB/REQ-07]. One item = one observable behaviour **or** one measurable threshold. FR items are Gherkin `Rule:` lines `FR-nnn.Rk` with a happy and a negative Example. NFR items are numbered `NFR-nnn.<n>` under the existing register id (no new register rows) and name characteristic, metric and unit, method (tool, load, measuring point, configuration), target and sample or window. Process items have no FR/NFR id; they use `PRC-<story>.<n>`, release items `REL-1.<n>`, demo items `DEMO-1.<n>`.
- **Id format** (agreed with the senior-qa-engineer for `measurelib._FINDING_ID`, retro 4 M15): `<PREFIX>-<number>.<n>` or `FR-nnn.R<k>`. `QA-DOR-CHECK` parses this file and fails on any row that breaks it.
- **Test levels:** unit, component, integration (IT, with the boundary named), E2E (Playwright project named), perf (Locust), ops-drill (scripted run on a Compose project), promtool (Prometheus rule unit test), doc-check (`CI-DOC-CHECK` job), human (a "not met: waiting on P-n" row; never an agent goal).
- **Human-only items** are marked **human (P-n)** here and are rows of `goal-scorecard.md` §5, not goal metrics (PO P12 option b). They are never decomposed into agent proxies that could be reported as met.

## 1. NFR items

### NFR-010 API read latency at 50 RPS (R1 gate) → story ST-074, ticket ST-074

Common method for .1-.9: Locust 2.46.7 (ADR 0008) at the client, open loop, **achieved rate ≥ 49.5 RPS** (else the run is invalid, not passed), 1 min warm-up excluded, 5 min measured window, on the Compose stack started by `make up` with **all four FEATURE_* flags on**, 3 runs, every run must pass; one seeded demo account per user; the command is the CI `perf-r1` step's command, pinned by `QA-PIN-05`.

| Id | Characteristic | Metric and unit | Target | Test level | Scorecard |
|---|---|---|---|---|---|
| NFR-010.1 | latency, `GET /matches/{id}` | p95 ms | ≤ 300 | perf | G05-01 |
| NFR-010.2 | latency, `GET /matches/{id}` | p99 ms | ≤ 800 | perf | G05-01 |
| NFR-010.3 | latency, score sheet (`score-sheet` route of `locustfile_sprint04.py`) | p95 ms | ≤ 300 | perf | G05-01 |
| NFR-010.4 | latency, score sheet | p99 ms | ≤ 800 | perf | G05-01 |
| NFR-010.5 | latency, dashboard reads (`_dashboard_paths`) | p95 ms | ≤ 300 | perf | G05-01 |
| NFR-010.6 | latency, dashboard reads | p99 ms | ≤ 800 | perf | G05-01 |
| NFR-010.7 | latency, `GET /me/plan` | p95 ms | ≤ 300 | perf | G05-01 |
| NFR-010.8 | latency, `GET /me/plan` | p99 ms | ≤ 800 | perf | G05-01 |
| NFR-010.9 | errors under the same load | non-2xx responses / all, % | ≤ 0.5 | perf | G05-01 |

Label: pre-production evidence on a local stack, not production (sre-devops-engineer kickoff).

### NFR-041 API availability and NFR-042 upload completion (R1) → story ST-075, tickets ST-075a/b/c/d

Burn-rate multipliers and windows are judgment (SRE workbook unverified, AQS Gaps); the PE-5a ADR fixes them before ST-075c starts.

| Id | Characteristic | Metric and unit | Method | Target | Test level | Ticket | Scorecard |
|---|---|---|---|---|---|---|---|
| NFR-041.1 | SLI definition | non-5xx / all, 429 excluded from both | `slis.availability()` unit test (exists, ST-024) re-run; Prometheus query in `docs/ops/sli-metrics.md` evaluated by promtool on a synthetic series | query value equals the pure function on the same series | unit + promtool | ST-075c | G05-02 |
| NFR-041.2 | SLO record | target and window written | `docs/ops/slo.md` row | 99.5 % over 30 days, 429 excluded | doc-check | ST-075c | G05-02 |
| NFR-041.3 | fast-burn alert | alert state on a synthetic 5xx series | promtool rule test | `ApiAvailabilityFastBurn` firing within the PE-5a window on a 10 % 5xx series; not firing on a 0.1 % series (negative) | promtool | ST-075c | G05-02 |
| NFR-041.4 | slow-burn alert | as .3 | promtool | `ApiAvailabilitySlowBurn` firing on a 1 % series held 6 h; not firing on 0.3 % (negative) | promtool | ST-075c | G05-02 |
| NFR-041.5 | live alert path | minutes from injected fault to alert `firing` in Prometheus `/api/v1/alerts` | ops-drill: `scripts/ops/inject_5xx.py` drives a 5xx burst through the ADR 0012 seam (`RACKET_FAULT_INJECTION=api:5xx_on_header`, honoured only under `APP_ENV=test`) on the Compose `obs` profile | firing ≤ 10 min; 0 alerts on a clean 10 min run (negative) | ops-drill | ST-075c (drill), ST-075d (seam) | G05-02 |
| NFR-041.6 | fault seam inert outside tests | 500 responses to `X-Racket-Fault: 5xx` with the seam value set and `APP_ENV` ≠ test | unit + IT-05-12 | 0 (negative); seam honoured only under `APP_ENV=test` | unit + integration | ST-075d | G05-02 |
| NFR-042.1 | SLI definition | completed / (created − rejected − cancelled) | `slis.upload_completion()` unit test (exists) + promtool on a synthetic series | as NFR-041.1 | unit + promtool | ST-075c | G05-02 |
| NFR-042.2 | SLO record | target and window | `docs/ops/slo.md` | 99.0 % over 30 days | doc-check | ST-075c | G05-02 |
| NFR-042.3 | fast-burn alert | alert state | promtool | `UploadCompletionFastBurn` firing on a 20 % failure series; not on 0.5 % | promtool | ST-075c | G05-02 |
| NFR-042.4 | slow-burn alert | alert state | promtool | `UploadCompletionSlowBurn` firing on 3 % held 6 h; not on 0.5 % | promtool | ST-075c | G05-02 |
| NFR-042.5 | metrics reach the backend | `racket_upload_sessions_total` and `http_server_request_duration_seconds_count` series present in Prometheus after one demo upload | ops-drill on the `obs` profile | both series > 0 | ops-drill | ST-075b | G05-02 |
| NFR-069.1 | pseudonymous metrics and logs | metric attributes or log lines with an email, nickname or signed URL during the SLO drill | IT: log scanner over the API log and the Prometheus label set after the drill | 0 | integration | ST-075a | G05-06 |
| NFR-049.1 | error-budget policy text | policy exists with trigger, action and owner | `docs/ops/error-budget-policy.md` | drafted; **PO acceptance is human (P17)** | doc-check | ST-075c | §5 P17 |

### NFR-045 durability and recovery (R1, before beta) → story ST-076, tickets ST-076a/b/c

Method for .1-.3: `python3 scripts/ops/restore_drill.py --project racket-drill05 --json <out>` on a fresh Compose project: seed demo data, take a backup with the ST-076a service, record before-state, destroy the Postgres and object-store volumes, restore, wait for API health, re-check.

| Id | Characteristic | Metric and unit | Target | Test level | Ticket | Scorecard |
|---|---|---|---|---|---|---|
| NFR-045.1 | RPO | age of the newest restorable backup at drill start, from backup metadata, hours | ≤ 24 | ops-drill (+ unit on the age function; negative: a 25 h old backup fails) | ST-076a, ST-076c | G05-03 |
| NFR-045.2 | RTO | wall time from empty volumes to `/healthz` 200 **and** NFR-045.3 passing, minutes | ≤ 240 | ops-drill | ST-076c | G05-03 |
| NFR-045.3 | confirmed corrections lost | row count and SHA-256 of the confirmed-corrections table, before vs after | equal (0 lost); a planted deleted row makes the check fail (negative) | integration + ops-drill | ST-076b | G05-03 |
| NFR-045.4 | object store restored | count and hash of objects under the demo account prefix, before vs after | equal | ops-drill | ST-076c | G05-03 |
| NFR-045.5 | cadence | drills per quarter | **first measurement only** this sprint (calendar-gated, not "met") | ops-drill | ST-076c | §5 note |

### NFR-024 supported clients (R1 gate) → story ST-079, ticket ST-079

Critical journeys: E2E-04-01..05, sign-in (E2E-01-*), tus upload resume. Each item = pass rate of those specs in one Playwright project, CI form (`PW_PROJECTS=<name>`), 3 repeats, 0 flaky.

| Id | Browser × form factor | Target | Test level | Scorecard |
|---|---|---|---|---|
| NFR-024.1 | desktop Chrome (`chromium`) | 100 % | E2E | G05-04 |
| NFR-024.2 | iPhone 13 emulation (`webkit`; evidence of record is CI, local WebKit is not installed) | 100 % | E2E | G05-04 |
| NFR-024.3 | Android phone emulation (`android-chrome`, `devices['Pixel 7']`, new) | 100 % | E2E | G05-04 |
| NFR-024.4 | real iOS Safari, current and previous major | 100 % | **human (P20, OQ-17)** | §5 |
| NFR-024.5 | real Android Chrome, current and previous major | 100 % | **human (P20, OQ-17)** | §5 |

### NFR-036 effort to get value (R1 gate) → stories ST-080 (agent) and ST-083 (kit)

| Id | Metric and unit | Method | Target | Test level | Scorecard |
|---|---|---|---|---|---|
| NFR-036.1 | Quick Tag median s per rally | moderated session, n ≥ 5 players on their own phones | ≤ 5 s | **human (P9, OQ-20)** | §5 |
| NFR-036.2 | mis-tags per 20 rallies | moderator count, same sessions | ≤ 1 | **human (P9)** | §5 |
| NFR-036.3 | median upload → plan effort, 3-game match | same sessions | ≤ 15 min | **human (P9)** | §5 |
| NFR-036.4 | taps or keys to fix a call from where it is seen | Playwright tap/key counter per call type (rally winner, fault, ending) on score sheet and Quick Tag review, `chromium` and `android-chrome` | ≤ 2 for every call type; a planted 3-step path fails the counter (negative) | E2E | G05-05 |

### NFR-063 data classification (R1 gate, before beta) → story ST-077, ticket ST-077

| Id | Metric and unit | Method | Target | Test level | Scorecard |
|---|---|---|---|---|---|
| NFR-063.1 | stored data types without a class | IT: every SQLAlchemy table and column, every object-store key prefix and every backup artefact appears in `docs/security/data-classification.md`; a planted unclassified column fails (negative) | 0 | integration | G05-06 |
| NFR-063.2 | classes without encryption, retention or access rule | doc-check over the map's columns | 0 | doc-check | G05-06 |

### NFR-050 ASVS 5.0 L2 (R1 gate) and NFR-067 client hygiene → story ST-078, tickets ST-078a..e

| Id | Metric and unit | Method | Target | Test level | Ticket | Scorecard |
|---|---|---|---|---|---|---|
| NFR-050.1 | applicable L2 rows in V1-V5 still `Not assessed`, `S0 planned` or `S1` | `python3 docs/security/tools/asvs_status.py --chapters V1-V5` (ST-078a) | 0 | doc-check | ST-078a | G05-07 |
| NFR-050.2 | as .1 for V6-V10 | same tool | 0 | doc-check | ST-078b | G05-07 |
| NFR-050.3 | as .1 for V11-V17 | same tool | 0 | doc-check | ST-078c | G05-07 |
| NFR-050.4 | `Fail` rows without a fix ticket id or a residual-risk row in the draft ADR for the PO | same tool, `--fails-need-owner` | 0 | doc-check | ST-078a..c | G05-07 |
| NFR-050.5 | `Pass` rows without an evidence command or test id | same tool | 0 | doc-check | ST-078a..c | G05-07 |
| NFR-050.6 | object-level authorisation: non-404 answers to account B across every id route of `bola.MATRIX`, 2 accounts | existing BOLA IT; a new test fails when an id route is missing from the matrix | 0 | integration | ST-078d | G05-07 |
| NFR-067.1 | authenticated GET responses without `Cache-Control: no-store` | IT over every authenticated GET route | 0 | integration | ST-078d | G05-06 |
| NFR-067.2 | auth data left in local/session storage or IndexedDB after logout | E2E (`chromium`, `webkit`) | 0 | E2E | ST-078e | G05-06 |
| NFR-067.3 | media responses in the service-worker cache | SW unit test with mocked fetch + E2E cache listing | 0 | unit + E2E | ST-078e | G05-06 |
| NFR-050.7 | web responses missing CSP, `X-Content-Type-Options: nosniff` or frame denial | IT on the web origin | 0 | integration | ST-078e | G05-07 |
| NFR-050.8 | forms with `onSubmit` that are submittable before hydration | component test per form | 0 | component | ST-078e | G05-07 |
| NFR-050.9 | residual-risk ADR accepted | PO decision | accepted | **human (P19)** | — | §5 |

### NFR-070 legal gate → **human (P16)**, no ticket. §5 row; the team keeps privacy flags default-off for real users.

### NFR-006 vision accuracy, R2 readiness (footage-free part) → story ST-084

| Id | Rule or item | Test level | Ticket |
|---|---|---|---|
| NFR-006.1 | A predicted rally matches a gold rally only when its start **and** end are each within ±1.0 s (negative: end 1.01 s off → no match) | unit | ST-084b |
| NFR-006.2 | A prediction spanning two gold rallies (merge) gives 0 matches: 2 FN, 1 FP | unit | ST-084b |
| NFR-006.3 | Two predictions inside one gold rally (split) give no match | unit | ST-084b |
| NFR-006.4 | Matching is one-to-one (negative: two predictions near one gold rally → 1 TP, 1 FP) | unit + property | ST-084b |
| NFR-006.5 | Each NFR-006 metric has a regression-tolerance row and a regression/capability label in an ADR | doc-check | ST-084a |
| NFR-006.6 | Rally F1 ≥ 90 % on frozen gold set QD-GD-04 | **human (P11 footage)**; no measurement this sprint | — |

## 2. FR rules

### FR-124 / FR-141 single-weakness swap → story ST-081, tickets ST-081a/b

Dimensions modelled (retro 4 M3): targeted metric × level × players (1, 2, 4) × equipment (wall, no wall, ball machine) × weaknesses in the plan (1, 2, ≥ 3).

```gherkin
Rule: FR-124.R1 When a player presses "Not for me" in a plan that trains one weakness, the API returns a different drill that targets the same metric and fits the player's preferences
  Example: solo player with a wall, one weakness (happy)
  Example: no other fitting drill exists for that metric, level and equipment → 409 no_alternative and the plan is unchanged (negative)
Rule: FR-124.R2 When the plan holds 3 or more drills for overlapping weaknesses, a swap never returns a drill already in that session
  Example: 3-weakness session (happy)
  Example: the only alternative is already in the session → 409 no_alternative (negative)
Rule: FR-141.R1 The coverage check fails naming the cell when any metric × level × profile cell, single-target plans included, has fewer than 2 fitting drills
  Example: current library → rc 0 (happy)
  Example: gap fixture without a second solo-wall drill for one metric → rc 1 naming the cell (negative)
```

Test levels: FR-124.R1/R2 integration (`backend/tests/integration`, plan API boundary) + scenario; FR-141.R1 unit on `racket-drill-coverage` + CI job. Domain truth: drill efficacy is not claimed (coach, P15); drills stay `coach-reviewed`.

### FR-055 "unofficial scoring" label in the release candidate → ticket ST-082 (release notes) and G05-09

```gherkin
Rule: FR-055.R1 While the scoring preset is PROVISIONAL-UNVERIFIED, every score sheet, stats page, plan page and the R1 release notes show the "unofficial scoring" notice
  Example: preset unverified → notice shown once before the first card (happy)
  Example: release notes draft without the notice → `check_release_notes.py` rc 1 (negative)
```

## 3. Release and demo items

| Id | Item | Test level | Ticket |
|---|---|---|---|
| REL-1.1 | R1 release notes list every R1 FR shipped, every flag and its default, and every known limitation with its P-n | doc-check (`check_release_notes.py`) | ST-082 |
| REL-1.2 | Rollback: the previous image tag set redeploys with `make up IMAGE_TAG=<prev>` and the API is healthy | ops-drill | ST-082 |
| REL-1.3 | Every Alembic migration since the R1 baseline downgrades one step and upgrades again on a seeded copy (negative: a migration without `downgrade` fails) | integration | ST-082 |
| REL-1.4 | PO signs off the R1 release candidate | **human (P18)** | — |
| DEMO-1.1 | `make demo` on a flag-on stack: demo users are age-confirmed through the domain service (no DB poke), rc 0, twice | integration (`infra/tests/test_seed_demo_plan.py` on a flag-on stack) | QA-VERIFY04R5-01 |
| USAB-1.1 | Usability kit: protocol, task script mapped to NFR-036.1-.4, interim consent script, observation sheet, safety-reviewed drill list | doc-check | ST-083 |

## 4. Process items (ADR 0056, retro 4 actions)

| Id | Rule (one observable outcome) | Test level | Ticket |
|---|---|---|---|
| PRC-1.1 | A scheduled run with conclusion `cancelled` produces a red notice | unit (negative first: today `none`) | CI-NOTICE-CANCELLED |
| PRC-1.2 | A scheduled run with conclusion `timed_out` produces a red notice; `success` and `skipped` do not (negative) | unit | CI-NOTICE-CANCELLED |
| PRC-1.3 | The Flaky-test report job finishes within its 45 min budget on the scheduled run (root cause of run 41622904539 removed) | CI evidence (next scheduled run) | CI-NOTICE-CANCELLED |
| PRC-2.1 | Changed paths map to a tier by a data table; a file gets the highest tier of every rule it matches and the PR the highest over its files; a path that matches no rule is tier 2 (fail closed) | unit | CI-TIERS-a |
| PRC-2.2 | A PR touching only non-executable Markdown under `docs/**`, top-level `*.md` or `.claude/agents/*.md` is tier 0. Negatives: adding one `backend/src` file → ≥ 1; `docs/security/tools/check_threat_notes.py`, `docs/security/tools/asvs_status.py`, `docs/design/tools/check_flows.py`, `docs/domain/tools/*.py`, `docs/sprints/*/close-checks/*.py` and an extensionless shebang file under `docs/` → 1 (executable floor); `docs/architecture/api-*.md` → 2 although it also matches the tier 0 rule | unit | CI-TIERS-a |
| PRC-2.3 | Tier 2 paths (auth, uploads, storage, media URLs, privacy/age/consent/retention, quotas, logging config, secrets, CI permissions, migrations, API contracts, `scripts/ci/merge_ready.py`) classify as tier 2 | unit (planted fixture per path) | CI-TIERS-a |
| PRC-2.4 | Tier 0 passes with one fresh-context APPROVE on the head plus a green `doc-check`; fails without `doc-check` (negative) | unit (`infra/tests/github_stub.py`) | CI-TIERS-b |
| PRC-2.5 | Tier 1 passes only with principal-engineer **and** `Reviewer: senior-qa-engineer` APPROVE on the head; PE + senior-backend-engineer only fails (negative) | unit | CI-TIERS-b |
| PRC-2.6 | Every tier 2 PR additionally needs `Reviewer: security-privacy-engineer` APPROVE on the head, whatever made it tier 2 (kickoff SEC-1); PE + QA only fails for a security path, a migration-only PR, an API-contract-only PR and an unmatched-path-only PR (4 negatives) | unit | CI-TIERS-b |
| PRC-2.7 | An APPROVE from the role that authored the PR is not counted. The author role is computed from the head branch's row in the sprint plan §15 ticket map (`Owner`), cross-checked with `status.json` `ticket_prs`; PR body, labels and author comments are never read for it. A PR body claiming another role does not change it; a head branch with no row fails closed (negatives) | unit | CI-TIERS-b |
| PRC-3.1 | `doc-check` fails when a changed Markdown file references a repo path that does not exist | unit + CI | CI-DOC-CHECK |
| PRC-3.2 | `doc-check` fails when an `[ASB/<ID>]` citation names an id that is not a Confirmed row and lacks "(unverified)" | unit + CI | CI-DOC-CHECK |
| PRC-3.3 | `doc-check` fails when a `.claude/agents/*.md` front matter does not parse or lacks `name`, `description`, `tools` | unit + CI | CI-DOC-CHECK |
| PRC-3.4 | `doc-check` runs `check_flows.py --decider` on the current sprint's flows file once it exists | CI | CI-DOC-CHECK |
| PRC-4.1 | `pr-policy` runs `reconcile_due.py`; a PR whose decisions file names a blocker or major id with no ledger row fails | unit + CI | CI-RECON-ON-PR |
| PRC-4.2 | A decisions-file line containing "known gap", "can only" or "not covered" without a finding id fails `pr-policy` (retro 4 L13) | unit + CI | CI-RECON-ON-PR |
| PRC-4.3 | The parseable finding-id format is documented next to `measurelib._FINDING_ID` and in the verifier brief template | doc-check | CI-RECON-ON-PR |
| PRC-5.1 | `flow_metrics.py` reports median and max cycle time (first commit → merge) from the REST API (no GraphQL) | unit (stubbed REST) | QA-FLOW-METRICS |
| PRC-5.2 | It reports throughput (tickets merged into `main` in the sprint window) | unit | QA-FLOW-METRICS |
| PRC-5.3 | It reports work item age for every open ticket PR | unit | QA-FLOW-METRICS |
| PRC-5.4 | It reports WIP breaches from the stage log in the EM status records | unit | QA-FLOW-METRICS |
| PRC-5.5 | It reports the share of merged ticket decisions files with a cost-per-PR table, and lists rounds marked "not measured" | unit | QA-FLOW-METRICS |
| PRC-6.1 | `retro_ready.py` exits non-zero while a VERIFY-05 PR is open or any VERIFY-05 finding row is not Fixed | unit | EM-CLOSE-CHECKS |
| PRC-6.2 | The close check fails when the merged-PR set from GitHub differs from the `status.json` map, printing the set difference | unit | EM-CLOSE-CHECKS |
| PRC-6.3 | The close check fails when an Open blocker row names a cause that is closed | unit | EM-CLOSE-CHECKS |
| PRC-7.1 | `check_atomic_breakdown.py` fails when an NFR row in this file lacks a metric, method, target or test level, or an FR rule lacks a negative Example | unit + CI | QA-DOR-CHECK |
| PRC-8.1 | Every timed or load method in `goal-scorecard.md` §4 is pinned by an infra test to the CI step it mirrors | unit (infra test) | QA-PIN-05 |

## 4.1 Carried test-change decisions (no new requirement)

| Item | Ticket |
|---|---|
| TCR rows 11 and 14 in `docs/sprints/04/test-change-requests.md` decided (retro F2) | QA-TCR-04 |

## 5. Assumptions (business-analyst defaults for PM and PO review; ASB/REQ-07)

| # | Assumption | Default | Who confirms |
|---|---|---|---|
| A1 | OQ-17: iOS Safari is release-blocking | yes (working assumption since S1, roadmap §8.1); emulation is not counted as a real device | PO (P20) |
| A2 | Burn-rate windows: fast 1 h / 5 min at 14.4×, slow 6 h / 30 min at 6× (multipliers judgment) | PE-5a ADR may change them | principal-engineer, sre-devops-engineer |
| A3 | Metrics backend: OpenTelemetry collector + Prometheus in a Compose `obs` profile (free, self-hosted) | escalate to the PO if any paid service is proposed | PE-5a; PO only if paid |
| A4 | Backup: nightly `pg_dump` custom format + object-store mirror inside the Compose network, encrypted at rest with a dev key from `.local`; WAL archiving deferred (RPO 24 h is met by daily dumps) | PE-5b ADR | principal-engineer, security-privacy-engineer |
| A5 | 50 RPS runs on the Compose stack with flags **on** (the configuration R1 ships for the RC) | yes; flags-off covered by the existing CI `perf-baseline` | product-manager |
| A6 | FR-162 pricing fake door (Could, OQ-14) is out of Sprint 5 | out | product-manager; PO may override |
| A7 | NFR-036.4 call types: rally winner, fault, rally ending | coach confirms in COACH-5 | pickleball-domain-coach |
| A8 | Sprint 5 counts the in-progress WIP limit as 4 (task brief), under working-agreement §3's 5 | 4 | engineering-manager |

No `[NEEDS CLARIFICATION]` marker remains on scope, security or a domain rule. Rules that rest on an unverified pickleball rule are not in this sprint.
