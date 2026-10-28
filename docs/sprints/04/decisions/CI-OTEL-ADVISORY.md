# CI-OTEL-ADVISORY decisions

| # | Decision | Reason | Evidence |
|---|---|---|---|
| 1 | Upgrade `opentelemetry-api` 1.45.0 -> 1.45.1 in `backend/uv.lock` (`uv lock --upgrade-package opentelemetry-api`). uv moved `opentelemetry-sdk` to 1.45.1 and `opentelemetry-semantic-conventions` to 0.66b1 with it, as their pins require. | Advisory CVE-2026-114603 was published against opentelemetry-api 1.45.0. The strict `pip-audit (NFR-062)` step has failed every scheduled CI run on main since 2026-10-23 (latest: run 40666026362) with no code change. | Before: `opentelemetry-api 1.45.0 CVE-2026-114603 1.45.1`, exit 1. After: `No known vulnerabilities found`. Backend unit 2471 passed (includes tests/unit/platform/test_tracing.py); app and tracing import OK. |
| 2 | Keep the audit strict; no ignore entry. A daily audit job that opens these upgrade PRs before main goes red is being delivered separately (CI-DAILY-AUDIT). | NFR-062. This is the second advisory in a week (after certifi, #148). | n/a |
