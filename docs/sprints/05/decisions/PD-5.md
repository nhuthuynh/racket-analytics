# PD-5 decisions

Per-ticket decision file (working-agreement §3). Ticket: PD-5, gate for ST-083 (USAB-1.1) and design input to ST-075, ST-078e, ST-080, ST-082. Owner: principal-designer. Review tier 0 (ADR 0056: docs). Output: `docs/design/flows-sprint-05.md`.

## Decisions

| Date | Who | Decision | Evidence | Why |
|---|---|---|---|---|
| 2026-11-03 | principal-designer | **TDD does not apply**: the ticket adds design text and decisions, no executable behaviour. Doc checks run instead: `check_flows.py` (links, states rows, dated Opened columns), `check_docs.py` (paths, citations) | Commands and results in the PR body | sprint-05 §3.7 "docs, tier 0" |
| 2026-11-03 | principal-designer | **New screen family `N-` (N-01..N-06) and X-04**, not new ids in old families: the states appear on every route | flows-sprint-05 §0 | A-/Q- ids are taken (PD-4 precedent) |
| 2026-11-03 | principal-designer | **"Offline" only when the device is offline**; an online device that cannot reach the API sees N-02. The static `offline.html` covers both causes in one sentence because it cannot tell them apart | `web/public/sw.js` serves `offline.html` for every failed navigation; its words today send a signed-in player to sign in | Wrong cause leads to the wrong action (judgment) |
| 2026-11-03 | principal-designer | **No "your matches are safe" claim** in N-01 | ADR 0058 §6: a restore can undo up to 24 h of changes | Never claim more than the system knows |
| 2026-11-03 | principal-designer | **WCAG gap list covers all 55 A/AA SCs**, not only the 27 in the component checklist; no conformance claim anywhere, including the release notes | `grep -oE 'SC [0-9]\.[0-9]+\.[0-9]+' docs/design/component-accessibility-checklist.md \| sort -u \| wc -l` → 27; table rows 55 (31 A, 24 AA) | Kickoff PD-4; [ASB/RPD-08] |
| 2026-11-03 | principal-designer | **DR-05 cells scheduled, not written by the chair**: six decider rows "pending", Opened 2026-11-03, Due 2026-11-05. The PR stays draft until they are written, because PRC-3.4 makes `doc-check` fail on pending cells; the check is not changed | `check_docs.py --base origin/main --head HEAD` → 6 `FAIL cell` lines, one per pending decider; `ListAgents` → "No reachable agents" | ADR 0037 rule 2; CI-DOC-CHECK decision row 5 (decision row or PO waiver, never a change to the check) |
