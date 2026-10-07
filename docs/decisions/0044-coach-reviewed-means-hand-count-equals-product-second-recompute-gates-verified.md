# 0044. `coach-reviewed` means the coach's hand count equals the product; the second recompute and the κ check gate `verified`

- **Status:** Accepted (pickleball-domain-coach, 2026-10-07, Sprint 3 review round 1, COACH-1)
- **Date:** 2026-10-07
- **Deciders:** pickleball-domain-coach (metric owner; sprint-03 §0.4 row "Second reviewer" gives this decision to the coach)
- **Consulted:** senior-qa-engineer (GS-AN-1, oracle), senior-backend-engineer (PE-R1S3-05), product-manager and business-analyst (AN-02 label, FR-100/FR-101 wording; informed through the routed rows)
- **Related:** COACH-1; QD-AN-03 (`docs/requirements/brainstorm-quality-domain.md:136`); OQ-20 / P9; FR-100, FR-101, FR-102; NFR-004; ADR 0005, ADR 0041; metric-dictionary D-1, D-2; flows-sprint-02 R2-7 (E-2); flows-sprint-03 P-4, P-5; review rows PD-RV2-DR-COACH, COACH-1, PE-R1S3-05

## Context and problem statement

FR-102 shows users only `coach-reviewed` or `verified` metric entries. Every entry of the metric dictionary was `draft`, so the stats screen had nothing to show and the Sprint 3 goal could not be demonstrated. QD-AN-03 says: "Before a metric's status becomes `coach-reviewed`, the coach hand-computes it on 3 golden matches. The system must match exactly. A second coach or experienced player recomputes 1 match, and any disagreement in the *definition* (not arithmetic) means the definition text is revised." No second coach exists yet (OQ-20, a PO recruitment action, P9, date 2026-11-16). Three questions follow: (1) does `coach-reviewed` need the second recompute; (2) what "the system must match exactly" is compared against when the QA reference (`scripts/measure/statslib.py`) disagrees with the product; (3) whether D-2 (forced vs unforced reliability) blocks AN-04 and AN-07.

## Decision drivers

- A shown number must equal what a coach counts by hand (NFR-004, QD-AN-03).
- Users must not see a stronger claim than we have: no metric is `verified` without an independent second reader (QD-AN-03, OQ-20).
- A status must not be held hostage by a defect in a test oracle that the dictionary already contradicts.
- Data captured now cannot be split later; a merge later is cheap (a version bump).

## Considered options

1. **`coach-reviewed` = the coach's own hand count on the 3 golden matches equals the product on every compared field; the second recompute (OQ-20) and the D-2 κ check are the step to `verified`** (chosen).
   - Good: the protocol's arithmetic check runs now and is exact; the second reader still happens before any "verified" claim; the goal can be shown.
   - Bad: until P9 lands, the definitions rest on one coach's judgment. Mitigated: each card says "checked by our coach" with the definition version (flows-sprint-03 §2), never "verified", and every definition stays "(judgment)".
2. **`coach-reviewed` needs the second recompute too.**
   - Good: the strictest reading of QD-AN-03.
   - Bad: nothing can be shown before 2026-11-16 at the earliest; the Sprint 3 goal fails on a recruitment item, not on product quality; `verified` would then mean nothing more than `coach-reviewed`.
3. **Option 1, but an entry also needs `statslib.py` to agree on every field.**
   - Good: three-way agreement.
   - Bad: AN-07 would stay hidden because the oracle has a known defect (n-only flag, PE-R1S3-05) that contradicts dictionary rule 0.3, while the product and the hand count agree. The oracle is a test aid, not the definition.

## Decision outcome

Option 1, with these rules:

1. **`coach-reviewed`:** the coach hand-counts the entry on the golden matches (GS-AN-1) from the dictionary text alone, and the product equals that count on every compared field for both sides of every match. The record is `docs/domain/hand-counts/GS-AN-1-v1.json`, with a dated review-record row per entry in metric-dictionary §3.
2. **A reference that disagrees with both the dictionary and the product is a reference defect.** It goes to QA as a TCR row; it does not keep the entry at `draft`. If QA's decision on that TCR reads the dictionary differently from the coach, the entry returns to `draft` until the definition text is clarified (with a version bump if the meaning changes).
3. **`verified`** needs, in addition: (a) the second coach or a 4.0+ player recomputes 1 golden match and agrees on the definitions (QD-AN-03, OQ-20); (b) for AN-04 and AN-07, two labellers reach Cohen's κ ≥ 0.6 on 200 rallies for forced vs unforced (QD X3, D-2); (c) for rule-dependent entries (AN-01, AN-02, AN-03, AN-05, AN-06 as read from the score), the rules they read are verified (rules-verified.md §5).
4. **D-2: forced and unforced errors stay separate in v0.1**, in the Quick Tag buttons (flows-sprint-02 R2-7) and as AN-07 rows (flows-sprint-03 P-5). If 3(b) fails, v0.2 merges them into "errors" with a version bump; the tags already captured still hold both labels, so the merge loses nothing. The other order (merge now, split later) cannot recover the split.
5. **D-1: AN-02's UI name is "Rallies won when receiving"** (option a). "Side-out %" misnames it under side-out doubles scoring: winning a receiving rally against server 1 is not a side-out (SOD-03, provisional). The formula is unchanged, so no version bump. FR-100/FR-101 still say "side-out %"; the wording change is the business-analyst's (routed).

### Consequences

- Good: AN-01..AN-07 move to `coach-reviewed` on the evidence below; ST-048 can show them; G03-08 (e) has its dated rows.
- Bad: the two GS-AN-1 v1 frozen AN-07 `low_sample` values (gm1 A, gm2 A) disagree with the hand count until QA lands TCR PE-R1S3-05, so `test_golden_an_frozen_values_are_the_coachs_hand_count` stays red on those two cells only. This is the intended signal, not a test to weaken.
- Neutral: no definition text or formula changes, so the dictionary stays v0.1 and `metrics.lock.json` digests are unaffected; only `status` changes, which the BE lane mirrors into `metrics.json`.

## Evidence

- Hand count, written from the dictionary without importing the product or the oracle: `python3 docs/domain/tools/hand_count_gs_an1.py --write` (2026-10-07) → trace per rally and `wrote docs/domain/hand-counts/GS-AN-1-v1.json`.
- Product vs hand count: running the product path of `test_golden_an.py` (`product_stats`) on each script and comparing every field of the hand count (including `rallies`) and AN-06 `longest_by_game` → `product vs hand count differences: 0`.
- Hand count vs frozen GS-AN-1 v1 (the oracle's values): exactly 2 differences, `gm1-two-games AN-07 A low_sample hand True frozen False` and `gm2-three-games AN-07 A low_sample hand True frozen False`. Rule 0.3 applied to each AN-07 share: gm1 A n = 21, `wilson(6, 21)` width 0.3614 > 0.30; the same cells as PE-R1S3-05 (review-rounds, senior-backend-engineer).
- `cd backend && env -u APP_ENV uv run pytest -q tests/regression/test_golden_an.py` → `4 failed, 27 passed`: the two `product_equals_the_frozen_values[...AN-07]` cases (already red since `fee4fa3`) and the hand-count cases for gm1 and gm2, each on that one field; `[gm3-corrections-needs-decision]` passes.
