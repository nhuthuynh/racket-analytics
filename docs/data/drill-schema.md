# Drill schema v1 and the drill library lint (ST-053)

Owner: senior-ml-cv-engineer (schema and lint); drill content: pickleball-domain-coach (FR-141, Sprint 4). Status on 2026-10-07: **schema, lint and fixtures done; no real drill exists yet.** `content/drills/` holds lint fixtures only (`pb.fixture.*`, `draft`).

Sources: FR-140; QD-DR-01 (fields), QD-DR-02 (immutability), QD-DR-03 (lint rules) in `docs/requirements/brainstorm-quality-domain.md` §5; metric ids from `backend/src/racket/sports/pickleball/metrics.json` (ST-043). Decisions: `docs/sprints/03/decisions/ST-053.md` 2026-10-07 (slices, stdlib checker, interfaces, lock).

Code: `backend/src/racket/coaching/drills/` — `schema.json` (draft 2020-12), `schema_check.py` (the subset checker), `rules.py` (FR-140), `lock.py` (immutability), `lint.py` (CLI). Tests: `backend/tests/unit/coaching/`, IT-03-14 and `tests/features/drill_library.feature` (QA).

## 1. Files

- One JSON file per drill **version**: `content/drills/<id>/v<version>.json` (the lint reads every `*.json` under the directory, so the layout is a convention).
- `content/drills/library.lock` (`drill-library-lock/v1`) maps every version ever added, `id@version`, to the sha256 of its content.

## 2. Fields (`schema.json`, QD-DR-01)

| Field | Rule |
|---|---|
| `id` | slug of dot-separated lowercase parts, e.g. `pb.drop.third-shot-ladder`; never changes |
| `version` | integer ≥ 1; a content edit is a new file with the next version |
| `name`, `summary` | non-empty text |
| `skills` | unique strings; any `AN-*` entry must be a known metric |
| `target_metrics` | ≥ 1 unique `AN-nn`, each a known metric |
| `level_min`, `level_max` | `beginner` \| `intermediate` \| `advanced`, min ≤ max |
| `duration_min`, `duration_max` | integer minutes ≥ 1, min ≤ max ≤ 45 |
| `players` | 1-4 |
| `needs` | unique, from `wall`, `half_court`, `full_court`, `ball_machine`, `partner_feeder` |
| `equipment` | strings |
| `setup` | ≥ 1 step |
| `success_criterion` | text containing a number (e.g. "8 of 10 drops bounce in the kitchen") |
| `progressions`, `regressions` | drill ids of the library; neither graph may have a cycle |
| `safety_notes` | text (QD-DR-04 content rule is the coach's) |
| `source` or `coach_rationale` | at least one non-blank; a rationale without a source says "(judgment)" |
| `review_status` | `draft` \| `coach-reviewed` \| `verified` (lifecycle) |
| `deprecated_by` | optional `id@version` of an existing drill version (lifecycle) |

No other field is allowed.

## 3. Lint (`racket-drill-lint`)

```bash
cd backend
env -u APP_ENV uv run racket-drill-lint ../content/drills                 # the library, with its lock
env -u APP_ENV uv run racket-drill-lint ../backend/tests/fixtures/drills-invalid/no-source.json
env -u APP_ENV uv run racket-drill-lint ../content/drills --update-lock   # after adding a version
git show origin/main:content/drills/library.lock > /tmp/base.lock
env -u APP_ENV uv run racket-drill-lint ../content/drills --base-lock /tmp/base.lock  # as CI does
```

Exit codes: 0 pass; 1 problems; 2 a path that does not exist, or a lock (the library's or the base one) that is missing where named, unreadable or not `drill-library-lock/v1`. One line per problem: `FAIL <file>: drill <id>: <reason>: <detail>`.

| Reason | When |
|---|---|
| `schema` | a field is missing, unknown, of the wrong type or out of its enum/range |
| `unknown metric` | a target metric or `AN-*` skill is not in the metric dictionary (any status) |
| `unknown progression`, `unknown regression` | the id is not a drill of the library |
| `progression cycle`, `regression cycle` | the graph of the newest versions has a cycle; the detail prints it |
| `duration over 45` | `duration_min` or `duration_max` > 45 |
| `duration range`, `level range` | min > max |
| `criterion no number` | `success_criterion` has no digit |
| `no source` | neither `source` nor `coach_rationale` |
| `rationale not labelled` | a rationale alone without "(judgment)" |
| `duplicate version` | two files with the same `id@version` |
| `unknown deprecated_by` | it names no drill version of the library |
| `deleted drill` | a locked version has no file (deprecate, never delete) |
| `edited without version bump` | a locked version's content digest changed |
| `not in lock` | a new version; `--update-lock` adds it |
| `no lock`, `invalid json` | the directory has no `library.lock`; a file is not JSON |
| `lock entry removed` | a version locked on the base branch is gone from `library.lock` |
| `lock entry changed` | a version locked on the base branch has another digest in `library.lock` |

`--update-lock` only adds entries, and only when "not in lock" is the library's only problem. `review_status` and `deprecated_by` are outside the digest, so reviewing or deprecating a drill is not an edit.

**Against the base branch** (`--base-lock PATH`, default `$RACKET_DRILL_BASE_LOCK`; directories only): the library's own lock cannot prove immutability, because a PR can change the lock with the file. With the base branch's lock, every version locked there must keep its lock line and digest, and the files are checked against the base digests, so deleting a version with its lock line fails (`deleted drill`, `lock entry removed`), an in-place edit with a rewritten lock line fails (`edited without version bump`, `lock entry changed`), and a deleted lock is not rebuilt by `--update-lock` (PE-R1-ST053-01). A base branch with no lock is an empty `drill-library-lock/v1` lock.

## 4. Negative fixtures (G03-09 b)

`backend/tests/fixtures/drills-invalid/<rule>.json`, each breaking exactly one FR-140 rule: `unknown-metric`, `progression-cycle`, `duration-over-45`, `criterion-no-number`, `no-source`.

## 5. CI

The `drill-lint` job runs `racket-drill-lint ../content/drills` on every push and PR (G03-09 c), with `RACKET_DRILL_BASE_LOCK` set to `content/drills/library.lock` of the PR's base commit (on a push to `main`, the previous commit), read by `git show` from a full clone. An unknown base commit fails the job; a base commit without a lock gives an empty lock. Its workflow file is the SRE's (`.github/workflows/ci.yml`); requested by the ML lane on 2026-10-07 (`docs/sprints/03/decisions/ST-053.md`).
