# Sprint 2 report: Quick Tag to an unofficial score sheet, with undo, corrections and the rally video

- **Prepared by:** engineering-manager. Started 2026-10-06 in the review-round-2 status step (QA-RV2-05). §1 is rewritten in each status step when the scorecard numbers or the open count change (ADR 0033; sprint-02 §4 EM row). The other sections are written at the sprint close.
- **Head at this writing:** `48e1e71` on `sprint-02`, plus this docs-only commit.
- **Read this first:** nothing in §1 is the independent verifier's measurement. The verifier has not run yet, so the `Actual` / `Met` / `Evidence` columns of `goal-scorecard.md` §2 are still empty, as that file's rules require. §1 shows the newest **live** numbers from method authors' dry-runs (scorecard §6) and from reviewers' live checks, each with its source. They show where the goal stands, not that it is met.

## 1. Goal and scorecard status (review round 2, 2026-10-06)

> **The Sprint 2 goal is NOT yet shown to be met.** Live dry-runs reach the target on 10 of 12 rows. **G02-11** (open defects: 3 after this round, target 0) and **G02-12** (domain suite over its 10 s budget on the loaded host) do not. The verifier's isolated run is still to come.
>
> New this round: the H.264 blocker is closed locally. With ADR 0036 (Chrome for Testing at `/opt/google/chrome`, `PW_CHROMIUM_CHANNEL=chrome`), E2E-02-04, G02-06 (c) and the V-01 axe check on the real video now run **on the local stack**. No PO exception is needed.

### 1.1 Metrics: target against the latest live result

