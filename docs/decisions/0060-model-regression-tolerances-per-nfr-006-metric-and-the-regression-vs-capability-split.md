# 0060. Model regression tolerances per NFR-006 metric, and the regression vs capability split

- **Status:** Accepted (senior-ml-cv-engineer, owner of the model-quality layer; tier 0 review per ADR 0056). The tolerance values are (judgment) until the first frozen gold-set baseline exists; the first baseline run reviews them and any change is a new ADR (Rule 4, `docs/decisions/README.md`).
- **Date:** 2026-11-05
- **Deciders:** senior-ml-cv-engineer
- **Consulted:** principal-engineer (tier 0 reviewer), senior-qa-engineer (gate owner, testing-strategy §6)
- **Related:** ticket ST-084a, story ST-084 (R2 entry is measurable, P2); NFR-006 and its atomic item NFR-006.5 (`docs/sprints/05/requirements-breakdown.md`); ST-084b (rally-F1 matcher, NFR-006.1-.4, depends on this ADR); NFR-006.6 (rally F1 on QD-GD-04, human item P11); ADR 0004 (rally matching rule), ADR 0005 (low-sample rule), ADR 0015 (CV licences), ADR 0056 (tier 0 review)

## Context and problem statement

NFR-006 lists the vision metrics measured at R2 entry on a frozen, venue-split gold set and says "regression tolerances set in an ADR before R2". testing-strategy §6 splits the model-quality layer into *regression evals* (pass at about 100 %, gate merges; "a metric may not drop by more than its tolerance") and *capability evals* (track progress to targets, do not gate merges), and ADR 0004 left the tolerances to this ADR. No tolerance and no split exists yet, so a model PR cannot be judged pass or fail, and the senior-ml-cv-engineer DoD item "no regression beyond tolerance on frozen gold sets" cannot be checked.

This ADR answers two questions for every NFR-006 metric: (1) how far may a candidate model drop against the accepted baseline before the model PR fails, and (2) is the metric's NFR-006 target a gate (regression label) or tracked only (capability label)? No model and no gold-set footage exist in Sprint 5 (footage waits on P11), so nothing is measured here; the ADR fixes the rules the first measurement will use.

## Decision drivers

- Capability evals start at a low pass rate; regression evals should pass at close to 100 % [ASB/ANT-17]; keep the two suites separate [EP/ENG-27].
- Evaluate on frozen, versioned gold sets; nobody edits a gold set to improve a score (testing-strategy §6) [EP/ENG-28].
- Every NFR must be measurable [DPA/DESIGN-16]; a tolerance with no unit or direction is not.
- A model PR must not be blocked by a target the pipeline has never reached; it must be blocked when it makes things worse (judgment).
- Tolerances are small next to the gap a target leaves, but not smaller than run-to-run noise on a small gold set (judgment; the noise is unknown until the first baseline).
- Metric definitions come from their reference implementations: HOTA from TrackEval [DOM/CV-08]; ball accuracy, precision, recall, F1 from TrackNetV3 with a documented pixel threshold [DOM/CV-01]; homography valid on the court plane only [DOM/CV-12].

## Considered options

1. **Do nothing:** keep "tolerances set in an ADR before R2" open and judge model PRs case by case.
2. **Absolute targets only:** every model PR must meet the NFR-006 targets; no baseline comparison.
3. **Zero tolerance:** every model PR must be at least as good as the baseline on every metric.
4. **Per-metric tolerance against the accepted baseline for every metric, plus a regression/capability label per metric target** (chosen).
5. **Statistical test per metric** (e.g. a paired bootstrap interval of the difference must exclude a drop larger than a margin).

## Decision outcome

Chosen option: **4**, because it is the only option that gates what a model PR changes (a drop against the baseline) without blocking work on targets nobody has met yet, and it is measurable today with fixed numbers. Option 5 is the better instrument once gold sets are large enough; it is kept as the follow-up below.

### Rule 1. The regression check (gates every model PR, every metric)

