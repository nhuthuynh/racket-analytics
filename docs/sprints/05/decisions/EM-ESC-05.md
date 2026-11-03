# EM-ESC-05 decisions

This is the per-ticket decision file (working-agreement §3, "Daily sync").

- **Ticket:** EM-ESC-05, "One PO escalation note: P6-P20, setting 6, the S5 'Done when' change, audit items 12-15, drill JSON in size — each with options, default, deadline" (`docs/sprints/sprint-05.md` §3).
- **Owner:** engineering-manager.
- **Review tier:** 0 (ADR 0056). One fresh-context reviewer plus the automated doc checks.
- **Depends on:** PM-5 (#194, merged).
- **Output:** `docs/sprints/05/po-escalations.md`.

**TDD does not apply.** The ticket writes an escalation note and no executable behaviour, so there is no failing test to write first. Doc checks run instead (PR description, "Test evidence").

## 1. Decisions

| Date | Role | Decision | Evidence | Reason |
|---|---|---|---|---|
| 2026-11-03 | engineering-manager | **One note with a summary table first and an answer id per item** (D1, E1-E3, SZ, S6, A12-A15, P6-P20), so the PO can reply in one line per item | kickoff PM-6, COACH-4; sprint-05 §10 RM-12 | Holiday availability: the cheapest answer path gets the most answers (judgment) |
| 2026-11-03 | engineering-manager | **A default is only what the team does with no answer.** No default changes a milestone "Done when", accepts a risk, waives a review or spends money. In particular, E1's default leaves roadmap §5 unedited, and D1's default is "not held", not a waiver | working-agreement §8; ADR 0047; PD-DR04 §14.5 | Only the PO can make those decisions |
| 2026-11-03 | engineering-manager | **PD-DR04's waiver request is carried unchanged from PR #200 (not yet merged)** as item D1 with deadline 2026-11-05 | `git diff origin/main...origin/s05/pd-dr04-collect-the-five-dr-04-decider-cells-on- -- docs/design/flows-sprint-04.md` → §14.5 | The chair asked the EM to carry it, and does not write this file |
| 2026-11-03 | engineering-manager | **The PM-5 PO questions (Product Goal wording, FR-162) are included** as E2 and E3 | `docs/sprints/05/decisions/PM-5.md` §5 routes them to EM-ESC-05 | One list (kickoff PM-6) |
| 2026-11-03 | engineering-manager | **Drill size data:** 34 drill files, 1429 lines in total (≈ 41 per drill), so the 400-line limit allows about 9 drills per PR | `find content/drills -name '*.json' -exec cat {} + \| wc -l` → 1429; `ls content/drills \| wc -l` → 35 (34 drills + `library.lock`) | Gives the PO a number for item SZ |
| 2026-11-03 | engineering-manager | **P10 fact checked against the source**, not the record: the repository is public | `gh api repos/nhuthuynh/racket-analytics --jq '{private,visibility}'` → `{"private":false,"visibility":"public"}` | Retro-02 L5 |
| 2026-11-03 | engineering-manager | **COACH-5 has not yet drafted its P7/P15 fallback request** (no branch on origin). The EM wrote P7 and P15 from sprint-05 §0.4 and the Sprint 4 report. COACH-5 can add a ledger row if its fallback wording differs | `git ls-remote --heads origin \| grep -i coach-5` → nothing | The send-by date of 2026-11-05 does not wait for COACH-5 |

## 2. Cost per PR (ADR 0056 decision 1)

| Round | wall_time_min | total_cost_usd / tokens |
|---|---|---|
| Author build | not measured | not measured |
