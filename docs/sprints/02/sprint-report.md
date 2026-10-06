# Sprint 2 report: Quick Tag to an unofficial score sheet, with undo, corrections and the rally video

- **Prepared by:** engineering-manager, at the sprint close on 2026-10-06. The session was compressed; the review with the PO keeps its planned date, 2026-11-13. §1 was first written in the review-round-2 status step and is now final (ADR 0033 rule 4).
- **Head at this writing:** `b0e7cbb` on `sprint-02`, plus this docs-only commit. The verifier measured `e4c24bc`. Since then only docs and the G02-11 counter changed: `git diff --stat e4c24bc HEAD -- backend web infra/docker infra/compose.yaml` is empty.
- **Sources:** `goal-scorecard.md` §2 and §9 (verification round 3, by the independent verifiers), `review-rounds.md`, `status.json`, `blockers.md`, and the CI runs on `sprint-02`.

## 1. Goal and scorecard (read this first)

> **The Sprint 2 goal is NOT met** under the PO standing rule. The independent verifiers met **11 of 12** metrics on a fresh-volume Compose stack over https at `e4c24bc` (round 3). The product part of the goal works live: tagging by taps and by keys, the score sheet with the "unofficial scoring" label, corrections that re-score and keep conflicts, byte-identical undo, the audit trail and the rally video. **G02-11 (open blocker and major findings, target 0) fails.** The verifier counted 2. At this close the EM wrote rows for the review-round-3 findings that had none and recounted **14** (§1.2).

### 1.1 Metrics: target against the verifier's result (round 3, `e4c24bc`)

| ID | What | Target | Actual | Met |
|---|---|---|---|---|
| G02-01 | Full tagging journey over https, 12 steps, fresh accounts | 5 of 5 runs | 5/5, no failing step; step 9 `@needs-verification` 5/5 | yes |
| G02-02 | (a) correction or undo to confirmed state; (b) last tag to sheet | (a) p95 ≤ 1,500 ms, ≥ 100 samples, 0 failed, identical; (b) p95 ≤ 5 s | (a) 35.3 ms, n=100, 0 failed, byte-identical; (b) 19.0 ms, n=30 | yes |
| G02-03 | Integration tests on real services | 100%, 0 skipped, every id | IT-02 + BOLA 253/253; IT-01 80/80; missing [] | yes |
| G02-04 | Read latency at 50 RPS for 60 s | p95 ≤ 300 ms, p99 ≤ 800 ms, ≥ 99.5%, ≥ 47.5 RPS | 16.8 / 54.6 ms, 1.0, 0 unexpected, 50.0 RPS | yes |
| G02-05 | Playwright E2E over https (Chrome for Testing, ADR 0036) | 100% of non-skipped, E2E-02 ids present, ≤ 6 named skips, 0 flaky ×3 | 93 passed, 0 failed, 6 named skips; ×3: 279 passed, 0 flaky | yes |
| G02-06 | Browser timings | p95 (a) ≤ 200 (b) ≤ 100 (c) ≤ 1,500 (d) ≤ 2,000 ms, n ≥ 20 | 12.8 / 12.7 / 672.7 / 388.5 ms (n 160/640/40/60) | yes |
| G02-07 | Scoring and replay correctness | 100%, golden 100%, ≥ 46 provisional, 0 committed `red_until`, ≤ 90 s | 304 passed + 1 P3 skip in 33.2 s; golden 4/4; 70 collected, 52/52; 0 | yes |
| G02-08 | Oracle and mutation | 100,000 / 0; rules ≥ 0.85; projection recorded | 100,000 / 0; 0.8635; 0.9196 | yes |
| G02-09 | Coverage | changed lines ≥ 85%; rules + aggregates ≥ 95% / 90%; web ≥ 80% | 97%; 99.57% / 98.41%; 91.7% | yes |
| G02-10 | Accessibility (T, K, S, H, V and Sprint 1 screens) | 0 serious/critical; 0 small targets; E2E-02-02/03; 320/360 px | 0 in 37 axe checks (incl. `axe-V-01` on the real video); 0 / 0; passed; passed | yes |
| G02-11 | Open blocker/major findings | **0** | verifier: **2**; EM close recount: **14** | **no** |
| G02-12 | Fast tests (NFR-073) | domain < 10 s; unit ≤ 60 s; integration < 10 min | 7.1 / 6.8 / 6.8 s; 10.3 s; 210.6 s; 0 failed | yes |

