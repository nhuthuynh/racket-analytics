# Eval report 2026-11-13: dry-run-0 (DRY RUN)

<!-- Report template for scripts/eval/run_eval.py (ST-176a; NFR-006.7; ADR 0060). The harness
fills every double-brace field; a field it does not know fails the run (rc 2). Do not hand-edit a filled
report; re-run the harness. Owner: senior-ml-cv-engineer. -->

**DRY RUN:** the metric values are synthetic inputs that exercise the harness; no model and no gold-set footage exist (P11). Never cite them.

## 1. Provenance

| Field | Value |
|---|---|
| Candidate pipeline_version | dry-run-0 |
| Gold set | dry-run-synthetic v1 |
| Weights sha256 | none (no weights) |
| Weights licence | none (no model in the dry-run) |
| Config | `{"ball_px_threshold": 10, "rally_match_window_s": 1.0, "seed": 0}` |

## 2. Cost (NFR-020 input; reported, not gated by ADR 0060)

| Field | Value |
|---|---|
| Stage measured | FFmpeg decode of every clip (no model) |
| Clips decoded | 6 |
| Match-minutes | 0.200 |
| CPU-seconds | 4.767 |
| CPU-seconds per match-minute | 23.833 |

## 3. ADR 0060 rows

Baseline = the per-metric best accepted value on the same gold-set version (Rule 1). Verdicts:
`pass`, `fail`, `low sample` (fewer units than the minimum: the senior-ml-cv-engineer and the
senior-qa-engineer agree in the PR review), `n/a: no baseline` (first model of a stage),
`not measured`. M11 below its target also fails once a baseline has met it (Rule 2).

| ID | Metric | Unit, direction | Target | Tolerance | Min. units | Label | Candidate | Units | Baseline | Delta | Verdict | Target met |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| M1 | Ball F1 (10 px at 1080p) | %, higher is better | ≥ 80 | 1 | 2000 | capability | 79.50 | 2400 | 80.00 | -0.50 | pass | no |
| M2 | HOTA (4 players) | points, higher is better | ≥ 65 | 1 | 3 | capability | 62.40 | 3 | 62.00 | +0.40 | pass | no |
| M3 | Auto-calibration success | % videos, higher is better | ≥ 70 | 5 | 20 | capability | 70.00 | 20 | 70.00 | +0.00 | pass | yes |
| M4 | Reprojection error | cm RMS, lower is better | ≤ 15 | 1 | 20 | capability | 14.60 | 20 | 14.00 | +0.60 | pass | yes |
| M5 | Hit precision | %, higher is better | ≥ 85 | 1 | 500 | capability | 84.50 | 520 | 84.00 | +0.50 | pass | no |
| M6 | Hit recall | %, higher is better | ≥ 85 | 1 | 500 | capability | 82.20 | 520 | 83.00 | -0.80 | pass | no |
| M7 | Median hit-timing error | ms, lower is better | ≤ 33 | 3 | 500 | capability | 31.00 | 510 | 30.00 | +1.00 | pass | yes |
| M8 | p95 hit-timing error | ms, lower is better | ≤ 100 | 10 | 500 | capability | 99.00 | 510 | 95.00 | +4.00 | pass | yes |
| M9 | Bounce recall | %, higher is better | ≥ 70 | 2 | 300 | capability | 66.50 | 310 | 68.00 | -1.50 | pass | no |
| M10 | Landing error p80 | cm, lower is better | ≤ 60 | 3 | 300 | capability | 60.00 | 305 | 58.00 | +2.00 | pass | yes |
| M11 | Rally-segmentation F1 (ADR 0004) | %, higher is better | ≥ 90 | 1 | 100 | regression | 88.50 | 110 | 88.00 | +0.50 | pass | no |

## 4. Verdict

**rc 0: PASS.** Failing rows: none. Low sample (needs ML + QA agreement): none.

## 5. How to reproduce

`python3 scripts/eval/run_eval.py --candidate <run.json> --baseline <best.json> --clips <clip dir> --out docs/evals/<date>-<name>.md --date <date>`.
Inputs: the candidate run (`pipeline_version`, `gold_set` id and version, `weights` path or sha256
and licence, `config`, `metrics` with `value` and `units` per ADR 0060 row) and the per-metric best
accepted baseline on the same gold-set version. Exit 0 pass, 1 a row fails, 2 input error.