| ID | Target | Latest live result | Source (who, head, stack) | On target |
|---|---|---|---|---|
| G02-01 | 5 of 5 runs pass | 5/5, rc=0, no failing step (step 9 `@needs-verification` passed) | EM dry-run, `48e1e71`, own native https stack `.local/em-rv2` (https://localhost:47943) | yes (dry-run) |
| G02-02 | (a) p95 ≤ 1,500 ms, ≥ 100 samples, 0 failed, byte-identical; (b) p95 ≤ 5 s | (a) p95 28.3 ms, n=100, 0 failures, restored byte-identical (76 rallies, 3 games); (b) p95 17 ms, n=30 | same run | yes (dry-run) |
| G02-03 | (a) 100%, every id; (b) 13/13 | IT-02 231/231, missing []; IT-01 80/80, missing []; rc=0 | QA dry-run, `0609d6a`..`77a7201` | yes (dry-run) |
| G02-04 | p95 ≤ 300 ms, p99 ≤ 800 ms, ≥ 99.5%, 0 unexpected, ≥ 47.5 RPS | p95 14.5 ms, p99 17.7 ms, availability 1.0, 0 unexpected, 50.0 RPS, 3,000 requests, rc=0 | EM dry-run, `48e1e71`, `.local/em-rv2` (load on the API port, seeding through https) | yes (dry-run) |
| G02-05 | 100% of non-skipped, 0 failed, every E2E-02 id, ≤ 6 named skips, 0 flaky ×3 | `93 passed, 0 failed, 6 skipped`, rate 1.0, missing [], 6 skips each name their API binding; ×3 repeat `279 passed, 0 failed, 18 skipped`, `flaky_report.py --fail-on-flaky` rc=0, 0 flaky | EM dry-run in Chrome for Testing (ADR 0036), `48e1e71`, `.local/em-rv2` | yes (dry-run) |
| G02-06 | (a) ≤ 200; (b) ≤ 100; (c) ≤ 1,500; (d) ≤ 2,000 ms p95, n ≥ 20 each | (a) 11.5 ms n=160; (b) 11.8 ms n=640; (c) 740.1 ms n=40 (reference profile, real H.264 link); (d) 392.8 ms n=60; `pw_timings.py` rc=0 | same | yes (dry-run) |
| G02-07 | 100% (P3 skip), golden 100%, ≥ 46 provisional, 0 `red_until` on committed, ≤ 90 s | 275 passed, 1 skipped (P3) in 34.9 s; golden 4 passed; 62 provisional collected; 0 | QA dry-run | yes (dry-run) |
| G02-08 | (a) 100,000, 0 disagreements; (b) ≥ 0.85; (c) recorded | (a) 0 disagreements; (b) 0.8635; (c) 0.9107 | QA dry-run | yes (dry-run) |
| G02-09 | changed lines ≥ 85%; rules/aggregates ≥ 95% / 90%; web ≥ 80% | 97%; 99.54% / 98.25%; 91.02% | QA dry-run | yes (dry-run) |
| G02-10 | (a) 0 serious/critical, T K S H V + Sprint 1 families; (b) 0 and 0; (c), (d) passed | 37 axe checks, 0 serious/critical, families T, K, S, H, **V on the real video (`axe-V-01`)** and every Sprint 1 family; 0 target failures; E2E-02-02, E2E-02-03, sheet at 320/360 px passed | EM dry-run (G02-05 report) | yes (dry-run) |
| G02-11 | 0 | `open_defects.py` → rc=1, **open 3** after the round-2 EM rows (4 before) | EM, `48e1e71` + this commit | **no** |
| G02-12 | domain < 10 s; unit ≤ 60 s; IT < 10 min; 0 failed | domain rc=124 (budget exceeded, wall 9.5-10.4 s on a loaded host; pytest itself 7.8-8.5 s); unit 11.2 s; IT 227.9 s | QA dry-run | **no** |

QA's own live check at `e270c8d` (review round 2, QA-RV2-05) agrees: G02-01/02 5/5, tag_to_sheet p95 26 ms, corrections p95 33.7 ms (n=100); G02-04 p95 13.0 ms, p99 14.7 ms, 50.0 RPS. That run used bundled Chromium, so its G02-05 was `91 passed, 2 failed, 6 skipped` (the two H.264 tests), the gap ADR 0036 closes.

### 1.2 Open blocker and major findings (G02-11)

`python3 scripts/measure/open_defects.py docs/sprints/02/review-rounds.md` → rc=1, **open 3**:

| # | Finding (family) | Sev. | What is open | Who can close it |
|---|---|---|---|---|
| 1 | BE-D1-01 | major | Harness `_code()` error-code fix: the row was never re-dispositioned, although G02-01 now passes 5/5 live | principal-engineer (harness owner) writes the closing row |
| 2 | QA-R1-06 family (QA-RV2-01) | blocker | The SRE round-2 row ("Fixed on CI", run 37464553177 at `fd363fa`, **ci-gate green**) names only `QA-R1-06` and `QA-RV2-01`. The family's other ids (PE-R2-02, QA-R2-02, PE-R3-05, QA-R3-05, QA-R2V-01) still have "Not fixed" (line 275) as their latest row, so the counter keeps the family open (fail closed, as designed) | sre-devops-engineer adds one row naming every id of the family |
| 3 | PD-R1-06 / DR-01 / DR-02 family | blocker | Flows design reviews not held; the chair's routed cells (PD-RV2-DR-FE, -COACH, -BA, -PM, -SEC) are not yet filled | principal-designer with the named roles; DR-02 by end of 2026-10-07, DR-01 by 2026-11-02 |

**Counted elsewhere, not open:** QA-R3-GATE-01 / C-06 (manual screen-reader pass) is "Deferred" to the named row C-06 under ADR 0030, so the counter does not count it. It is still **not done**: 0 of 24 rows have been run, so NFR-027 (b) is unmet (§1.4).

**Counter gaps the EM found this round:** the principal-designer's routed table (PD-RV2-DR-*) has no Disposition column, so the counter does not read those routed rows. They ride on the open DR-01 / DR-02 family above. A closing row has to name every alias of its family (row 2). QA's round-2 findings QA-RV2-05 and QA-RV2-07 had no Open rows of their own (ADR 0033 rule 1). They are answered in the EM's round-2 rows.

### 1.3 G02-05 flake check (×3, Chrome for Testing)

`PW_CHROMIUM_CHANNEL=chrome … playwright test --repeat-each=3 --workers=1` → rc=0, `279 passed, 18 skipped` (the 6 named skips ×3), 20.5 min. `flaky_report.py --fail-on-flaky` over the single run and the repeat gives "2 runs, 99 tests, 0 flaky", rc=0. The stand-in seek flake from QA's earlier dry-run (QA-S2-UI-04) did not recur.

### 1.4 Not measurable by agents

- **C-06 / NFR-027 (b):** the VoiceOver and TalkBack pass needs a human (PO item P6, due 2026-11-13). If P6 has no answer by then, the EM carries C-06 into the Sprint 3 plan as a named row (ADR 0030 rule 1; review-rounds row of review round 1). Until it runs, nobody has heard the Sprint 2 announcements (T-01 live region, S-01 "Rally n corrected", the disclosure options), and the sprint DoD item for NFR-027 (b) stays open.
- **Scoring rules:** still PROVISIONAL-UNVERIFIED (ADR 0023, P7). The sheet says "unofficial scoring (rules not yet verified)". `@needs-verification` rows never count toward a Must FR.

## 2. Next step to a verdict

1. Owners close G02-11 rows 1-3 (above).
2. QA (G02-12 owner) runs the domain budget on an unloaded host, or proposes a method change through a decision-log row. The budget itself does not change.
3. The independent verifier runs §4 at one recorded head on its own Compose stack, with `PW_CHROMIUM_CHANNEL=chrome` for G02-05/06/10 (ADR 0036), and fills §2.
