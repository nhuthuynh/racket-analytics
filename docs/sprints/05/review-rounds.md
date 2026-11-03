# Sprint 5 review rounds

Every reviewer appends one row per finding under its own heading, with the disposition **Open**, as soon as it states the finding (ADR 0033 rule 1; ADR 0050 rule 5). Owners add a later row with the new disposition (Fixed with evidence, Deferred to a named backlog row, or Rejected with a reason). The engineering-manager writes the reconciliation row of each round before the next round starts (ADR 0037 rule 1, ADR 0047 rule 1). Ticket PRs may add ledger rows here (sprint-05.md, shared sprint files). G05-12 counts the open blocker/major rows: `python3 scripts/measure/open_defects.py docs/sprints/05/review-rounds.md`.

Created by the engineering-manager in the PR-policy decision for SEC-5 (PR #199), as CI-RECON-ON-PR row AF-CIRECON-02 asks: the first Sprint 5 PR that declares a blocker/major finding creates this file with its row.

## SEC-5 (PR #199): threat-note findings for the Sprint 5 stories (security-privacy-engineer, 2026-11-03)

Source: `docs/security/threat-notes-sprint-05.md` §7 and `docs/sprints/05/decisions/SEC-5.md`. These are design inputs that block their stories until met, not defects in the SEC-5 change. SEC-S5-TM-03 is "Should-fix" (minor) and is not ledgered here.

| Finding | Severity | Disposition | Owner (Sprint 5) | Waits on |
|---|---|---|---|---|
| SEC-S5-TM-01 | blocker | Open: ST-076a must stream `pg_dump` into the encryptor and test that no plaintext dump file exists after the run (T5-BK-1) | sre-devops-engineer (ST-076a) | ST-076a |
| SEC-S5-TM-02 | blocker | Open: PE-5b (ADR 0058) must decide backup expiry and deletion replay on restore, so a restore does not bring back deleted accounts (NFR-066, T5-BK-4) | principal-engineer (PE-5b), sre-devops-engineer (ST-076a, ST-076c) | PE-5b, ST-076a, ST-076c |

## PD-DR04: shipped Sprint 4 screens against flows-sprint-04 (principal-designer, 2026-11-03)

Source: `docs/design/flows-sprint-04.md` §14.4 (chair's re-read; DR-04 not yet held). Found by reading the Sprint 4 decision files and `web/src`, not by a live walk.

| Finding | Severity | Disposition | Owner (Sprint 5) | Waits on |
|---|---|---|---|---|
| PD-DR04-01 | major | Open: R-01 has no shorter-retention confirmation dialog (flows-sprint-04 §6, HAX G16); shortening retention deletes videos within a day with no confirm. Needs PM words (PD-FL4-04) and an FE ticket before `feature_retention_setting` is on | product-manager (words), engineering-manager (ticket), senior-frontend-engineer (build) | PD-FL4-04 |
| PD-DR04-02 | minor | Open: A-12/A-13 (existing unconfirmed account answers "No") not built (ST-068b decisions row 8) | product-manager (PD-FL4-06 words), senior-frontend-engineer | PD-FL4-06 |
| PD-DR04-03 | minor | Open: no "Privacy settings" link on X-00 or the account menu (ST-071 deferred row (2)) | engineering-manager (ticket), senior-frontend-engineer | — |
