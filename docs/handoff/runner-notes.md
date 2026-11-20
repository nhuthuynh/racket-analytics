STOPPED (PO 2026-11-14). Do not relaunch until the PO says go and #269 and #270 are merged. The runner refuses to start without args {po_go: '<date and PO words>'}; the relaunch notes below are the history of Run wf_51d7a44e-01d.

Run wf_51d7a44e-01d, relaunched 2026-11-13 ~05:20 UTC as task wehkfoxf0.
History: 04:3x the run hit the Workflow 1000-agent()-calls-per-invocation cap (cached replays count). Sprint 5 tickets phase
had finished (unmerged tickets -> no S5 verification/retro, per ADR 0055); Sprint 6 kickoff + plan done, PLAN-06 merged #241.
A resume of the Sprint-6-only args did NOT hit the cache (earlier prompts carry a harness-added remote-control taint suffix),
so the runner now embeds (line 15) a Sprint 6 'mode: tickets' entry: the 35 unmerged non-phase tickets from the cached S06 plan
(scratchpad/s06-plan.json), merged ones dropped (OPS-DISK-06 EM-ESC-06 PM-6 BA-6 PE-6a SEC-6 COACH-6a), open PRs passed as
existing_pr (CI-SCHEDULED-RED #242, PE-6b #247). Args JSON: scratchpad/run-args-2026-11-13-s06-tickets.json.
Relaunch (needs po_go from the PO, and the engineering-manager link pass on the embedded ticket list first; the embedded list has no links, so the runner refuses it as it stands): Workflow({scriptPath: '<scratchpad>/sprint-runner-v4.js', resumeFromRunId: 'wf_51d7a44e-01d', args: {po_go: '<date and PO words>'}})
(if the scratchpad copy is gone, copy the script from docs/handoff/sprint-runner-v4.md again).
If it hits the cap again: regenerate the tickets list (drop merged, set existing_pr for open) the same way, re-embed, relaunch.
TODO after S06 tickets: a closeout entry (mode 'closeout', ticket_results with merged flags) for S06 (smoke, verification, reflection, RETRO-06);
Sprint 5 closeout (verification/retro) still pending its unmerged tickets.

## 2026-11-15: STOPPED by the PO; new rules, runner changed (backups .bak-1114, .bak-1115)
- PO 2026-11-14: "STOP, WE KEEP FAILING, NEED TO FIND THE ROOT CAUSE AND FIX IT FIRST". RCA in scratchpad/sre-rca-ci.md.
- PO rules 2026-11-15 (verbatim in PR #270): ticket links (blocked_by, relates_to), start from latest main, CI passes before merge, principal-engineer monitors and fixes CI, reviews each ticket, no failures.
- Runner now:
  - pr-check is required before every push.
  - Circuit breaker: the same CI failure twice, or a policy failure twice, means blocked.
  - The plan schema requires blocked_by and relates_to.
  - External Blocked-by tickets must be verified merged.
  - The principal-engineer checks main CI before every wave; a red main means a CI-FIX ticket first (written by sre-devops-engineer).
  - The principal-engineer review lens refuses a red head.
- Before any restart:
  - #268, #269 and #270 must merge (human merge: the permission system blocks merges).
  - The remaining S06 tickets need blocked_by and relates_to filled in (EM re-link pass). The embedded list has depends_on only.
