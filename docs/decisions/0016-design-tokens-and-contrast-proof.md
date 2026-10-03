# 0016. Design tokens are a JSON source of truth with an executable contrast proof

- **Status:** Proposed. The design review happens at the ST-010 PR.
- **Date:** 2026-10-03
- **Deciders:** principal-designer
- **Consulted:** senior-frontend-engineer (consumer, ST-010), senior-qa-engineer (gate), sre-devops-engineer (CI job)
- **Related:** ST-010, ST-013..ST-019; NFR-027, NFR-028, NFR-029, NFR-031, NFR-034; `docs/design/tokens.json`, `docs/design/tokens.md`, `docs/design/tools/contrast_check.py`

## Context and problem statement

- NFR-029 requires text contrast ≥ 4.5:1 and UI-component contrast ≥ 3:1, checked by a "design-token check". The thresholds come from [DPA/DESIGN-03] and [DPA/DESIGN-04].
- ST-010 builds the PWA shell in Sprint 0 and needs tokens now.
- axe-core (NFR-027) checks rendered pages, but only the combinations a test happens to render. Focus rings, hover states, banners and text over video are often missed (judgment).
- We must decide how tokens are expressed and how their contrast is proven.

## Decision drivers

- Contrast thresholds 4.5:1 for text and 3:1 for non-text [DPA/DESIGN-03, DPA/DESIGN-04].
- Evidence over assertion: "it works" is not evidence (definition-of-done).
- One source for designers and the front end, so values cannot drift (judgment).
- The designer's lane is `docs/` only. The tool must not need product code.

## Considered options

1. **Tokens in JSON plus a standard-library contrast checker that fails on any declared pair below its minimum.** The generated table is embedded in `tokens.md`.
2. **Tokens in CSS only.** The contrast is checked by axe-core on rendered pages.
3. **Tokens in a design tool,** with contrast checked by eye or by a plugin.

## Decision outcome

Chosen option: **Option 1**, with axe-core kept as a second, rendered-page check.

- Every foreground/background combination the design allows is declared as a `contrastPairs` row.
- A combination that is not declared is not allowed (tokens.md §3 rule 1).
- Semi-transparent colours are composited over a declared worst case: a pure white video frame for the scrim.
- A token below 4.5:1 is never used for informative text, including "disabled" options that carry information (tokens.md §3 rule 4).

## Pros and cons of the options

### Option 1: JSON plus an executable proof
- Good: every allowed pair is proven, including states axe rarely renders (focus halo, banners, scrim).
- Good: re-runnable by anyone with `python3`, with no dependencies.
- Good: the first run caught a real defect (below).
- Bad: proves only the declared pairs. Rendered combinations are still checked by axe (NFR-027).

### Option 2: CSS plus axe only
- Good: no extra tooling.
- Bad: covers only what the tests render, and the evidence is scattered across CI runs.

### Option 3: a design tool
- Bad: no reviewable evidence in the repo. It also contradicts "design docs live in the repo and are reviewed as PRs" [DPA/DESIGN-15].

## Evidence

| Claim | Evidence | Type |
|---|---|---|
| Thresholds 4.5:1 text, 3:1 large text, 3:1 non-text | [DPA/DESIGN-03], [DPA/DESIGN-04] | verified source |
| The checker computes WCAG ratios correctly | Fixtures, 2026-10-03: `#777777` on white → 4.48:1 FAIL, exit 1; `#767676` on white → 4.54:1 PASS; black on white → 21.00:1; empty pair list → exit 1; unknown token → exit 2 | test result |
| The first run caught a real defect | `python3 docs/design/tools/contrast_check.py` → `FAIL light Focus ring vs primary fill: 1.07:1 < 3.0:1`, `53/54 pairs pass`, exit 1 | test result |
| Fixed by geometry, not colour | The ring has a 2 px offset and a `focus-inner` halo fills the gap, so the ring touches only the halo (7.00:1 light, 8.78:1 dark) and the page. The halo vs the primary fill is 6.51:1 (light) and 8.13:1 (dark) | test result |
| Current tokens pass | `python3 docs/design/tools/contrast_check.py --markdown` → `55/55 pairs pass`, exit 0 (table in tokens.md §2) | test result |
| White text on a 65% scrim over a white frame reaches 7.00:1 | same run | test result |
| Darker reference frames (shaded, indoor) cannot be worse than a white frame for white-on-scrim text | (judgment); a manual check on 3 reference frames remains per NFR-029 | judgment |

## Consequences

- The FE maps `tokens.json` to CSS custom properties. Colours are not hard-coded in components.
- Suggested follow-up for the sre-devops-engineer: add the checker as a CI docs job, so a token change cannot merge red. The designer does not edit CI.
- Chart, heatmap and court-overlay colours are out of v0.1. They need their own ramp and proof before the dashboard work (Sprint 3) and R2.

## Confirmation

- ST-010's PR shows axe with 0 serious or critical violations, and a Vitest snapshot shows the generated CSS variables equal the JSON values.
- The checker exits 0 on `main`.
