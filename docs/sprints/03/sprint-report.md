# Sprint 3 report: starter stats with uncertainty and evidence, deletion, labelling tools

- **Prepared by:** engineering-manager, ticket RETRO-03, at the sprint close on 2026-10-15. This replaces the first close report of 2026-10-08, which was written before any Sprint 3 ticket reached `main` (`git show 6c666b9:docs/sprints/03/sprint-report.md`). The review with the PO keeps its planned date, 2026-11-27 (sprint-03 header).
- **Head measured:** `origin/main` `6c666b9` (merge of PR #80, FIX-03-2d), by the independent verifiers in VERIFY-03-r3 (goal-scorecard §12; PR #81, folded into this PR). After `6c666b9` only this docs PR changes the tree.
- **Sources:** `goal-scorecard.md` §10-§12 (verification rounds 1-3 on `main`), `review-rounds.md` (with the RETRO-03 reconciliation), the per-ticket files in `decisions/`, `smoke.md`, and GitHub REST read with the rules of `scripts/ci/merge_ready.py` (command in §3).

## 1. Goal and scorecard (read this first)

> **The Sprint 3 goal is NOT met** under the PO standing rule: **11 of 12** metrics met live on a fresh HTTPS Compose stack built from `main` at `6c666b9`. The one row short is **G03-12, open blocker/major findings: 2**, and neither needs product code.
>
> **The product works live, in real time, from `main`:** every player promise of the goal ran 5 of 5 times on fresh accounts (the seven stats per side equal to the reference after every tag and every correction; n, Wilson range and "low sample" in text; the "unofficial" notice; "Show me"; delete match; delete account, which signs out every session; the scheduled purge leaving 0 rows and 0 objects). Full Tag works for a consented labeller and its export validates. CI is green at the head in every job, WebKit and `drill-lint` included (push run 38714259188).
>
> **What is left for G03-12** (`open_defects.py` → rc=1, open 2, after the RETRO-03 reconciliation):
> - **PD-R1S3-01 group (blocker):** the BA and PM cells are done; the chair (principal-designer) has to flip the DR-03 row of `flows-sprint-03.md` §13 to "Held". Then the EM writes the Fixed row.
> - **EM-PR27-01 (major, new at this close):** PR #27 (ST-042) merged with a principal-engineer and an **sre-devops-engineer** verdict, but no senior engineer (ADR 0039 rule 3). A senior-backend-engineer verdict on `52582fd` closes it.
> - PE-PR24-01 (major) is **closed** by this reconciliation: the PE's APPROVE on PR #24's merged head exists (FIX-03-2b).

### 1.1 Metrics: target against actual (VERIFY-03-r3, `6c666b9`, 2026-10-15)

| ID | Target | Actual | Met | Evidence |
|---|---|---|---|---|
| G03-01 | 5 of 5 live journeys pass | 5/5, rc=0, no failing step key; delete account `{202, old session 401, items []}` ×5 | yes | `live_stats.py --runs 5 … --purge-cmd '$DC exec -T purge python -m racket.platform.purge --once'` → rc=0 in 24 s |
| G03-02 | (a) p95 ≤ 5,000 ms n ≥ 70; (b) p95 ≤ 5,000 ms n ≥ 5; (c) p95 ≤ 60,000 ms n ≥ 5 | (a) 32.7 ms n 70; (b) 23.0 ms n 5; (c) 24.0 ms n 5 | yes | `jq .summary live-stats.json` |
| G03-03 | 0 rows; every checked link 404; purge scheduled ≤ 24 h | 0 rows in 20 columns; 5/5 links 404; `PURGE_INTERVAL_S 86400`, first run ok | yes | live_stats `.summary.purge`; `$DC config \| grep PURGE_`; purge log `next_run_in_s 86400` |
| G03-04 | IT-03 + BOLA 100%, 0 skipped; earlier ITs 100%; ids present | IT-03 + BOLA 185/185; earlier 317/317; strict sandbox 10/10; missing none | yes | backend IT 797 passed, 2 skipped in 520 s rc=0; `junit_rate` rc=0 ×2 |
| G03-05 | p95 ≤ 300 ms, p99 ≤ 800 ms, ≥ 99.5%, 0 unexpected, ≥ 47.5 RPS | 28.1 ms, 59.6 ms, 100% of 3,000, 0 unexpected, 50.01 RPS | yes | `stats_latency.py --rps 50 --duration 60` → rc=0 (the §6 dry-run row is still missing: VR3-S3-02, process only) |
| G03-06 | 100% non-skipped, every E2E-03 id, ≤ 6 named skips, 0 flaky ×3 | 127/127, 6 named Sprint 1 skips, missing none, 0 flaky; WebKit green on CI | yes | `playwright test --workers=1` rc=0; `--repeat-each=3` 381 passed; `flaky_report` 0 flaky; CI run 38714259188 webkit success |
| G03-07 | dashboard p95 ≤ 2,000 ms; first frame p95 ≤ 1,500 ms; CLS 0; n ≥ 20 | 252.6 ms / 868.1 ms / 0, n 20 each | yes | `timing.spec.ts --repeat-each=20` 40 passed; `pw_timings.py --min-n 20` rc=0 |
| G03-08 | golden 100%; scenarios 100%; conservation 0 over ≥ 1,000; manifest rc 0; review record | golden 37/37; scenarios 42/42; property 1,000 / 0; manifest rc 0; 7/7 coach-reviewed | yes | `pytest -m golden_an` 37 passed; `racket-manifest-check` rc=0 |
| G03-09 | IT-03-11 and E2E-03-05 pass; lint 1 pass + 5 named fails; `drill-lint` CI green at the head | IT-03-11 15/15; E2E-03-05 1/1; lint ok + 5× rc=1 naming drill and reason; `drill-lint` and `ci-gate` success at `6c666b9` | yes | run 38714259188: all 17 jobs success or PR-only skip |
| G03-10 | axe 0 and targets 0 with D/E/X/L and states; keyboard; 320/360 | axe 0 over 60 attachments; targets 0; every family and state; keyboard and 320/360 passed | yes | `jq` over `reports/goal03/e2e.json` |
| G03-11 | changed lines ≥ 85%; analytics ≥ 90%; rules ≥ 95/90%; web ≥ 80%; mutation rules ≥ 0.85, stats ≥ 0.80; oracle 100,000/0; budgets 10/60/600 s | 97%; 98.34%; 99.57/98.41%; 93.03%; 0.8635 / 0.8977; 100,000/0; 6.2 s / 14.7 s / 478.0 s, 0 failed | yes | coverage run 3,050 passed; `diff-cover --compare-branch=ce91984` 97%; vitest 681 passed |
| G03-12 | 0 open blocker/major | verifier: 2 (PE-PR24-01, PD-R1S3-01 group). **After RETRO-03: 2** (PD-R1S3-01 group; EM-PR27-01). GitHub `bug` issues 0 | **no** | `open_defects.py docs/sprints/03/review-rounds.md` → rc=1, open 2 |

`@needs-verification`: 15 of the 21 frozen comparisons of G03-08 read the provisional scoring rules (AN-01/02/03/05/06). They are reported but count toward no Must FR. Stats stay "unofficial scoring (rules not yet verified)" until the PO supplies the rulebook (P7, ADR 0023).

### 1.2 Sub-rows of G03-12 and the demo

| Row | Target | Actual | Met | Owner if not met |
|---|---|---|---|---|
| G03-12-PE-PR24-01 | ledger row closed | **Closed by RETRO-03**: PE APPROVE on `898883b` (review 5530455097); `merged_verdict.py --pr 24 --role principal-engineer` → met, rc=0; Fixed row in `review-rounds.md` | **yes** (at this PR's merge) | — |
| G03-12-PD-R1S3-01 | ledger row closed | BA R3-9 cell done (FIX-03-2a #79); PM `sprint-03.md:35` done (FIX-03-2c #78, `unofficial_notice.py` agree rc=0); chair's §13 row still "not yet held" (`flows-sprint-03.md:292`; line 3 stale) | no | principal-designer (flip to Held with DoR R7), then engineering-manager (Fixed row) |
| G03-12-EM-PR27-01 | ledger row closed | New: no senior verdict on PR #27; `merged_verdict.py --pr 27 --role principal-engineer --role senior-backend-engineer` → rc=1 | no | senior-backend-engineer (verdict on `52582fd`); engineering-manager (row) |
| DEMO-03 | demo steps 1-10 as scripted; step 10 shows 0 open defects | Steps 1-9 live in real time (10:29:28-10:29:39Z): AN-01 A 4/7 0.5714 low sample; evidence 7/7, Range 206; correction AN-02 0.3333 → 0.4; delete hidden in 25 ms; purge rc 0, inventory 0\|0\|0, media 404; DELETE /me 202 then old session 401; Full Tag 200, labels 201, export validates, player 404. Step 10: `demo_test_report.py` rc=1 (11 of 12; open defects 2) | no | engineering-manager (follows G03-12) |

### 1.3 Human-gated rows (PO P12 option (b)): not counted in the totals

| Row | Item | State | Evidence | Owner |
|---|---|---|---|---|
| S3-DoD-P6 | Manual VoiceOver/TalkBack pass (38 rows, NFR-027 b) | **not met: waiting on P6** (0 of 38 rows run). Sprint 3 must not be called WCAG-checked | `a11y_manual.py --rows 38` → rc=1 | product-manager (to the PO); senior-qa-engineer with the tester |
| S3-DoD-P10 | Repository private, or confirmed public | **not met: waiting on P10** (GitHub reports public) | `repo_visibility.py` → rc=1 | product-manager (to the PO) |
| S3-DoD-P11 | Private footage bucket provider named | **not met: waiting on P11**; no footage of people stored | `footage_bucket.py` → rc=1 | product-manager (to the PO); sre-devops-engineer builds |

### 1.4 How the goal moved

| Round | Head | Met | Short |
|---|---|---|---|
| VR1 / VR2 / VR3 (on `sprint-03`) | `fdeeb53` / `593f7ff` / `fb920bc` | 0 / 2 / 10 of 12 | VR3: G03-09 (no CI at the head), G03-12 (3; close recount 8) |
| First close (2026-10-08) | `c1fba6a` | 10 of 12 | G03-09, G03-12 = 8; 0 ticket PRs |
| VERIFY-03-r1 on `main` (2026-10-10; §10) | `1842e96` | 11 of 12 | G03-12 = 6 (ledger behind `main`, VM-R1-01) |
| VERIFY-03-r2 on `main` (2026-10-15; §11) | `420ca96` | 11 of 12 | G03-12 = 2 |
| VERIFY-03-r3 on `main` (2026-10-15; §12) | `6c666b9` | 11 of 12 | G03-12 = 2 (after RETRO-03: still 2, one swapped) |

## 2. Tickets: PR, reviews, CI and merge

**71 ticket PRs merged into `main`** (#5-#80 except the docs PRs listed below), **0 sprint-wide PRs** (PR #4, `sprint-03` → `main`, was closed unmerged). Every merged PR has `ci-gate` success on its head. **68 of 71** meet the review rule on the merged head (a principal-engineer and a senior-engineer "Verdict: APPROVE" on the head SHA). Three do not: #24, #26 and #27 (§2.2).

Command (read-only; reuses `merge_ready.py`'s `verdicts`, `review_reasons`, `check_reasons` and `latest_runs` for each PR, at the PR's head SHA): a scratch script in the EM's scratchpad that imports `scripts/ci/merge_ready.py` and calls `GET /pulls/{n}`, `/pulls/{n}/reviews`, `/commits/{head}/check-runs` and `/actions/runs?head_sha={head}` for #5-#15, #17, #19-#80 → rc=0. #6-#15 (merged before `merge_ready.py` was on `main`, 13:57Z on 2026-10-08) wrote "Reviewer:" in a looser format the script does not parse; their verdicts were read by hand (`pull_request_read get_reviews`): each has a principal-engineer and a senior APPROVE on the merged head.

Columns: changed lines are GitHub's additions + deletions (labels: `waiver` = `size-waiver`, `TCR` = `qa-approved-test-change`); "Rule met" is the review rule on the merged head; "CI" is `ci-gate` on the PR head.

| Ticket | PR | Merged (UTC) | Head | Changed | Latest verdicts | Rule met | CI | Note |
|---|---|---|---|---|---|---|---|---|
| CI-PR-GATE | #5 | 2026-10-08 13:57 | `30a4fa7` | 1222 (waiver) | PE APPROVE; senior-qa-engineer APPROVE | yes | green |  |
| SIZE-WAIVERS-03 | #6 | 2026-10-08 13:16 | `5561836` | 607 (waiver) | PE + senior APPROVE on head (pre-`merge_ready` format, read by hand) | yes | green |  |
| SEC-RV3-02 | #7 | 2026-10-08 05:51 | `d6b5646` | 385 | PE + senior APPROVE on head (pre-`merge_ready` format, read by hand) | yes | green |  |
| CI-WEBKIT-PD-R3S2-02 | #8 | 2026-10-08 13:10 | `f6e3a23` | 397 | PE + senior APPROVE on head (pre-`merge_ready` format, read by hand) | yes | green |  |
| CI-FLAKE-RESUMABLE | #9 | 2026-10-08 06:46 | `a3e17fe` | 170 (TCR) | PE + senior APPROVE on head (pre-`merge_ready` format, read by hand) | yes | green |  |
| CI-FLAKE-RESUMABLE-2 | #10 | 2026-10-08 15:18 | `9402341` | 465 (waiver) | PE APPROVE; senior-frontend-engineer APPROVE | yes | green |  |
| CI-POLICY-BASE | #11 | 2026-10-08 07:30 | `58cd8c7` | 472 | PE + senior APPROVE on head (pre-`merge_ready` format, read by hand) | yes | green |  |
| PE-R1S3-07 | #12 | 2026-10-08 08:32 | `b46d58e` | 398 | PE + senior APPROVE on head (pre-`merge_ready` format, read by hand) | yes | green |  |
| CI-PERF-GATES | #13 | 2026-10-08 09:25 | `90bc69c` | 888 (TCR, waiver) | PE + senior APPROVE on head (pre-`merge_ready` format, read by hand) | yes | green |  |
| ST-052 | #14 | 2026-10-10 12:27 | `5e10cfd` | 2196 (TCR, waiver) | PE APPROVE; senior-qa-engineer APPROVE | yes | green |  |
| CI-INTEG-BUDGET | #15 | 2026-10-08 13:09 | `b184b95` | 695 (waiver) | PE + senior APPROVE on head (pre-`merge_ready` format, read by hand) | yes | green |  |
| CI-IT0213-HANG | #17 | 2026-10-08 14:36 | `342302b` | 467 (TCR, waiver) | PE APPROVE; senior-qa-engineer APPROVE | yes | green |  |
| C3-01 | #19 | 2026-10-08 19:48 | `9fceaaa` | 15 (TCR) | PE APPROVE; senior-backend-engineer APPROVE | yes | green |  |
| HARNESS-03 | #20 | 2026-10-08 20:04 | `c1800f7` | 2057 (waiver) | PE APPROVE; senior-backend-engineer APPROVE | yes | green |  |
| C3-04 | #21 | 2026-10-08 19:48 | `286321b` | 398 | PE APPROVE; senior-qa-engineer APPROVE | yes | green |  |
| C3-03 | #22 | 2026-10-08 20:14 | `bd78ea5` | 461 (TCR, waiver) | PE APPROVE; senior-qa-engineer APPROVE | yes | green |  |
| QA-R1S3-01 | #23 | 2026-10-08 19:49 | `48fdebb` | 106 | PE APPROVE; senior-qa-engineer APPROVE | yes | green |  |
| ST-043 | #24 | 2026-10-08 20:13 | `898883b` | 941 (waiver) | PE APPROVE; senior-qa-engineer CHANGES REQUESTED (earlier head `9583e71`) | **no** | green | PE APPROVE on the merged head only post-merge (FIX-03-2b, 2026-10-15); senior-qa APPROVE as an issue comment. PE-PR24-01 fixed |
| SRE-PURGE-a | #25 | 2026-10-08 21:18 | `9c501a8` | 914 (waiver) | senior-backend-engineer APPROVE; PE APPROVE | yes | green |  |
| ST-044 | #26 | 2026-10-08 20:12 | `7974a9b` | 1119 (waiver) | PE APPROVE (earlier head `b3ec328`); senior-qa-engineer APPROVE (earlier head `b3ec328`) | **no** | green | both APPROVE on `b3ec328`; one docs-only commit after (PE-PR26-01, minor, open) |
| ST-042 | #27 | 2026-10-08 20:14 | `52582fd` | 1291 (waiver) | PE APPROVE; sre-devops-engineer APPROVE | **no** | green | second verdict by sre-devops-engineer, not a senior engineer (EM-PR27-01, major, open) |
| C3-02 | #28 | 2026-10-08 19:47 | `e1e2f85` | 19 | PE APPROVE; senior-frontend-engineer APPROVE | yes | green | docs only (C3-02) |
| ST-045 | #29 | 2026-10-08 21:16 | `c22dbf1` | 739 (waiver) | PE APPROVE; senior-qa-engineer APPROVE | yes | green |  |
| C3-10 | #30 | 2026-10-08 21:16 | `695b5ca` | 474 (TCR, waiver) | PE APPROVE; senior-qa-engineer APPROVE | yes | green |  |
| DR-02-FE | #31 | 2026-10-08 21:50 | `5994ae7` | 260 | PE APPROVE; senior-qa-engineer APPROVE | yes | green |  |
| ST-049 | #32 | 2026-10-08 22:27 | `c3a3607` | 972 (TCR, waiver) | PE APPROVE; senior-backend-engineer APPROVE | yes | green |  |
| COACH-1 | #33 | 2026-10-08 23:33 | `c6c15e7` | 1568 (TCR, waiver) | PE APPROVE; senior-qa-engineer APPROVE | yes | green |  |
| QA-ACC-3 | #34 | 2026-10-08 23:33 | `4ca7db3` | 3149 (TCR, waiver) | PE APPROVE; senior-backend-engineer APPROVE | yes | green |  |
| QA-FUZZ-3 | #35 | 2026-10-09 01:48 | `b0956fb` | 502 (TCR, waiver) | PE APPROVE; senior-backend-engineer APPROVE | yes | green |  |
| GS-AN-1-V2 | #36 | 2026-10-09 00:48 | `f2fabe4` | 368 (TCR) | PE APPROVE; senior-qa-engineer APPROVE | yes | green |  |
| ST-054 | #37 | 2026-10-09 04:14 | `6aa7733` | 924 (TCR, waiver) | PE APPROVE; senior-backend-engineer APPROVE | yes | green |  |
| PE-DESIGN-3 | #38 | 2026-10-09 03:21 | `637e50e` | 1317 (waiver) | senior-backend-engineer APPROVE; PE APPROVE | yes | green |  |
| VR1-S3-01 | #39 | 2026-10-09 05:36 | `5280853` | 83 (TCR) | PE APPROVE; senior-backend-engineer APPROVE | yes | green |  |
| ST-053 | #40 | 2026-10-09 06:54 | `2beedde` | 1764 (TCR, waiver) | senior-backend-engineer APPROVE; PE APPROVE | yes | green |  |
| ST-046a | #41 | 2026-10-09 06:03 | `865dea0` | 1026 (TCR, waiver) | PE APPROVE; senior-qa-engineer APPROVE | yes | green |  |
| ST-046b | #42 | 2026-10-09 07:09 | `47bb28e` | 652 (TCR, waiver) | PE APPROVE; senior-qa-engineer APPROVE | yes | green |  |
| ST-052a | #43 | 2026-10-09 08:33 | `d189f2a` | 911 (waiver) | PE APPROVE; senior-backend-engineer APPROVE | yes | green |  |
| ST-047-API | #44 | 2026-10-09 08:32 | `b7b4173` | 330 (TCR) | PE APPROVE; senior-qa-engineer APPROVE | yes | green |  |
| ST-050a | #45 | 2026-10-09 09:41 | `24ca0ef` | 724 (TCR, waiver) | PE APPROVE; senior-qa-engineer APPROVE | yes | green |  |
| ST-048 | #46 | 2026-10-10 00:55 | `6f2334f` | 2694 (TCR, waiver) | PE APPROVE; senior-qa-engineer APPROVE | yes | green |  |
| ST-050b | #47 | 2026-10-09 11:18 | `563e391` | 1235 (TCR, waiver) | PE APPROVE; senior-qa-engineer APPROVE | yes | green |  |
| CI-DOMAIN-BUDGET | #48 | 2026-10-09 14:54 | `ab8a2e7` | 522 (waiver) | PE APPROVE; senior-qa-engineer APPROVE | yes | green |  |
| CI-E2E-MAIN-RED | #49 | 2026-10-09 16:47 | `52648da` | 418 (TCR, waiver) | PE APPROVE; senior-qa-engineer APPROVE | yes | green |  |
| CI-MERGE-READY-CANCELLED | #50 | 2026-10-09 15:52 | `508866c` | 522 (waiver) | PE APPROVE; senior-qa-engineer APPROVE | yes | green |  |
| CI-REDUNTIL-HANG | #51 | 2026-10-09 19:58 | `3469dec` | 394 | PE APPROVE; senior-backend-engineer APPROVE | yes | green |  |
| CI-OBJSTORE-SLOW | #52 | 2026-10-09 22:27 | `501a2df` | 637 (waiver) | senior-backend-engineer APPROVE; PE APPROVE | yes | green |  |
| ST-051-API | #53 | 2026-10-10 02:20 | `bf02c61` | 1190 (TCR, waiver) | PE APPROVE; senior-qa-engineer APPROVE | yes | green |  |
| SRE-PURGE-b | #54 | 2026-10-10 00:56 | `dd53fee` | 304 | PE APPROVE; senior-backend-engineer APPROVE | yes | green |  |
| ST-038 | #55 | 2026-10-10 07:49 | `a48b46c` | 903 (TCR, waiver) | senior-qa-engineer APPROVE; PE APPROVE | yes | green |  |
| ST-050 | #56 | 2026-10-10 07:41 | `d5bf341` | 554 (TCR, waiver) | senior-qa-engineer APPROVE; PE APPROVE | yes | green |  |
| CI-E2E-JOURNEYS-TIMEOUT | #57 | 2026-10-10 05:06 | `0635f33` | 397 | PE APPROVE; senior-qa-engineer APPROVE | yes | green |  |
| ST-051 | #58 | 2026-10-10 08:57 | `82484bb` | 333 (TCR) | senior-qa-engineer APPROVE; PE APPROVE | yes | green |  |
| G03-FE-404 | #59 | 2026-10-10 08:30 | `4250a31` | 10 | PE APPROVE; senior-qa-engineer APPROVE | yes | green |  |
| ST-052b | #60 | 2026-10-10 10:12 | `ec6ac37` | 876 (TCR, waiver) | PE APPROVE; senior-backend-engineer APPROVE | yes | green |  |
| ST-052c | #61 | 2026-10-10 11:10 | `34ea807` | 779 (TCR, waiver) | PE APPROVE; senior-backend-engineer APPROVE | yes | green |  |
| VR2-S3-01 | #62 | 2026-10-10 11:35 | `e0bea28` | 9 | senior-backend-engineer APPROVE; PE APPROVE | yes | green |  |
| PE-R3S3-03-ITS | #63 | 2026-10-10 13:29 | `d185e33` | 949 (waiver) | senior-backend-engineer APPROVE; PE APPROVE | yes | green |  |
| DOCS-03 | #64 | 2026-10-10 14:25 | `9aa150e` | 4180 (waiver) | senior-qa-engineer APPROVE; PE APPROVE | yes | green |  |
| DR-HELD-03 | #65 | 2026-10-10 19:38 | `fd1ebd2` | 181 | PE APPROVE; senior-frontend-engineer APPROVE | yes | green |  |
| CI-OBJSTORE-STALL | #66 | 2026-10-10 17:26 | `3bf24c5` | 295 | senior-backend-engineer APPROVE; PE APPROVE | yes | green |  |
| PE-R3S3-04 | #67 | 2026-10-10 20:16 | `f10cf2d` | 720 (waiver) | PE APPROVE; senior-qa-engineer APPROVE | yes | green |  |
| FIX-03-1b | #70 | 2026-10-11 06:00 | `52285d2` | 812 (waiver) | PE APPROVE; senior-backend-engineer APPROVE | yes | green |  |
| FIX-03-1c | #71 | 2026-10-11 01:53 | `be8f802` | 748 (waiver) | PE APPROVE; senior-backend-engineer APPROVE | yes | green |  |
| FIX-03-1a | #72 | 2026-10-11 00:09 | `d4ed6d5` | 842 (waiver) | PE APPROVE; senior-backend-engineer APPROVE | yes | green |  |
| FIX-03-1d | #73 | 2026-10-11 00:08 | `180768e` | 701 (waiver) | PE APPROVE; senior-backend-engineer APPROVE | yes | green |  |
| CI-POLICY-LIVE-LABELS | #74 | 2026-10-11 01:11 | `3626b6d` | 393 | senior-backend-engineer APPROVE; PE APPROVE | yes | green |  |
| CI-STALL-SCENARIO-RACE | #75 | 2026-10-11 04:25 | `cbe2081` | 694 (TCR, waiver) | senior-qa-engineer APPROVE; PE APPROVE | yes | green |  |
| FIX-03-2b | #77 | 2026-10-15 09:15 | `482e716` | 370 | PE APPROVE; senior-backend-engineer APPROVE | yes | green |  |
| FIX-03-2c | #78 | 2026-10-15 09:15 | `c77a727` | 351 | PE APPROVE; senior-backend-engineer APPROVE | yes | green |  |
| FIX-03-2a | #79 | 2026-10-15 09:16 | `bb3657a` | 24 | PE APPROVE; senior-backend-engineer APPROVE | yes | green |  |
| FIX-03-2d | #80 | 2026-10-15 09:37 | `0255a75` | 400 | PE APPROVE; senior-backend-engineer APPROVE | yes | green |  |

### 2.1 PRs not merged

| PR | What | Outcome |
|---|---|---|
| #4 | `sprint-03` → `main` (sprint-wide PR) | Closed unmerged: replaced by the ticket PRs (ADR 0039, PO P13) |
| #16 | SMOKE-03 at `5f80f0a` (first attempt) | Closed unmerged; superseded by #68 |
| #68 | SMOKE-03 sprint-close smoke of `main` at `1842e96` | **Folded into this PR** (merge of its branch; `smoke.md` section and `decisions/SMOKE-03.md`); closed with a pointer |
| #69, #76, #81 | VERIFY-03-r1, -r2, -r3 (goal verification on `main`) | **Folded into this PR** as scorecard §10, §11, §12 with their decisions files; the scorecard table keeps the r3 values; closed with a pointer (VM-R2-02, VM-R3-01) |

### 2.2 Merges that missed the review rule (all three merged in one batch, 2026-10-08 20:12-20:14 UTC)

| PR | Ticket | What was missing at merge | Now |
|---|---|---|---|
| #24 | ST-043 | PE's latest verdict CHANGES REQUESTED on `9583e71` (its round-2 review stayed PENDING); the senior-qa APPROVE on `898883b` was an issue comment | PE APPROVE on `898883b` posted 2026-10-15 (FIX-03-2b #77); PE-PR24-01 **Fixed** (RETRO-03) |
| #26 | ST-044 | Both APPROVE on `b3ec328`; the merged head `7974a9b` adds one docs-only commit (its own decision rows) | PE-PR26-01 (minor) open: both reviewers to confirm the delta |
| #27 | ST-042 | Second verdict from the sre-devops-engineer, not a senior engineer; `merge_ready.py` (on `main` since 13:57Z) would have refused | EM-PR27-01 (major) **open** |

Root cause and action: retro 3 M10, action B1.

## 3. Committed against implemented and DoD-done

DoD-done here means the work is on `main` through merged ticket PRs that meet the review rule, with CI green. Units are ADR 0010's.

| Lane | Committed | Implemented | DoD-done | Not DoD-done |
|---|---|---|---|---|
| BE | 12.5 | 12.5 | 11.5 | ST-042 BE half (1.0): EM-PR27-01 |
| FE | 11.0 | 11.0 | 11.0 | — |
| QA | 9.5 | 9.0 | 9.0 | C3-06 (0.5): needs a human tester (P6) |
| SRE | 7.0 | 4.0 | 2.0 | ST-042 SRE half (1.0, EM-PR27-01); SRE-SMOKE-3 (1.0, DoD-done when this PR merges); not implemented: C3-08 (1.0, P11), ST-054 SRE half (1.0, Locust on stats/evidence in CI), SRE-MIN-3 (1.0) |
| ML | 3.0 | 3.0 | 3.0 | — |
| **Total** | **43.0** | **39.5 (0.919)** | **36.5 (0.849)** | |

- First close (2026-10-08): 38.5 implemented, **0** DoD-done. The change is the ticket-PR delivery of 2026-10-08..15 (retro 3 A1).
- Decider tasks: DR-01 and DR-02 **held** (DR-HELD-03 #65, 2026-10-10); DR-03 decided on every item, **not yet recorded held** (PD-R1S3-01). ADR 0043 accepted (#65). ADR 0005 is still Proposed (PM-1).
- Stretch: ST-035, ST-034, ST-033, ST-036 not started; ST-025 still blocked on P3 clips.
- Sprint 4 stories meeting the DoR (BA-1): not delivered (§5).

## 4. Gates and CI

| Gate | State | Evidence |
|---|---|---|
| `ci-gate` on `main` at the head | **Green**, all jobs (WebKit, `drill-lint`, Integration, E2E chromium/webkit) | push run 38714259188 at `6c666b9` |
| CI on `main`, 2026-10-08..15 | 71 push runs: 53 success, 3 failure, 15 cancelled (13 superseded by the next merge, 2 at the job time limit) | `actions_list list_workflow_runs ci.yml branch=main event=push` (REST, created ≥ 2026-10-08) |
| Red `main` incidents (CI FIRST, PO 2026-10-08) | 5, each fixed by its own ticket before feature work: domain budget (37882972340 → CI-DOMAIN-BUDGET #48); E2E (37905693381 → CI-E2E-MAIN-RED #49); `red_until` step hang (37961668800 → CI-REDUNTIL-HANG #51, CI-OBJSTORE-SLOW #52); E2E journeys 42 min (38016581726 → CI-E2E-JOURNEYS-TIMEOUT #57); infra stall-report scenario race (38103354166, after #71 → CI-STALL-SCENARIO-RACE #75). Not counted, as the run passed: the object-store throughput preflight stall seen in 38059526467 (→ CI-OBJSTORE-STALL #66) | the tickets' decisions files |
| Merge gate (`merge_ready.py`, CI-PR-GATE #5) | On `main` from 2026-10-08 13:57Z. Bypassed once (the 20:12-20:14 batch: #24, #26, #27) | §2.2 |
| Integration smoke at the close | Green on `main` `1842e96` (SMOKE-03, folded in); VERIFY-03-r3 ran the live stack again at `6c666b9` | `smoke.md` last section; scorecard §12 |
| Test immutability (ADR 0014) | 29 merged PRs carried `qa-approved-test-change` (applied only by the QA decision step; rows in `test-change-requests.md` and the ticket files) | `test-change-requests.md`; labels in §2 |
| PR size (≤ 400, ADR 0030) | 46 of 71 merged PRs over 400 changed lines, 45 with an EM `size-waiver`; #11 (472 by GitHub's count) passed `check_pr_size.py` (lockfile excluded) | §2 table; `SIZE-WAIVERS-03.md` |
| Nightly on `main` | Green: oracle 100,000/0, mutation rules 0.8635 (2026-10-15, run 38700640873 at `420ca96`) | `status.json` `nightly` |

## 5. Sprint-level DoD (sprint-03 §9)

| Item | State |
|---|---|
| Every metric card shows n and a working "Show me"; the notice once before the first card | **Yes**, live (G03-01, demo steps 2-3; E2E-03-01/02/03); `sprint-03.md:35` now matches (FIX-03-2c) |
| Only `coach-reviewed` metrics; review record per entry | **Yes**: 7 of 7 (G03-08 e) |
| Rule-dependent rows reported separately | **Yes** (15 of 21, §1.1) |
| Traceability matrix lists the Sprint 3 feature files | **Yes** (`traceability-matrix.md` §13; outcome at this close §15) |
| Sprint 4 stories meet the DoR (BA-1) | **No**: BA-1 not delivered; Sprint 4 planning runs it as a gate task (ADR 0047 rule 2) |
| Retro 2 actions reviewed first | Yes (sprint-03 §0.3; retro 3 §1) |
| Every scorecard row "yes" | **No**: 11 of 12 (G03-12) |
| Every method dry-run before the verifier | **No**: the G03-05 row is still missing (VR3-S3-02) |
| Every round has an EM reconciliation row | **Late**: VERIFY-03-r1..r3 had none until RETRO-03; FIX-03-1a reconciled the ticket PRs on 2026-10-10 |
| Every decider task has its output, or an escalation, by its date | **Late**: BA/PM DR-03 cells landed 2026-10-15; the chair's DR-03 record is still open |
| Human-gated items handled as the PO chose | **Yes**: P12 (b), §1.3 |
| Every ticket reached `main` as its own PR with two APPROVE verdicts on the merged head | **68 of 71**; #24 now fixed after merge, #26 (minor) and #27 (major) open |

## 6. Test counts by level (latest independent run, VERIFY-03-r3 at `6c666b9`, unless named)

| Level | Result | Source |
|---|---|---|
| Backend, whole gated run with coverage | 3,050 passed, rc=0; changed lines 97% (vs `ce91984`); analytics 98.34%; rules 99.57/98.41% | G03-11 |
| Backend integration + regression (real Postgres, object store, Mailpit) | 797 passed, 2 skipped (strict sandbox, run separately 10/10) in 520 s; IT-03 + BOLA 185/185; earlier 317/317 | G03-04 |
| Scenarios and properties | analytics scenarios 42/42; golden GS-AN-1 v2 37/37; conservation 1,000 / 0; manifest rc 0 | G03-08 |
| Oracle / mutation | 100,000 / 0; rules 0.8635; starter stats 0.8977 | G03-11 |
| Fast-test budgets | domain 6.2 s of 10; unit 14.7 s of 60; integration 478.0 s of 600 | G03-11 |
| Web unit (Vitest) | 681 passed; lines 93.03% | G03-11 |
| E2E (Playwright, Chrome for Testing, https) | 127 passed, 6 named skips; ×3: 381 passed, 0 flaky; timing 40 passed; WebKit green on CI | G03-06, G03-07 |
| Infra and harness | 936 passed, 3 skipped (SMOKE-03 at `1842e96`); this ticket's run at the PR head in its PR body | `smoke.md` |

## 7. Delivery metrics

| Measure | Sprint 3 | Sprint 2 |
|---|---|---|
| Ticket PRs merged into `main` | **71** (2026-10-08 05:51 → 2026-10-15 09:37 UTC) | 0 (Sprint 1 + 2 merged as PR #2) |
| Deployment frequency | N/A: nothing deployed beyond `main` (no staging) | N/A |
| PR time-to-merge (open → merged) | median 1.6 h, mean 3.3 h, max 51.8 h (#14) | — |
| Median PR size (GitHub additions + deletions) | **607**; 6 of 71 ≤ 100; 46 over 400 (45 waived); max 4,180 (#64, DOCS-03) | median commit 63 |
| Change failure rate (`main` push runs red or timed out after a merge) | 5 of 71 runs (7%), each fixed first by a CI ticket | N/A |
| Time to restore `main` CI | each red run fixed by the next merged CI ticket, from 1.5 h to about 1 day (judgment from the merge times) | N/A |
| Review rule met on the merged head | 68 of 71 (§2.2) | — |
| Review rounds per PR | 1-3 per PR (verdict reviews on earlier heads, §2 table) | — |
| Goal metrics met (verifier) | 0 → 2 → 10 (on `sprint-03`) → 11 → 11 → 11 (on `main`) | 10 → 11 → 11 |
| Open blocker/major | 14 (planning) → 8 (first close) → 6 (VERIFY-03-r1) → 2 → **2** | 17 → 14 |
| Escalations to the human | P6-P14; P12 and P13 answered | P1-P11 |

## 8. PO items

| Item | State | Need-by |
|---|---|---|
| P6 screen-reader tester | Open (S3-DoD-P6) | overdue (2026-11-13) |
| P7 rulebook (OQ-01) | Open; scoring and stats stay "unofficial" | 2026-11-16 |
| P8 beta budget (OQ-13) | Open | before any beta |
| P9 testers and second reviewer (OQ-20) | Open; gates `verified`, not `coach-reviewed` (ADR 0044) | 2026-11-16 |
| P10 repository visibility | Open (S3-DoD-P10) | sooner is safer |
| P11 footage bucket provider | Open (S3-DoD-P11) | before any footage of people, and before Full Tag on real matches |
| P12 human-gated goal items | Answered 2026-10-07: option (b) | — |
| P13 start of the ticket-PR rule | Answered 2026-10-08 (ADR 0039): Sprint 3 ships as ticket PRs | — |
| P14 decider cells | Done by the deciders (last: BA R3-9, 2026-10-15) | — |

## 9. Carry-over to Sprint 4 (each row gets an owner and a Sprint 4 backlog row at planning)

| Row | Items | Owner | Size (judgment) |
|---|---|---|---|
| C4-G12 | Close G03-12: the chair's DR-03 "Held" flip and line 3 (PD-R1S3-01, VM-R3-03); a senior verdict on PR #27 (EM-PR27-01); then the EM's Fixed rows and a re-run of `demo_test_report.py` | principal-designer; senior-backend-engineer; engineering-manager | 0 build units; under 1 hour of review |
| C4-GATE | Merge only through `merge_ready.py` (no batch merges); post-merge `merged_verdict.py` on every PR in the status step (retro 3 B1) | orchestrator (merge step); engineering-manager checks | 0.5 unit |
| C4-SEC | T-AC-5 (re-created account has no labeller role; SEC-S3-TM-07); the other ADR 0045 ITs are on `main` (#63) | senior-qa-engineer | 0.5 unit |
| C4-SRE | ST-054 SRE half (Locust on stats/evidence in CI); SRE-MIN-3; VR3-S3-01 (`extra_ca` in `infra/compose.yaml`); VR3-S3-02 (G03-05 dry-run row) | sre-devops-engineer | 2 units |
| C4-MIN | PE-PR26-01; PE-ST043-03/-04/-06/-07/-08; VM-R1-02, VM-R2-01, VM-R3-02; the verifier-id pattern in `measurelib._FINDING_ID`; the earlier minors of the first close (PE-R3S3-06/-07/-08, SEC-R3S3-04, SEC-S3-TM-03/-04/-09/-10, PD-R3S3-02, PD-FL3-02/-03, VR2-S3-03, VR3-S3-03, PE-S2-R3-08) as their latest ledger rows say | owners in `review-rounds.md` | about 3 units of review-loop reserve |
| C4-PROC | R3-IN-1 `Red:` check in CI (retro 3 A5, still not built); BA-1 DoR for Sprint 4; ADR 0005 PM-1 | engineering-manager with sre-devops-engineer; business-analyst; product-manager | 1 unit |
| Human-gated | S3-DoD-P6, -P10, -P11; ST-025 (P3 clips); P7 rulebook | human PO with QA, SRE, ML | — |
| Stretch not started | ST-035, ST-034, ST-033, ST-036 | BE, FE | as sized in sprint-02 §3 |

## 10. History of this report

- 2026-10-08, first close (`c1fba6a`): 10 of 12; G03-12 recounted 3 → 8; 0 ticket PRs; DoD-done 0.
- 2026-10-15, sprint close (RETRO-03, `6c666b9`): rewritten after 71 ticket PRs merged and three verification rounds on `main`; 11 of 12; G03-12 = 2 after the RETRO-03 reconciliation; DoD-done 36.5 of 43.
