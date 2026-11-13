# BA-6 decisions

Per-ticket decision file (working-agreement §3). Ticket: BA-6, "Register rows FR-170..FR-174 with verbatim source; traceability rows; glossary terms in ddd-guidelines; DoR verdicts with PR numbers" (`docs/sprints/sprint-06.md` §3.2). Owner: business-analyst. Review tier 0 (ADR 0056). Wave 1 gate: every wave 2 story waits on its DoR verdict here.

**TDD does not apply:** the ticket changes requirement text, glossary entries, one DoR checklist line and traceability rows. There is no executable behaviour to drive with a failing test. The doc checks run instead: `scripts/ci/check_docs.py` (paths exist, `[ASB/<ID>]` citations resolve, agent front matter parses) and `scripts/ci/check_atomic_breakdown.py` (PRC-7.1). The PR description lists the commands and results.

## 1. Decisions

| Date | Role | Decision | Evidence | Reason |
|---|---|---|---|---|
| 2026-11-13 | business-analyst | **FR-170..FR-174 go into a new §L of `functional-requirements.md`**, after §K, with the PO quote of 2026-11-12 copied character for character as the Source of every row | `diff <(sed -n 151p docs/requirements/po-input-2026-10-05.md) <(grep -m1 '^  > resume' docs/requirements/functional-requirements.md \| sed 's/^  //')` → no output | Kickoff BA-1: new scope gets new rows, FR-107 and FR-108 are not stretched. A new section keeps the baseline §A-§K untouched apart from the counts |
| 2026-11-13 | business-analyst | **Priority is a BA default** (Must for FR-170..FR-173, Should for FR-174) from the sprint-06 §3.3 P0/P1 order, to be confirmed by the product-manager in PM-6 (#245) | sprint-06 §3.3 Prio column | Priority is PM-assigned (DoR "Value and scope"); the BA states the default rather than leave the field empty [ASB/REQ-07] |
| 2026-11-13 | business-analyst | **Release "post-R1 (Sprint 6)"**, not R2 | `functional-requirements.md` §0.3; P21 open in EM-ESC-06 (#243) | Writing R2 would assume the answer to P21 (Go port first or the slice first). Agent text is not PO text (retro 3 M7) |
| 2026-11-13 | business-analyst | **Counts recomputed:** 88 FRs, Must 46, Should 29, Could 10, Won't 3; new epic E17 with 5 FRs | `grep -c '^#### FR-' docs/requirements/functional-requirements.md` → 88; `grep -oE '^- \*\*Priority:\*\* (Must\|Should\|Could\|Won)' … \| sort \| uniq -c` → 46/29/10/3 | The traceability header says "do not hand-edit the counts": both files are updated from the same grep |
| 2026-11-13 | business-analyst | **E17 is a BA addition** (as E16 was) | PROD §5 has no video-analysis-vs-reference epic | The five FRs belong to no existing product epic; E10 (full analytics) is R3 and vision-based |
| 2026-11-13 | business-analyst | **Glossary:** Reference pattern, Reference set, Pattern measure, Reference gap, Exercise (= drill assignment, A1), Footage source (with "provenance record") added to `ddd-guidelines.md` §6. Contexts follow sprint-06 §3.7 and are marked "owner per PE-6a / PE-6b" | kickoff BA-2, SEC-2 | DoR "Terms are taken from the glossary"; "Reference gap" states how it differs from the ADR 0003 point leak so the two rankings are not confused (A4) |
| 2026-11-13 | business-analyst | **DoR line for footage provenance** added under "Design", next to the threat-notes line, covering fixtures too; a story without footage says "team-made or synthetic fixtures only" | kickoff SEC-2 ("the DoR line is added by BA-6") | Footage rights and consent are a precondition, not a test result; putting it in the DoR stops a story using unlicensed or unconsented video from being pulled |
| 2026-11-13 | business-analyst | **DoR verdicts at `91a58c78`:** PRC-06 Ready; ST-170..ST-176 and SEC-R Not Ready (gates and E1 named per row in breakdown §7) | `gh api 'repos/nhuthuynh/racket-analytics/pulls?state=all&per_page=60'` at 2026-11-13 03:41Z: no PR for PE-6a, PE-6b, COACH-6a/b/c, SEC-6, PD-6, DR-06, ML-6, CI-TIERS-06, CI-DOC-CHECK-06; #242, #243, #244, #245 open; 13 Sprint 5 PRs open | Rule BA-1: no "Ready on condition". A gate ticket adds its PR number to §7 when it merges, the way BA-5 rows were updated in Sprint 5 |
| 2026-11-13 | business-analyst | **Three Amigos are recorded as questions with the place each answer lands** (breakdown §8), not as agreed answers | rule BA5-PE-01 (Sprint 5): agreement is cited, never inferred | The coach, ML and QA answers come in COACH-6a/6b/6c, ML-6 and their reviews; the BA cannot write their agreement for them |
| 2026-11-13 | business-analyst | **Traceability §21** links each atomic item to story, ticket, feature file, test file, scorecard row and DoR verdict; files that do not exist yet are marked "(planned)" | `python3 scripts/ci/check_docs.py --base origin/main --head HEAD` → 0 problems | DoD "Traceability updated"; each ticket PR replaces its own "(planned)" marker |

## 2. Cost per PR (ADR 0056 decision 1)

| Round | wall_time_min | total_cost_usd |
|---|---|---|
| Author build | not measured | not measured (the session does not expose per-ticket wall time or cost to the agent) |
