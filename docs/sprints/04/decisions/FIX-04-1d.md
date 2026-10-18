# FIX-04-1d decisions

Small decisions of ticket FIX-04-1d (meet goal metric G04-05 (e); FR-141; QD-DR-04; drill-review-checklist C5), one dated row each. Append only. RETRO-04 folds these rows into the sprint's decision log. Owner: pickleball-domain-coach. Every coaching statement is **(judgment)**: no coaching source is verified [DOM G2], so drill content stays `@needs-verification` until a human coach reviews it (P15).

## Root cause

G04-05 (e) printed `pb.volley.line-volleys-no-step-in`: `coach-reviewed`, skill `footwork`, empty `safety_notes`. Two gaps let it through:

1. `racket-drill-lint` had no QD-DR-04 rule; C5 was left to the coach's reading (drill-schema.md: "QD-DR-04 content rule is the coach's").
2. The ST-058c mechanical C5 check (ST-058c.md) searched only `summary` and `setup`, with the pattern `lob|speed-up|drive|live|sprint|dive`. The drill names `footwork` only in `skills`, so the check passed and the coach's C5 row passed it as well.

## Decisions

| Date | Decision | Alternatives considered | Reason |
|---|---|---|---|
| 2026-10-18 | Add the lint rule "safety notes missing" (`rules.py`): a `coach-reviewed`/`verified` drill with no `deprecated_by` whose content (every field except `safety_notes`, `review_status` and `deprecated_by`) matches `lob\|div(e\|ing)\|sprint\|footwork`, case-insensitive, needs non-blank `safety_notes`. | (a) Fix the content only, with no guard. (b) A separate script. | (a) leaves the root cause in place. (b) would duplicate the `drill-lint` CI job. With the rule in the lint, G04-05 (b) and (f) also enforce (e). |
| 2026-10-18 | Use the same trigger pattern as the G04-05 (e) measurement, matched against the whole drill content. | A narrower, word-bounded pattern, or a curated list of fields. | Using the same pattern means the lint and the goal measurement cannot disagree. A false positive (e.g. "global") only asks for a safety note, which is cheap. |
| 2026-10-18 | Leave drafts and deprecated versions out of the rule's scope. | Every version. | Drafts and deprecated versions are never assigned to a player, which matches G04-05 (a). Locked versions are immutable, so a rule over every version would fail `pb.volley.line-volleys-no-step-in@1` and the `pb.fixture.*` lint fixtures permanently. |
| 2026-10-18 | Content fix: add `pb.volley.line-volleys-no-step-in@2`, identical to @1 except `version` and `safety_notes` = "Soft, cooperative feeds below head height only. Stop the feet before each volley with small steps; never lunge or jump forward to reach a ball. Stop if dizzy or in pain." (judgment). Set @1 `deprecated_by` to @2. That is a lifecycle field outside the digest, so the lock is unchanged for @1 and gains @2 only. | Remove `footwork` from `skills`. | The drill does train footwork (the stop at the line). Removing the skill would hide the trigger instead of answering it. Any content change needs a new version anyway (QD-DR-02). |
| 2026-10-18 | The G04-05 (e) command as written in goal-scorecard §4 greps **every** version file. Those files include `pb.volley.line-volleys-no-step-in@1` (deprecated, immutable) and the 5 `pb.fixture.*` draft lint fixtures (QA-V04R1-02). The command can never print nothing. This ticket does not edit the scorecard. The scoped form below (latest version, reviewed, not deprecated: the population of (a)) is proposed to the scorecard owners (EM, senior-qa-engineer) as QA-V04R1-02's resolution. | Edit the method in this PR. | Scorecard rule 4: no edits to make a row pass. Changing a method is the scorecard owners' decision. |

## C1..C8 review row (drill-review-checklist §1)

| id@version | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 | Date |
|---|---|---|---|---|---|---|---|---|---|
| `pb.volley.line-volleys-no-step-in@2` | pass (lint ok) | pass ((judgment) rationale) | pass (AN-07, `share:fault`) | pass ("at most 1 own fault" in 2 sets of 20) | pass (safety_notes set; soft cooperative feeds, no lunging) | pass (beginner-intermediate, cooperative feeds) | pass (2 players, half_court) | pass (10-15) | 2026-10-18 |

## Evidence (head of this branch, commands run from `backend/`)

- Red (commit `bc5dbbf`): `uv run pytest -q tests/unit/coaching/test_drill_safety_rule.py tests/integration/test_drill_safety_notes.py tests/features/test_drill_safety_notes.py` gave `13 failed, 7 passed`. The fixture lint reported `reviewed-footwork-no-notes.json: ok, 0 problem(s)` (no rule), and the library scan reported `['pb.volley.line-volleys-no-step-in@1']`.
- Green (commit `3bc23c8`): the same command gave `20 passed`. `uv run pytest -q tests/unit <drill features and ITs>` gave `2291 passed, 1 skipped`.
- (a) The `jq` count from §4 gives `23`.
- (b) `uv run racket-drill-lint ../content/drills` gives `ok, 0 problem(s)`, rc 0. With `--base-lock <(git show origin/main:content/drills/library.lock)` it also gives `ok, 0 problem(s)`, rc 0.
- (c) `uv run racket-drill-coverage ../content/drills` gives rc 0 and `library: 23 reviewed drill(s), 3 warm-up(s)`.
- (d) `uv run racket-drill-coverage tests/fixtures/drills-coverage-gap` gives rc 1 and `FAIL AN-05 × beginner: players ≤ 2: 0`.
- (e), scoped form: `grep -liE 'lob|div(e|ing)|sprint|footwork' $(ls -d ../content/drills/*/ | while read d; do ls "$d"v*.json | sort -V | tail -1; done) | xargs jq -r 'select((.review_status=="coach-reviewed" or .review_status=="verified") and (.deprecated_by==null) and .safety_notes=="") | .id'` prints nothing.
- (e), literal form: the same grep over every `v*.json` prints only `pb.volley.line-volleys-no-step-in@1` (deprecated_by @2) and the 5 `pb.fixture.*` drafts, as the last decision row explains.
