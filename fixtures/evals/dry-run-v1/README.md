# dry-run-v1: synthetic eval-harness inputs (ST-176a)

Inputs for the `scripts/eval/run_eval.py` dry-run on `fixtures/clips/phone-profiles-v1`.
**The metric values are synthetic.** No model exists and no gold-set footage exists (P11 / OQ-06);
the values only exercise the ADR 0060 rules. Never cite them as a measurement.

| File | Purpose |
|---|---|
| `candidate.json` | dry-run candidate: every row within tolerance of the baseline (rc 0) |
| `baseline.json` | per-metric best accepted values on gold set `dry-run-synthetic` v1 |
| `planted-regression.json` | as `candidate.json` with M1 −1.5 pp (tolerance 1.0) and M7 +5 ms (tolerance 3): rc 1 |
