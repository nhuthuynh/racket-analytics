# Sprint 5 review rounds

Every reviewer appends one row per finding under its own heading, with the disposition **Open**, as soon as it states the finding (ADR 0033 rule 1; ADR 0050 rule 5). Owners add a later row with the new disposition (Fixed with evidence, Deferred to a named backlog row, or Rejected with a reason). The engineering-manager writes the reconciliation row of each round before the next round starts (ADR 0037 rule 1, ADR 0047 rule 1). Ticket PRs may add ledger rows here (sprint-05.md, shared sprint files). G05-12 counts the open blocker/major rows: `python3 scripts/measure/open_defects.py docs/sprints/05/review-rounds.md`.

Created by the engineering-manager in the PR-policy decision for SEC-5 (PR #199), as CI-RECON-ON-PR row AF-CIRECON-02 asks: the first Sprint 5 PR that declares a blocker/major finding creates this file with its row.

## SEC-5 (PR #199): threat-note findings for the Sprint 5 stories (security-privacy-engineer, 2026-11-03)

Source: `docs/security/threat-notes-sprint-05.md` §7 and `docs/sprints/05/decisions/SEC-5.md`. These are design inputs that block their stories until met, not defects in the SEC-5 change. SEC-S5-TM-03 is "Should-fix" (minor) and is not ledgered here.

| Finding | Severity | Disposition | Owner (Sprint 5) | Waits on |
|---|---|---|---|---|
| SEC-S5-TM-01 | blocker | Open: ST-076a must stream `pg_dump` into the encryptor and test that no plaintext dump file exists after the run (T5-BK-1) | sre-devops-engineer (ST-076a) | ST-076a |
| SEC-S5-TM-02 | blocker | Open: PE-5b (ADR 0058) must decide backup expiry and deletion replay on restore, so a restore does not bring back deleted accounts (NFR-066, T5-BK-4) | principal-engineer (PE-5b), sre-devops-engineer (ST-076a, ST-076c) | PE-5b, ST-076a, ST-076c |

## COACH-5: domain findings for the Sprint 5 stories (pickleball-domain-coach, 2026-11-03)

Source: `docs/domain/drill-review-checklist.md` §3.1.1, `docs/domain/rc-copy-review.md`, `docs/domain/usability-drill-safety.md` and `docs/sprints/05/decisions/COACH-5.md`. COACH-S5-01 is the ledger row that kickoff item COACH-1 asks for. ST-081a reports the gap red, and ST-081b closes it.

| Finding | Severity | Disposition | Owner (Sprint 5) | Waits on |
|---|---|---|---|---|
| COACH-S5-01 | major | Open: "Not for me" can dead-end with `409 no_alternative` on a single-weakness plan, and in a session of 3 or more drills whose drills overlap. Each target × level × profile cell needs ≥ S + 1 swap-counted drills (3 for `solo+wall`, 30 min, each with `duration_min` ≤ 10 so it fits the smallest slot, QA-R2-1), which guarantees the **first** "Not for me" per target per plan, not later ones (swapped-out drills stay excluded plan-wide; checklist §3.1.1, PE-COACH5-1). It closes when ST-081a's check and ITs (first press swaps; press N − S + 1 answers 409 with the plan unchanged) and ST-081b's drills merge. On `main` at `8c37e98d`, 4 cells are short by one drill (AN-02, AN-04, AN-07:fault, AN-07:forced-error × intermediate × solo+wall) | senior-backend-engineer (ST-081a: check and swap ITs); pickleball-domain-coach (ST-081b: ≤ 6 drills) | ST-081a, ST-081b |
| COACH-S5-02 | minor | Open: the stats line "Definition version N, checked by our coach." reads as a human review next to the plan's "not yet checked by a human coach" (rc-copy-review R9) | principal-designer (words); senior-frontend-engineer (`web/src/lib/stats/view.ts` `versionLine`) | P15 answer (EM-ESC-05) |
| COACH-S5-04 | minor | Open: after COACH-S5-01 closes, the second "Not for me" for a target in a `solo+wall` plan with 3 drills of that target answers `409 no_alternative` (R10 copy, plan unchanged). Guaranteeing k presses needs S + k + 1 drills per cell (10 more drills for k = 2), or a planner or swap rule (checklist §3.1.1) | pickleball-domain-coach (drills), product-owner (whether more presses per plan matter for R1) | Sprint 6 refinement |
| COACH-S5-05 | major | Open: FR-124.R1 has no first-press qualifier and FR-141.R1 says "fewer than 2", while ST-081a's IT pins 409 on the second press of a single-weakness plan and its check needs S + 1 swap-counted drills (QA-R2-2). The business-analyst qualifies both rules before ST-081a is marked Ready (proposed text in `docs/sprints/05/decisions/COACH-5.md` §5); the engineering-manager puts the narrowing to the PO in Sprint 5 | business-analyst (rule text); engineering-manager (PO question) | ST-081a DoR; PO decision (Sprint 5) |
| COACH-S5-03 | minor | Open: `pb.drive.wall-margin@1` and `pb.return.wall-return@1` are solo wall drills with empty `safety_notes`. They are excluded from the usability sessions (class C) until a new version adds notes and is reviewed again (checklist §1 C5) | pickleball-domain-coach | the next drill PR (ST-081b if within its 6 drills, else a Sprint 6 drill ticket) |

## PD-DR04: shipped Sprint 4 screens against flows-sprint-04 (principal-designer, 2026-11-03)

Source: `docs/design/flows-sprint-04.md` §14.4 (chair's re-read; DR-04 not yet held). Found by reading the Sprint 4 decision files and `web/src`, not by a live walk.

| Finding | Severity | Disposition | Owner (Sprint 5) | Waits on |
|---|---|---|---|---|
| PD-DR04-01 | major | Open: R-01 has no shorter-retention confirmation dialog (flows-sprint-04 §6, HAX G16); shortening retention deletes videos within a day with no confirm. Needs PM words (PD-FL4-04) and an FE ticket before `feature_retention_setting` is on | product-manager (words), engineering-manager (ticket), senior-frontend-engineer (build) | PD-FL4-04 |
| PD-DR04-02 | minor | Open: A-12/A-13 (existing unconfirmed account answers "No") not built (ST-068b decisions row 8) | product-manager (PD-FL4-06 words), senior-frontend-engineer | PD-FL4-06 |
| PD-DR04-03 | minor | Open: no "Privacy settings" link on X-00 or the account menu (ST-071 deferred row (2)) | engineering-manager (ticket), senior-frontend-engineer | — |

## ST-078e (PR #218) round 1: web-origin answers left out of IT-05-08 (senior-frontend-engineer, 2026-11-05)

Source: PR #218 review round 1 (PE-078e-01 principal-engineer; F-1, ST-078e-R1) and `docs/sprints/05/decisions/ST-078e.md` D3, D4, D9. Ledger ids are upper-case forms (`open_defects.py` reads no lower-case letter in an id; the PR thread id is in brackets). The two gap rows stay Open until their fixes merge; G05-07's header line is not met while they are open.

| Finding | Severity | Disposition | Owner (Sprint 5) | Waits on |
|---|---|---|---|---|
| PE-078E-01 (thread `PE-078e-01`) | major | Fixed (round-1 fix commit on PR #218): exclusions stated in the IT docstring, traceability row and D9; gaps tracked as ST-078f/ST-078g (#221, #222) and probed red-first; EM and QA asks in D9 | senior-frontend-engineer | EM §15 rows, QA TCR row |
| ST078E-RV-1 (thread `F-1`) | major | Fixed: same fix as PE-078e-01 (`/api/healthz` and both media-route branches probed in `red_until` files, listed step in the E2E job) | senior-frontend-engineer | — |
| ST078E-RV-2 (thread `ST-078e-R1`) | major | Fixed: (a) #221, #222 opened and linked in D3, D4; (b) D3, D4, D9 and the IT docstring say G05-07 is not met until both merge; (c) `/api/healthz` is IT-05-08's red-first row for ST-078f | senior-frontend-engineer | — |
| ST078E-GAP-1 (`ST-078e-F1`) | major | Open: `/api/*` answers on the web origin carry no CSP (NFR-050.7); acceptance `test_it_05_08_api_csp.py` passes | senior-backend-engineer (ST-078f, #221) | ST-078f |
| ST078E-GAP-2 (`ST-078e-F2`) | major | Open: the media route sends no frame denial and its unsigned 403 no security headers (NFR-050.7); acceptance `test_it_05_08_media_route.py` passes | sre-devops-engineer (ST-078g, #222) | ST-078g |