- **Baseline:** the metrics of the last accepted `pipeline_version`, run on the **same gold-set version** with the same config as the candidate. A new gold-set version is first run with the baseline model; a candidate is never compared across gold-set versions.
- **Pass:** for a higher-is-better metric, `candidate ≥ baseline − tolerance`; for a lower-is-better metric, `candidate ≤ baseline + tolerance`. A drop of exactly the tolerance passes.
- **Fail:** any one metric outside its tolerance fails the model PR. There is no averaging across metrics and no trade of one metric against another inside this check; a deliberate trade needs a new ADR that records it (judgment).
- **No baseline yet** (the first model of a stage): the check is "not applicable" for that stage, and the PR's eval report becomes the baseline when it merges.
- **Low sample:** when the gold set gives fewer units than the "Min. units" column, the result is reported as low sample and the PR needs the senior-ml-cv-engineer and senior-qa-engineer to agree in the PR review; it neither passes nor fails automatically (judgment, in the spirit of ADR 0005).
- **Determinism:** fixed seeds, pinned weights hash and config, recorded in the eval report (planned) under `docs/evals/` per the role DoD.

### Rule 2. The regression vs capability label (applies to the NFR-006 target)

- **Regression label:** the NFR-006 target is a gate. A model PR or release that falls below it fails, in addition to Rule 1.
- **Capability label:** the target is tracked and reported on each eval run; it does not gate merges. Rule 1 still gates.
- **Graduation:** a capability metric becomes regression-labelled when the baseline meets its NFR-006 target on the frozen gold set at a sprint eval run; the change is recorded as a dated note on this ADR. A metric never moves back from regression to capability without a new ADR (judgment).
- **Labels at R2 entry:** rally-segmentation F1 is regression-labelled, because NFR-006 makes it the R2 gate (spec M2, ADR 0004). Every other NFR-006 metric is capability-labelled, because NFR-006 calls them "R2 entry targets, reviewed at retro".

### Rule 3. Tolerances, direction and labels per NFR-006 metric

All values are (judgment) until the first baseline (see Confirmation). "pp" means percentage points on a 0-100 % scale.

| # | NFR-006 metric | Unit, direction | NFR-006 target | Regression tolerance (max drop vs baseline) | Min. units for an automatic verdict | Label at R2 entry | Reason for the tolerance (judgment unless cited) |
|---|---|---|---|---|---|---|---|
| M1 | Ball F1 (visible frames, centre within 10 px at 1920×1080) | %, higher is better | ≥ 80 % | 1.0 pp | 2 000 labelled frames | capability | Frame-level metric with many units; 1 pp is a fifth of a typical fine-tuning gain. Definition per [DOM/CV-01] |
| M2 | HOTA (4 on-court players) | HOTA points 0-100, higher is better | ≥ 65 | 1.0 point | 3 clips | capability | HOTA combines DetA and AssA [DOM/CV-08]; a 1-point drop usually means visible ID switches |
| M3 | Auto-calibration success rate (videos without fallback) | % of videos, higher is better | ≥ 70 % | 5.0 pp | 20 videos | capability | Per-video metric with few units: at 20 videos one video is 5 pp, so the tolerance allows at most one newly failing video |
| M4 | Reprojection error | cm RMS, lower is better | ≤ 15 cm | 1.0 cm | 20 videos | capability | Court-plane points only [DOM/CV-12]; 1 cm is under 7 % of the target |
| M5 | Hit precision | %, higher is better | ≥ 85 % | 1.0 pp | 500 labelled hits | capability | Event-level; reported apart from recall so a precision-for-recall trade is visible |
| M6 | Hit recall | %, higher is better | ≥ 85 % | 1.0 pp | 500 labelled hits | capability | As M5 |
| M7 | Median hit-timing error | ms, lower is better | ≤ 33 ms | 3 ms | 500 matched hits | capability | 33 ms is one frame at 30 fps; 3 ms is a tenth of a frame |
| M8 | p95 hit-timing error | ms, lower is better | ≤ 100 ms | 10 ms | 500 matched hits | capability | The tail is noisier than the median, so the tolerance is a tenth of the target |
| M9 | Bounce recall | %, higher is better | ≥ 70 % | 2.0 pp | 300 labelled bounces | capability | Fewer bounces than hits per match, so a wider tolerance than M5/M6 |
| M10 | Landing error p80 | cm, lower is better | ≤ 60 cm | 3 cm | 300 matched bounces | capability | 5 % of the target; court-plane metric [DOM/CV-12] |
| M11 | Rally-segmentation F1 (start and end each within ±1.0 s, no merge, no split; ADR 0004) | %, higher is better | ≥ 90 % (R2 gate) | 1.0 pp, and never below 90 % once met | 100 gold rallies | **regression** | The R2 gate (spec M2); the matcher is ST-084b (NFR-006.1-.4). Below 90 % the target fails the release even when Rule 1 passes |

