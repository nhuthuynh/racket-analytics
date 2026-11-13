# COACH-6a decisions

Per-ticket decision file (working-agreement §3). Ticket: COACH-6a, "Pattern catalogue v0.1 and sources register" (`docs/sprints/sprint-06.md` §3.2, wave 1 gates). Owner: pickleball-domain-coach. Review tier 0 (ADR 0056). Covers FR-171.R2-R7, A2, A6.

**TDD does not apply:** the ticket writes definitions and a citation register (`docs/domain/pattern-catalogue.md`, `docs/domain/sources.md`); there is no executable behaviour in the product to drive with a failing test. The extractors (ST-171b/c/d), the gold fixture with `pattern_example.py --check` (COACH-6b) and the golden test (QA-REF-GOLD) write the red tests against these definitions. Instead, a doc check was run red before the files existed and green after (PR description, "Evidence"): structure per pattern, a happy and a negative Example per rule, every `SRC-nnnn` cited resolves to a register row, every worked label document passes `validate_labels` (`backend/src/racket/dataset/labels.py`) and gives the stated counts, and every Wilson figure equals `wilson(k, n)` (`backend/src/racket/analytics/uncertainty.py`).

## 1. Decisions

| Date | Role | Decision | Evidence | Reason |
|---|---|---|---|---|
| 2026-11-13 | pickleball-domain-coach | **AN-13 keeps the error-ended median** (FR-171.R4) with n_censored always shown; a Kaplan-Meier median is the v0.2 candidate if the censored share is above one half | catalogue §5 "Why the error-ended sample"; PE-PLAN06-03 (`docs/sprints/06/review-rounds.md`) | The ticket allowed either a justification or a switch; the error-ended statistic is hand-countable on GS-PAT-1 and like-for-like with the reference (judgment) |
| 2026-11-13 | pickleball-domain-coach | **AN-13 min_n = 10** (FR-171.R4 requires ≥ 6) | n = 6 gives l = 1, the interval [x(1), x(6)] (the whole range); n = 10 gives l = 2 (doc check) | A whole-range interval can never be wholly on one side of a band, so ranking at n = 6 is empty in practice (judgment) |
| 2026-11-13 | pickleball-domain-coach | **AN-09 `better_direction` = `inside_band`**; AN-10, AN-08, AN-11, AN-13 `higher`; AN-12, AN-16 `lower`; stacking none (descriptive) | catalogue §1 | FR-172.R1 examples already treat AN-09 as two-sided; always dropping and never dropping are both gaps (judgment) |
| 2026-11-13 | pickleball-domain-coach | **Level bands** = the plan model's `beginner`, `intermediate`, `advanced` plus `pro` as direction only; band values live in the reference set (COACH-6c), not here | catalogue §0.6; `backend/src/racket/coaching/plan/domain/model.py` `LEVELS` | A2; the profile stores the word, not a rating, so no numeric band can be matched today |
| 2026-11-13 | pickleball-domain-coach | **No reference value may be `published` yet**: no `statistic` row of the register is `resolved` | `docs/domain/sources.md` §3; egress probe in its SRC-0008 row | FR-170.R1, P22 (a) default; external coaching sources are blocked or unread |
| 2026-11-13 | pickleball-domain-coach | **AN-08 follows FR-171.R7 (d ≥ 4.47 m)**, not QD's NVZ-to-baseline third (d ≥ 5.18 m); the BA decides before ST-171d | catalogue §4 "open", §10 Q2 | The FR rule is the newer binding text; the coach's preference for QD's deeper line is judgment |
| 2026-11-13 | pickleball-domain-coach | **Court frame convention proposed** for `court_xy_m` (origin at side A's left baseline corner, y towards B); ML confirms | catalogue §0.7, §10 Q1; labels v1 (`docs/data/gold-label-schema.md` §4) does not pin the axes | AN-08 and AN-10 cannot be counted without it |
| 2026-11-13 | pickleball-domain-coach | **AN-11, AN-12, stacking and AN-16 partner spacing are CV patterns, "needs CV (7.1)"**, tier 2 with the security-privacy-engineer when built (player tracks are personal data) | catalogue §6-§9; roadmap §7.1; NFR-006 | Labels v1 have no player positions (`position` is derived, never labelled) |
| 2026-11-13 | pickleball-domain-coach | **BA co-authoring:** the BA's FR-171 Examples are reused verbatim and marked "BA example"; the BA is asked to review the rest on the PR | catalogue header | The BA cannot be co-author inside this session; agreement is cited, never inferred (rule BA5-PE-01) |

## 2. Cost per PR (ADR 0056 decision 1)

| Round | wall_time_min | total_cost_usd |
|---|---|---|
| Author build | not measured | not measured (the session does not expose per-ticket wall time or cost to the agent) |
