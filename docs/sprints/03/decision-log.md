# Sprint 3 decision log

Small decisions, one dated row each (who, decision, evidence, reasoning). Append only; do not rewrite other rows.
Significant decisions go to `docs/decisions/` as ADRs.

| Date | Who | Decision | Evidence | Reasoning |
|---|---|---|---|---|
| 2026-10-08 | senior-qa-engineer | **CI-FLAKE-RESUMABLE: the E2E-01 "Return after closing the tab" failure (CI run 37715576115) is a race in the spec's wait logic, not a product bug. Fixed in the spec (TCR row of this date): the tab closes while a held-back chunk is unsent, so the upload is unfinished by construction. No timeout bump, no retry, no quarantine** | Reproduced on the Compose stack in Chromium (`--repeat-each=20` at `259a0a8` → 1 failed, 19 passed; trace: final PATCH in flight at `page.close()`, server finished the upload, list shows "Video received"). Fix: see the PR's test evidence (`--repeat-each=20` locally and in CI, `flaky_report.py --fail-on-flaky` rc=0) | Product behaviour is right: a user who closes the tab after the last byte has reached the server has no unfinished upload, so no banner is due. A longer `toBeVisible` timeout cannot help (the banner never comes), and slowing every chunk (as E2E-01-02 does) still leaves the close-vs-last-chunk race; holding one chunk removes it. The same race sat in "A different file is chosen to resume" (QA-V1-02 settled only the offset), so it gets the same hold |
