# 0023. Product-owner decisions 2026-10-05: accept all open-question recommendations

- **Status:** Accepted
- **Date:** 2026-10-05
- **Deciders:** human product owner (decision); product-manager (recorder); engineering-manager (A for log completeness, working-agreement §4)
- **Consulted:** business-analyst (author of `docs/requirements/open-questions.md`)
- **Related:** OQ-01..OQ-22; ADRs 0001, 0002, 0003, 0004, 0006, 0007, 0009, 0010, 0015, 0022; sprint-00 §10 (escalations); sprint-01 preconditions; `docs/sprints/00/sprint-report.md` §6

## Context and problem statement

`docs/requirements/open-questions.md` lists 22 questions for the human product owner (PO). Each has a team recommendation, and several gate Proposed ADRs and Sprint 1 planning preconditions (ADR 0002, 0007 and 0009 ratified; OQ-06 for fixture footage; OQ-17 for the browser matrix). Sprint 0 also asked the PO to ratify ADRs 0001 and 0022 and the ADR 0010 PO-time assumption (sprint-00 §10; sprint-report §9 step 10). On 2026-10-05 the PO replied, verbatim: **"accept all recommendations, repo created https://github.com/nhuthuynh/racket-analytics.git, push and start sprint 1"**. This ADR records what that answer decides, item by item, and what it cannot decide because it needs an input only the PO can supply.

## Decision drivers

- Escalation answers are recorded as ADRs (docs/decisions/README.md "Escalations"; working-agreement §8).
- An accepted recommendation that names an input the PO has not supplied (a file, a jurisdiction, an amount, people) cannot be treated as closed (judgment).
- Sprint 1 starts now; its preconditions must be checkable from the repo.

## Considered options

1. **Record one ADR listing every OQ with its accepted recommendation and its residual open part; flip the referenced Proposed ADRs to Accepted with a dated note** (chosen).
2. Write one ADR per OQ. Rejected: 22 near-identical ADRs, no extra information; the per-question detail already lives in `open-questions.md` (judgment).
3. Only add dated notes to the Proposed ADRs, no new ADR. Rejected: OQs with no ADR (OQ-01, 03, 05, 10-14, 16-22) would have no decision record, contrary to the README "Escalations" rule.

## Decision outcome

Chosen option: **1**. "Accept" below means the PO accepted the team recommendation exactly as written in `open-questions.md` on 2026-10-03.

