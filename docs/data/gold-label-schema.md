# Gold-set manifest v1 and Full Tag labels v1 (ST-040)

Owner: senior-ml-cv-engineer. Status on 2026-10-06: **schemas and checks done; no real footage exists or may be collected yet** (capture rules in `gold-capture-protocol.md`; legal review NFR-070 first).

Sources: FR-150 (Full Tag), FR-151 (frozen, versioned gold sets), QD §8 (manifest fields and sets QD-GD-01..07), QD-TX-01..03 (facets and agreement), QD X3 (forced/unforced κ), brainstorm-engineering §5.3 (venue split), `docs/architecture/match-aggregate.md` §2 (slots, sides, endings), OQ-06 and ADR 0023 (consent, US and AU), ADR 0035 (this design).

Code: `backend/src/racket/dataset/gold_set.py` (manifest v1), `labels.py` (labels v1), `filesystem.py` (reads label files), `cli.py` (`racket-manifest-check`). Tests: `backend/tests/unit/dataset/test_gold_set.py`, `test_labels.py`. Example set: `fixtures/gold/example-full-tag-v1/` (built by `fixtures/gold/make_example_full_tag_v1.py`; **not an evaluation set**).

## 1. How the check runs

`racket-manifest-check <set_dir>` (CI: `scripts/ci/check_fixtures.sh`, every set under `fixtures/` with a `manifest.json`, with the merge-base manifest for the version-bump rule):

1. The integrity rules for every set (ST-011): sha256 per file, no unlisted, missing or symlinked file, no hash change without a version bump, consent record for a clip that shows people (ST-025).
2. If the manifest has `"schema": "gold-set-manifest/v1"`, the gold rules below, and every label file is validated against `full-tag-labels/v1`.

Exit codes: 0 pass; 1 rule problems (each printed with the file and its `[kind]`); 2 malformed manifest, including an unknown `schema` (a newer manifest is never checked as a plain fixture).

## 2. Manifest v1 fields

Every field of the fixture manifest (`id`, `version`, `licence`, `consent_status`, `files` with `path` and `sha256`) plus:

| Field | Type | Rule | Source |
|---|---|---|---|
| `schema` | `"gold-set-manifest/v1"` | required to be a gold set | ADR 0035 |
| `created` | ISO date | required | QD §8 |
| `purpose` | `vision` \| `analytics` \| `scoring` \| `fixture` | QD-GD-04, -03, -02, -07 | QD §8 |
| `label_schema` | `"full-tag-labels/v1"` | required | FR-150 |
| `rules_version`, `metric_dict_version` | string or null | required keys; null only when the set has no scoring or metric use | QD §8 |
| `consent_status` | `synthetic` \| `consented` | anything else is refused until the legal review (NFR-070); `consented` = team-recorded with written consent from everyone filmed | OQ-06, ADR 0023 |
| `labellers` | list of `{role_id, role}` | non-empty; role IDs only, never a name or an email address (`@` refused) | QD §8; privacy (judgment) |
| `agreement` | list of `{facet, kappa, n, admitted}` | `kappa` in -1..1 or null; `n` ≥ 0; facet from §4 | QD-TX-03 |
| `venues` | list of `{id, split}` | unique ids; split `train` \| `val` \| `test` | brainstorm-engineering §5.3 |
| `clips` | list (see below) | non-empty; each clip has its own label file(s) | FR-151 |

Clip entry:

| Field | Rule |
|---|---|
| `path` | a file of the set (else `clip_not_in_files`) |
| `label_file` | a file of the set, unique across clips (else `label_not_in_files` / format error) |
| `double_labelled`, `second_label_file` | a double-labelled clip names the second labeller's file; a single-labelled clip has `null` |
| `venue_id` | one of `venues` (else `unknown_venue`); the clip's split is its venue's split, so no venue is in two splits |
| `shows_people`, `consent_record` | a clip that shows people needs a consent record (`consent_missing`) |
| `consent_jurisdiction` | `US` or `AU` when the clip shows people (`consent_jurisdiction`); a `synthetic` set showing people fails (`consent_contradiction`) |

## 3. Rules a well-formed manifest can still break (exit 1)

