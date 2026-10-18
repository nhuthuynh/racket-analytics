# VERIFY-04 decisions

Per-ticket decision file (PO rule 2026-10-07). Ticket: verification round(s) of the Sprint 4 goal on `main` (`goal-scorecard.md` §2, §7). Docs-only: no product code or test file changes, so the checks are the scorecard methods themselves, run as written.

| Date | Who | Decision | Evidence | Why |
|---|---|---|---|---|
| 2026-10-18 | senior-qa-engineer, sre-devops-engineer | **Round 1 at `3c4be05`: met 1 / 12.** Live rows not run are "no", never "n/a" | `goal-scorecard.md` §2 Actual/Met/Evidence columns and §7 | ADR 0014 (fail closed); scorecard §3 rule 3 |
| 2026-10-18 | sre-devops-engineer | **The verifiers did not restart the host Docker daemon and did not build images by a path other than `docker compose … up --build`** (SRE-V04R1-01) | `docker info` → `HTTPS Proxy: http://127.0.0.1:34223`, `Live Restore Enabled: false`; `docker ps` → other agents' `racket-analytics-*` containers running | A restart would stop other agents' stacks (scorecard §3 rule 1: never remove another agent's stack); a side-built image would not be the method's build |
| 2026-10-18 | senior-qa-engineer | **Non-Compose parts ran on `scripts/dev-postgres.sh` + `scripts/dev-objectstore.sh`** (no Mailpit, so 18 Mailpit tests skip and G04-11 (a) cannot be "0 skipped") | `3428 passed, 19 skipped, 22 deselected in 854.25s` | The working agreement names these scripts as the non-Compose services; the result is recorded as partial, not met |
| 2026-10-18 | senior-qa-engineer | **G04-12 (b): a PR passes when the principal-engineer and any one `senior-*` role APPROVE on the merged head**; for #98 (planned reviewer sre-devops-engineer) and #106 the passing senior role is named in the evidence | `merged_verdict.py` rc=0 for all 27 PRs | ADR 0039 rule 3 and the PO rule ask for "a senior engineer", which `merge_ready.py` counts as a `senior-*` role |
| 2026-10-18 | senior-qa-engineer | **The G03-11 form's nightly `--deselect` (used by §4 G04-11) is not used:** `-m "… and not nightly"` already excludes it (Sprint 3 note: remove once C3-05 merged) | backend run line above | No other test deselected than the two phone-fixture lines the Sprint 3 note allows |
