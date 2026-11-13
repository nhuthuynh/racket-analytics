# Pattern-source matrix (QT / FT / CV) and the §7.1 evidence each CV pattern needs

- **Owner:** senior-ml-cv-engineer (ML-6, Sprint 6, 2026-11-13), with the pickleball-domain-coach, who owns every pattern definition in `docs/domain/pattern-catalogue.md` and is asked to review this matrix on the ML-6 PR. Agreement is cited from the PR review, never inferred. Review tier 0 (ADR 0056).
- **Requirement:** SPK-1.1 (`docs/sprints/06/requirements-breakdown.md` §5): "each candidate pattern × source (QT, FT, new tag field, CV stage), measurable today yes/no, §7.1 evidence needed". Also FR-171.R5 (unavailable, never zero), NFR-006, NFR-062, roadmap §7.1.
- **Who uses it:** BA-6 (DoR of ST-171), ST-171b/c/d (extractors), ST-176a (eval harness report rows), ST-176b (CPU-only spike plans), COACH-6b (gold fixture GS-PAT-1), PD-6 (which patterns the slice shows), VERIFY-06.
- **Decision this file makes:** which patterns enter the Sprint 6 demo slice (§3). Everything else in it is evidence or a proposal; proposals that change a target or a schema need the ADR named in their row.

## 0. Terms

| Term | Meaning here |
|---|---|
| `QT` | Quick Tag fields per rally (FR-050): start, end, winning side, ending, optional responsible player, optional fault kind. No shot-level data |
| `FT` | Full Tag labels v1 (`docs/data/gold-label-schema.md` §4; ADR 0035): `hit` events with `hitter` and facets `contact`, `trajectory`, `intent`, `technique`; `bounce` events with `visible` and `court_xy_m` typed by the labeller in metres (`web/src/components/label/FullTag.tsx`, "Across"/"Along" fields). `position` is derived by rule and refused if labelled |
| new tag field | a field labels v1 does not have. Adding one changes ADR 0035 and the label API (tier 2 contract change); never proposed for Sprint 6 here |
| `CV` | a vision stage of spec §3. **None exists in the product on 2026-11-13**: `backend/src/racket/worker/stages.py` registers `probe` and `send_sign_in_link` only |
| measurable today | a user can create the input data in the local stack today (`make up`), so the pattern can be counted once its extractor exists. It says nothing about whether the extractor is built or the value is reliable |
| §7.1 evidence | the committed eval report the roadmap §7.1 gate needs at planning: a metric of NFR-006 (row `M<n> (ADR 0060)` with its minimum units), measured on the frozen, venue-split vision gold set QD-GD-04 (≥ 3 held-out venues, ≥ 20 % of clips double-labelled; `docs/data/gold-label-schema.md` §3) |

## 1. Matrix

One row per candidate pattern of the PO brief (third-shot drop vs drive, transition and kitchen-line arrival, dink tolerance, serve and return depth, stacking and partner spacing) plus the Quick Tag measures FR-171.R1 reuses and the QD patterns not yet in the catalogue. "Today" is the source usable now; "later" is a source that could replace or pre-fill it.

