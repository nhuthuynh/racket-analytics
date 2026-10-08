# Sprint 3 report: starter stats with uncertainty and evidence, deletion, labelling tools

- **Prepared by:** engineering-manager, at the sprint close on 2026-10-08. The session was compressed (2026-10-06..08). The review with the PO keeps its planned date, 2026-11-27 (sprint-03 header).
- **Head at this writing:** `c1fba6a` on `sprint-03`, plus this docs-only close commit. The verifier measured `fb920bc` (VR3). After that, only docs changed: `git diff --stat fb920bc c1fba6a -- backend web infra scripts .github` is empty.
- **Sources:** `goal-scorecard.md` §9 (verification round 3, by the independent verifiers), `review-rounds.md` (including the close reconciliation), `status.json`, `blockers.md`, `smoke.md`, `ci-status.md`, and GitHub (`list_pull_requests`, `list_branches`, `actions_list`, `search_issues`, 2026-10-08).

## 1. Goal and scorecard (read this first)

> **The Sprint 3 goal is NOT met** under the PO standing rule. The independent verifiers met **10 of 12** metrics on a fresh HTTPS Compose stack at `fb920bc` (VR3). **The product works live, in real time:**
>
> - every player-facing promise of the goal ran 5 of 5 times on fresh accounts: the seven stats per side equal to the reference after every tag and every correction; n, the Wilson range and "low sample" in text; the "unofficial" notice; "Show me" playing each rally; delete match; delete account, which signs out every session; and the purge leaving 0 rows and 0 objects;
> - Full Tag works for a consented labeller, and its export validates;
> - every latency target was met with margin, from tag → stats p95 34.3 ms against 5 s to the first video frame at 837 ms against 1,500 ms.
>
> **Two rows fail:**
> - **G03-09 (c):** no CI run exists at the head.
> - **G03-12:** open blocker and major findings. The verifier counted 3. At this close the EM reconciled review round 3, which had no rows, and recounted **8** (§1.2).

### 1.1 Metrics: target against the verifier's result (VR3, `fb920bc`)

| ID | What | Target | Actual | Met |
|---|---|---|---|---|
| G03-01 | Goal journey live over https, fresh account per run (stats after every tag, Show me, correction, BOLA, delete match, delete account) | 5 of 5 runs | 5/5, rc=0, no failing step; delete account `{202, old session 401, items after sign-in []}` each run | yes |
| G03-02 | (a) tag → stats current; (b) correction → stats; (c) DELETE → hidden | p95 ≤ 5,000 ms n ≥ 70; ≤ 5,000 ms n ≥ 5; ≤ 60,000 ms n ≥ 5 | 34.3 ms (n 70); 24.0 ms (n 5); 22.2 ms (n 5) | yes |
| G03-03 | Purge completeness; media links after deletion; schedule | 0 rows; every link 404 (≥ 1); ≤ 24 h | 0 rows in all 20 columns; 5/5 links 404; `purge` service `PURGE_INTERVAL_S 86400`, first scheduled run ok | yes |
| G03-04 | Integration tests on real Postgres, object store, Mailpit | 100%, 0 skipped, every id | IT-03 + BOLA 183/183; earlier ITs 317/317; strict sandbox 10/10; missing [] | yes |
| G03-05 | Read latency at 50 RPS for 60 s (stats, evidence, match) | p95 ≤ 300 ms, p99 ≤ 800 ms, ≥ 99.5%, 0 unexpected, ≥ 47.5 RPS | 32.5 / 114.9 ms, 100%, 0 unexpected, 50.0 RPS | yes |
| G03-06 | Playwright E2E over https (Chrome for Testing) | 100% of non-skipped, E2E-03/02 ids present, ≤ 6 skips, 0 flaky ×3 | 114 passed, 0 failed, 6 named Sprint 1 skips; ×3: 342 passed, 0 flaky | yes |
| G03-07 | Browser timings (20 samples each) | dashboard p95 ≤ 2,000 ms; Show me first frame ≤ 1,500 ms; CLS = 0 | 231 ms; 837 ms; 0 | yes |
| G03-08 | Metric correctness | golden 100% + manifest; scenarios 100%; conservation 0 over ≥ 1,000; review record | GS-AN-1 v2 31/31, manifest rc 0; scenarios 15/15; 1,000 / 0; 7 of 7 coach-reviewed | yes |
| G03-09 | Full Tag and drill lint; CI drill-lint job | IT-03-11 + E2E-03-05 pass; 1 pass + 5 named failures; CI green at the head | IT-03-11 15/15, E2E-03-05 passed, lint correct; **no CI run at the head** (origin `sprint-03` is `723bb7f`; last run 37643676432 at `09f1f67`, failed) | **no** |
| G03-10 | Accessibility: axe, targets, keyboard, 320/360 px (D, E, X, L and earlier families) | 0 serious/critical, 0 targets < 24×24, every family checked | 55 axe checks, 0; 0 small targets; every family and state including `E-01-empty`; keyboard and 320/360 passed | yes |
| G03-11 | Coverage, mutation, oracle, speed | changed lines ≥ 85%; analytics ≥ 90%; rules ≥ 95/90%; web ≥ 80%; mutation rules ≥ 0.85, stats ≥ 0.80; oracle 100,000/0; domain < 10 s, unit ≤ 60 s, integration < 600 s | 94%; 98.1%; 99.57/98.41%; 91.64%; 0.8635 / 0.9251; 100,000/0; 8.0 s / 12.2 s / 350.1 s | yes |
| G03-12 | Open blocker/major findings | **0** | verifier: 3; **EM close recount: 8** (§1.2); GitHub `bug` issues 0 | **no** |