`@needs-verification` results (G02-01 step 9 and the 52 provisional rows in G02-07) are reported but never counted toward a Must FR. Scoring stays `PROVISIONAL-UNVERIFIED` until the PO supplies the rulebook (P7, ADR 0023).

Demo (sprint-02 §12): steps 1-7 ran live in 9.6 s (`goal-scorecard.md` §9.3). Step 8 is this scorecard. Step 9 (stretch) was not in scope. Step 10 belongs to the PO.

### 1.2 G02-11 at close: 14 open

`python3 scripts/measure/open_defects.py docs/sprints/02/review-rounds.md` → rc=1, **open 14** (at `b0e7cbb` plus the EM close rows). GitHub open issues labelled `bug`: 0 (verifier round 3). `smoke.md` and `blockers.md` have no open product-defect row that is missing from review-rounds.

Why the count rose from 2 to 14: review round 3 ran at `db0f0be` in parallel with goal round 1, and no reviewer wrote rows for its findings (retro 2, M1). The counter also skipped the chair's routed design-review table because it had no disposition column (PD-R3S2-04, fixed in `b0e7cbb`). The EM has now written one row per round-3 finding, each re-checked at this head. 14 is the true count under the scorecard's own method.

| # | Finding | Sev. | What is open | Owner |
|---|---|---|---|---|
| 1 | PD-R1-06 / DR-01 / DR-02 family (+ PE-S2-R3-06) | blocker | Design reviews DR-01 and DR-02 not held; the decider cells are empty | principal-designer (chair) |
| 2-5 | PD-RV2-DR-FE, -COACH, -BA, -PM | blocker | Each role's DR-02 and DR-01 decision cells are empty | senior-frontend-engineer, pickleball-domain-coach, business-analyst, product-manager |
| 6 | PD-RV2-DR-SEC | major | Security cell R2-6 is empty. The reviewer's decision ("Accept") is in its review output; the reviewer cannot write files, so the cell is filled once the reviewer confirms the text | security-privacy-engineer |
| 7 | QA-R3-GATE-01 / C-06 | major | VoiceOver and TalkBack pass: 0 of 24 rows run; NFR-027 (b) not met. Not waived | senior-qa-engineer with a human tester (P6, due 2026-11-13) |
| 8 | QA-RV3-02 | blocker | 5 committed test changes (TCR rows 24-28) have no QA decision | senior-qa-engineer |
| 9 | PE-S2-R3-01 | major | S-01 offers "move to next game" where the server refuses it; the client does not know `not_last_in_game` | senior-frontend-engineer |
| 10 | PE-S2-R3-02 | major | Contract drift: `not_last_in_game` and "latest kept rally first" are not in api-sprint-02 or match-aggregate | principal-engineer |
| 11 | PE-S2-R3-03 | major | No CI run at the close head. The newest is 37464553177 at `fd363fa` (success) | sre-devops-engineer |
| 12 | SEC-RV3-01 | major | The PO record says the repository is private; GitHub says it is public | human PO (P10); the EM escalates |
| 13 | QA-RV3-04 | major | `scripts/dev-chrome.sh` (ADR 0036 residual) is missing, so the H.264 evidence browser cannot be re-provisioned | sre-devops-engineer |
| 14 | BLK-GOLD-01 (BLK-GOLD-BUCKET) | major | No private bucket exists for footage that shows people, so ST-040 recording is blocked | sre-devops-engineer; human PO (provider, P11) |

Nine of the 14 wait on a decision: rows 1-6 by roles that never ran in this session, and rows 7, 12 and 14 by the human. Rows 8-11 and 13 are agent work, sized in §8.

## 2. Committed against implemented and DoD-done

