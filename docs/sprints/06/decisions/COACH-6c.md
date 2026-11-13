# COACH-6c decisions

Per-ticket decision file (working-agreement §3). Ticket: COACH-6c, "Reference set v1 content, cited and coach-reviewed" (`docs/sprints/sprint-06.md` §3.3). Story ST-170 (reference pattern set), FR-170.R1 as amended by ADR 0061 Rule 3.3. Owner: pickleball-domain-coach. Review tier 1 (ADR 0056; `content/references/**` is tier 1 with the coach flag in `scripts/ci/review_tiers.py`).

**How TDD applies.** This ticket writes content, not code ("Tests: lint in CI (no new code)", sprint-06 §3.3). The executable checks already exist and were run red before the content was complete: `racket-reference-lint` (ST-170a), IT-06-01 `test_repository_reference_content_lints` (it lints this repository's `content/references` tree, so the backend suite in CI refuses a broken reference) and the doc check `scripts/ci/check_docs.py` (CI-DOC-CHECK-06: every `citation_id` is a row of the sources register). No new test file is added: a test that pins these 24 values would be a second copy of the content. The scenarios the existing checks enforce here, in Gherkin:

```gherkin
Feature: Reference set v1 (COACH-6c; FR-170.R1, ADR 0061 Rules 1 and 3.3)

  Scenario: Wave A entries are refused while the catalogue has no comparison row for them
    Given content/references/pickleball/v1.json holds AN-05 and AN-07 entries
    And the pattern catalogue §1 has no AN-05 or AN-07 row
    When the coach runs "racket-reference-lint content/references"
    Then it exits with code 1
    And each AN-05 and AN-07 entry is named with field "pattern_id": "not a ranked pattern of the catalogue"

  Scenario: Every v1 entry is a labelled coach judgment that lints clean
    Given the catalogue §1 lists AN-05 and AN-07 (wilson, lower) and AN-04 with no interval method
    And every v1 entry has source_type "judgment", a resolved citation, a band, no n, status "coach-reviewed"
    And no entry has level band "pro"
    When the coach runs the lint and IT-06-01
    Then the lint prints "reference-lint: 1 version file(s), 0 problem(s)" and exits with code 0

  Scenario: AN-04 gets no reference entry
    Given AN-04 unforced errors per game has no interval method (ADR 0061 Rule 3.1)
    When an AN-04 entry is written
    Then the lint refuses it with field "interval_method"
    And AN-04 is shown as context with "no reference yet"; the AN-07 unforced-error share is compared instead
```

## 1. Decisions

| Date | Role | Decision | Evidence | Reason |
|---|---|---|---|---|
| 2026-11-13 | pickleball-domain-coach | **Every v1 entry is `source_type: judgment`**, with `label` "coach judgment, not measured from pro matches", a band and no n | `docs/domain/sources.md` §3: no `statistic` row is `resolved`; SRC-0012 `unresolved` | FR-170.R1, P22 (a) default; a `published` entry needs a resolved statistic (sources.md §1 rule 3) |
| 2026-11-13 | pickleball-domain-coach | **No `pro` entries and no text that says "pro"** apart from the label's "not measured from pro matches" | `grep -i pro content/references/pickleball/v1.json` (PR evidence) | A judgment value may not claim pro play (lint rule; catalogue §0.6) |
| 2026-11-13 | pickleball-domain-coach | **AN-04 has no entry** in v1; the catalogue §1 lists it as "context only" with `interval_method` none | ADR 0061 Rule 3.1; PE-6a decision "AN-04 not rankable as defined"; the lint refuses such an entry (ST-170a round 1) | The ticket names AN-04, but the ADR forbids a reference without an interval method. AN-04 per game is shown as context ("no reference yet"); the gap for unforced errors is the AN-07 unforced-error share. Adding a method for AN-04 needs a new ADR note (Rule 3.1) |
| 2026-11-13 | pickleball-domain-coach | **AN-07 references compare the unforced-error share** (`AN-07:unforced-error`, ST-171a), `lower` is better; the catalogue row id is `AN-07` because the lint accepts only `AN-nn` ids | catalogue §1 AN-07 row; `racket.sports.references.loader.parse_catalogue`; `quick_tag.py` `AN-07:unforced-error` | ADR 0061 Rule 3.1 recommendation. **For ST-172a / ST-170b:** the reference `AN-07` matches the measure `AN-07:unforced-error` only; the other three shares have no reference and are never ranked against these bands |
| 2026-11-13 | pickleball-domain-coach | **AN-05 and AN-07 rows added to catalogue §1** (QT, wilson, min_n 20, `lower`); definitions stay the metric dictionary's v0.1 (`coach-reviewed`); `definition_version` 0.1 | catalogue §1; metric dictionary §1 AN-05, AN-07 [SRC-0017] | The lint copies `better_direction` and `interval_method` from catalogue §1 (ST-170a); without the rows the wave A entries are refused (red run below) |
| 2026-11-13 | pickleball-domain-coach | **Citations:** each judgment entry cites the definition its band is set against: SRC-0017 (metric dictionary AN-05, AN-07) and SRC-0018 (catalogue AN-09, AN-13), both new `resolved` rows of kind `definition` | `docs/domain/sources.md` §2 | A judgment band has no statistic behind it; the citation says which quantity the band is about, and the label says it is judgment |
| 2026-11-13 | pickleball-domain-coach | **Set name `pickleball`** (`content/references/pickleball/v1.json`) | ADR 0061 Rule 1 ("`content/references/pickleball/` (planned)") | The ADR names the folder; the test fixtures' `pb-reference` is a fixture name only |
| 2026-11-13 | pickleball-domain-coach | **Singles bands:** AN-09 and AN-13 have their own, lower singles bands; AN-05 and AN-07 use the same band in both formats, each as its own entry | catalogue §2 "a singles band must not reuse a doubles band"; §0.6 "a doubles reference never applies to a singles match" | Drops and dink exchanges are rarer in singles (judgment); serve faults and unforced-error share have no format reason to differ that a source supports (judgment) |
| 2026-11-13 | pickleball-domain-coach | **Bands are wide on purpose** | ADR 0061 Rule 3.4 (non-overlap) and "Why non-overlap" | A judgment band with no n should flag only clear gaps; a narrow guessed band would call noise a weakness (PM6-M2) (judgment) |
| 2026-11-13 | pickleball-domain-coach | **Status `coach-reviewed`** on every entry: reviewed by the coach against the definitions SRC-0017 and SRC-0018 on 2026-11-13. `verified` needs a resolved statistic or measured footage and a second reviewer (ADR 0044) | v1.json | FR-170.R4: only `coach-reviewed` and `verified` entries are served |

### Band values (judgment, coach, 2026-11-13)

| Pattern | Direction | Format | beginner | intermediate | advanced |
|---|---|---|---|---|---|
| AN-05 serve fault share | lower | doubles, singles | 0.05-0.15 | 0.02-0.08 | 0.01-0.05 |
| AN-07 unforced-error share of rallies the side ended | lower | doubles, singles | 0.35-0.60 | 0.25-0.45 | 0.15-0.35 |
| AN-09 third-shot drop share | inside_band | doubles | 0.20-0.60 | 0.40-0.75 | 0.50-0.85 |
| AN-09 third-shot drop share | inside_band | singles | 0.05-0.40 | 0.10-0.45 | 0.10-0.50 |
| AN-13 dink tolerance (median own dinks before own dink error) | higher | doubles | 1-3 | 2-5 | 3-7 |
| AN-13 dink tolerance | higher | singles | 1-2 | 1-4 | 2-5 |

## 2. Red evidence

Commit "red" (v1 content, lock and the two register rows; catalogue §1 not yet changed):

```text
$ PYTHONPATH=backend/src python -m racket.sports.references.lint content/references --update-lock
FAIL pickleball/v1.json: REF-AN05-D-BEG: pattern_id: not a ranked pattern of the catalogue
... (one line per AN-05 and AN-07 entry, 12 in all)
FAIL pickleball/v1.json: REF-AN07-S-ADV: pattern_id: not a ranked pattern of the catalogue
reference-lint: 1 version file(s), 12 problem(s)
rc=1

$ cd backend && PYTHONPATH=src:. python -m pytest -q tests/integration/test_it_06_01_reference_lint.py
FAILED tests/integration/test_it_06_01_reference_lint.py::test_repository_reference_content_lints
1 failed, 31 passed
```

The AN-09 and AN-13 entries already lint clean; the 12 refusals are the wave A entries whose comparison rows the catalogue lacks (the right reason).

## 3. Not met: waiting on P-n

| Item | Waiting on | What the team prepares |
|---|---|---|
| A `published` reference value (a cited statistic) | P22 answer and a resolved `statistic` row (SRC-0012 unresolved; egress blocked) | the register row format (sources.md §1); the lint already accepts a published entry with k and n |
| A `measured` reference value from pro-match footage | P11 / OQ-06 licensed footage, ADR 0062 provenance export | nothing in v1 cites footage; the lint refuses `measured` until then |
| `verified` status for any entry | P15 second coach (ADR 0044) | the band table above for the second reviewer |
| FR-170.R2 in CI (base-lock job) | ticket CI-REF-BASE-LOCK (not a P-n item) | v1 is in `references.lock` |

## 4. Cost per PR (ADR 0056 decision 1)

| Round | wall_time_min | total_cost_usd |
|---|---|---|
| Author build | not measured | not measured (the session does not expose per-ticket wall time or cost to the agent) |