`@needs-verification`: 15 of the 21 frozen-value comparisons in G03-08 depend on the provisional scoring rules. They are reported, but they count toward no Must FR. Scoring and every metric card stay "unofficial scoring (rules not yet verified)" until the PO supplies the rulebook (P7, ADR 0023).

**Demo (sprint-03 §12), run live in real time by the verifier (scorecard §9.5):** steps 1-9 work end to end. Step 10 shows open defects ≠ 0. Step 11 is the PO's.

**Not runnable in the sandbox, so not counted as met:** WebKit (CI only), the CI `drill-lint` job at the head, and the manual screen-reader pass (S3-DoD-P6).

### 1.2 G03-12 at close: 8 open

`python3 scripts/measure/open_defects.py docs/sprints/03/review-rounds.md` → rc=1, **open 8** at `c1fba6a` plus the EM close rows. `search_issues is:open label:bug` → 0.

Why the count went from 3 to 8: review round 3 ran at `fdeeb53` in parallel with verification round 1. Nobody wrote rows for its findings, and the EM's goal-round reconciliation covered rounds 1-2 and VR1 but not round 3. This is retro 2 M1 again (retro 3 M1). At this close the EM wrote one row per round-3 id (25 new ids, 47 findings with the re-raised ones) and re-checked each at the head:

- 6 are fixed: QA-R1S3-06/SEC-R3S3-01/QA-R3S3-01 (routes live), PE-R3S3-02, PE-R2S3-04-FOLLOWUP, SEC-S3-TM-12, QA-R1S3-01, PD-FL3-01.
- 2 majors are deferred to sprint-DoD rows (§4.1).
- The minors go to the Sprint 4 carry-over (§8).
- **5 majors are still open, and no goal round ever saw them.**

