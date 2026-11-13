# ML-6 decisions

Per-ticket decision file (working-agreement §3). Ticket: ML-6, "Pattern-source matrix (QT / FT / CV) with the §7.1 evidence each CV pattern needs" (`docs/sprints/sprint-06.md` §3.2, wave 1 gates). Owner: senior-ml-cv-engineer, with the pickleball-domain-coach as reviewer of the matrix. Review tier 0 (ADR 0056). Covers SPK-1.1; feeds ST-176a, ST-176b, ST-171b/c/d, BA-6.

**TDD does not apply:** the ticket writes a decision matrix (`docs/data/pattern-sources.md`); it adds no executable behaviour to drive with a failing test. The extractors (ST-171b/c/d) and the eval harness (ST-176a) write the red tests. Instead a doc check was run red before the file existed and green after (PR description, "Evidence"): a row for every pattern of catalogue §1 plus AN-01..AN-07, nine cells per row, a yes/no "measurable today" per row, §7.1 evidence on every CV-only row, every `SRC-nnnn` resolving to `docs/domain/sources.md`, and `scripts/ci/check_docs.py` on the changed files.

## 1. Decisions

| Date | Role | Decision | Evidence | Reason |
|---|---|---|---|---|
| 2026-11-13 | senior-ml-cv-engineer | **Demo slice = AN-01..AN-07 (QT), AN-09 and AN-13 (FT, P0), AN-08 (FT, stretch)**; no CV pattern | `docs/data/pattern-sources.md` §3; `backend/src/racket/worker/stages.py` (no vision stage) | Only QT and FT are measurable today; matches sprint-06 §3.3 P0/P2 order |
| 2026-11-13 | senior-ml-cv-engineer | **Court frame of `court_xy_m` confirmed** as catalogue §0.7 (side-A-relative per rally); a future homography maps into the same frame | matrix §4.1 | Answers catalogue §10 Q1 with no schema change; the end-switch mirroring risk goes to COACH-6b as a `not_in_play` share check |
| 2026-11-13 | senior-ml-cv-engineer | **Four CV evidence rows have no NFR-006 target** (E-SHOT, E-FOOT, E-POSE, E-PAT); proposed values are (judgment) and need an ADR 0060 amendment by the principal-engineer before any CV pattern story is Ready | matrix §2 | NFR-006 measures court-line reprojection (M4), not player foot points; stage metrics do not bound pattern error |
| 2026-11-13 | senior-ml-cv-engineer | **E-LBL-XY proposed**: labeller agreement on bounce positions p80 ≤ 60 cm before AN-08/AN-10 are shown as reliable on real matches | matrix §4.2; `docs/data/gold-label-schema.md` §3 ("a gate for them needs an ADR") | Bounce positions are typed by eye in the Full Tag UI |
| 2026-11-13 | senior-ml-cv-engineer | **No `hybrid` trajectory value** (catalogue §10 Q4) until a `trajectory` κ exists | matrix §4.3 | A new value resets the QD-TX-03 agreement evidence |
| 2026-11-13 | senior-ml-cv-engineer | **No new tag field proposed** (e.g. "stacked" per service turn) | matrix §0, §1 STACK row | It changes ADR 0035 and the label API (tier 2); not needed for the slice |

## 2. Not met: waiting on P-n

| Item | Waiting on | What the team prepares |
|---|---|---|
| Every §2 CV evidence row measured | P11 / OQ-06 footage with rights or consent | ST-176a harness dry-run, ST-176b spike plans, this matrix, `docs/data/gold-capture-protocol.md` |

## 3. Cost per PR (ADR 0056 decision 1)

| Round | wall_time_min | total_cost_usd |
|---|---|---|
| Author build | not measured | not measured (the session does not expose per-ticket wall time or cost to the agent) |
