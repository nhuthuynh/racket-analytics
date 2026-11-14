# CI-FIX-OTEL-CVE: opentelemetry 1.45.2 for CVE-2026-126360

Owner: sre-devops-engineer (CI FIRST, bootstrap branch `s06/ci-fix-*`). Review tier 1.

## 1. Problem

The scheduled CI run on `main` 5956974 (2026-11-14) failed the step `pip-audit (NFR-062)`:

```
opentelemetry-api 1.45.1  CVE-2026-126360 1.45.2
```

No commit caused it: the advisory was published overnight. A red scheduled run blocks every merge
(`merge_ready.py`, CI-SCHEDULED-RED), and every PR's CI fails the same step until the lock moves.

The `Dependency audit` workflow produced the fix on `deps/security-audit` (4412bed4), but
`gh pr create` failed: the repository setting "Allow GitHub Actions to create and approve pull
requests" is off (docs/process/ci-cd.md 2.1). That branch name also has no owner in
`BOOTSTRAP_OWNERS` (`scripts/ci/review_tiers.py`), so it could not merge through `merge_ready.py`.
Both gaps are recorded as findings in the CI RCA of 2026-11-14 and are out of scope here.

## 2. Decision

Cherry-pick 4412bed4 onto a `s06/ci-fix-*` branch. `backend/uv.lock` only:

- opentelemetry-api 1.45.1 -> 1.45.2
- opentelemetry-sdk 1.45.1 -> 1.45.2
- opentelemetry-semantic-conventions 0.66b1 -> 0.66b2

TDD does not apply (lockfile only). The red/green evidence is the CI command itself.

## 3. Evidence

`uv export --color never --locked --no-dev --no-emit-project --format requirements-txt` then
`pip-audit --strict --requirement <file> --disable-pip`:

- origin/main 59569749: `opentelemetry-api 1.45.1 CVE-2026-126360 1.45.2`, exit 1 (red).
- this branch: `No known vulnerabilities found` (green).
- `make test-unit` on this branch: 2975 passed, 1 skipped.

## 4. Cost per PR (ADR 0056 decision 1)

| Round | wall_time_min | total_cost_usd | Note |
|---|---|---|---|
| Author build (red, green, checks) | not measured | not measured | the session does not expose per-ticket wall time or cost |
| Fix: add this decisions file (cost-table gate) | not measured | not measured | the first CI run failed `Cost per PR table`: the author ran pip-audit and the unit suite but not the pr-policy checks locally |