| # | Finding | Sev. | What is open | Owner |
|---|---|---|---|---|
| 1 | PE-R1S3-01 / QA-R1S3-04 / QA-R3S3-02 / SEC-R3S3-03 | blocker | No Sprint 3 ticket PR exists. No principal and senior verdict has been given, and nothing from Sprint 3 is on `main` (PO rule, ADR 0039) | orchestrator; EM tracks; principal-engineer + senior engineers review |
| 2 | PD-R1S3-01 (+ -PM, -BA, QA-R3S3-06) | blocker | Every DR-03 decider cell is written (`1433a92`). The chair has not recorded DR-03 as held, and ADR 0043 is still Proposed | principal-designer |
| 3 | PD-R1-06 family (DR-01, DR-02) | blocker | The R-1 walk is done and D-1/D-2 are closed. Still to do: the R2-1 walk record and the chair's "held" outcome | principal-designer with senior-frontend-engineer |
| 4 | PE-R3S3-01 / QA-R3S3-04 | major | No CI run since `09f1f67`. Origin is 10 commits behind | sre-devops-engineer with the orchestrator |
| 5 | PE-R3S3-05 / QA-R3S3-03 | major | The listed E2E step fails closed when no spec is tagged, so `ci-gate` is red by construction. ADR 0046 was accepted with an amendment at this close; the SRE implements it and QA decides TCR row 30 | sre-devops-engineer; senior-qa-engineer |
| 6 | PE-R3S3-03 / SEC-R3S3-02 / QA-R3S3-05 | major | The security ITs of ADR 0045 (T-DL-3 two-owner, T-DL-4, T-AC-2 race, T-AC-3) are missing. The code shipped first | senior-qa-engineer |
| 7 | PE-R3S3-04 | major | The ADR 0039 ticket map has no rows for `606edcd` or any goal-round commit | principal-engineer |
| 8 | PD-R3S3-01 | major | The FE's accepted DR-03 amendments are not folded into the spec (E stale state, `<video>` focus) | principal-designer |

None of the 8 is product code that a player would see failing. Each one needs a role other than the build lanes, or the orchestrator: PRs, push and CI, the chair, the ticket map, the missing ITs.

## 2. Committed against implemented and DoD-done

| Lane | Committed | Implemented | DoD-done | Not implemented |
|---|---|---|---|---|
| BE | 12.5 | 12.5 (ST-043/044/045, ST-046a/b, ST-047-API, ST-050a/b, ST-051-API, ST-038, ST-042 grants + 0013) | 0 | — |
| FE | 11.0 | 11.0 (C3-03, ST-048, ST-047 UI, ST-050 UI, ST-051 UI, ST-052 UI) | 0 | — |
| QA | 9.5 | 9.0 | 0 | C3-06 (0.5): needs a human tester (P6) |
| SRE | 7.0 | 3.0 (C3-04, C3-05, ST-042 Compose, SRE-PURGE a+b) | 0 | ST-054 SRE half (Locust on stats/evidence in CI); SRE-SMOKE-3 close-head smoke; SRE-MIN-3; C3-08 (P11) |
| ML | 3.0 | 3.0 (ST-053, ST-052 a/b/c) | 0 | — |
| **Total** | **43.0** | **38.5 (0.895)** | **0** | |

