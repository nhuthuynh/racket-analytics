# Sprint 6 flows: reference browser (V), weakness view (W), exercise Why (E), consent and provenance (C)

- **Status:** draft v0.1, 2026-11-13 (principal-designer, gate ticket PD-6, review tier 0, ADR 0056). **Written before any Sprint 6 UI was built**: on `origin/main` `dc2aeed8` there is no reference or weakness route under `web/src/app` (`ls web/src/app` → `auth error.tsx globals.css guide label layout.tsx manifest.ts matches not-found.tsx page.tsx plan settings signed-out tokens.css welcome`). Design review **DR-06 is opened in §7 and is not yet held**. ST-170c, ST-172c and ST-173d depend on DR-06 (kickoff FE-4); until §7 records "held", this file is a proposal.
- **Stories:** ST-170c reference browser (family V); ST-172c weakness view (W); ST-173d plan Why with the reference (E); ST-175a footage provenance, whose player-facing words are family C. C-10 (provenance component) is used by V, W and E.
- **Requirements:** FR-170.R5, FR-172.R5, FR-173.R1, FR-173.R2, FR-173.R4, FR-174.R1-R2; NFR-027.10-.14; NFR-028, NFR-034, NFR-039, NFR-058. Atomic rules: `docs/sprints/06/requirements-breakdown.md` §1-§2.
- **Inputs (merged):** pattern catalogue v0.1 and sources register (COACH-6a, #250: [`pattern-catalogue.md`](../domain/pattern-catalogue.md), [`sources.md`](../domain/sources.md)); ADR 0061 (PE-6a, #248: [`0061`](../decisions/0061-reference-patterns-and-player-vs-reference-comparison.md)); threat notes (SEC-6, #249: [`threat-notes-sprint-06.md`](../security/threat-notes-sprint-06.md)). Pattern names come from the catalogue's "Name (UI)" column and reach the web from the API; the web holds no pattern copy of its own (one source, as FR-102).
- **Not merged on 2026-11-13:** the ST-170b and ST-172b contracts. Field names below (`provenance_label`, `state`, `reference.version`) are **placeholders**; the contract tests of ST-170b and ST-172b win and §5 gets a row.
- **Design sources:** HAX [DPA/DESIGN-11]; targets [DPA/DESIGN-02, DPA/DESIGN-10]; contrast [DPA/DESIGN-03, DPA/DESIGN-04]; focus not obscured [DPA/DESIGN-07]; error summary [DPA/DESIGN-13]; design review with the coach as SME [DPA/DESIGN-15]. Everything else is (judgment).
- **Builds on:** [`flows-sprint-03.md`](flows-sprint-03.md) §0 (numbers in text, "range a% to b%", low sample in words, E-01 "Show me" panel, `role="alert"` errors) and [`flows-sprint-04.md`](flows-sprint-04.md) §2 (P-01 plan page, drill row "Why", human-coach notice). Tokens: [`tokens.md`](tokens.md), proven pairs only, **no new colour**. Components: [`component-accessibility-checklist.md`](component-accessibility-checklist.md).
- **Size rule:** each family section stays ≤ 400 lines (sprint-06 §3.2). Viewport 360 CSS px, one hand (judgment); reflow to 320 px with no sideways page scroll (NFR-034).

## 0. Conventions (in addition to flows-sprint-03 §0 and flows-sprint-04 §0)

- **Screen ids.** V-01 (video player) and E-01/E-02 (evidence) are taken, so the new ids start at 10, as A-10 did in Sprint 4 (decision PD-6 row 1).

| Id | Screen | Route | Story |
|---|---|---|---|
| V-10 | Reference patterns (list) | `/references` (planned) | ST-170c |
| V-11 | One pattern's reference (detail) | `/references/<pattern id>` (planned) | ST-170c |
| W-10 | Your patterns against the reference | `/weaknesses?match=<id>` (planned; path form per SEC-S6-TM-03) | ST-172c |
| E-10 | Plan drill row: Why with the reference (P-01 row) | `/plan` | ST-173d |
| E-11 | Drills for a gap "not in this plan" (section of W-10) | `/weaknesses` (planned) | ST-172c, ST-173d |
| E-12 | "The reference changed" notice (P-01 and W-10) | existing routes | ST-173d |
| C-10 | Provenance component (on V-10, V-11, W-10, E-10, E-11) | — | ST-170c, ST-172c, ST-173d |
| C-11 | Where reference values come from | `/references/about` (planned) | ST-170c |
| C-12 | Training-video consent notice (on F-01, Q-06, U-04) | existing routes | ST-175a |
| C-13 | "Analysis not started" notice (on M-02) | existing route | ST-175a |

- **States.** Every screen has one row for each of nine states: Empty, Loading, Error, Low-confidence, Low-sample, Not measured, Not enough data, No clear gap, No reference yet. "N/A" carries its reason. Offline follows flows-sprint-04 §0 (last cached copy with "You are offline. This is your <page> as of <time>.").
- **The four comparison states** (FR-171.R5, FR-172.R1-R3; ADR 0061 rule 3) are words, never colour (NFR-027.14):
  - **Not measured**: the match lacks the data source (`no_shot_facets`, `no_bounce_positions`, `needs_cv`). Never shown as 0.
  - **Not enough data**: n below the pattern's min_n (20; AN-13: 10). Printed as "Not enough data (7 of 20 third shots)". Never ranked.
  - **No clear gap**: the player's range overlaps the reference, touches it, or lies on the better side.
  - **No reference yet**: no `coach-reviewed` or `verified` entry for the player's level band and format, or the pattern has no supported interval method (ADR 0061 rule 3.1).
  - A **gap** (the ranked state) names its side: "Below the reference", "Above the reference", "Below the band", "Above the band".
- **Low-sample** is the flows-sprint-03 §0 tag "low sample" on a value whose n is below min_n. On W-10 a low-sample measure **is** the "Not enough data" state (FR-172.R2); on V-10/V-11 it marks a published reference whose n is small.
- **Low-confidence** is N/A in Sprint 6: every value comes from Quick Tag or Full Tag labels, no automatic call (no vision model in the product, roadmap §7.1, NFR-006). **Rule for later:** a CV-derived measure shows "Estimated from video. It may be wrong." with the model's measured accuracy, and is never ranked until its §7.1 gate is met.
- **Numbers in text:** "20%", "range 11% to 33%", "n = 25 third shots". AN-13: "median 5 dinks, range 3 to 8, n = 10 rallies" plus "4 dink rallies ended another way (not counted)" (n_censored, catalogue §5).
- **Notices before the first number, once per page:** the unofficial notice (flows-sprint-03 §0) while `unofficial: true`, then the **reference notice** while any shown reference is `judgment`: "These reference values are a coach's judgment, not measured from pro matches." (FR-170.R5; PM-3 "name the pro reference honestly").
- **Flag:** with `FEATURE_REFERENCE_PATTERNS` off, V-10, V-11, W-10 and C-11 do not exist (app not-found page), no link to them is shown, and P-01 is exactly today's plan (ADR 0061 rule 4). C-12 and C-13 follow ST-175a, not this flag.
- **Targets:** every control ≥ 24×24 CSS px (SC 2.5.8; NFR-027.13); "Show me", "Make my plan", "Show the numbers as a table" and every list-row link ≥ 48 px high [DPA/DESIGN-10]; ≥ 8 px between adjacent targets. No sticky bar (SC 2.4.11).
- **Errors:** one `role="alert"` notice at the top of the working area: what happened, what to do, `Reference: <support_ref>` (NFR-058).

## 1. Flow map

```
 account menu ──"Reference patterns"──► V-10 ──row──► V-11 ──"Where do these values come from?"──► C-11
 M-02 / D-01 ──"Patterns against the reference"──► W-10 (this match, your side)
   W-10 "Gaps against the reference" (ranked) ──"Show me"──► E-01 panel ──► S-01 at the rally (fix a tag)
        │                                    └──"Drills for this gap"──► E-11 (in plan: link to P-01 row; not in plan: drill list)
        ├─ "Where you lose most rallies" (ADR 0003, always shown) ──"Your training plan"──► P-01
        └─ "Other patterns" (no clear gap / not enough data / no reference yet / not measured) ──pattern name──► V-11
 P-01 ──drill row "Why" (E-10) cites the reference via C-10 ──"About this reference"──► V-11
 new reference version published ──► E-12 notice on P-01 and W-10 ──"Make a new plan"──► P-02
 Q-06 / U-04 / F-01 ──C-12 consent notice (information only)
 M-02 analysis request ──422 provenance or consent reason──► C-13 notice on M-02 (nothing analysed)
```

## V. Reference browser (ST-170c; FR-170.R5)

### V-10 Reference patterns

- **Title** "Reference patterns"; `<h1>` the same. Under it (HAX G1): "What we compare your tagged matches with, for doubles and singles at each level. Every value says where it comes from." Link "Where do these values come from?" (→ C-11).
- **Notices** per §0 (reference notice while any entry is `judgment`).
- **Filter** (two `<select>`s with visible labels, no drag): "Format" (Doubles, Singles) and "Level" (the catalogue §0.6 display labels "below 3.0", "3.0-3.5", "4.0 and above"). Default: the player's plan level and the format of their latest match; with no level set, "3.0-3.5" and the sentence "Set your level in your practice setup to see your band first." with a link to P-02. Changing a filter updates the list in place and announces "Showing <n> patterns for doubles, 3.0-3.5" (polite).
- **List** (`<ul>`), one item per pattern in catalogue order. Each item is one link (whole row ≥ 48 px) to V-11 and shows: pattern name (`<h2>`); the reference value or band in words ("Reference: 45% to 70%"); C-10 in compact form; for a `pro` direction, nothing until a resolved pro source exists (catalogue §0.6).
- **Patterns with no entry** for the chosen band and format are listed under "No reference yet" (`<h2>`), name only, with "We have no checked reference for this level and format yet."
- **CV patterns** (AN-11, AN-12, stacking, partner spacing): one line under the list, "Arrival at the kitchen line, transition, stacking and partner spacing need video analysis that has not yet passed its accuracy check." (roadmap §7.1; words per coach, §4 row V-6).

### V-11 One pattern's reference

- **Title** "<pattern name>: reference"; `<h1>` the pattern name. Breadcrumb link "Reference patterns".
- **"How it is counted"** (`<h2>`): the catalogue definition from the API (e.g. AN-09 "drops / third shots with a trajectory"), its data source in words ("Needs Full Tag: each third shot labelled drop or drive"), min_n ("We compare once you have 20 third shots"), and which way is better ("Better: inside the band. Too few and too many drops are both gaps." for `inside_band`; "Better: higher" / "Better: lower").
- **"References"** (`<h2>`): a table, caption "References for <pattern name>", columns Level, Format, Reference, Where it comes from, Status, Version. One row per `coach-reviewed` or `verified` entry. "Where it comes from" holds C-10's label in words.
- **"About this reference"**: C-10 in full form for the row of the player's band and format.
- **Version history:** "Version 1, published <date>." When a newer version exists: "Version 2 replaced version 1 on <date>. Your plan uses the version it was made with." (FR-170.R2, FR-173.R4).

### V states

| Screen | State | What the player sees |
|---|---|---|
| V-10 | Empty | No entry is `coach-reviewed` (reference set not published): "No reference patterns are ready yet. Our coach checks each value before you see it." No list, no filter |
| V-10 | Loading | Skeleton of the notices, filter and 5 rows at final height (NFR-039), `aria-busy="true"`; polite "Loading reference patterns" |
| V-10 | Error | Alert "We could not load the reference patterns. Try again." with "Try again" and `Reference:`. An entry that arrives without a provenance label is **not shown**; its row says "We could not show where this value comes from." (FR-170.R5 negative) |
| V-10 | Low-confidence | N/A: no automatic call; values are coach content, not model output (§0) |
| V-10 | Low-sample | A `published` entry with n below the pattern's min_n keeps its value and gets the tag "low sample" and "Based on only <n> <unit>." |
| V-10 | Not measured | N/A for references: "Not measured" describes a player's match (W-10). A pattern whose reference needs a vision stage is in the CV line (V-10 list rule) |
| V-10 | Not enough data | N/A: a reference with too little data is "low sample" (above), not this player state |
| V-10 | No clear gap | N/A: V-10 compares nothing with the player |
| V-10 | No reference yet | Pattern listed under "No reference yet" with the sentence above, never a blank or 0 (FR-172.R3 wording) |
| V-11 | Empty | Unknown or draft pattern id → 404 with the same body (T6-PL-3): app not-found page "We could not find that pattern." and a link to V-10 |
| V-11 | Loading | Skeleton of the heading, definition and table at final height; polite "Loading <pattern name>" |
| V-11 | Error | Alert as V-10; the definition and table are not shown half-loaded |
| V-11 | Low-confidence | N/A (as V-10) |
| V-11 | Low-sample | As V-10, in the table's Reference cell |
| V-11 | Not measured | N/A (as V-10) |
| V-11 | Not enough data | N/A (as V-10) |
| V-11 | No clear gap | N/A (as V-10) |
| V-11 | No reference yet | Definition shown; the table is replaced by "We have no checked reference for this pattern yet." |

## W. Weakness view (ST-172c; FR-172.R5, NFR-027.11, .12, .14)

### W-10 Your patterns against the reference

- **Title** "Patterns against the reference: <match title>"; `<h1>` "Your patterns against the reference". Subtitle: "<match title> · your side (Ivy and Dana) · compared with: doubles, 3.0-3.5 (from your practice setup)". Link "Change my level" (→ P-02, prefilled).
- **HAX G1 line:** "We count patterns in the rallies you tagged and compare them with a reference for your level. A gap is shown only when your whole range is outside the reference."
- **Notices** per §0, then this order of sections (FR-172.R5):
  1. **"Gaps against the reference"** (`<h2>`): ranked weaknesses as a numbered list in API order (ADR 0061 rule 3.5). Zero gaps → the sentence **"No clear gap against the reference."** in its place (FR-172.R5).
  2. **"Where you lose most rallies"** (`<h2>`): the ADR 0003 rallies-lost top 3, same names and units as P-01, with "Your training plan" link. Always shown, also with zero gaps (FR-172.R5; ADR 0061 rule 4).
  3. **"Other patterns"** (`<h2>`): every other pattern with its state words, in catalogue order.
- **Gap row** (each item of section 1): pattern name (`<h3>`); state words ("Below the band"); "You: 20% (n = 25 third shots, range 11% to 33%)"; "Reference: 45% to 70%"; the distance in the pattern's unit ("12 points below the band", from the range edge nearest the reference); C-10 compact; button **"Show me"** (accessible name "Show me the 25 rallies behind Third-shot drop share") opening E-01 with the measure's rally ids; link "Drills for this gap" (→ E-11).
- **Gap chart** (one per row, decorative, `aria-hidden="true"`, the printed lines above are the content): a horizontal 0-100% scale (AN-13: 0 to the larger of the two upper ends, in dinks). The **reference band** is an outlined box, 2 px `border-control` (`#69737E`, 4.82:1 light; `#7F8B97`, 5.33:1 dark) with no fill; the **player range** is a solid bar in `primary` (6.51:1 / 8.13:1) 8 px high; the **player value** is a 12 px diamond in `text` (17.67:1 / 15.73:1). Shape tells marks apart (box, bar, diamond), not hue. Printed at the ends: "11%", "33%", "45%", "70%". All pairs are already proven in `tokens.md` §2, so `docs/design/tools/contrast_check.py` covers them with no new row (NFR-027.11).
- **Data table equivalent** (NFR-027.12): under section 1, a disclosure button **"Show the numbers as a table"** (`aria-expanded`). The table is always in the DOM (hidden while closed), caption "Your patterns against the reference", columns: Rank, Pattern, You, Your range, n, Reference, Reference id and version, State. One row per pattern of all three sections, so the table holds every chart value and every state. The table sits in a focusable scroll region (`role="region"`, `aria-label` = caption, `tabindex="0"`) so only the table scrolls at 320 px, never the page (SC 1.4.10 exception for data tables).
- **"Other patterns" row:** name (link to V-11); state words with their numbers ("Not enough data (7 of 20 third shots)"; "No clear gap: you 30% to 55%, reference 45% to 70%"; "No reference yet for doubles, 3.0-3.5"; "Not measured: this match has Quick Tag only. Third-shot patterns need Full Tag."). A "No clear gap" row keeps its chart; the other states have no chart.
- **"Show me"** reuses `EvidencePanel` (`web/src/components/stats/EvidencePanel.tsx`): the rallies behind the measure, each opening S-01 at the rally, so a wrong tag is one tap from its fix (HAX G9; flows-sprint-03 §3).
- **Owner only** (FR-172.R6): a foreign or unknown match id → the app not-found page (same body as unknown, T6-WK-1).

### W states

| Screen | State | What the player sees |
|---|---|---|
| W-10 | Empty | No tagged rally in the match: "Tag this match to compare it with the reference." and link "Tag rallies" (T-01). No sections, no table |
| W-10 | Loading | Skeleton of the notices, three section headings and 3 rows each at final height (NFR-039), `aria-busy="true"`; polite "Loading your patterns" |
| W-10 | Error | Alert "We could not load your patterns. Try again." with "Try again" and `Reference:`. A row whose reference arrives without a provenance label shows "We could not show where this reference comes from." and no comparison (FR-170.R5) |
| W-10 | Low-confidence | N/A in Sprint 6 (§0 rule for later) |
| W-10 | Low-sample | Same as "Not enough data": the "low sample" tag and the n of min_n, value still printed, never ranked (FR-172.R2) |
| W-10 | Not measured | Row under "Other patterns" with the reason in words (`no_shot_facets` → "this match has Quick Tag only. Third-shot patterns need Full Tag."; `no_bounce_positions` → "no bounce was placed on the court"; `needs_cv` → "needs video analysis that has not yet passed its accuracy check"). Never 0 (FR-171.R5) |
| W-10 | Not enough data | Row "Not enough data (7 of 20 third shots)" with "Tag more matches to compare this pattern." |
| W-10 | No clear gap | Per pattern: row with both ranges and its chart. With zero gaps: section 1 reads "No clear gap against the reference." and section 2 (rallies lost) stays (FR-172.R5; its negative Example: never an empty page) |
| W-10 | No reference yet | Row "No reference yet for doubles, 3.0-3.5"; if only a `pro` direction exists, "Pros tend to <direction>; this is not a target for your level" once a resolved pro source exists (A2, FR-172.R3), else nothing more. No level set → every pattern is this state, with the link "Set your level" (→ P-02) at the top |

## E. Exercise Why (ST-173d, ST-172c; FR-173.R1, R2, R4)

### E-10 Plan drill row: Why with the reference

- **Where:** P-01 drill row (flows-sprint-04 §2), `web/src/components/plan/PlanView.tsx` and `PlanViewWords.ts`. Only when the drill's weakness is one of the plan's ADR 0003 top 3 **and** a ranked gap shares its primary AN id (ADR 0061 rule 4). Every other row keeps today's "Why: <metric>: <value> of <n> <unit>".
- **Why line, two parts** (FR-173.R2; template text from cited fields only, no LLM):
  1. "Why: Third shot: drop 20% (n = 25, range 11% to 33%)." The "low sample" tag follows a low-sample value.
  2. "Reference: 45% to 70% (REF-AN09-D35, version 1, not yet checked by a human coach, coach judgment, not measured from pro matches)." This is C-10's inline form; the label is the FR-170.R5 string, word for word.
- **Controls:** "Show me" (as P-01) and the link **"About this reference"** (→ V-11 at the row's band and format). Both ≥ 48 px high, 8 px apart.
- **Missing part:** a citation without reference id, version, status or label is rejected by the plan validator (FR-173.R2 negative), so the row shows only the P-01 error text "We could not show why this drill was chosen." — never a Why with a part missing.

### E-11 Drills for a gap "not in this plan" (section of a W-10 gap row)

- **Opens** from "Drills for this gap" (disclosure, focus stays on it, the list follows in reading order).
- **Gap is a plan target:** "This gap is in your training plan." with link "See it in your plan" (→ P-01 at the row).
- **Gap is not a plan target** (ADR 0061 rule 4): heading "Drills that fit this gap (not in this plan)"; up to 3 library drills that fit players, equipment, level, time and safety (FR-173.R1): name, "<m> minutes · <p> players · Needs: <equipment>", the same two-part Why as E-10, and the human-coach notice once ("These drills have not yet been checked by a human coach. Warm up first, and stop any drill that hurts."). Under them: "Your plan works on the 3 places you lose most rallies. These drills are extra." (judgment; ADR 0061 rule 4: gaps add no plan target).
- **No fitting drill** (FR-173.R1 negative): "No exercise yet for this gap." and "Change my setup" (→ P-02). Never a drill that does not fit.

### E-12 "The reference changed" notice

- **When:** the plan's stored reference version is older than the published one for a cited pattern (FR-173.R4; HAX G14, G18).
- **On P-01**, after the notices of flows-sprint-04 §2, `info-surface`: "The reference for Third-shot drop share changed from version 1 to version 2 on <date>. Your plan still uses version 1. Make a new plan to use version 2." Button "Make a new plan" (→ P-02, prefilled). The plan never changes by itself.
- **On W-10:** the comparison always uses the published version; a line under the subtitle says "Compared with reference version 2. Your plan uses version 1." with the same button.

### E states

| Screen | State | What the player sees |
|---|---|---|
| E-10 | Empty | No plan: P-01's empty states unchanged (flows-sprint-04 §2). No gap cited: today's Why line only |
| E-10 | Loading | P-01 skeleton; the Why line's two lines reserved at final height (NFR-039) |
| E-10 | Error | "We could not show why this drill was chosen." in the row (validator refusal or a citation part missing), never a blank |
| E-10 | Low-confidence | N/A in Sprint 6 (§0) |
| E-10 | Low-sample | "low sample" tag after the player's value; the reference part unchanged |
| E-10 | Not measured | N/A: an unmeasured pattern cannot be a ranked gap, so it is never cited; the row keeps today's Why |
| E-10 | Not enough data | N/A for the same reason (FR-172.R2: never ranked) |
| E-10 | No clear gap | Today's Why only; no reference part (nothing to cite) |
| E-10 | No reference yet | Today's Why only |
| E-11 | Empty | Zero ranked gaps: no "Drills for this gap" control (W-10 shows "No clear gap against the reference.") |
| E-11 | Loading | "Finding drills…" (polite), 3 reserved rows |
| E-11 | Error | Alert in the panel "We could not load drills for this gap. Try again." with `Reference:` |
| E-11 | Low-confidence | N/A in Sprint 6 (§0) |
| E-11 | Low-sample | N/A: low-sample measures are never ranked, so they have no drills panel |
| E-11 | Not measured | N/A (never ranked) |
| E-11 | Not enough data | N/A (never ranked) |
| E-11 | No clear gap | N/A (never ranked); with no fitting drill for a ranked gap: "No exercise yet for this gap." |
| E-11 | No reference yet | N/A (never ranked) |
| E-12 | Empty | Plan and published version equal: no notice |
| E-12 | Loading | Not shown until the plan has loaded (no layout shift: the notice slot is part of P-01's notice block) |
| E-12 | Error | No notice; P-01's own error state applies |
| E-12 | Low-confidence | N/A in Sprint 6 (§0) |
| E-12 | Low-sample | N/A: the notice carries no value |
| E-12 | Not measured | N/A (as above) |
| E-12 | Not enough data | N/A (as above) |
| E-12 | No clear gap | Still shown if the version changed: the new version may change the comparison |
| E-12 | No reference yet | A withdrawn entry (pattern now "No reference yet"): "The reference for <pattern> was withdrawn on <date>. Your plan still cites version 1." |

## C. Consent and provenance (ST-170c, ST-172c, ST-173d, ST-175a; FR-170.R5, FR-174.R1-R2)

### C-10 Provenance component

One component, two forms, used wherever a reference value is shown. A reference value is **never** rendered without it (FR-170.R5); the component test fails when the label is absent (ST-170c red test).

| Field | Compact form (V-10 row, W-10 row) | Full form (V-11, "About this reference") | Source field (placeholder) |
|---|---|---|---|
| Label | tag in words, one of exactly three: "measured from licensed footage", "published source", "coach judgment, not measured from pro matches" | same | `provenance_label` from `source_type` |
| Value | "Reference: 45% to 70%" | same, plus format and band "for doubles, 3.0-3.5" | `band` or `value` |
| n | published or measured: "n = 412 third shots"; judgment: omitted | judgment: "A coach's band, not a count of shots." | `n` |
| Interval | published or measured: "range 53% to 63%"; judgment: the band is the range | same, plus "95% range, Wilson method" or "95% range for a median" | `interval`, `interval_method` |
| Reference id and version | "REF-AN09-D35 v1" | "REF-AN09-D35, version 1, published <date>" | `reference.id`, `reference.version` |
| Status | "not yet checked by a human coach" (`coach-reviewed`) or "checked by a human coach" (`verified`) | same | `status` |
| Citation | — | published: "Source: <title> (SRC-nnnn)" linking to its C-11 row; judgment: "Source: coach judgment, reference set version 1"; measured: "Source: licensed match footage, <n> rallies" (no player names, P16 Q9) | `source.citation_id` |

- **Markup:** compact = one `<p>` with the tag first; full = `<dl>` with the field names as `<dt>`. The label tag is `warning-text` on `warning-surface` for `judgment` (6.86:1), `text` on `surface` otherwise; it is a word, so colour adds nothing the text lacks.
- **Sprint 6 reality:** no `statistic` row of the sources register is `resolved` and the lint refuses every `measured` entry (ADR 0061; COACH-6a), so only the judgment label can appear. The other two forms are specified so ST-170c tests all three.

### C-11 Where reference values come from

- **Title** "Where reference values come from"; sections (`<h2>`): "The three kinds of source" (one paragraph per label, words of §4); "Who checks them" (status ladder: a coach reviews every value before you see it; "checked by a human coach" appears only after a human coach recomputes it, P15); "Video we use" (C-12 words: only video we have the rights to; no broadcast or YouTube copies; training video only with everyone's agreement, FR-174); "Sources" (table: id, source, what it backs, status, from the API's copy of `docs/domain/sources.md`, rows of kind `statistic` only).

### C-12 Training-video consent notice

- **Extends** the Sprint 4 footage notice "Before you upload" (flows-sprint-04 §5) on F-01, Q-06 and U-04, one more paragraph: "Only upload video if everyone on it agreed to be filmed and to have their play analysed. We use your video only to analyse your matches. We never add it to our reference patterns or use it to train a model." (T6-FT-3: player uploads permit `analysis` only.)
- **Information, not a checkbox** (as Sprint 4 R4-5; judgment): the notice informs; consent records come from the operator registration path, never from a player form (T6-FT-5). No UI in Sprint 6 writes rights or consent fields.
- **No pose or body tracking** runs on player video in Sprint 6 (threat notes §1 scope boundary), so no body-data notice is needed yet. The first ticket that shows one is tier 2 with the security-privacy-engineer.

### C-13 "Analysis not started" notice (on M-02)

- **When** an analysis job request is refused (422, FR-174.R1-R2). `role="alert"` at the top of M-02; the video and tags are untouched; "Nothing was analysed."

| Code | Player text |
|---|---|
| `provenance_missing` | "We could not start the analysis: this video has no record of who owns it. Nothing was analysed." |
| `consent_incomplete` | "We could not start the analysis: we do not have agreement from everyone on this video. Nothing was analysed." |
| `use_not_permitted` | "We could not start the analysis: this video may not be used for this. Nothing was analysed." |
| `provenance_revoked` | "We could not start the analysis: permission to use this video was withdrawn or has ended. Nothing was analysed." |
| `provenance_invalid` | "We could not start the analysis because of a problem on our side. Nothing was analysed." |

- Each ends with `Reference: <support_ref>`. The body names the reason code only (T6-FT-8): no rights holder, no consent reference.

### C states

| Screen | State | What the player sees |
|---|---|---|
| C-10 | Empty | No reference value on the page: the component is not rendered |
| C-10 | Loading | Part of its host's skeleton (one reserved line compact, five full) |
| C-10 | Error | Label missing or unknown: the host shows "We could not show where this value comes from." and **not** the value (FR-170.R5 negative) |
| C-10 | Low-confidence | N/A in Sprint 6 (§0) |
| C-10 | Low-sample | Published or measured entry with n below min_n: "low sample" tag after n |
| C-10 | Not measured | N/A: describes a reference, not a player's match |
| C-10 | Not enough data | N/A (as above) |
| C-10 | No clear gap | N/A: shown the same in every comparison state |
| C-10 | No reference yet | Not rendered; the host shows its "No reference yet" words |
| C-11 | Empty | No `resolved` statistic source: the "Sources" table is replaced by "No published source is in use yet. Every value is a coach's judgment." (true on 2026-11-13) |
| C-11 | Loading | Static text renders at once; the sources table reserves 3 rows |
| C-11 | Error | Static sections shown; the table area: "We could not load the source list. Try again." with `Reference:` |
| C-11 | Low-confidence | N/A in Sprint 6 (§0) |
| C-11 | Low-sample | N/A: the page shows no values |
| C-11 | Not measured | N/A (no values) |
| C-11 | Not enough data | N/A (no values) |
| C-11 | No clear gap | N/A (no values) |
| C-11 | No reference yet | Same as Empty |
| C-12 | Empty | N/A: static notice on its host pages |
| C-12 | Loading | Rendered with the host page (no fetch) |
| C-12 | Error | N/A: static text |
| C-12 | Low-confidence | N/A in Sprint 6 (§0) |
| C-12 | Low-sample | N/A: no values |
| C-12 | Not measured | N/A: no values |
| C-12 | Not enough data | N/A: no values |
| C-12 | No clear gap | N/A: no values |
| C-12 | No reference yet | N/A: no values |
| C-13 | Empty | No refusal: not shown |
| C-13 | Loading | "Starting the analysis…" (polite) on the request button, `aria-busy` |
| C-13 | Error | The five texts above; an unknown code → the `provenance_invalid` text (fail closed, T6-FT-7) |
| C-13 | Low-confidence | N/A in Sprint 6 (§0) |
| C-13 | Low-sample | N/A: no values |
| C-13 | Not measured | N/A: no values |
| C-13 | Not enough data | N/A: no values |
| C-13 | No clear gap | N/A: no values |
| C-13 | No reference yet | N/A: no values |

## 2. HAX checklist (Sprint 6 scope) [DPA/DESIGN-11]

| Guideline | Where | Design response |
|---|---|---|
| G1 What the system can do | V-10, W-10 lines | "We count patterns in the rallies you tagged…"; no claim of video analysis or AI |
| G2 How well it can do it | C-10, W-10, notices | n and 95% range on every player value; label and status on every reference; reference notice; "low sample" in words |
| G10 Scope services when in doubt | W-10 | A gap only when the whole range is outside the reference (ADR 0061 rule 3.4, conservative); otherwise "No clear gap" or "Not enough data", never a guess |
| G11 Why the system did what it did | E-10, E-11, W-10 | Two-part Why citing value, n, range, reference id, version, status and label; "Show me" to the rallies |
| G9 Efficient correction | W-10 "Show me" | E-01 → S-01 at the rally: a wrong tag is fixed where it is seen, and the measure follows |
| G14, G18 Update cautiously, notify of changes | E-12 | A new reference version never rewrites a plan; the notice names old and new versions and the date |
| G12 Remember recent interactions | V-10 filter | Defaults to the player's level and latest format |

## 3. WCAG 2.2 AA design-level checklist per screen

"✓" means this file specifies it; evidence comes from ST-174b (axe, target scan; NFR-027.10, .13), ST-172c component tests (NFR-027.11, .12, .14) and the human pass (P6). This is not a conformance claim [ASB/RPD-08].

| Check | V-10 | V-11 | W-10 | E-10..E-12 | C-10 | C-11 | C-12, C-13 |
|---|---|---|---|---|---|---|---|
| Unique title, one `<h1>` (SC 2.4.2) | ✓ | ✓ | ✓ | — (host P-01 / W-10) | — | ✓ | — (host) |
| Targets ≥ 24 px, primary ≥ 48 px (SC 2.5.8; NFR-027.13) | ✓ rows 48 | ✓ | ✓ | ✓ | ✓ links | ✓ | ✓ |
| Non-text contrast ≥ 3:1 for marks and bars (SC 1.4.11; NFR-027.11) | — | — | ✓ proven tokens | — | ✓ tag | — | — |
| Not colour alone: states and labels in words (SC 1.4.1; NFR-027.14) | ✓ | ✓ | ✓ state words, shapes | ✓ | ✓ | ✓ | ✓ |
| Text equivalent of the chart: data table (SC 1.1.1, 1.3.1; NFR-027.12) | — | ✓ table | ✓ table = chart | — | — | ✓ table | — |
| Label in name (SC 2.5.3) | ✓ | ✓ | ✓ "Show me the 25 rallies…" | ✓ | — | — | — |
| Keyboard, logical order, disclosure focus (SC 2.1.1, 2.4.3) | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ |
| Focus not obscured (SC 2.4.11) | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ |
| No dragging (SC 2.5.7) | ✓ selects | ✓ | ✓ | ✓ | — | ✓ | ✓ |
| Status messages (SC 4.1.3) | ✓ filter count | ✓ | ✓ loading | ✓ "Finding drills…" | — | — | ✓ alert |
| Reflow at 320 px (SC 1.4.10) | ✓ | ✓ table region | ✓ table region | ✓ | ✓ | ✓ | ✓ |
| Consistent help, same place (SC 3.2.6) [ASB/RPD-06] | ✓ C-11 link | ✓ | ✓ | — | — | — | — |

## 4. Copy register (proposed; the coach owns pattern words and coaching claims)

Every claim names its source. "Coach" = the pickleball-domain-coach's cell on the DR-06 PR (R6-6); until it is written the row is the designer's proposal and is not claimed as agreed.

| Row | Screen | Text | Source of the claim | Coach |
|---|---|---|---|---|
| V-1 | C-10 | "coach judgment, not measured from pro matches" | FR-170.R5 (verbatim) | pending |
| V-2 | C-10 | "published source" / "measured from licensed footage" | FR-170.R5 (verbatim); neither can appear in Sprint 6 (sources §3; ADR 0061) | pending |
| V-3 | §0 notice | "These reference values are a coach's judgment, not measured from pro matches." | FR-170.R5; kickoff PM-3 | pending |
| V-4 | C-10 | "not yet checked by a human coach" / "checked by a human coach" | status ladder (catalogue header); ADR 0051 rule 3 notice | pending |
| V-5 | V-10, W-10 | Pattern names ("Third-shot drop share", "Dink tolerance", "Return depth") | catalogue §1 "Name (UI)" | pending |
| V-6 | V-10 | "kitchen line" for the NVZ in the CV line | judgment (player word); catalogue says NVZ | pending |
| V-7 | V-11 | "Too few and too many drops are both gaps." | catalogue §0.4 `inside_band` for AN-09 | pending |
| W-1 | W-10 | "A gap is shown only when your whole range is outside the reference." | ADR 0061 rule 3.4; FR-172.R1 | pending |
| W-2 | W-10 | "No clear gap against the reference." | FR-172.R5 (verbatim) | pending |
| W-3 | W-10 | "Not enough data (<n> of <min_n> <unit>)" | FR-172.R2 Example | pending |
| W-4 | W-10 | "No reference yet for <format>, <band>" | FR-172.R3 | pending |
| W-5 | W-10 | "Not measured: this match has Quick Tag only. Third-shot patterns need Full Tag." | FR-171.R5 `no_shot_facets` | pending |
| W-6 | W-10 | "Below the band" / "Above the band" / "Below the reference" / "Above the reference" | FR-172.R1 | pending |
| W-7 | W-10 | "<d> points below the band" | ADR 0061 rule 3.5 (distance; the ordering uses band widths) | pending |
| E-1 | E-10 | Two-part Why (§E-10) | FR-173.R2 Example (split into two sentences, judgment) | pending |
| E-2 | E-11 | "No exercise yet for this gap." | FR-173.R1 (verbatim) | pending |
| E-3 | E-11 | "Your plan works on the 3 places you lose most rallies. These drills are extra." | ADR 0061 rule 4 | pending |
| E-4 | E-12 | "Your plan still uses version 1. Make a new plan to use version 2." | FR-173.R4 | pending |
| C-1 | C-12 | Consent paragraph (§C-12) | FR-174.R1-R2; T6-FT-3; interim until P16 Q6 | pending |
| C-2 | C-13 | Five refusal texts | FR-174.R1-R2 codes; T6-FT-7, T6-FT-8 | pending |

## 5. Open items and routed

| Id | Item | Owner |
|---|---|---|
| PD-FL6-01 | Field names `provenance_label`, `state`, `reference.version`, the rallies-lost list and rally ids per measure in the weakness response | senior-backend-engineer (ST-170b, ST-172b contracts) |
| PD-FL6-02 | W-10 scope: one match (`?match=`, as ST-172b) or pooled over the format (ADR 0061 rule 3.6); the route form (SEC-S6-TM-03) | principal-engineer, security-privacy-engineer |
| PD-FL6-03 | Copy register rows V-1..E-4, the word "kitchen line" (V-6) | pickleball-domain-coach (R6-6) |
| PD-FL6-04 | C-12 and C-13 wording is interim until the legal review (P16 Q6) | product-manager, security-privacy-engineer |
| PD-FL6-05 | The ST-083 usability kit is not on `origin/main` (Sprint 5 drain); §6 tasks are appended to it when it merges | principal-designer (follow-up on ST-083) |

## 6. Usability tasks for the R1 kit (S6-P9; NFR-036)

Moderated, ≥ 5 players on their own phones (waiting on **P9**). Seeded with the demo stack (`make demo`, players demo-a and demo-b). Observer tallies success without help, time, and the words the player uses.

| Task | Prompt to the player | Success when the player… | Observation |
|---|---|---|---|
| UT6-1 | "Find what the app compares your third shots with." | reaches V-11 for Third-shot drop share | path taken; time |
| UT6-2 | "Where does that reference value come from?" | says it is a coach's judgment, not measured from pro matches | label read or missed |
| UT6-3 | "Is there something in your play this match that is clearly off the reference?" | names the ranked gap and its side, or says "no clear gap" for demo-b | over-claiming a "No clear gap" row as a weakness (count) |
| UT6-4 | "Why is a pattern marked 'not enough data'?" | explains too few shots, and what to do (tag more) | words used |
| UT6-5 | "Check the rallies behind that gap and fix one wrong tag." | opens "Show me", reaches S-01, corrects a tag in ≤ 2 taps (NFR-036 (d)) | taps |
| UT6-6 | "Your plan has a drill for this. Why did it choose it?" | reads both parts of the Why, including the reference version | which part is skipped |
| UT6-7 | "The reference changed. What happens to your plan?" | says the plan stays until they make a new one | belief that the plan changed |

## 7. Design review record (DR-06)

| Date | Participants | Outcome |
|---|---|---|
| Opened 2026-11-13; cells due **2026-11-17** (wave 1 merge-by) | principal-designer (chair); deciders pickleball-domain-coach (SME), senior-ml-cv-engineer, security-privacy-engineer, senior-frontend-engineer, business-analyst, product-manager | **Not yet held.** Each decider's cell is carried by that decider's own review on the PD-6 PR or its DR-06 follow-up (kickoff PD-1): the decider adds its row to the cell table below with "accept/reject (YYYY-MM-DD): reason". The chair never writes another role's cell (ADR 0037 rule 2). A row is added only with its dated cell, so `check_flows.py --decider` and the doc-check job stay green while a cell is outstanding |

**Agenda** (chair's proposals, judgment unless cited):

| # | Item | Proposal | Decides |
|---|---|---|---|
| R6-1 | Screen ids V-10, V-11, W-10, E-10..E-12, C-10..C-13 and the nine-state convention (§0) | Accept | senior-frontend-engineer, business-analyst |
| R6-2 | V-10/V-11 reference browser, filter defaults, "No reference yet" list (§V) | Accept | pickleball-domain-coach, senior-frontend-engineer |
| R6-3 | W-10 section order, gap row, chart marks by shape and proven tokens, table equivalent in a scroll region (§W) | Accept | senior-frontend-engineer, business-analyst (FR-172.R5, NFR-027.11-.14), senior-ml-cv-engineer (interval wording) |
| R6-4 | E-10 two-part Why, E-11 "not in this plan", E-12 version notice (§E) | Accept | pickleball-domain-coach, product-manager, business-analyst (FR-173.R1, R2, R4) |
| R6-5 | C-10 provenance component, C-12 consent notice as information, C-13 refusal texts (§C) | Accept | security-privacy-engineer, product-manager |
| R6-6 | Copy register V-1..C-2 (§4) | Accept | pickleball-domain-coach, product-manager |
| R6-7 | Low-confidence N/A in Sprint 6 and the rule for CV-derived values (§0) | Accept | senior-ml-cv-engineer |
| R6-8 | Usability tasks UT6-1..UT6-7 (§6) | Accept | product-manager |

**Decider steps** (one dated step per decider, sprint-06 DR-06):

| Role | Items | Opened | Due | How the decision arrives |
|---|---|---|---|---|
| pickleball-domain-coach | R6-2, R6-4, R6-6 | 2026-11-13 | 2026-11-17 | review on the PD-6 PR, row added below |
| senior-ml-cv-engineer | R6-3, R6-7 | 2026-11-13 | 2026-11-17 | as above |
| security-privacy-engineer | R6-5 | 2026-11-13 | 2026-11-17 | as above |
| senior-frontend-engineer | R6-1, R6-2, R6-3 | 2026-11-13 | 2026-11-17 | as above |
| business-analyst | R6-1, R6-3, R6-4 | 2026-11-13 | 2026-11-17 | as above |
| product-manager | R6-4, R6-5, R6-6, R6-8 | 2026-11-13 | 2026-11-17 | as above |

**Decider cells:**

| Role | Items | Cell |
|---|---|---|
| principal-designer | R6-1..R6-8 | accept (2026-11-13, author) |

## 8. Traceability

| Screen | FR / NFR | Test (planned owner) |
|---|---|---|
| V-10, V-11, C-10, C-11 | FR-170.R5 | component per state, label absent fails (ST-170c); E2E (ST-174b) |
| W-10 | FR-172.R5, NFR-027.11, .12, .14 | component per state, table equals chart, state text labels, contrast check (ST-172c) |
| E-10, E-11, E-12 | FR-173.R1, R2, R4 | PlanView component (ST-173d); validator (ST-173a) |
| C-12, C-13 | FR-174.R1-R2 | IT-06-08 codes (ST-175a); text per code in the M-02 component test |
| all new screens | NFR-027.10, .13 | axe and target scans in `web/e2e/sprint-06/reference-slice.spec.ts` (planned) (ST-174b) |
