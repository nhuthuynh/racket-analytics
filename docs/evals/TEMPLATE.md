# {{title}}

<!-- Report template for scripts/eval/run_eval.py (ST-176a; NFR-006.7; ADR 0060). The harness
fills every double-brace field; a field it does not know fails the run (rc 2). Do not hand-edit a filled
report; re-run the harness. Owner: senior-ml-cv-engineer. -->

{{dry_run}}

## 1. Provenance

| Field | Value |
|---|---|
{{provenance}}

## 2. Cost (NFR-020 input; reported, not gated by ADR 0060)

| Field | Value |
|---|---|
{{cost}}

## 3. ADR 0060 rows

Baseline = the per-metric best accepted value on the same gold-set version (Rule 1). Verdicts:
`pass`, `fail`, `low sample` (fewer units than the minimum: the senior-ml-cv-engineer and the
senior-qa-engineer agree in the PR review), `n/a: no baseline` (first model of a stage),
`not measured`. M11 below its target also fails once a baseline has met it (Rule 2).

| ID | Metric | Unit, direction | Target | Tolerance | Min. units | Label | Candidate | Units | Baseline | Delta | Verdict | Target met |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
{{rows}}

## 4. Verdict

{{verdict}}

## 5. How to reproduce

`python3 scripts/eval/run_eval.py --candidate <run.json> --baseline <best.json> --clips <clip dir> --out docs/evals/<date>-<name>.md --date <date>`.
Inputs: the candidate run (`pipeline_version`, `gold_set` id and version, `weights` path or sha256
and licence, `config`, `metrics` with `value` and `units` per ADR 0060 row) and the per-metric best
accepted baseline on the same gold-set version. Exit 0 pass, 1 a row fails, 2 input error.