| OQ | Accepted recommendation (short) | ADR effect | What remains open (owner) |
|---|---|---|---|
| OQ-01 | The PO supplies the 2026 USAP rulebook and change document; the coach records rule numbers in `docs/domain/rules-verified.md` | ADR 0009 Accepted | **PDFs not yet supplied** (human PO). Until then the only preset stays `PROVISIONAL-UNVERIFIED`, every provisional row stays `@needs-verification`, and R1 shows "unofficial scoring" (NFR-003). Latest need-by: Sprint 3 planning, 2026-11-16 (sprint-00 §10) |
| OQ-02 | MVP slicing: R1 walking skeleton on manual Quick Tag; R2 first automation plus LLM explanations; R3 automatic scoring; M6/M7 later | ADR 0002 Accepted; ADR 0007 Accepted | — |
| OQ-03 | USAP only for v1; other federations later as extra `RulesConfig` presets | none (recorded here) | — |
| OQ-04 | Rally scoring in R2, not R1; engine flag exists from R1; no preset with a guessed rotation (FR-043) | none | Rule verification (OQ-01) |
| OQ-05 | 18+ account holders (FR-003); capture guide asks not to upload matches with minors; beta in one PO-chosen jurisdiction; no real-user beta until a verified privacy/legal review is an ADR (NFR-070) | none | **Jurisdiction not yet named** (human PO). **Legal review before any real-user beta** (human PO with security-privacy-engineer). No real-user beta is planned, so this blocks nothing in Sprint 1 |
| OQ-06 | Training use is a separate opt-in, off by default and revocable (FR-009); Full Tag only on consented matches (FR-150); revoked consent leaves future gold-set versions; until the legal pass, gold and fixture footage only from team-recorded matches with written consent from everyone filmed | none | Legal pass (with OQ-05). Unblocks ST-025 for empty-court or consenting-team footage (Sprint 1 DoR P12) |
| OQ-07 | Retention defaults: original deleted 30 days after analysis; review video by user setting, default 90 days; abandoned uploads freed after 24 h; deleted match hidden in 1 min, purged in 7 days; re-processing after 30 days uses the 720p review video or is unavailable | ADR 0006 Accepted (interim) | Legal adequacy of every window (legal review, OQ-05) |
| OQ-08 | Rank weaknesses by rallies lost per game, split serve/receive | ADR 0003 Accepted | Coach verification of the underlying side-out rule (OQ-01) |
| OQ-09 | M2: rally-segmentation F1 ≥ 90% (±1.0 s, no merge/split). M3: ≤ 2.0 score-affecting corrections per game plus ≤ 5 confirmations, unflagged rallies ≥ 95% correct; ≤ 1.0 correction per game stays a later target | ADR 0004 Accepted | — |
| OQ-10 | Confidence as "Sure / Likely / Check this", raw % in a details view; band calibration is a model release gate (NFR-008) | none | — |
| OQ-11 | Calibration: confirm any ≥ 4 named court points, no dragging required (FR-082) | none | — |
| OQ-12 | MIT/Apache-only CV stack by default; Enterprise licence only if SPIKE-01 shows a measured gap; no AGPL without an ADR (NFR-062) | ADR 0015 Accepted | PE and security reviews of the SPIKE-01 evidence continue as ADR 0015 notes |
| OQ-13 | Set a monthly beta budget with alerts at 50/80/100% (NFR-022); analysed-minutes quota 180 min/month placeholder, reset to measured P75 after R1; 10 jobs/hour/user | none | **Budget amount not yet named** (human PO). Need-by: Sprint 2 review (sprint-00 §10) |
| OQ-14 | Fake-door freemium test in R1 (FR-162): manual Quick Tag and the plan free, automatic analysis paid; no payments in the MVP | none | Decide the model after MA-1/MA-2 data |
| OQ-15 | Opponent scouting: Won't for this MVP; gated on OQ-05/OQ-06; demand validated by a fake door | none | — |
| OQ-16 | Drop "height over the net" from v1 | none | — |
| OQ-17 | Reference profile: mid-range Android (~4 GB RAM), 4G throttled to 9/1.5 Mbps. Release-blocking browsers: iOS Safari and Android Chrome, current and previous major | none | WebKit/iOS runs in CI (ST-002 carry-over, SRE) |
| OQ-18 | "Resume on return" upload copy in R1 (FR-022); native wrapper decided after SPIKE-06 | none | SPIKE-06 result (Sprint 1, FE) |
| OQ-19 | English only in v1 | none | — |
| OQ-20 | Recruit ≥ 5 amateur testers, ≥ 8 interviewees, one second coach or 4.0+ player | none | **Recruitment is a PO action** (agents cannot recruit). Need-by: Sprint 3 planning |
| OQ-21 | Keep "racket-analytics" as the working name | none | — |
| OQ-22 | Coach multi-player view: Won't for the MVP; validate with 5 coach interviews after R2 | none | — |

Sprint 0 ratification items covered by the same answer:

| Item | Effect |
|---|---|
| ADR 0001 (ADRs and agent team) | Ratified: "pending ratification" removed |
| ADR 0007 (sequencing) | Accepted |
| ADR 0009 (rules-engine readiness split) | Accepted. ST-020a, ST-021a and ST-023 meet DoR P3 |
| ADR 0010 PO-time assumption (≈ 2 h per sprint review; escalation answers within 3 business days) | Confirmed by dated note |
| ADR 0022 (review-loop routing, smoke before review, one story per commit) | Not vetoed; Accepted without the Sprint-1-only limit |
| Repo admin (retro A1, QA-R3-02) | Remote created by the PO: `nhuthuynh/racket-analytics`. Branch protection on `ci-gate`, labels, the `ANTHROPIC_API_KEY` secret, a failing sample PR and 3 nightly runs are **not** evidenced by this answer and stay open (human PO with sre-devops-engineer) |

Not decided by this ADR: technical ADRs awaiting peer review rather than the PO (0005, 0012, 0013, 0014, 0016-0021). Their status is unchanged.

## Pros and cons of the options

### Option 1
- Good: one place that maps the PO's one-line answer to every question and ADR; residual open parts are explicit.
- Bad: a long table; the reader must open `open-questions.md` for the full reasoning.

### Option 2
- Good: each decision independently supersedable.
- Bad: 22 ADRs with the same evidence and decider; noise in the index (judgment).

### Option 3
- Good: smallest change.
- Bad: 16 OQs would have no ADR record.

## Consequences

- **Good:** Sprint 1 planning preconditions (ADR 0002, 0007, 0009 ratified) are met; the rules stories may start under the (a)/(b) split. OQ-06 lets ST-025 record empty-court or consenting-team footage.
- **Trade-offs accepted:** the PO accepted recommendations whose legal adequacy is unverified (OQ-05, 06, 07) [AQS G3.5]. This is acceptable only because no real-user beta happens before a recorded legal review (NFR-070).
- **Follow-up work:** the PO supplies the rulebook PDFs (OQ-01), names the jurisdiction (OQ-05) and the beta budget (OQ-13), recruits participants (OQ-20), and completes repo-admin setup (retro A1). The product-manager tracks these in `open-questions.md` and the Sprint 1 progress file.