| Kind | Rule | Applies to | Source |
|---|---|---|---|
| `held_out_venues` | ≥ 3 `test` venues that have clips | `vision` | QD-GD-04; brainstorm-engineering §5.3 |
| `double_label_share` | ≥ 20% of clips double-labelled | `vision` | QD-GD-04 |
| `kappa_below_gate` | an admitted shot facet has κ ≥ 0.7 on n ≥ 300; an admitted `ending` κ ≥ 0.6 | all | QD-TX-03; QD X3 |
| `facet_not_admitted` | label files carry only admitted shot facets | all | QD-TX-03 |
| `consent_contradiction`, `consent_jurisdiction` | §2 clip table | all | OQ-06, ADR 0023 |
| `people_in_git` | a clip with `shows_people: true` is not tracked by git and is git-ignored (or outside any repository); git missing or failing counts as exposed | all sets, fixture manifests too | consent form item 4 (gold-capture-protocol §2 step 6); SEC-S2-TM-06 |
| `label_not_in_files`, `label_invalid` | every label file is in the set and valid against §4, and names its own clip | all | FR-150, FR-151 |

`hit`, `bounce`, `hitter`, `rally_boundaries` and `winning_side` agreement rows may be recorded; no gate is set for them yet (the engineering targets CV-T05..T11 measure models, not labellers). A gate for them needs an ADR.

## 4. Full Tag labels v1 (one JSON file per clip and labeller)

```json
{
  "schema": "full-tag-labels/v1",
  "clip": "clips/c1.mp4",
  "fps": 60,
  "frame_count": 120,
  "players": ["A1", "A2", "B1", "B2"],
  "rallies": [
    {
      "id": "r1", "start_frame": 6, "end_frame": 70,
      "outcome": {"ending": "unforced_error", "winning_side": "A",
                  "responsible_player": "B2", "fault_kind": null},
      "events": [
        {"type": "hit", "frame": 10, "hitter": "A1", "facets": {"trajectory": "drive"}},
        {"type": "bounce", "frame": 34, "visible": true, "court_xy_m": [3.1, 12.4]},
        {"type": "hit", "frame": 52, "hitter": "B2", "facets": {}}
      ]
    }
  ]
}
```

| Part | Rule |
|---|---|
| Frames | integers, `0..frame_count-1`; frame numbers, not milliseconds, because hit timing is judged per frame (CV-T07) |
| `players` | `["A1","B1"]` (singles) or `["A1","A2","B1","B2"]` (doubles): the match-aggregate slots; identities are per match, never names or faces (spec §8) |
| Rallies | `start_frame < end_frame`; in order, no overlap |
| Events | `hit` or `bounce`; inside their rally; in frame order; no two hits on one frame; `hitter` is a slot of `players` |
| `bounce` | `visible` true/false (ball visibility is first-class, DOM/CV-01); `court_xy_m` = `[x, y]` in court metres or null (homography is valid only for court-plane points, DOM/CV-12) |
| Facets | `contact` {groundstroke, volley}, `trajectory` {drive, drop, dink, lob}, `intent` {neutral, speed_up, reset}, `technique` {none, erne, atp} (QD-TX-01). `position` is derived by rule and **refused** if labelled. Definitions are UNVERIFIED until the coach sources them (QD-TX-02) |
| Outcome | `ending` ∈ {winner, unforced_error, forced_error, fault, replay}; `winning_side` A/B, null only for replay; `responsible_player` optional, on the winning side for `winner` and on the losing side for errors and faults (match-aggregate §2.1); `fault_kind` only for a fault, ∈ {serve, foot, two_bounce, nvz, other}. A unit test pins endings and fault kinds equal to Match & Scoring's |

The validator lists every problem with its location (e.g. `rallies[0].events[1].frame: events must be in frame order`), so one CI run names all of them.

## 5. Changing a frozen set

A frozen set is never edited to raise a score (NFR-078, EP/ENG-28). Any change to a file needs a higher `version` (the CI base check fails otherwise) and, for a set already used in an eval report, an ADR (FR-151). A changed schema is a new `schema` id (`…/v2`) and an ADR; the check refuses unknown ids rather than skipping them.

## Changelog

| Date | Who | Change |
|---|---|---|
| 2026-10-06 | senior-ml-cv-engineer | Written with ST-040: manifest v1, labels v1, checks, example set |
