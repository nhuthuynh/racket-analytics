# drills-safety fixtures (FIX-04-1d; QD-DR-04; drill-review-checklist C5)

One file per case for the "safety notes missing" lint rule, linted one file at a time (no lock):

- `reviewed-footwork-no-notes.json`: `coach-reviewed`, skill `footwork`, empty `safety_notes` -> rc 1.
- `draft-footwork-no-notes.json`: the same content as a `draft` -> rc 0 (not handed to players).
- `deprecated-footwork-no-notes.json`: `coach-reviewed` but `deprecated_by` a newer version -> rc 0.