**DoD-done is 0.** No Sprint 3 ticket has reached `main` as its own reviewed PR (ADR 0039; the PO rule). The Sprint 2 increment did reach `main` (PR #2, merged 2026-10-06, CI green, run 37514696229), the first merge to `main` in this project. The UI stories also lack "Design review held" (DR-03).

**Stretch:** ST-035, ST-034, ST-033 and ST-036 were not started. ST-025 is still blocked on P3 clips.

**Built outside the plan's gates (recorded, not undone):**
- The Sprint 3 UI was built in goal round 1, before DR-03 was held and without a PO waiver (FE decision-log row, 2026-10-07; ADR 0037 rule 2).
- The goal-round backend slices were committed on `sprint-03` instead of `s3/<ticket>` (ADR 0039 rule 6; EM decision-log row).

## 3. Gates

| Gate | State | Evidence |
|---|---|---|
| `ci-gate` on `sprint-03` | **No run at the head.** 4 runs on the branch, 0 green; the newest is 37643676432 at `09f1f67` (failure). Origin is `723bb7f` | `actions_list list_workflow_runs ci.yml`; `list_branches` |
| `ci-gate` on `main` | Green at the Sprint 2 merge (37517222513). The nightly is red on the known gitleaks finding until T-SEC-RV3-02 merges (QA-R1S3-02, deferred) | `actions_list`; blockers.md |
| E2E listed step (ADR 0046) | Would fail at the head on an empty selection; amendment accepted at close (§1.2 row 5) | ADR 0046 Notes |
| Integration smoke before review (ADR 0022) | Pre-review at `316a514`; round-2 fix head at `8e25478`. **No close-head section in `smoke.md`.** The VR3 live run at `fb920bc` is the closest evidence | `smoke.md` |
| Test immutability (ADR 0014) | 1 row undecided: TCR row 30 (QA). Every other row is decided | `test-change-requests.md` |
| Golden GS-AN-1, conservation, evidence crawl, deletion IT, JSON fuzz | Met (G03-08, G03-02 crawl in E2E-03-02, IT-03-06/08, IT-03-12) | VR3 |
| Coverage on analytics ≥ 90%; mutation rules ≥ 0.85, stats ≥ 0.80 | Met: 98.1%; 0.8635; 0.9251 | G03-11 |
| Drill lint | Met locally (1 + 5); CI job exists (`4d8af6d`) but has no run at the head | G03-09 |
| Locust on stats/evidence (NFR-010 baseline) | Not in CI; measured live by `stats_latency.py` (G03-05) | `ci.yml` has `locustfile_sprint02.py` only |
| Open blocker/major | **8** | §1.2 |

## 4. Sprint-level DoD (sprint-03 §9)

| Item | State |
|---|---|
| Every metric card in the demo shows n, the "unofficial" notice and a working "Show me" | **Yes**, live (VR3 demo steps 2-3; E2E-03-01/02/03). The notice appears once per page, not on each card. That is a PM decision (DR-03 R3-3 option a); its `sprint-03.md:35` follow-up row is still due |
| Only `coach-reviewed` metrics shown; review record per entry | **Yes**: 7 of 7 coach-reviewed (ADR 0044), and the shipped statuses are pinned to the record by a test |
| Rule-dependent rows reported separately | **Yes** (15 of 21, §1.1) |
| Traceability matrix lists the Sprint 3 feature files | **Yes**, at this close (`traceability-matrix.md` §13-§14) |
| Sprint 4 stories meet the DoR (BA-1) | **No**: BA-1 was not delivered. Sprint 4 planning must run it as a gate task (ADR 0047 rule 2) |
| Retro 2 actions reviewed first | Yes (sprint-03 §0.3; retro 3 §1) |
| Every scorecard row "yes", from one independent run at one head | **No**: 10 of 12 (§1) |
| Every method dry-run before the verifier | **No**: the G03-05 row is still missing (VR3-S3-02). The method ran end to end and met its target |
| Every round has an EM reconciliation row | **No**: review round 3's row was written only at this close (§1.2) |
| Every decider task has its output, or an escalation, by its date | **Late**: PE-1/2/3, SEC-1, PD-1 and COACH-1 landed in review round 1; the BA/PM cells came at the end (`1433a92`, P14). DR-03 is still not recorded as held |
| Human-gated items handled as the PO chose | **Yes**: P12 option (b), rows below |
| Every Sprint 3 ticket reached `main` as its own reviewed PR | **No**: 0 ticket PRs |

### 4.1 Sprint-DoD rows for human-gated items (PO P12 option (b))

| Row | Item | State |
|---|---|---|
| S3-DoD-P6 | Manual VoiceOver/TalkBack pass (38 rows, NFR-027 b) | **not met: waiting on P6** (0 of 38 run). Sprint 3 must not be called WCAG-checked |
| S3-DoD-P10 | Repository visibility | **not met: waiting on P10** (GitHub reports public) |
| S3-DoD-P11 | Private footage bucket | **not met: waiting on P11**. No footage of people has been stored |

## 5. Test counts by level (latest independent or isolated run)

| Level | Result | Source |
|---|---|---|
| Backend unit (`-m unit`) | 1,833 passed, 1 skipped (P3 rally scoring), in 11.17 s | `cd backend && env -u APP_ENV uv run --no-sync pytest -q -m unit` (EM, this close, `c1fba6a`) |
| Domain unit (CI `DOMAIN_TEST_PATHS` incl. `tests/unit/analytics`) | 8.0 s of the 10 s budget, 0 failed | VR3 G03-11 |
| Backend integration + regression | 691 passed, 2 skipped (the strict sandbox, run separately: 10/10). IT-03 + BOLA 183/183; earlier ITs 317/317; integration budget 350.1 s of 600 | VR3 G03-04, G03-11 |
| Scenarios and properties | analytics scenarios 15/15; golden GS-AN-1 v2 31/31; conservation 1,000 passing / 0 failing; manifest rc 0 | VR3 G03-08 |
| Whole gated backend run with coverage | 2,664 passed, 1 skipped; changed lines 94%; analytics 98.1% | VR3 G03-11 |
| Oracle / mutation | 100,000 sequences, 0 disagreements; rules 0.8635; starter stats 0.9251 | VR3 G03-11 |
| Web unit (Vitest) | 68 files, 580 passed; lines 91.64% | `cd web && npx vitest run` (EM, this close); VR3 for coverage |
| E2E (Playwright, Chrome for Testing, https) | 114 passed, 0 failed, 6 named skips; ×3: 342 passed, 0 flaky; timing spec 40 passed | VR3 G03-06, G03-07 |
| Infra and harness | 618 passed, 1 skipped (gitleaks binary not installed) | `cd infra && DOCKERHUB_REGISTRY=mirror.gcr.io uv run --no-sync pytest -q -m "not live"` (EM, this close) |
| WebKit | Not run (CI only; no CI run at the head) | — |

## 6. Delivery metrics

| Measure | Sprint 3 | Sprint 2 |
|---|---|---|
| Commits on the branch | 138 (`ce91984..c1fba6a`): 57 docs, 32 test, 29 feat, 16 fix, 4 ci | 161 |
| Median commit size (changed lines, excl. `uv.lock`) | 84.5; 14 over 400 (max 2,125, `d83ee1b`) | 63; 16 over 400 |
| CI runs on the branch | 4 dispatched, 0 green | 5, 1 green |
| Merges to `main` | 1 (PR #2, the Sprint 1 + 2 increment, 2026-10-06), the first ever | 0 |
| Deployment frequency, lead time, change failure rate, MTTR | N/A: nothing deployed | N/A |
| Ticket PRs opened / merged | 0 / 0 | — |
| Review rounds | 3 review rounds + 3 goal verification rounds | 3 + 3 |
| Open blocker/major trajectory | 14 (planning) → 11 → 9 (round 1) → 8 (round 2) → 4 (goal round 1) → 3 (goal rounds 2-3, without round 3) → **8** (close recount) | 17 → 14 at close |
| Goal metrics met (verifier) | 0/12 (VR1) → 2/12 (VR2) → 10/12 (VR3) | 10 → 11 → 11 |
| Escalations to the human | P6-P12 at planning (P12 answered, option b); P13, P14 new | P1-P11 |

## 7. PO items

| Item | State | Need-by |
|---|---|---|
| P6 screen-reader tester | Open (S3-DoD-P6) | overdue (2026-11-13) |
| P7 rulebook (OQ-01) | Open; scoring and stats stay "unofficial" | 2026-11-16 |
| P8 beta budget (OQ-13) | Open | before any beta |
| P9 testers and second reviewer (OQ-20) | Open; it now gates `verified`, not `coach-reviewed` (ADR 0044), so it no longer gates Sprint 3 | 2026-11-16 |
| P10 repository visibility | Open (S3-DoD-P10) | sooner is safer |
| P11 footage bucket provider | Open (S3-DoD-P11) | before any footage of people, and before Full Tag on real matches |
| P12 human-gated goal items | **Answered 2026-10-07: option (b)** | — |
| P13 start of the ticket-PR rule | Open. Default in force: ADR 0039 (Sprint 3 ships as ticket PRs). The PO may say otherwise in their own words | before the Sprint 3 merge |
| P14 decider cells for DR-01/02/03 | Done by the deciders (`1433a92`); no PO waiver needed. Only the chair's outcome record is left | — |
| Known red nightly on `main` until T-SEC-RV3-02 merges | Open: accept, or ask for the hotfix order | before the next nightly |

## 8. Carry-over to Sprint 4 (each row gets an owner and a Sprint 4 backlog row at planning)

| Row | Items | Owner | Size (judgment) |
|---|---|---|---|
| C4-PR | Sprint 3 ticket PRs (ADR 0039): map rows for every later commit (PE-R3S3-04), the FE split for `d83ee1b`/`cd8856f` (decision-log 2026-10-08), branches, PRs, two verdicts each, merges; T-SEC-RV3-02 first, which ends the red nightly | orchestrator; principal-engineer; senior engineers; EM tracks | 0 build units; review effort about 1 lane-day (judgment) |
| C4-CI | Push `sprint-03`, implement the ADR 0046 amendment red first, dispatch CI, green `ci-gate` at the head incl. WebKit and `drill-lint`; close-head smoke section | sre-devops-engineer with the orchestrator | 1 unit |
| C4-DR | Chair records DR-01/02/03 outcomes and accepts ADR 0043; folds the FE amendments into flows-sprint-03 (PD-R3S3-01); R2-1 walk record; the PM's `sprint-03.md:35` row and the PM-1 acceptance of ADR 0005 (still Proposed); the BA's FR-006/FR-021/FR-100 follow-ups | principal-designer; product-manager; business-analyst | 0.5 unit |
| C4-SEC | ADR 0045 security ITs: T-DL-3 two-owner shared key, T-DL-4 held recompute + orphan sweep, T-AC-2 race, T-AC-3 old link, T-AC-5 re-created account | senior-qa-engineer (BE fixes if one fails) | 1.5 units |
| C4-SRE | ST-054 SRE half (Locust on stats/evidence in CI); SRE-MIN-3; VR3-S3-01 (`extra_ca` build secret); VR3-S3-02 (G03-05 dry-run row) | sre-devops-engineer | 2 units |
| C4-MIN | PE-R3S3-06/-07/-08, PD-R1S3-02-FOLLOWUP, SEC-R3S3-04, SEC-S3-TM-03/-04/-07/-09/-10, PD-R3S3-02, PD-FL3-02/-03, VR2-S3-03, VR3-S3-03, PE-S2-R3-08 (no text: PE to restate or withdraw) | owners as in `review-rounds.md` | about 3 units of review-loop reserve |
| Human-gated | S3-DoD-P6, -P10, -P11; ST-025 (P3 clips); P7 rulebook | human PO with QA, SRE, ML | — |
| Stretch not started | ST-035, ST-034, ST-033, ST-036 | BE, FE | as sized in sprint-02 §3 |
| Process | ADR 0047 from Sprint 4 planning; R3-IN-1 `Red:` hook (retro 3 A5) | engineering-manager with sre-devops-engineer | 0.5 unit |

## 9. History of this report

- 2026-10-08, sprint close: first and final report. G03-12 recounted from 3 to 8 after the review-round-3 reconciliation (review-rounds "Sprint close: engineering-manager").
