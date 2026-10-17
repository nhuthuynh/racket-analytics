# drills-coverage-gap (ST-059; FR-141; QD-DR-05)

A schema-valid drill library for IT-04-13 and `tests/features/drill_coverage.feature`. It has 21
counted reviewed drills (3 warm-ups) and covers every cell of drill-review-checklist §3 except
one: **no counted drill targets AN-05 for beginners with 2 or fewer players**, so
`racket-drill-coverage` fails with exactly `AN-05 × beginner: players ≤ 2: 0`.

Three AN-05 beginner pairs drills are present and must not count: `fx.an05.draft` (draft),
`fx.an05.retired` (has `deprecated_by`) and `fx.an05.superseded@1` (its latest version, v2, is
for 4 players). Fixture only: not a coaching drill, no lock.