## Evidence

| Claim | Evidence | Type |
|---|---|---|
| PO answer, verbatim | PO message 2026-10-05: "accept all recommendations, repo created https://github.com/nhuthuynh/racket-analytics.git, push and start sprint 1" | PO decision |
| The recommendations accepted | `docs/requirements/open-questions.md` (2026-10-03) Summary and Details | repo document |
| Rulebook still unverified; fetch 403 | [DOM G1, DOM Gaps 1]; ADR 0009 | research gap |
| Legal adequacy unverified | [AQS G3.5, AQS Gaps] | research gap |
| Escalations and need-by dates | `docs/sprints/sprint-00.md` §10 | repo document |
| Residual items need PO-only inputs (files, jurisdiction, amount, people) | (judgment) | judgment |

## Confirmation

- `open-questions.md` shows every OQ as Answered 2026-10-05, with the residual open part in its own column.
- ADRs 0001, 0002, 0003, 0004, 0006, 0007, 0009, 0015 and 0022 carry status Accepted and a 2026-10-05 note pointing here; ADR 0010 has the PO-time note.
- `docs/decisions/decision-log.md` indexes 0023 and the new statuses.
- `docs/sprints/01/status.json` lists the residual PO items as open.

## Notes

- **2026-10-05, later the same day (engineering-manager, folding `docs/requirements/po-input-2026-10-05.md`).** The decision above is not rewritten; this note adds the PO's later inputs.
  - **OQ-05:** the PO named the beta jurisdictions: **United States (US) and Australia (AU)**. The recommendation was one jurisdiction; the PO chose two. The "jurisdiction not yet named" part of the OQ-05 row is closed. Still open: the legal/privacy review before any real-user beta (NFR-070). It must cover both the US (including state privacy laws relevant to video and biometrics) and AU (Privacy Act 1988 / APPs). This also bounds the legal adequacy checks for OQ-06 and OQ-07 (ADR 0006).
  - **OQ-01:** the PO will upload the rulebook PDFs later. Unchanged: presets stay `PROVISIONAL-UNVERIFIED` and rows stay `@needs-verification` (ADR 0009). The need-by stays Sprint 3 planning, 2026-11-16.
  - **WebKit cookie fix (addendum to the PO input):** the PO directed https for the dev stack and ruled out an insecure-cookie flag. This is recorded in ADR 0029 (Accepted).
- **2026-10-06 (engineering-manager, Sprint 2 close, folding the 2026-10-06 addenda of `docs/requirements/po-input-2026-10-05.md`).** The decision above is not rewritten; this note records the PO's later inputs and where each one lives.
  - **Sprint 1 close, P1-P4:** P1 agents may push `sprint-*` branches (no force) and dispatch CI; branch protection on `main` stays with the PO. P2 ADR 0031 option 1 (Accepted, re-review before any real-user beta). P3 ST-025 carried, upload caps provisional until the PO's clips. P4 carry-over accepted; every open finding becomes a named backlog row.
  - **PR #1 path to green:** "merge with Sprint 2". The order is `sprint-02` → `sprint-01`, then PR #1 → `main`, each when its CI is green. The six WebKit failures were fixed test-first in Sprint 2 (CI WebKit green at `fd363fa`, run 37464553177). PR #1 is still open at the Sprint 2 close.
  - **Port the product to Go (with the clarification "no Python exception"):** everything moves to Go in **Sprint 6**, directly after the R1 release candidate (S5), including the API, domain, queue, workers, future CV inference, tooling, measurement and CI scripts. This supersedes the language part of ADR 0008. Release 2 moves by one sprint (old S6-S9 become S7-S10). Done means behaviour parity proven by the language-independent tests. The port ADR (options for model training in Go, with evidence) is the principal-engineer's at S6 planning. Roadmap §12 records the shift.
  - **P5 disk:** approved (prune below 10 GB free; agents may remove stale `racket-*` images of finished rounds).
  - **Footage that shows people:** never in git or Git LFS; it goes to a dedicated private object-store bucket (ADR 0006 retention and deletion). The provider is a PO decision and still open: **P11**.
  - **Repository visibility:** the orchestrator's correction says the repository is private. On 2026-10-06 GitHub's API reports `nhuthuynh/racket-analytics` as `"private": false`, `"visibility": "public"` (`search_repositories`, full output). The EM does not edit the verbatim PO record. The discrepancy is PO item **P10** (SEC-RV3-01): make the repository private, or confirm it is public so the record is corrected. Until then, nothing may depend on the repository being private.
  - **Still open:** P6 (screen-reader tester, 2026-11-13), P7 (rulebook, OQ-01, 2026-11-16), P8 (beta budget, OQ-13), P9 (testers, OQ-20), P10, P11.
