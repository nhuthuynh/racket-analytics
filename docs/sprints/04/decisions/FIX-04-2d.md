# FIX-04-2d decisions

Small decisions of ticket FIX-04-2d (meet goal metric G04-05 (e): drills involving lobs retreating, diving, sprints or high-intensity footwork have `safety_notes`; FR-141, QD-DR-04; `docs/domain/drill-review-checklist.md` C5), one dated row each. Append only. RETRO-04 folds these rows into the sprint's decision log. Every coaching statement here is **(judgment)**, `@needs-verification` until a human coach reviews the library (P15).

## Root cause

Verifier result: (a) 23 reviewed, (b) lint 0 problems, (c) coverage rc 0, (d) gap fixture rc 1 `FAIL AN-05 × beginner`, (f) CI green; **(e) the safety grep listed 6 lines**:

```
$ grep -liE 'lob|div(e|ing)|sprint|footwork' content/drills/*/v*.json | xargs jq -r 'select(.safety_notes=="") | "\(.id) \(.review_status) \(input_filename)"'
pb.fixture.drop-and-advance draft content/drills/pb.fixture.drop-and-advance/v1.json
pb.fixture.drop-ladder draft content/drills/pb.fixture.drop-ladder/v1.json
pb.fixture.drop-ladder draft content/drills/pb.fixture.drop-ladder/v2.json
pb.fixture.drop-ladder draft content/drills/pb.fixture.drop-ladder/v3.json
pb.fixture.serve-target draft content/drills/pb.fixture.serve-target/v1.json
pb.volley.line-volleys-no-step-in coach-reviewed content/drills/pb.volley.line-volleys-no-step-in/v1.json
```

Two causes:

1. **Method (5 of 6 lines).** The §4 command scanned every `v*.json`, not the drills (a) counts. The 5 `pb.fixture.*` lines are ST-053 lint fixtures (`draft`, never served); they match only because their summary says "coach-reviewed in **Sprint** 4" (`sprint`). They are locked (QD-DR-02: edits bump the version; never deleted), so no content change can ever empty the old command; superseded versions (e.g. `pb.fixture.drop-ladder@1`, `@2`) would stay listed for the same reason.
2. **Content (1 of 6 lines).** `pb.volley.line-volleys-no-step-in@1` (coach-reviewed in ST-058c) carries the skill tag `footwork` (foot placement at the non-volley-zone line) and empty `safety_notes`. The ST-058c checklist row judged C5 "no trigger (soft, high cooperative feeds)". The drill is not high-intensity, but it is the one reviewed drill a C5 reader (and the mechanical check) flags, and a volleyer reaching for a ball at the line can lunge or step into the zone; a short precautionary note costs nothing (judgment).

## Decisions

| Date | Who | Decision | Evidence | Reasoning |
|---|---|---|---|---|
| 2026-10-18 | pickleball-domain-coach | **TDD: content and docs ticket, no production code or test** (role file: the coach writes no source or test; precedent ST-058a/b/c, COACH-4). The check comes first: the corrected G04-05 (e) command (scorecard §4), run red before the content change | Red (commit "test(FIX-04-2d) ... (red)", content unchanged): from `backend/`, `grep -liE 'lob\|div(e\|ing)\|sprint\|footwork' $(ls -d ../content/drills/*/ \| while read d; do ls "$d"v*.json \| sort -V \| tail -1; done) \| xargs -r jq -r 'select((.review_status=="coach-reviewed" or .review_status=="verified") and (has("deprecated_by")\|not) and .safety_notes=="") \| .id'` → `pb.volley.line-volleys-no-step-in` (1 line; the right reason: the reviewed drill, not a fixture) | The automated gate for drill content stays `racket-drill-lint` + `racket-drill-coverage` (ST-053, ST-059); a C5 lint rule in code would be a backend ticket (senior-backend-engineer), not this one |
| 2026-10-18 | pickleball-domain-coach | **Scorecard §4 G04-05 safety method scoped to the counted set of (a)**: latest version, `coach-reviewed`/`verified`, no `deprecated_by`; same trigger terms, same target (empty) | Old command → 6 lines, 5 of them draft fixtures matching "Sprint 4"; corrected command on unchanged content → 1 line (row above) | QD-DR-04 is about drills a player can be given; drafts and superseded versions are never served (checklist §3 "Counted drills"). The terms are not narrowed, so a reviewed drill with "sprint" in any field still has to carry a note. Alternative (rejected): edit the fixtures' summary, impossible without a version bump of locked fixtures and still leaving the old versions listed. The scorecard header requires this row for any change outside Actual/Met/Evidence; reviewers (principal-engineer, senior) to confirm the method change |
| 2026-10-18 | pickleball-domain-coach | **`pb.volley.line-volleys-no-step-in@2` adds `safety_notes`; `@1` gets `deprecated_by: pb.volley.line-volleys-no-step-in@2`** (QD-DR-02: a content change bumps the version; `deprecated_by` is a lifecycle field outside the lock digest, so `@1`'s lock line is unchanged) | See green evidence rows | Only `version` and `safety_notes` differ between `@1` and `@2`; ids in other drills' `progressions`/`regressions` are unversioned, so they now resolve to `@2` |
