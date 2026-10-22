# CI-CERTIFI-ADVISORY decisions

| # | Decision | Reason | Evidence |
|---|---|---|---|
| 1 | Upgrade `certifi` 2026.7.22 -> 2026.10.19 in `backend/uv.lock` and `infra/uv.lock` (`uv lock --upgrade-package certifi`); no other package moves. | Advisory PYSEC-2026-4320 was published against certifi 2026.7.22 after it was locked. The `pip-audit (NFR-062)` step runs `--strict`, so the nightly CI run on main (run 39570329619, 2026-10-21) went red with no code change. 2026.10.19 is the fixed version. | Before: `pip-audit --strict` -> `certifi 2026.7.22 PYSEC-2026-4320 2026.10.19`, exit 1. After: `No known vulnerabilities found`, exit 0. Backend unit 2471 passed; infra unit 1265 passed. |
| 2 | Keep the audit strict and blocking; no ignore entry. | NFR-062 needs known vulnerabilities fixed, not waived. A transitive CA bundle has no API change, so upgrading is the safe fix. | n/a |