| Lane | Committed units | Implemented | DoD-done | Not implemented |
|---|---|---|---|---|
| BE | 12.5 | 12.5 | 0 | — |
| FE | 12.0 | 12.0 | 0 | — |
| QA | 11.5 | 10.5 | 0 | C-06 (1.0): needs a human tester (P6) |
| SRE | 8.0 | 8.0 | 0 | — (W-01 implemented: ci-gate green at `fd363fa`; the nightly waits on the PR #1 merge) |
| ML | 2.0 | 2.0 | 0 | — |
| **Total** | **46.0** | **45.0 (0.978)** | **0** | |

**DoD-done is 0** because no story is "Merged to `main`", which is a story-level DoD box. PR #1 (`sprint-01` → `main`) is still open and `sprint-02` is not merged (PO merge order, po-input addendum "PR #1 path to green"). Two other gaps also apply: the UI stories ST-027..ST-032 and ST-037 lack "Design review held" (DR-02), and no CI run covers the close head.

**Stretch:** ST-028b is done (FE, `30fc21a`). ST-035, ST-034, ST-038, ST-033 and ST-036 were not started: the stretch rule allowed them only after review round 1, and the review rounds then used the remaining capacity. ST-025 is still blocked on P3. ST-042 moved to Sprint 3 at planning.

## 3. Gates

| Gate | State | Evidence |
|---|---|---|
| `ci-gate` on `sprint-02` | Green at `fd363fa`; **no run at the close head** | Run 37464553177 (success, 2026-10-06 12:52 UTC). Runs 37461758337, 37452407537, 37438997898 and 37434214390 failed and were triaged (`ci-status.md`) |
| WebKit | Green on CI at `fd363fa` (in run 37464553177); 0 Sprint 1 `[webkit]` failures since run 37438997898 | `ci-status.md` |
| Nightly (`nightly-quality.yml`) | Not run: the workflow is not on `main` until PR #1 merges | PO P1; merge-order addendum |
| Locust per-PR perf baseline (ST-039) | Green on CI: 0 failures, correction p95 410 ms, 51.2 RPS | Run 37438997898 |
| Integration smoke before review (ADR 0022) | Smoke 2 at `aeed281` and smoke 3 at `fe156e7`; **the "Sprint-close head" section is empty** | `smoke.md` |
| Test immutability (ADR 0014) | **Not met:** TCR rows 24-28 undecided (QA-RV3-02) | `test-change-requests.md` |
| Mutation gate on rules (NFR-072; a gate for the first time this sprint) | Met: 0.8635 ≥ 0.85 | G02-08 |

## 4. Sprint-level DoD

| Item | State |
|---|---|
| Every story meets the story-level DoD | **No** (0 of 46 units; §2) |
| Functional, integration, performance and E2E suites pass on `main` | **No**: nothing is merged to `main`. The suites pass on `sprint-02` locally (§5) and on CI at `fd363fa` |
| Model and coaching evals | N/A this sprint |
| Sprint goal demonstrated against its bullets | Bullets 1-4: **yes**, live (G02-01..G02-10 and the demo). Bullet 5 ("none is open at the close"): **no** (G02-11) |
| Manual screen-reader pass (NFR-027 b) | **Not met**: 0 of 24 rows (C-06, P6). Reported as not met, not waived |
| Retro written, previous actions reviewed | Yes: `docs/retros/2026-11-13-sprint-02.md` |
| Significant decisions have ADRs | Yes: ADRs 0034-0036 this sprint and ADR 0037 from the retro; small decisions are in `decision-log.md` |

## 5. Test counts by level (latest independent or isolated run)

| Level | Result | Source |
|---|---|---|
| Backend domain unit (CI `DOMAIN_TEST_PATHS`) | 1,031 passed, 1 skipped; 6.8-7.1 s | verifier round 3, G02-12 |
| Backend unit (`-m unit`) | 1,466 passed, 1 skipped; 10.3 s | verifier round 3, G02-12 |
| Backend integration + regression | 490 passed, 2 skipped. The 2 are the strict sandbox tests, run separately: 10 passed | verifier round 3, G02-03 |
| Scoring scenarios and properties | 304 passed, 1 skipped (P3); golden replay 4/4; `@needs-verification` 70 collected, 52/52 on committed stories | verifier round 3, G02-07 |
| Whole backend suite | 2,070 passed, 21 failed, 3 skipped. The 21 are `red_until` rows of stretch or PO-blocked stories (ST-035 ×18, ST-025 ×2, ST-024 ×1), which the gate excludes | QA review round 3 at `db0f0be` |
| Oracle / mutation | 100,000 sequences, 0 disagreements; rules 0.8635, projection 0.9196 | G02-08 |
| Web unit (Vitest) | 55 files, 458 passed; lines 91.7% | G02-09 |
| E2E (Playwright, Chrome for Testing, https) | 93 passed, 0 failed, 6 named skips; ×3: 279 passed, 0 flaky | G02-05 |
| Infra and harness | 472 passed | `cd infra && uv run pytest -q -p no:cacheprovider` at `b0e7cbb` (EM, this close) |
| Coverage | backend changed lines 97%; rules + aggregates 99.57% line / 98.41% branch | G02-09 |

## 6. Delivery metrics

| Measure | Sprint 2 | Sprint 1 |
|---|---|---|
| Commits on the branch | 161 (`2b97fa0..b0e7cbb`): 59 docs, 40 fix, 32 feat, 26 test, 2 style, 2 ci | 139 |
| Median commit size (changed lines) | 63; 16 commits over 400 (max 2,336) | 94; 13 over 400 |
| Commits after the integration smoke (`941bf7f`) | 45 | 49 |
| CI runs on the branch | 5 dispatched; 1 green (37464553177) | 3 |
| Deployment frequency, lead time, change failure rate, MTTR | N/A: nothing deployed, no merged PR | N/A |
| Review rounds | 3 review rounds + 3 goal verification rounds | 3 + 3 |
| Open blocker/major trajectory | 17 (planning) → 14 → 6 (review round 1) → 3 (round 2) → 2 (goal rounds 1-3) → **14** (close recount) | 17 at close |
| Escalations to the human | P1-P9 on day 1; P1-P5 answered; P10 and P11 new at this close | P1-P5 |

## 7. PO items

| Item | State | Need-by |
|---|---|---|
| P1-P4 | Answered 2026-10-06 (po-input addenda) | — |
| P5 disk prune | Answered 2026-10-06: approved | — |
| P6 screen-reader tester (C-06) | Open | 2026-11-13 |
| P7 USAP rulebook (OQ-01) | Open | 2026-11-16 (Sprint 3 planning) |
| P8 beta budget (OQ-13) | Open | 2026-11-13 |
| P9 testers and interviewees (OQ-20) | Open | 2026-11-16 |
| **P10 repository visibility (SEC-RV3-01), new** | Open. GitHub reports `nhuthuynh/racket-analytics` as **public** (API, 2026-10-06), but the PO record says private. Either make it private, or confirm it is public so the record is corrected. Until then the threat model's exploit notes and the dev keys are world-readable; no personal data is in git | 2026-11-13; sooner is safer |
| **P11 provider of the private footage bucket (BLK-GOLD-01), new** | Open (relayed 2026-10-06). No ST-040 footage of people may be recorded until the bucket exists | Sprint 3 planning, 2026-11-16 |

## 8. Carry-over to Sprint 3 (each row gets an owner and a Sprint 3 backlog row at planning)

| Row | Items | Owner | Size (judgment) |
|---|---|---|---|
| Design reviews | DR-02 (due end of 2026-10-07, otherwise it moves to DR-01's date); DR-01 (hard date 2026-11-02); PD-RV2-DR-FE/-COACH/-BA/-PM/-SEC | principal-designer with the named roles | 0 units (decisions); XS for FE follow-ups |
| Blocker/major code and docs | QA-RV3-02 TCR decisions; PE-S2-R3-01 (FE, red first); PE-S2-R3-02 (contract); PE-S2-R3-03 CI at the head; QA-RV3-04 `scripts/dev-chrome.sh` | QA, FE, PE, SRE | about 2 units |
| Human-gated | C-06 (P6); SEC-RV3-01 (P10); BLK-GOLD-01 (P11); ST-025 (P3 clips) | human PO with QA, SRE, ML | — |
| Minors and nits | PE-S2-R3-07/-08/-09, SEC-RV3-02/-03/-04, SEC-S2-TM-03-DOC/-04/-05/-07, QA-RV3-06, PD-R3S2-01/-02, PD-FL2-03/-05, VR1-01 | the owners named in review-rounds | about 3 units of review-loop reserve |
| Stretch not started | ST-035, ST-034, ST-038 (a gate before any non-dev deployment), ST-033, ST-036; ST-042 is already in Sprint 3 | BE, FE | as sized in sprint-02 §3 |
| Merge chain | `sprint-02` → `sprint-01` once ci-gate is green at the head, then PR #1 → `main`, then the first nightly | sre-devops-engineer, orchestrator | XS |

## 9. History of this report

- 2026-10-06, review round 2 status step: §1 first written from dry-runs (QA-RV2-05).
- 2026-10-06, goal rounds 1-2: §1 rewritten (10/12, then 11/12).
- 2026-10-06, sprint close: final report. G02-11 recounted from 2 to 14. This also fixes PD-R3S2-05: the earlier §1.2 left C-06 out as "counted elsewhere", which contradicted the scorecard method.
