# COACH-6b decisions

Per-ticket decision file (working-agreement §3). Ticket: COACH-6b, "Gold fixture GS-PAT-1 and `docs/domain/tools/pattern_example.py --check`" (`docs/sprints/sprint-06.md` §3.2). Story ST-171 (player pattern measures). Owner: pickleball-domain-coach. Review tier 1 as planned (ADR 0056: an executable file under `docs/`); `scripts/ci/review_tiers.py` computes tier 2 because no tier rule names `docs/domain/hand-counts/` yet, so the path fails closed (see §1). Covers FR-171.R2-R4 (AN-09, AN-13) and FR-171.R7 (AN-08, labelled in the fixture).

**How TDD applies.** The coach writes only under `docs/`, so the executable test of this ticket is the doc tool itself: `pattern_example.py --check` was written first and seen failing for the right reason (no fixture, no tables), then the fixture and the catalogue tables were added. The product tests (unit, property, `tests/features/pattern_measure.feature` (planned), golden) belong to ST-171b/c/d and QA-REF-GOLD, which read this fixture. The scenarios the check enforces, in Gherkin:

```gherkin
Feature: Pattern catalogue check on gold fixture GS-PAT-1 (COACH-6b; FR-171.R2-R4, R7)

  Scenario: The check fails while the gold fixture and its tables are missing
    Given the pattern catalogue v0.1 has no "GS-PAT-1" table
    And docs/domain/hand-counts/GS-PAT-1-v1.json does not exist
    When the coach runs "python3 docs/domain/tools/pattern_example.py --check"
    Then it exits with code 1
    And it names the missing fixture and each missing table: AN-09, AN-13, AN-08, unassigned

  Scenario: The coach's hand count equals the replay of the catalogue definitions
    Given GS-PAT-1-v1.json holds a team-made Full Tag label document per match
    And for each side a hand count of AN-09, AN-13 and AN-08 with the rally ids of every bucket
    When the coach runs the check
    Then the replay gives the same rally ids in every bucket, every exclusion reason and every sample
    And every catalogue GS-PAT-1 table row equals the printed row
    And the check prints "pattern-check: 0 difference(s)" and exits with code 0

  Scenario: A worked example that disagrees with its definition is caught
    Given the worked label example W-13-a expects side A runs [2]
    When the replay of §5 gives anything else
    Then the check prints one DIFF line naming W-13-a, the key and both values, and exits with code 1
```

## 1. Decisions

| Date | Role | Decision | Evidence | Reason |
|---|---|---|---|---|
| 2026-11-13 | pickleball-domain-coach | **The check is a replay written from the catalogue text**, standard library only; it imports neither `racket.analytics` nor `scripts/measure/` | `docs/domain/tools/pattern_example.py` docstring | ADR 0044: coach-reviewed needs hand count = product, so the coach's replay must not share code with the product |
| 2026-11-13 | pickleball-domain-coach | **The fixture holds the label documents, a rally sheet and the hand count in one file** (`labels`, `sheet`, `counts` per match); counts list the rally ids of every bucket, not only totals | `docs/domain/hand-counts/GS-PAT-1-v1.json` | QA recounts one match by hand from the sheet and the ids; the extractors (ST-171b/c/d) and QA-REF-GOLD read the same `labels` |
| 2026-11-13 | pickleball-domain-coach | **Two matches:** `gp1-doubles` (48 rallies; AN-09 side A, AN-13 both sides and AN-08 side B reach min_n, the rest stay `low_sample`) and `gp2-singles` (12 rallies; every exclusion reason in a few rallies, the QA recount target) | catalogue §11 tables | One match exercises rankable and low-sample states; the small one is quick to recount by hand |
| 2026-11-13 | pickleball-domain-coach | **The catalogue statuses stay `draft`.** An entry becomes `coach-reviewed` only when the product equals this hand count (ADR 0044); the extractors do not exist yet | catalogue header; ADR 0044 | The hand count alone is half of the ADR 0044 condition |
| 2026-11-13 | pickleball-domain-coach | **Tier 2 computed, tier 1 planned:** the fixture path `docs/domain/hand-counts/GS-PAT-1-v1.json` matches no rule of `scripts/ci/review_tiers.py`, so the PR is tier 2 (fail closed); the coach cannot edit `scripts/ci/`. Asked of the sre-devops-engineer: add `docs/domain/hand-counts/**` to tier 1 (the GS-AN-1 record lives there too). Until then the merge step applies tier 2 | `python3 scripts/ci/review_tiers.py --base origin/main --head HEAD` → `review-tier: 2` | The tier is computed, never declared (ADR 0056); fail closed is the safe reading |
| 2026-11-13 | pickleball-domain-coach | **Serve depth (AN-08S) is not in the GS-PAT-1 tables**; it stays checked on W-08-a only | §10 Q2 (no AN id) | Serve depth is defined, not built, in Sprint 6 |

## 2. Findings for COACH-6c and §10 Q5

- **The Q5 trigger "censored share above one half" is met by construction.** Every error-ended dink rally is a sample for the side that erred and a censored rally for the other side. With both sides erring about as often, each side's censored share is about one half before any rally is won by a speed-up. On `gp1-doubles` the censored share is 13 / 25 for side A and 15 / 25 for side B. The trigger should be stated on the rallies the side ended itself (its own errors plus its own winning speed-ups), not on all its dink rallies. This is a question for COACH-6c and the senior-ml-cv-engineer; v0.1 is not changed here (judgment).
- `GS-PAT-1` is team-made: no video, no real people (clip names are placeholders). Its counts are not reference values and never feed a band (COACH-6c owns the reference set).

## 3. Red evidence

`python3 docs/domain/tools/pattern_example.py --check` before the fixture and the tables existed (commit "red first"):

```text
pattern-examples: 25 compared, 0 difference(s)
pattern-figures: 12 compared, 0 difference(s)
DIFF MISSING fixture docs/domain/hand-counts/GS-PAT-1-v1.json
pattern-fixture: 1 compared, 1 difference(s)
DIFF MISSING table GS-PAT-1 AN-09
DIFF MISSING table GS-PAT-1 AN-13
DIFF MISSING table GS-PAT-1 AN-08
DIFF MISSING table GS-PAT-1 unassigned
pattern-tables: 4 compared, 4 difference(s)
pattern-check: 5 difference(s)
```

Exit code 1. The four COACH-6a worked examples (25 expected fields) and all 12 stated Wilson and median figures already agree with the replay.