| Pattern | Name | Source today | Source later | Measurable today | Inputs it reads | §7.1 / gold evidence needed | Demo slice (§3) | Privacy tier |
|---|---|---|---|---|---|---|---|---|
| AN-01..AN-07 | Quick Tag starter stats | QT | CV-T09 rally segmentation and CV-T11 outcome pre-fill (R2) | yes | rally winner, ending, responsible player, fault kind | none for QT (hand count GS-AN-1, metric dictionary §2b, QD-AN-03 done). A CV pre-fill needs M11 (ADR 0060) ≥ 90 % before boundaries are pre-filled as fact (§7.1 S9 row) | yes (reuse, FR-171.R1) | 1 |
| AN-09 | Third-shot drop share | FT `trajectory` on hit 3 | CV: hit detection M5/M6 + shot classification CV-T10 + hitter from tracking M2 | yes | hit order, hitter, `trajectory` | FT: COACH-6b hand count on GS-PAT-1; `trajectory` has no admitted κ yet (QD-TX-03: κ ≥ 0.7 on n ≥ 300). CV: §2 rows E-HIT, E-SHOT, E-TRK | **yes (ST-171b, P0)** | 1 |
| AN-10 | Third-shot drop success | FT `trajectory`, `intent` on hits 3-4, bounce `court_xy_m` | CV: as AN-09 plus bounce M9/M10 and calibration M3/M4 | yes, when the labeller types bounce positions | as AN-09 plus bounce position | FT: as AN-09 plus §2 row E-LBL-XY. CV: E-HIT, E-SHOT, E-TRK, E-BNC, E-CAL | no (defined only; next wave) | 1 |
| AN-08 | Return depth | FT bounce `court_xy_m` after hit 2 | CV: bounce M9/M10 + calibration M3/M4 | yes, when the labeller types bounce positions | hit order, hitter, bounce position | FT: GS-PAT-1 hand count (COACH-6b, AN-08 "if labelled"); §2 row E-LBL-XY; court frame §4.1. CV: E-BNC, E-CAL, and E-PAT at the deep line | **stretch (ST-171d, P2)**, only after §4.1 and catalogue §10 Q2 are answered | 1 |
| SERVE-D | Serve depth (no AN id yet) | FT bounce `court_xy_m` after hit 1 | CV: as AN-08 | yes, as AN-08 | as AN-08 | as AN-08 | no (defined, not built; catalogue §4) | 1 |
| AN-13 | Dink tolerance | FT `trajectory` on every rally shot | CV: E-HIT and E-SHOT on every hit, not only hit 3 | yes | hit order, hitter, `trajectory`, ending | FT: COACH-6b hand count on GS-PAT-1; `trajectory` κ as AN-09. CV: E-HIT, E-SHOT, E-TRK; one missed hit splits a dink run, so hit recall matters more here than for AN-09 (judgment) | **yes (ST-171c, P0)** | 1 |
| AN-11 | Arrival at the NVZ (kitchen line) | CV only (player foot points at hit 5) | — | **no** | foot points of both serving players at the hit-5 frame; FT gives the frame | §7.1 S7 calibration and S7 tracking rows: E-CAL (M3, M4), E-TRK (M2 ≥ 65, CV-T04), plus **E-FOOT**, which NFR-006 does not have (§2) | no (needs CV (7.1)) | **2** |
| AN-12 | Lost in transition | CV only (hitter foot point at the hitter's last hit) | — | **no** | hitter foot point at a hit frame, rally loser | as AN-11; the transition-zone bounds (3.13 < d < 5.205 m) make E-FOOT error at the bounds decisive | no (needs CV (7.1)) | **2** |
| STACK | Stacking | CV only (both foot points vs centre line after S's first rally shot) | a new QT or FT field "stacked" per service turn would avoid CV (needs an ADR 0035 change; not proposed) | **no** | foot points, player identity across the turn | as AN-11, with CV-T04 identity errors ≤ 2 per game decisive: a swapped identity reads as a stack (judgment) | no (descriptive only; needs CV (7.1)) | **2** |
| SPACING | Partner spacing (AN-16) | CV only (lateral gap between partners per frame) | — | **no** | foot points of both partners per frame | as AN-11; per-rally counting unit (catalogue §9) | no (needs CV (7.1)) | **2** |
| AN-14 | Errors by facet × zone | FT facets; the zone needs player position (CV) | CV for the zone | facet part yes, zone part no | `trajectory`, ending, hitter position | not in catalogue v0.1; zone part as AN-12 | no (not catalogued) | 1 (facet part), 2 (zone) |
| AN-15 | Facet n-grams | FT facets | CV: E-SHOT | yes | facet sequences | not in catalogue v0.1; FT only | no (not catalogued) | 1 |
| POSE-* | Pose-derived (ready position, split step, paddle height) | none | CV pose (RTMPose ONNX, ST-176b spike plan) | **no** | body keypoints | no NFR-006 target exists for pose; needs E-POSE (§2) through a new ADR row before any story; weights and training-data licence per ADR 0015 | no (not catalogued) | **2** |

## 2. Evidence each CV source needs (§7.1)

Every row is measured on QD-GD-04 (frozen, venue-split), reported with ST-176a's harness in `docs/evals/` (planned) with dataset version, weights hash and config, and gated by ADR 0060's tolerance once a baseline exists. None can be measured in Sprint 6: no footage with rights or consent exists (P11/OQ-06), and the CPU-only spike plans (ST-176b) are written so they run the day footage lands.

| Id | What is measured | NFR-006 / ADR 0060 row and target | Minimum units | Spike | Patterns that need it |
|---|---|---|---|---|---|
| E-CAL | court calibration success; reprojection of court-line points | M3 (ADR 0060) ≥ 70 % of videos; M4 (ADR 0060) ≤ 15 cm RMS | 20 videos (SPIKE-07 plans ≥ 30) | SPIKE-07 (ST-176b) | AN-08, AN-10, AN-11, AN-12, STACK, SPACING |
| E-TRK | player tracking; identity errors after the confirm tap | M2 (ADR 0060) HOTA ≥ 65; CV-T04 ≤ 2 per game (ENG §5.4) | 3 clips | SPIKE-01 licence (ADR 0015 reviews still pending) | AN-09/AN-13 (hitter, CV path), AN-11, AN-12, STACK, SPACING |
| E-HIT | hit precision, recall, timing | M5, M6 (ADR 0060) ≥ 85 %; M7 ≤ 33 ms, M8 ≤ 100 ms | 500 labelled hits | SPIKE-05 (blocked on P11) | AN-09, AN-10, AN-13 (CV path); hit 5 frame for AN-11 |
| E-BNC | bounce recall; landing error | M9 (ADR 0060) ≥ 70 %; M10 (ADR 0060) p80 ≤ 60 cm | 300 labelled bounces | SPIKE-02 (blocked on P11) | AN-08, SERVE-D, AN-10 (CV path) |
| E-SHOT | coarse shot classification | CV-T10 macro-F1 ≥ 0.70 (ENG §5.4); **not an NFR-006 row and not in ADR 0060** | proposed: 300 classified hits per class with ≥ 3 venues (judgment) | none planned | AN-09, AN-10, AN-13, AN-15 (CV path) |
| E-FOOT | foot-point position on the court plane (bottom-centre of a player box through the homography) against labelled foot points | **none**: NFR-006 measures reprojection of court lines (M4), not of players. Proposed target p80 ≤ 30 cm, a third of AN-11's 1.0 m window (judgment) | proposed: 500 labelled foot points from ≥ 3 venues (judgment) | part of SPIKE-07 (ST-176b adds it) | AN-11, AN-12, STACK, SPACING |
| E-POSE | keypoint accuracy (PCK or OKS) on our footage | **none** | proposed in ST-176b's pose feasibility plan | pose spike (ST-176b) | POSE-* |
| E-PAT | pattern agreement: the pattern computed from CV outputs vs from FT gold labels on the same clips | **none**. Proposed: the CV value's Wilson interval overlaps the gold value's and the absolute difference ≤ 0.05 (judgment) | the pattern's min_n (catalogue §0.3) per held-out venue | none yet | every CV path; this is the gate a pattern needs, the stage metrics above are necessary, not sufficient (judgment) |

**Gaps that need an ADR before any CV pattern story can be Ready:** E-SHOT, E-FOOT, E-POSE and E-PAT have no NFR-006 target. Proposed owner: principal-engineer, as an ADR 0060 amendment (new rows with tolerance and minimum units), authored by the senior-ml-cv-engineer with ST-176b. Until then no CV pattern passes §7.1 even if every existing row passes (NFR-006: "no vision story is Ready on an unmeasured accuracy").

**Why E-FOOT matters (judgment, from the catalogue thresholds):** AN-11 counts a player "at the line" within 1.0 m behind the NVZ line; AN-12's transition zone ends 1.0 m behind it. A foot-point error of 30 cm moves a share of players across that boundary; at the 60 cm the bounce target allows, a player standing 0.5 m inside the window would read as "not arrived" often enough to bias AN-11 low. M4 (≤ 15 cm on court lines) does not bound this, because the box bottom is not a line point and occlusion moves it.

## 3. Demo slice decision (Sprint 6)

| Pattern | In the slice | Reason |
|---|---|---|
| AN-01..AN-07 | yes | QT, measurable and hand-counted (FR-171.R1) |
| AN-09 | yes (P0) | FT, measurable today, sprint P0 (ST-171b) |
| AN-13 | yes (P0) | FT, measurable today, sprint P0 (ST-171c) |
| AN-08 | stretch (P2) | FT, measurable today, but blocked on the court frame (§4.1) and the deep-line question (catalogue §10 Q2) |
| AN-10, SERVE-D, AN-14, AN-15 | no | defined only or not catalogued; FT positions have no agreement gate (§4.2) |
| AN-11, AN-12, STACK, SPACING, POSE-* | no | CV only; no stage exists, no footage (P11), and §2 gaps E-FOOT, E-PAT (and E-POSE) have no target. A match without the source reports them `unavailable` with reason `needs_cv`, never 0 (FR-171.R5) |

A pattern whose source is FT reports `unavailable` with `no_shot_facets` on a Quick Tag-only match (catalogue §0.2), so the demo seed (ST-174a) needs at least one Full Tag match per format shown.

## 4. Answers to the coach's questions (catalogue §10)

### 4.1 Q1: court frame of `court_xy_m`

- **Confirmed for labels v1:** the catalogue §0.7 convention: origin at the left corner of side A's baseline as seen from side A, x across (0..6.10 m), y along towards side B's baseline (0..13.41 m). A future homography stage maps into the same frame, so labels and CV outputs compare without a transform (E-BNC, E-PAT).
- **End switches:** the frame is side-A-relative **per rally**, not fixed to the camera. After an end switch the labeller must therefore mirror what they see. The label UI only says "Across"/"Along" and stores no end per rally, so a mirrored label is not detectable by `validate_labels`; it would land in the wrong half and be excluded from AN-08 as `not_in_play`, a silent bias. Recommendation (not a decision of this ticket): COACH-6b reports the `not_in_play` share per game of GS-PAT-1, and a later FE/BE ticket adds the frame's origin to the "Across"/"Along" hint. Changing the stored frame needs an ADR 0035 change.

### 4.2 Bounce positions typed by a labeller

`court_xy_m` is typed by eye, and labels v1 set no agreement gate for bounce position ("a gate for them needs an ADR", `docs/data/gold-label-schema.md` §3). **E-LBL-XY (proposed):** before AN-08 or AN-10 is shown on a real user's match as reliable, two labellers place the same ≥ 300 bounces and the p80 distance is ≤ 60 cm, the same bar as M10 (ADR 0060) for the model (judgment). Not needed for the synthetic demo data. Owner: senior-qa-engineer with the senior-ml-cv-engineer, as an amendment of ADR 0035.

### 4.3 Q4: a `hybrid` third-shot value

Not added (agrees with the catalogue default). A new facet value resets the `trajectory` agreement evidence (QD-TX-03 admits a facet on κ ≥ 0.7 at n ≥ 300), and no κ for `trajectory` exists yet. Revisit after the first double-labelled `trajectory` κ is measured (judgment).

## 5. Footage, licence and privacy constraints on the CV rows

- **Footage (P11/OQ-06):** every §2 row needs real footage: pro matches only where we hold the right to use them (no scraping of broadcast or YouTube content), training video only with every filmed player's consent (FR-174.R1-R2; ADR 0062 footage provenance (planned), PE-6b). Status: **not met: waiting on P11**. What the team prepares meanwhile: the ST-176a harness dry-run on `docs/data/phone-fixtures.md` clips, the ST-176b spike plans with cut-offs written before any run, this matrix, and the gold capture protocol `docs/data/gold-capture-protocol.md`.
- **Licence (NFR-062, ADR 0015):** MIT/Apache code only, no AGPL in the shipped graph (Ultralytics, BoxMOT excluded [DOM/CV-05, DOM/CV-07]); pretrained weights judged by their training data. Each spike records a licence row per artefact (ST-176b).
- **Privacy:** player tracks, foot points and pose keypoints are personal data: every CV pattern story and spike that stores them is tier 2 with the security-privacy-engineer (catalogue §6-§9; ADR 0056). No face recognition; identity is per match and user-assigned (spec §8).

## Changelog

| Date | Who | Change |
|---|---|---|
| 2026-11-13 | senior-ml-cv-engineer | v0.1 written with ML-6: matrix of 13 candidate rows, CV evidence rows E-CAL..E-PAT, demo slice decision, answers to catalogue §10 Q1 and Q4 |
