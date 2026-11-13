# Sprint 6 requirements breakdown (atomic items)

- **Written:** 2026-11-13 at Sprint 6 planning (ticket PLAN-06) by the engineering-manager, from the business-analyst's kickoff breakdown advice and the per-role advice in [`kickoff.md`](kickoff.md). The business-analyst owns this file from here: ticket **BA-6** adds the new register rows (FR-170..FR-174), re-checks every row against the Definition of Ready and records the DoR verdict per story (§7).
- **Source of the new scope:** the PO instruction of 2026-11-12, quoted verbatim in `docs/requirements/po-input-2026-10-05.md`, addendum "Video analysis (PO 2026-11-12)". The **"..."** in the PO's list ("training, pro matches, ...") is not expanded by the team; it is question Q1 of EM-ESC-06 (§6, [NEEDS CLARIFICATION] A-Q1).
- **Rules applied:** `docs/process/definition-of-ready.md` "Atomic breakdown" [ASB/REQ-01, ASB/REQ-12, ASB/REQ-19, ASB/REQ-07]. One item = one observable behaviour **or** one measurable threshold, one data source, one owner. FR items are Gherkin `Rule:` lines `FR-nnn.Rk` with a happy and a negative Example. NFR items are numbered `NFR-nnn.<n>` under the existing register id and name characteristic, metric and unit, method (tool, configuration, data), target and test level. Process items use `PRC-<story>.<n>`, demo items `DEMO-6.<n>`, spike items `SPK-<n>.<k>`.
- **New register rows (DoR exception, BA kickoff "change" 1):** the DoR rule "no new register rows" covers breaking down existing FRs. The PO ordered new scope on 2026-11-12, so BA-6 adds **FR-170 reference pattern set, FR-171 player pattern measurement, FR-172 reference-gap ranking, FR-173 exercise recommendation with a cited Why, FR-174 footage provenance** to `docs/requirements/functional-requirements.md` with Source = the verbatim PO quote. FR-107 (AN-08..AN-14) and FR-108 are referenced, not stretched.
- **Id format** (`measurelib._FINDING_ID`, retro 4 M15): `<PREFIX>-<number>.<n>` or `FR-nnn.R<k>`. `check_atomic_breakdown.py` (QA-DOR-CHECK) parses this file in the `doc-check` job.
- **Data source axis (BA, BE, ML kickoff):** every pattern item names its source: **QT** (Quick Tag, fields that exist today, AN-01..AN-07), **FT** (manual Full Tag facets and events, `backend/src/racket/dataset/labels.py`: hit `trajectory` drive/drop/dink/lob, `intent`, hitter, bounce `court_xy_m`), or **CV** (a vision model). A Sprint 6 Ready item uses only QT or FT. A CV item is a spike item whose output is an eval report, never a Ready story (roadmap §7.1, NFR-006).
- **Verification data column (BA kickoff "change" 5):** synthetic fixture, Full Tag fixture (team-made or consented), licensed pro footage, consented training footage. A goal row met only on synthetic data says so in its Evidence cell; it never claims "measured from pro matches".
- **Test levels:** unit, property (Hypothesis), component (Vitest), integration (IT, boundary named), contract (`web/tests/contract`), E2E (Playwright project named), perf (Locust), doc-check, lint (a CI checker), eval (code grader over the plan eval set), human (a "not met: waiting on P-n" row; never an agent goal).
- **Status ladder for references (PM, COACH, BA kickoff):** `source_type` ∈ {`measured` (footage id with a rights record, n, interval, labeller), `published` (a citation that resolves), `judgment` (coach's own)}; `status` ∈ {`draft`, `coach-reviewed`, `verified`}. `verified` needs a human coach (P15) and cannot be reached this sprint.

## 1. FR rules

### FR-170 Reference pattern set (versioned, cited, provenance on every value) → story ST-170, tickets ST-170a/b/c, COACH-6c

Filter axes modelled: pattern id × level band × format (singles, doubles) × source_type × status.

```gherkin
Rule: FR-170.R1 A reference entry is accepted only with pattern id, definition version, better_direction (`higher`, `lower` or `inside_band`, copied from the pattern catalogue for that definition version), value or band, n, interval, level band, format, source_type, a source id that resolves (citation id or footage id with rights record), status and reference-set version
  Example: a complete coach-reviewed entry with a published citation → lint rc 0 (happy)
  Example: an entry with no source id → `racket-reference-lint` rc 1 naming the entry and the field "source" (negative)
  Example: an entry with no better_direction, or one that differs from the catalogue's value for its definition version → rc 1 naming the entry and the field "better_direction" (negative)
  Example: an entry with better_direction `inside_band` and a point value instead of a band → rc 1 naming the entry and "band" (negative)
Rule: FR-170.R2 A published reference-set version is immutable; a change is a new version with a new lock hash
  Example: v1 locked, v2 added with a changed value → lint rc 0 and both hashes in the lock (happy)
  Example: v1 edited in place → lint rc 1 "published version changed" (negative)
Rule: FR-170.R3 An entry whose source_type is measured carries a footage id whose provenance record permits the use "reference-library"
  Example: measured entry on owned footage with permitted use reference-library → rc 0 (happy)
  Example: measured entry on footage whose record permits only "analysis" → rc 1 naming the footage id (negative)
Rule: FR-170.R4 The reference read API returns only entries with status coach-reviewed or verified, each with its source_type, citation and version
  Example: set with 3 coach-reviewed and 1 draft entry → 3 entries returned (happy)
  Example: a draft entry is never returned, also not by id → 404 (negative)
Rule: FR-170.R5 Every reference value shown to a player carries its provenance label: "measured from licensed footage", "published source" or "coach judgment, not measured from pro matches"
  Example: entry with source_type judgment → the label "coach judgment, not measured from pro matches" is visible next to the value (happy)
  Example: an entry rendered without a provenance label → the component test fails (negative)
```

Test levels: R1-R3 unit + lint (CI); R4 integration (reference API boundary) + contract; R5 component + E2E. Domain truth: every value is `@needs-verification` until P15 (human coach).

### FR-171 Player pattern measurement from tags → story ST-171, tickets ST-171a..e

Filter axes: pattern × data source (QT, FT) × format × side (serving, receiving) × player.

```gherkin
Rule: FR-171.R1 A Quick Tag pattern measure reuses the AN-01..AN-07 computation unchanged and carries value, n, Wilson 95% interval with interval_method `wilson` (proportions only), low_sample flag and definition version
  Example: AN-05 serve fault % on GS-AN-1 gm1 equals the starter-stats value and n (happy)
  Example: a pattern measure whose value differs from the starter-stats value for the same match → the equivalence test fails (negative)
Rule: FR-171.R2 AN-09 third-shot drop share = third shots with trajectory drop / third shots with an admitted trajectory facet; the third shot is the serving side's first hit after the return
  Example: 10 rallies with a third shot, 6 drops, 4 drives → 0.60, n = 10 (happy)
  Example: a rally that ends before the 3rd hit is excluded and counted in n_excluded, never as a drive (negative)
Rule: FR-171.R3 A third shot with no trajectory facet is excluded and counted in n_excluded with reason facet_missing
  Example: 10 third shots, 2 without facet → n = 8, n_excluded = 2 (happy)
  Example: a missing facet counted as drive → the property test "excluded ∪ counted = all third shots" fails (negative)
Rule: FR-171.R4 AN-13 dink tolerance = number of consecutive dinks by the player's side before the side's dink error, per dink rally that ends in that error, reported as median, n of those rallies, n_censored (the side's dink rallies that ended any other way) and a 95% distribution-free order-statistic interval for the median, interval_method `order_statistic_median`: [x(l), x(n−l+1)] with l the largest rank where P(Binomial(n, 0.5) ≤ l−1) ≤ 0.025; below n = 6 the interval does not exist and the measure is not rankable (COACH-6a sets AN-13 min_n ≥ 6)
  Example: 10 error-ended dink rallies with runs 2, 3, 3, 4, 5, 5, 6, 7, 8, 10 → median 5, n = 10, l = 2, interval [3, 8] (happy)
  Example: runs 3, 5, 8 → median 5, n = 3, interval unavailable, rankable false, never a Wilson interval (negative)
  Example: a dink rally won by the side is counted in n_censored, never as a tolerance sample (negative)
Rule: FR-171.R5 A pattern that needs a data source the match does not have is reported unavailable with a reason, never as zero
  Example: a Quick Tag-only match → AN-09 unavailable, reason no_shot_facets (happy)
  Example: AN-09 reported as 0.0 on a Quick Tag-only match (negative)
Rule: FR-171.R6 Below the pattern's min_n the measure is flagged low_sample and is not rankable
  Example: AN-09 with n = 25 and min_n 20 → rankable (happy)
  Example: AN-09 with n = 7 → low_sample true, rankable false (negative)
Rule: FR-171.R7 AN-08 return depth = share of the receiving side's returns whose labelled bounce court_xy_m lies in the deepest third of the opponent half (stretch; FT only)
  Example: 12 returns with a labelled bounce, 5 deep → 5/12 (happy)
  Example: a return with no labelled bounce is excluded with reason bounce_missing (negative)
```

Test levels: R1 integration (analytics service boundary) + unit; R2-R4, R7 unit + property; R5-R6 unit + IT. Every definition is pinned by COACH-6b's `pattern_example.py --check` on gold fixture GS-PAT-1 (0 differences).

### FR-172 Reference-gap ranking (the weakness view) → story ST-172, tickets ST-172a/b/c

Filter axes: level band of the player vs reference band × format × n (below, at, above min_n) × interval overlap × number of gaps (0, 1, ≥ 3) × reference missing.

```gherkin
Rule: FR-172.R1 A pattern is a weakness only when the player's measure is rankable and its 95% interval (by the measure's interval_method) lies wholly on the worse side of the reference interval or band (no overlap). The worse side comes from the pattern's better_direction (FR-170.R1): `higher` → below the reference; `lower` → above it; `inside_band` → either side of the band (two-sided), and the weakness names the side ("below band" or "above band")
  Example: AN-09 (`inside_band`) player 0.20 [0.11, 0.33], reference band [0.45, 0.70] → weakness "below band" (happy)
  Example: AN-09 (`inside_band`) player 0.86 [0.80, 0.92], reference band [0.45, 0.70] → weakness "above band" (happy)
  Example: player [0.30, 0.55] overlaps reference [0.45, 0.70] → state "no clear gap", not ranked (negative)
  Example: a `higher` pattern with player [0.80, 0.92] above reference band [0.45, 0.70] → "no clear gap", never a weakness: the better side is not ranked (negative)
  Example: a `lower` pattern (AN-05 serve fault %) with player [0.12, 0.25] above reference [0.03, 0.08] → weakness "above reference" (happy)
Rule: FR-172.R2 A pattern with n below min_n is listed as "not enough data" with n and the min_n it needs, never ranked
  Example: n = 25, min_n 20 → eligible (happy)
  Example: n = 7 → "not enough data (7 of 20)" (negative)
Rule: FR-172.R3 A pattern with no coach-reviewed reference for the player's level band and format is listed as "no reference yet", never ranked
  Example: doubles reference present for band 3.0-3.5 → compared (happy)
  Example: only a pro-band reference exists for a 3.5 player → "no reference for your level" and the pro value shown as direction only (negative)
Rule: FR-172.R4 Weaknesses are ordered by gap size in reference-band widths (distance from the player's interval edge nearest the reference to the band edge on that side, divided by the band width; for a point reference the width is its 95% interval width); ties are broken by rallies lost on the linked ADR 0003 cell, then by catalogue order
  Example: gaps 1.4 and 0.6 band widths → order 1.4, 0.6 (happy)
  Example: two gaps of equal size → the one with more rallies lost first; reversing the input order gives the same output (negative, property test)
Rule: FR-172.R5 The view shows every pattern with its state; zero weaknesses shows "no clear gap against the reference" and the ADR 0003 rallies-lost ranking stays visible
  Example: 0 weaknesses → the message and the rallies-lost list (happy)
  Example: an empty page with neither message nor list (negative)
Rule: FR-172.R6 The weakness view API returns 404 for another player's match or player id
  Example: owner → 200 (happy)
  Example: another signed-in user → 404; anonymous → 401 (negative)
```

Test levels: R1-R4 unit + property (ranking deterministic and permutation-stable); R5 component + E2E; R6 integration (BOLA matrix row).

### FR-173 Exercise recommendation with a cited Why → story ST-173, tickets ST-173a..d

Exercise = a drill assignment from the existing library (assumption A1; no new aggregate). Filter axes: weakness pattern × level × players (1, 2, 4) × equipment (wall, no wall, ball machine) × safety class × number of weaknesses (1, 2, ≥ 3).

```gherkin
Rule: FR-173.R1 Each ranked weakness yields at least one library drill whose target_metrics contains the pattern's AN id and that fits players, equipment, level, time and safety class
  Example: AN-09 weakness, 2 players, no wall, level 3.5 → a drop drill for 2 players (happy)
  Example: no fitting drill → the plan line reads "no exercise yet for this gap", the API returns no_alternative for that gap and the coverage check reports the cell; a non-fitting drill is never offered (negative)
Rule: FR-173.R2 Each recommended drill's Why names the pattern id, the player's value, n and interval, the reference value, the reference id and version, and the reference status and provenance label
  Example: Why = "Third shot: drop 20% (n 25, 11-33%). Reference 45-70% (REF-AN09-D35 v1, coach-reviewed, coach judgment, not measured from pro matches)" (happy)
  Example: a Why missing the reference version → the plan validator rejects the plan line (negative)
Rule: FR-173.R3 The coverage check fails naming the cell when a rankable pattern × level × players × equipment cell has no fitting drill
  Example: current library + ST-173c drills → rc 0 (happy)
  Example: fixture without a solo-wall AN-13 drill → rc 1 naming that cell (negative)
Rule: FR-173.R4 A change of the reference version changes the Why text of the affected plan lines on the next plan generation and never silently rewrites an existing plan
  Example: reference v1 → v2 for AN-09, plan regenerated → Why cites v2 (happy)
  Example: an existing plan's Why changes without regeneration (negative)
```

Test levels: R1 integration (plan API boundary) + eval (pass^3 on new cases); R2 unit (validator) + eval grader; R3 unit + CI job; R4 integration.

### FR-174 Footage provenance (footage-ready preparation) → story ST-175, ticket ST-175a

```gherkin
Rule: FR-174.R1 An analysis job is created only for an asset with a provenance record whose rights basis is owned, licensed or consented and whose permitted uses include "analysis"
  Example: consented training clip with use analysis → job created (happy)
  Example: an asset with no provenance record → 422 provenance_missing and nothing is decoded (negative)
Rule: FR-174.R2 A provenance record of a training asset lists consent for every filmed person, or the asset is refused
  Example: 4 players, 4 consent references → accepted (happy)
  Example: 4 players, 3 consent references → 422 consent_incomplete (negative)
Rule: FR-174.R3 Revoking a consent removes the asset from the next reference-set version and deletes its derived pattern measures within the ADR 0006 window
  Example: revoke → next lint of the reference set fails while a measured entry still names the asset (happy)
  Example: derived measures still present after the window (negative)
```

Test levels: integration (job-creation boundary, tier 2), unit. Real footage supply is human (P11).

## 2. NFR items

### NFR-062 licences of the shipped graph, extended to weights and datasets → ticket ST-175b

Method for these items: the `sbom-licence` CI job extended by ST-175b over the worker image SBOM and `models/manifest.json` (planned; created by ST-175b).

| Id | Characteristic | Metric and unit | Target | Test level | Ticket | Scorecard |
|---|---|---|---|---|---|---|
| NFR-062.1 | licence of shipped packages incl. the worker image | AGPL-*, SSPL, non-commercial or unknown licences, count | 0; a planted AGPL package makes the job rc 1 (negative) | lint (CI) | ST-175b | G06-08 |
| NFR-062.2 | weights manifest completeness | manifest rows without licence or SHA-256, count | 0; a planted row without licence → rc 1 (negative) | lint (CI) | ST-175b | G06-08 |
| NFR-062.3 | no runtime model download | outbound model fetches by the worker under a network-denied test, count | 0 | integration | ST-175b | G06-08 |

### NFR-063 data classification of the new stored types → tickets ST-171e, ST-175a

| Id | Characteristic | Metric and unit | Method | Target | Test level | Ticket | Scorecard |
|---|---|---|---|---|---|---|---|
| NFR-063.3 | classification of pattern-measure snapshot columns | unclassified new columns, count | IT-05-05 extended (ORM metadata vs `docs/security/data-classification.md`) | 0; a planted unclassified column → red (negative) | integration | ST-171e | G06-08 |
| NFR-063.4 | classification of provenance records and pose artefacts | unclassified new columns or prefixes, count; pose and keypoint artefacts class High | IT-05-05 | 0; pose rows High | integration | ST-175a | G06-08 |

### NFR-075 reproducible outputs → tickets ST-171e, ST-172b

| Id | Characteristic | Metric and unit | Method | Target | Test level | Ticket | Scorecard |
|---|---|---|---|---|---|---|---|
| NFR-075.1 | stored gap results name their inputs | stored results without match version, rules_version, definition version or reference_version, count | IT over the snapshot table after `make demo` | 0 | integration | ST-171e | G06-03 |
| NFR-075.2 | golden replay | weakness-view JSON for GS-PAT-1 at a fixed reference version, two runs, byte diff | IT | identical | integration | ST-172b | G06-03 |

### NFR-010 read latency of the weakness view → ticket ST-172b

Common method for .10-.12: the NFR-010 Locust method of Sprint 5 (`locustfile_r1.py` with a `weakness-view` task added by ST-172b), 50 RPS open loop, achieved ≥ 49.5 RPS, 1 min warm-up excluded, 5 min window, Compose stack from `make up` with every FEATURE_* flag on incl. FEATURE_REFERENCE_PATTERNS, 3 runs.

| Id | Characteristic | Metric and unit | Target | Test level | Ticket | Scorecard |
|---|---|---|---|---|---|---|
| NFR-010.10 | latency, `GET /me/weaknesses` | p95 ms | ≤ 300 | perf | ST-172b | G06-06 |
| NFR-010.11 | latency, `GET /me/weaknesses` | p99 ms | ≤ 800 | perf | ST-172b | G06-06 |
| NFR-010.12 | read cost | SQL statements per read of an unchanged match (statement-count IT, the #232 pattern) | ≤ 4 | integration | ST-172b | G06-06 |

### NFR-027 / NFR-029 accessibility of the new screens → tickets ST-172c, ST-170c, ST-173d

| Id | Characteristic | Metric and unit | Method | Target | Test level | Ticket | Scorecard |
|---|---|---|---|---|---|---|---|
| NFR-027.10 | automated a11y, weakness view and reference browser | axe-core violations (serious and critical), count | `web/e2e/helpers/axe.ts` in the @critical journey on chromium, webkit, android-chrome | 0 | E2E | ST-174b | G06-07 |
| NFR-027.11 | non-text contrast of gap-chart marks and interval bars | contrast ratio against the background | `docs/design/tools/contrast_check.py` on the tokens the chart uses | ≥ 3:1 [DPA/DESIGN-04] | doc-check | ST-172c | G06-07 |
| NFR-027.12 | chart has a text equivalent | values in the chart vs values in its data table, mismatches | component test reading both | 0; the table missing → fail (negative) | component | ST-172c | G06-07 |
| NFR-027.13 | target size on new controls | controls smaller than 24 × 24 CSS px, count | E2E bounding-box scan | 0 [DPA/DESIGN-02] | E2E | ST-174b | G06-07 |
| NFR-027.14 | meaning not by colour alone | gap states shown only by colour, count | component test: each state has a text label | 0 | component | ST-172c | G06-07 |

### NFR-006 vision accuracy (footage-free preparation only) → story ST-176

| Id | Rule or item | Test level | Ticket |
|---|---|---|---|
| NFR-006.7 | The eval harness writes a report with candidate, baseline, delta and pass/fail per ADR 0060 row, gold-set version, weights hash and licence, config, CPU-seconds per match-minute; a planted regression beyond tolerance → rc 1 (negative) | unit + dry-run on phone fixtures | ST-176a |
| NFR-006.8 | Every CV pattern (kitchen-line arrival AN-11, transition AN-12, partner spacing AN-16, stacking) has a spike plan with dataset, n, venue split and pass/partial/fail cut-offs written before it runs | doc-check | ST-176b |
| NFR-006.9 | Calibration success and pose keypoint accuracy measured on licensed or consented footage | **human (P11 footage)**; no measurement this sprint | — |

### Privacy items (tier 2) → tickets ST-175a, ST-172b, SEC-6

| Id | Characteristic | Metric and unit | Method | Target | Test level | Ticket | Scorecard |
|---|---|---|---|---|---|---|---|
| NFR-066.10 | deletion covers derived pattern measures | pattern-measure rows left after match delete + purge window, count | IT in the deletion suite | 0 | integration | ST-171e | G06-08 |
| NFR-069.2 | pattern values and keypoints never in logs or metric labels | planted-value grep over API log and Prometheus labels after `make demo` | IT | 0 | integration | ST-172b | G06-08 |
| NFR-050.10 | BOLA on new routes | non-404 answers to a foreign id on every new ID-taking route, count | `tests/regression/test_bola_matrix.py` rows added per route | 0 | integration | ST-172b, ST-170b | G06-08 |
| NFR-050.11 | magic-link lifetime (ADR 0059 R-05) | `MAGIC_LINK_TTL_SECONDS` default, seconds | settings unit test + IT on an expired link | ≤ 600; a 601 s old link → 401 (negative) | integration | SEC-R05 | G06-09 |
| NFR-050.12 | upload checksum algorithms (ADR 0059 R-11) | tus `Upload-Checksum` algorithms accepted | contract IT | `sha256` only; `sha1` → 400 (negative) | integration | SEC-R11 | G06-09 |

## 3. Demo items (the PO's acceptance surface: `make up` + `make demo`)

| Id | Item | Test level | Ticket |
|---|---|---|---|
| DEMO-6.1 | `make demo` (twice, idempotent) seeds reference set v1, two demo players with Full Tag and Quick Tag matches and prints the URLs of the reference browser, the weakness view and the plan | integration (`infra/tests/test_seed_demo_plan.py` extended) | ST-174a |
| DEMO-6.2 | The two demo players get different top weaknesses and different recommended drills (negative: identical output fails, so a hard-coded slice cannot pass) | E2E (@critical) | ST-174b |
| DEMO-6.3 | A planted reference-set change (v1 → v2 for one pattern) changes the Why text of that plan line after regeneration | E2E | ST-174b |
| DEMO-6.4 | With FEATURE_REFERENCE_PATTERNS off, the R1 journey is unchanged and the new routes return 404 | E2E (flags-off project) | ST-174b |

## 4. Process items (ADR 0056 required tickets, retro 4 and kickoff actions)

| Id | Rule (one observable outcome) | Test level | Ticket |
|---|---|---|---|
| PRC-9.1 | A scheduled CI or Nightly quality run on `main` that ends red writes a line into the EM status record source (`scripts/measure/scheduled_red.py` (planned) output) and `merge_ready.py` refuses while the latest scheduled CI on `main` is red (negative: a planted red scheduled run → rc 1 naming its run id) | unit (`infra/tests/github_stub.py`) | CI-SCHEDULED-RED |
| PRC-10.1 | `merge_ready.py` classifies footage, provenance, pose, consent and pattern-snapshot paths as tier 2 and `content/references/**` as tier 1 with the pickleball-domain-coach specialist flag; tier 1-2 still need `Reviewer: senior-qa-engineer` APPROVE on the head (ADR 0056 required ticket a; negatives per path) | unit | CI-TIERS-06 |
| PRC-10.2 | Every new tier 2 glob matches a tracked path or is a `PENDING_GLOBS` entry naming its creating ticket (glob liveness) | unit | CI-TIERS-06 |
| PRC-11.1 | `doc-check` fails when a reference entry's citation id does not resolve to a row of `docs/domain/sources.md` (planned) (planned; COACH-6a) (ADR 0056 required ticket b: paths, citations, front matter, extended) | unit + CI | CI-DOC-CHECK-06 |
| PRC-11.2 | `doc-check` runs `docs/security/tools/check_threat_notes.py` on the newest `threat-notes-sprint-NN.md` | unit + CI | CI-DOC-CHECK-06 |
| PRC-11.3 | `pr-policy` fails a ready (non-draft) ticket PR whose `docs/sprints/<nn>/decisions/<ID>.md` has no cost-per-PR table (ADR 0056 decision 1; Sprint 5: 9 of 39 merged tickets had one) | unit + CI | CI-DOC-CHECK-06 |
| PRC-12.1 | `wip_gate.py` (planned) exits 1 naming the stage when a "start ticket" step would exceed in-progress 4, in-review 3, awaiting-QA 2 or awaiting-merge 1, from GitHub REST counts (negative: 3 PRs in review → a 4th start refused) | unit (stubbed REST) | QA-WIP-GATE |
| PRC-13.1 | `disk-precheck.sh` runs before every Compose build target in the Makefile, and `scripts/ops/worktree_report.py` (planned) lists every worktree under `/home/user/wt` with its branch's PR state (merged or closed → "remove") | unit + infra test | OPS-DISK-06 |
| PRC-14.1 | Every timed or thresholded method in `goal-scorecard.md` §4 is pinned by an infra test to the CI step or command it mirrors | unit (infra test) | QA-PIN-06 |

## 5. Spike items (output is an eval report or a plan, never a Ready story)

| Id | Item | Test level | Ticket |
|---|---|---|---|
| SPK-1.1 | Pattern-source matrix: each candidate pattern × source (QT, FT, new tag field, CV stage), measurable today yes/no, §7.1 evidence needed | doc-check | ML-6 |
| SPK-1.2 | Eval harness dry-run on `docs/data/phone-fixtures.md` clips rc 0 with a committed report under `docs/evals/` (planned) | eval | ST-176a |
| SPK-1.3 | CPU-only spike plans for SPIKE-07 calibration and a pose feasibility spike (RTMPose ONNX, Apache code; weights and dataset licence per ADR 0015) with cut-offs, runnable the day P11 footage lands | doc-check | ST-176b |

## 6. Assumptions and open questions (BA defaults for PM and PO review; ASB/REQ-07)

| Ref | Assumption or question | Default | Owner | Route |
|---|---|---|---|---|
| A1 | "Exercise" (PO) = a drill assignment from the existing library; no new aggregate | accepted by the team | BA, PE | ADR 0061 (PE-6a) |
| A2 | Reference values are level-banded; a pro-only value is shown as "direction", never as a target | coach default | COACH | COACH-6a |
| A3 | Full Tag stays labeller-only (FR-150); the demo player's Full Tag matches are seeded team-made fixtures, not the player's own labelling | default; a player-facing Full Tag needs a new FR and a PO decision | PM, BA | EM-ESC-06 Q4 |
| A4 | Pattern-gap ranking explains and orders the reference view; the ADR 0003 rallies-lost ranking stays the plan's primary ordering until ADR 0061 decides otherwise | default | PE | PE-6a |
| A5 | The reference set may cite published secondary statistics when the citation resolves | **[NEEDS CLARIFICATION]** | PO | EM-ESC-06 Q3 |
| A-Q1 | What the "..." in the PO's list ("training, pro matches, ...") covers | **[NEEDS CLARIFICATION]**; the team adds nothing | PO | EM-ESC-06 Q1 |
| A-Q2 | Sprint 6 = video analysis and the Go port moved to Sprint 7 (orchestrator note, not a PO decision; conflicts with "Port the product to Go (PO decision 2026-10-06)": "before any computer-vision work") | proceed with a CV-optional, tag-based slice that survives either answer | PO | EM-ESC-06 Q2 (P21) |
| A6 | min_n per new pattern = 20 opportunities (AN-07 rule 0.3 analogue), 95 % interval per the pattern's `interval_method` (`wilson` for proportions, FR-171.R1; `order_statistic_median` for AN-13, min_n ≥ 6, FR-171.R4) | coach + ML default (judgment) | COACH, ML | COACH-6a |

## 7. Definition of Ready verdict per story (BA-6, 2026-11-13 03:41Z, `origin/main` `91a58c78`)

Rule BA-1 (kickoff): a story is **Ready** only when every gate ticket is merged, named by its PR number, and E1 holds for wave 2 stories; there is no "Ready on condition". Gate PR states come from `gh api 'repos/nhuthuynh/racket-analytics/pulls?state=all&per_page=60'` at the time above: no PR exists yet for PE-6a, PE-6b, COACH-6a, COACH-6b, COACH-6c, SEC-6, PD-6, DR-06, ML-6, CI-TIERS-06 or CI-DOC-CHECK-06; EM-ESC-06 is #243 (open, draft), PM-6 #245 (open), CI-SCHEDULED-RED #242 (open), OPS-DISK-06 #244 (open). **E1 does not hold:** the 13 Sprint 5 PRs (#201, #218, #220, #224, #226, #230, #231, #232, #234, #235, #236, #238, #239) are open and VERIFY-05 and RETRO-05 are not merged. The orchestrator re-reads this table, and a gate ticket's PR adds its number here when it merges (BA-6 rule, as BA-5 in Sprint 5).

Atomic-breakdown items of the DoR, re-checked by BA-6 on every row of §1-§5: every FR rule has a happy and a negative Example; every NFR row names characteristic, metric and unit, method, target and test level; every id parses; `check_atomic_breakdown.py` rc 0. Register rows FR-170..FR-174 exist (BA-6). Glossary terms exist (BA-6). The footage provenance DoR line exists (BA-6). The "Gates" column below is what remains.

| Story | Atomic items | Gates (PR, state) | DoR verdict (BA-6) |
|---|---|---|---|
| ST-170 reference set | FR-170.R1-R5 | PE-6a (no PR), COACH-6a (no PR), SEC-6 (no PR), CI-TIERS-06 (no PR; after #231, open), DR-06 for ST-170c (no PR), E1 (not met) | **Not Ready**: waiting on PE-6a, COACH-6a, SEC-6, CI-TIERS-06, E1 |
| ST-171 player pattern measures | FR-171.R1-R7, NFR-063.3, NFR-066.10, NFR-075.1 | PE-6a (no PR), COACH-6a (no PR), COACH-6b (no PR; GS-PAT-1), SEC-6 for ST-171e (no PR), E1 (not met) | **Not Ready**: waiting on PE-6a, COACH-6a, COACH-6b, SEC-6, E1 |
| ST-172 weakness view | FR-172.R1-R6, NFR-010.10-.12, NFR-027.10-.14, NFR-050.10, NFR-069.2, NFR-075.2 | PE-6a (no PR), SEC-6 (no PR), PD-6 (no PR), DR-06 (no PR), E1 (not met) | **Not Ready**: waiting on PE-6a, SEC-6, PD-6, DR-06, E1 |
| ST-173 exercises | FR-173.R1-R4 | COACH-6a (no PR), ST-172a (not started), DR-06 for ST-173d (no PR), E1 (not met) | **Not Ready**: waiting on COACH-6a, ST-172a, E1 |
| ST-174 demo slice | DEMO-6.1-6.4, NFR-027.10, .13 | ST-172b, ST-173a, COACH-6c (none started) | **Not Ready**: waiting on the ST-172 and ST-173 build tickets and COACH-6c |
| ST-175 footage provenance and licence gate | FR-174.R1-R3, NFR-062.1-.3, NFR-063.4 | PE-6b (no PR), SEC-6 (no PR), E1 (not met); real footage is human (S6-P11), not a gate | **Not Ready**: waiting on PE-6b, SEC-6, E1 |
| ST-176 eval harness and spike plans | NFR-006.7-.8, SPK-1.1-1.3 | ML-6 (no PR), PE-6b for ST-176b (no PR), E1 for ST-176a (not met) | **Not Ready**: ST-176a waits on ML-6 and E1; ST-176b on ML-6 and PE-6b |
| PRC-06 | PRC-9.1 … PRC-14.1 | none (CI-TIERS-06 after #231; PRC-11.1 after COACH-6a) | **Ready** (CI-SCHEDULED-RED #242 and OPS-DISK-06 #244 in progress) |
| SEC-R | NFR-050.11-.12 | SEC-6 (no PR), E1 (not met) | **Not Ready**: waiting on SEC-6, E1 |

Open [NEEDS CLARIFICATION] items (§6 A5, A-Q1) do not block a story's mechanics: A5 affects only which citations COACH-6c may use (default applies until P22); A-Q1 adds no scope (the team adds nothing). A-Q2 (P21) is carried by EM-ESC-06 #243.

## 8. Three Amigos per story (business-analyst with pickleball-domain-coach, senior-ml-cv-engineer, senior-qa-engineer; BA-6)

One row per story: the question each amigo must answer before the story is Ready, and where the answer is recorded. The BA prepared the questions from the kickoff advice; each amigo's answer is their own review or gate PR, never written by the BA (rule BA5-PE-01 of Sprint 5: agreement is cited, not inferred). The senior-qa-engineer's test-level agreement for every item is requested in the review of this PR.

| Story | Domain coach | ML / CV | QA (testability, level) | Recorded in |
|---|---|---|---|---|
| ST-170 | Which patterns get a v1 entry per level band and format, and which source type each has (no "pro" without a pro source) | Does a `measured` entry need a footage id now? (No: none exists until S6-P11) | Is the lint refusal list complete (source, better_direction, band, rights, lock)? Unit + lint per refusal | COACH-6a, COACH-6c; QA review of ST-170a |
| ST-171 | Operational definition of AN-09 third shot and AN-13 dink run, with worked counts on GS-PAT-1 | Full Tag facets used (`trajectory`, hitter, bounce `court_xy_m`); interval methods (`wilson`, `order_statistic_median`) | Property "counted ∪ excluded = all"; QA recount of one match by hand | COACH-6a, COACH-6b; ML review of ST-171b/c |
| ST-172 | Level bands; pro-only value shown as direction (A2) | n per pattern on demo data vs min_n | Numeric Examples per state; permutation-stable property; BOLA row | PE-6a (A4); QA-REF-GOLD |
| ST-173 | Drills for AN-09 and AN-13 per players and equipment, safety class | — | Why validator rejects each missing part; coverage cell named | ST-173b, ST-173c; eval cases in ST-173a |
| ST-174 | Demo players differ for a coaching reason, not by fixture trick | — | DEMO-6.2 negative: identical output fails | ST-174b |
| ST-175 | — | Which artefacts (clips, keypoints, weights) need a record | Refusal codes `provenance_missing`, `consent_incomplete`; tier 2 | PE-6b, SEC-6; ST-175a |
| ST-176 | — | Spike cut-offs written before runs; dataset licence per ADR 0015 | Planted regression → rc 1 | ML-6, ST-176b |