The table has one row per NFR-006 metric: 11 rows for the 11 metrics in the NFR-006 "Metric" column (hit P/R and the two timing statistics each count separately, because each has its own target and direction).

### Out of scope

- NFR-008 (confidence-band calibration) already blocks a release that violates a band, so it needs no tolerance here.
- NFR-020 (GPU-seconds per match-minute) has its own target and alert; a cost tolerance is a follow-up ADR when the first throughput run exists.
- FPS (reported with ball metrics per [DOM/CV-01]) is reported, not gated; cost is gated by NFR-020.

## Pros and cons of the options

### Option 1: do nothing
- Good: no work now.
- Bad: model PRs have no pass/fail rule, which breaks the role DoD and testing-strategy §6; "before R2" becomes a last-minute decision under pressure.

### Option 2: absolute targets only
- Good: one rule, the one users care about.
- Bad: every early model PR fails, because no metric has met its target; people then waive the gate, and a real regression gets through with the waivers (judgment). It also ignores [ASB/ANT-17]: a capability eval is expected to start at a low pass rate.

### Option 3: zero tolerance
- Good: strict and simple.
- Bad: run-to-run noise on a small gold set (one video in M3 is 5 pp) fails PRs that changed nothing material; it pushes people to re-run until green (judgment).

### Option 4: per-metric tolerance plus labels (chosen)
- Good: blocks only real drops, keeps the R2 gate strict, and makes the capability work visible; every row has a unit, direction and number.
- Bad: the numbers are judgment until the first baseline, and a fixed tolerance ignores gold-set size beyond the "Min. units" floor.

### Option 5: statistical test per metric
- Good: separates real drops from noise and adapts to gold-set size.
- Bad: needs a resampling harness, per-metric unit definitions for resampling (frames, clips, rallies) and enough data, none of which exists before P11; harder for a reviewer to check by hand (judgment).

## Consequences

- Good: ST-084b can build the rally-F1 matcher against a fixed gate (M11), and every model PR from S6 has a pass/fail rule per metric.
- Good: the label table makes clear that only rally F1 gates R2; the other targets are reported at retro, as NFR-006 says.
- Bad / trade-offs accepted: the tolerances are judgment; they may be too loose or too tight until the first baseline shows the noise.
- Follow-up work: (a) the CI wiring of the regression eval waits for the first model (S7; kickoff item ML-2); (b) the first baseline run reviews every tolerance against measured run-to-run spread and either confirms it in a dated note or opens a new ADR; (c) a cost tolerance for NFR-020; (d) Option 5 once a gold set passes its "Min. units" by a wide margin.

## Evidence

| Claim | Evidence | Type |
|---|---|---|
| Capability evals start low; regression evals pass at close to 100 % | [ASB/ANT-17] | verified source |
| Keep regression and capability evals separate, on fixed labelled sets | [EP/ENG-27]; `docs/research/engineering-process.md` "Requirements (BA, PM)" | verified source |
| Never edit evaluation sets or tests to improve results | [EP/ENG-28]; testing-strategy §6 | verified source |
| HOTA, DetA, AssA from the TrackEval reference implementation | [DOM/CV-08] | verified source |
| Ball accuracy, precision, recall, F1 with a documented pixel threshold | [DOM/CV-01] | verified source |
| Homography valid only for court-plane points | [DOM/CV-12] | verified source |
| NFR-006 metrics, targets and "rally F1 is the R2 gate; others R2 entry targets" | `docs/requirements/non-functional-requirements.md` NFR-006 row | requirement |
| Rally matching rule (±1.0 s, no merge or split) | ADR 0004 | decision |
| Tolerance values, minimum units, graduation rule | (judgment) | judgment |
| No eval data yet; footage waits on P11 | `docs/sprints/05/goal-scorecard.md` row S5-P11 | not applicable (no model) |

## Confirmation

- NFR-006.5 doc check: the Rule 3 table has one row per NFR-006 metric, each with a tolerance and a label (checked in the ST-084a PR, `docs/sprints/05/decisions/ST-084a.md`).
- ST-084b's matcher reports rally F1 in the unit used by row M11.
- From the first model PR: its eval report shows candidate, baseline, delta and pass/fail per row, and the reviewer checks it against this table.
- The first baseline run (S7 at the earliest) reviews every tolerance and records the outcome as a dated note here.

## Notes
