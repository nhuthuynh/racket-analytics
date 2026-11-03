# Sprint 5 PO escalation note (EM-ESC-05)

- **To:** the human product owner (PO). **From:** engineering-manager. **Sent:** 2026-11-03, before the 2026-11-05 deadline in `docs/sprints/sprint-05.md` §3.6 (Wave 1).
- **Why one note:** working-agreement §8 says the EM escalates with the question, options, recommendation, evidence and deadline. Kickoff PM-6 and COACH-4 (`docs/sprints/05/kickoff.md` §2) asked for a single list with need-by dates and defaults. Risk RM-12 (holiday PO availability, sprint-05 §10) asks for every escalation to be out by 2026-11-05.
- **Status:** team text (ADR 0047). **None of the defaults below is a PO decision.** A default is only what the team does while there is no answer. It never changes a milestone "Done when", spends money, waives a review or accepts a risk on the PO's behalf. Answers count only when they are quoted verbatim in `docs/requirements/po-input-2026-10-05.md`.
- **Until an item is answered**, agents work only on what does not depend on it (working-agreement §8). Human-only items stay as "not met: waiting on P-n" rows in `docs/sprints/05/goal-scorecard.md` §5 (PO P12 option b, 2026-10-07).

## 1. Summary: what we need from you, by date

The quickest way to reply is one line per item, for example "E1: a; E3: a; P7: b". The `#` column is the id to answer with.

| # | Question (short) | Recommended | Default if no answer | Deadline |
|---|---|---|---|---|
| D1 | DR-04 on the shipped Sprint 4 screens: hold it or waive it? (PD-DR04) | a: hold | not held; the gaps stay Open | **2026-11-05** |
| E1 | Change the S5 "Done when" to the agent-measurable goal? | a | roadmap unchanged; S5 judged against sprint-05 §1 and reported as such | **2026-11-10** |
| E2 | Accept the Product Goal wording (PM-5)? | a: accept | stays team text (draft) | 2026-11-10 |
| E3 | FR-162 pricing fake door: R2, S5 stretch, or drop? (PM-5) | A: R2 | nothing built; stays Could | 2026-11-10 |
| A12 | Which "plan and brainstorm skills" did you mean? | a | (a), already used at S5 planning | 2026-11-10 |
| A13 | Deny rules plus a merge hook? | a | no settings change; role-file rule and `merge_ready.py` only | 2026-11-10 |
| A14 | Add a commands-only `CLAUDE.md`? | a: yes | no file | 2026-11-10 |
| A15 | Is the sprint goal one sentence or a bullet list? | a: one sentence plus bullet scorecard | (a) as in working-agreement §3; EM role file unchanged | 2026-11-10 |
| SZ | Should drill JSON count towards the 400-line PR size limit? | a: keep counting, revisit at RETRO-05 | (a): it counts (ADR 0054 as written) | 2026-11-10 |
| S6 | Admin setting 6 (ADR 0053 draft upgrade PR) | a: tick it | nothing; the upgrade job goes red when it has a fix to open | 2026-11-10 |
| P7 | Rulebook, or accept "R1 ships unofficial scoring" | b: accept the fallback for R1 | stays unofficial; S5-P7 not met | **2026-11-10** |
| P15 | Human coach review of drills, or accept `coach-reviewed` for R1 | b: accept the fallback for R1 | stays `coach-reviewed`; S5-P15 not met | **2026-11-10** |
| P8 | Budgets, storage quota, GPU (OQ-13) | a: give values | interim settings; no paid spend | **2026-11-10** |
| P17 | SLO commitment and error-budget policy | a: accept the ST-075c drafts | drafts are internal targets only | **2026-11-12** |
| P19 | Residual-risk ADR | a: review and decide | ADR stays Proposed; no real users | **2026-11-12** |
| P16 | Legal review (NFR-070, US + AU), incl. tester footage | a: commission now | flags stay off for real users; no tester footage kept | before the usability session and any real user |
| P9 | ≥ 5 usability testers | a: book them | S5-P9 not met; R1 effort unmeasured | testers booked by **2026-12-16** |
| P20 | Real-device iOS Safari and Android Chrome check | a: with the P9 testers | emulation only; S5-P20 not met | **2026-12-16** |
| P6 | Screen-reader pass | a: one tester | no screen-reader claim in the release notes | **overdue**; now 2026-12-16 |
| P10 | Repository visibility | a: confirm public | stays public; nothing private in git | sooner is safer |
| P11 | Footage bucket and consented footage | a: choose a provider | R2 spikes stay unplanned | S7 planning |
| P18 | R1 release-candidate sign-off | decide at the review | no release | sprint review **2026-12-22** |

Items PD-DR04 (D1) and the S5 "Done when" (E1) have the most effect on this sprint. P7, P15 and P8 come next, because their fallbacks shape the release notes that ST-082 writes.

## 2. Decisions that change this sprint's scope or gates

### D1. DR-04 never held: hold it now or waive it (PD-DR04)

The principal-designer (chair) wrote this request in PR #200, `docs/design/flows-sprint-04.md` §14.5. That PR is not merged yet. The EM carries the request here unchanged, because the chair does not write this file.

- **Question:** design review DR-04 was never held, and the Sprint 4 UI shipped anyway. Do we hold DR-04 on the shipped screens, or do you record a waiver?
- **Options:**
  - (a) **Hold.** The orchestrator invokes the five decider roles with the §14.4 brief by 2026-11-05. The chair records "held" once `check_flows.py … --decider <all five>` exits 0, and every reject becomes a ledger row.
  - (b) **Waive.** You record in `docs/requirements/po-input-2026-10-05.md` that DR-04 is waived for the shipped Sprint 4 screens. The three §14.4 gaps stay Open in the ledger with their owners, and DR-05 (PD-5) is held before its UI starts.
  - (c) **Wait until after Sprint 5.** Not recommended, because it repeats retro-04 M5.
- **Recommendation:** (a). All five deciders are agent roles, so a hold costs five short invocations. Choose (b) only if a cell is still empty at the deadline.
- **Default if no answer:** the team does **not** assume a waiver. DR-04 stays "not held", and the gaps PD-DR04-01 (major: no confirmation before a shorter retention period deletes videos), PD-DR04-02 and PD-DR04-03 (minor) stay Open.
- **Evidence:** PR #200, `docs/design/flows-sprint-04.md` §14.2-§14.5 on that branch; `docs/retros/2026-12-11-sprint-04.md` M5.
- **Deadline:** 2026-11-05.

### E1. The S5 "Done when" change

- **Question:** roadmap §5 says S5 is done when there has been a moderated usability test with ≥ 5 players, SLOs and alerts, a restore drill, an ASVS L2 review, performance gates, a browser matrix, an R1 release candidate for your sign-off, and R2 spike ADRs. Several of these depend on you: the testers (P9), the sign-off (P18), and the footage and GPU behind the spikes (P11, P8). Agents cannot finish those parts. Do we change this "Done when"?
- **Options:**
  - (a) **Change it** to the sprint-05 §1 goal: "R1 is a release candidate whose agent-measurable release gates are each proven live on the local stack, and every human gate has a ready kit and a dated PO ask." The usability test (P9) and the sign-off (P18) move to the **R1 release** Definition of Done. The R2 spike ADRs move to S7 planning (P11, P8).
  - (b) **Keep it.** Sprint 5 is then reported as not met for as long as P9, P18, P11 or P8 is open, whatever the agents deliver.
  - (c) **Keep it and extend S5** past the holidays until the usability test can run. Sprint 6 (the Go port) moves back by the same time.
- **Recommendation:** (a). Since your P12 rule (option b, 2026-10-07), human-only items are no longer counted in sprint goals. Option (a) makes the roadmap say what the sprints already do. (b) would put a goal in place that agents cannot meet, which is the retro-02 M3 pattern.
- **Default if no answer:** roadmap §5 is **not** edited. Sprint 5 is planned and measured against sprint-05 §1, as already planned. The sprint report states that the roadmap S5 "Done when" is unchanged and waiting on you, with the human parts reported as S5-P9, S5-P18, S5-P11 and S5-P8.
- **Evidence:** `docs/sprints/roadmap.md` §5 row S5 and the header "Status" line of §"Product Goal"; `docs/sprints/05/decisions/PM-5.md` §1 row 2 and §5; kickoff PM-2; sprint-05 §10, first risk row; `docs/requirements/po-input-2026-10-05.md` addendum "Sprint 3 PO list P12".
- **Deadline:** 2026-11-10. That gives RETRO-05 and the sprint report a settled target.

### E2. Product Goal wording (PM-5)

- **Question:** do you accept the Product Goal that PM-5 wrote into `docs/sprints/roadmap.md` §"Product Goal"? It reads: "a real amateur pickleball player, on their own phone, goes from an uploaded match to a 2-week training plan in ≤ 15 min of median effort, can trace every number and drill to its rallies; the PO signs R1 off". It restates the R1 exit criterion and does not change it.
- **Options:** (a) accept it as written; (b) accept it with your edits; (c) reject it, and the section stays a draft.
- **Recommendation:** (a).
- **Default if no answer:** the section stays team text with status "draft".
- **Evidence:** `docs/sprints/05/decisions/PM-5.md` §1 and §5.
- **Deadline:** 2026-11-10.

### E3. FR-162 pricing fake door (PM-5 §4)

- **Question:** should the freemium fake door (FR-162, a Could; OQ-14) ship in R1?
- **Options:** (A) move it to R2, after the legal review, once a paid tier (automatic analysis) exists; (B) build it in S5 as a stretch goal behind a flag that is off by default; (C) drop it.
- **Recommendation:** (A). A fake door only produces data when real users click it. Real users wait on P16, and the paid tier first exists in R2.
- **Default if no answer:** (A). Nothing is built and the Could stays in the backlog.
- **Evidence:** `docs/sprints/05/decisions/PM-5.md` §4.
- **Deadline:** 2026-11-10.

### SZ. Should drill JSON count towards the PR size limit?

- **Question:** ADR 0054 counts only production code against the 400-line limit. It excludes tests, docs, lockfiles, fixtures and snapshots. Drill content under `content/drills/` is not on that list, so it counts. One drill file is about 41 lines (`wc -l` over the 34 drills in `content/drills/` → 1429 lines). That caps a drill PR at about 9 drills. Should drill JSON be excluded?
- **Options:**
  - (a) **Keep counting it** and slice drill tickets at ≤ 6 drills per PR. This is the current rule (kickoff COACH-3); ST-081b fits it.
  - (b) **Exclude `content/drills/**/*.json`** by amending ADR 0054. Drill content would then be limited only by the drill lint, the coverage check and the domain-coach review.
  - (c) **Count it under a separate content limit**, for example 20 drills per PR (judgment).
- **Recommendation:** (a) for Sprint 5, because nothing in this sprint is blocked by it. RETRO-05 reviews the waiver share and the drill PR sizes (red-team item R6) and comes back to you with data if (b) or (c) looks better.
- **Default if no answer:** (a). ADR 0054 is unchanged.
- **Evidence:** `docs/decisions/0054-pr-size-gate-counts-production-code-only.md` decision 2; `scripts/ci/check_pr_size.py`; `docs/sprints/05/kickoff.md` COACH-3.
- **Deadline:** 2026-11-10.

### S6. Admin setting 6 (ADR 0053 part 2)

- **Question:** the daily dependency audit opens a draft upgrade PR, which needs the repository setting Actions → General → Workflow permissions → "Allow GitHub Actions to create and approve pull requests". Only an admin can tick it (`docs/process/ci-cd.md` §2.1 item 6). Will you tick it?
- **Options:** (a) tick it; (b) leave it off and have an SRE ticket change ADR 0053 so the job opens an issue instead of a PR; (c) leave it off and accept that the job goes red whenever it has an upgrade to open.
- **Recommendation:** (a). The job never approves a PR, and every PR still needs `ci-gate` and the `merge_ready.py` verdicts (`docs/process/ci-cd.md` §2.1 item 6).
- **Default if no answer:** nothing changes. The red-run notice tells you when the job fails, and row S5-S6 stays "not met: waiting on setting 6".
- **Evidence:** `docs/decisions/0053-daily-dependency-audit-opens-a-draft-upgrade-pr-that-a-reviewer-marks-ready-to-start-ci.md` ("Still to observe live"); `docs/sprints/04/blockers.md`, rows of the second to fourth close.
- **Deadline:** 2026-11-10.

## 3. Audit items left open (`docs/process/audit-2026-10-31-open-items.md` §2)

### A12. Which "plan and brainstorm skills"? (finding F08)

- **Question:** your 2026-10-31 instruction says "plan + brainstorm skills". Did you mean (a) the installed product-management brainstorm and sprint-planning skills, (b) Claude Code plan mode, or (c) new repository skills in a new .claude/skills/ folder (it does not exist yet)?
- **Recommendation:** (a). It costs nothing new, and sprint-05 §0.6 shows what it produced.
- **Default if no answer:** (a), as used at Sprint 5 planning.
- **Evidence:** `docs/sprints/sprint-05.md` §0.6; audit item 12.
- **Deadline:** 2026-11-10.

### A13. Deny rules and a merge hook (findings F11, F02)

- **Question:** should `.claude/settings.json` deny `enable_pr_auto_merge` and force-push, and should a PreToolUse hook allow `merge_pull_request` only when `scripts/ci/merge_ready.py` passes?
- **Already settled:** the QA-by-name half of the question. Under ADR 0056 decision 2, CI-TIERS-b (#193, merged) makes `merge_ready.py` require the senior-qa-engineer verdict on tier 1.
- **Options:** (a) add the deny rules now as guards against mistakes, plus an SRE ticket with tests for the merge hook (Sprint 6); (b) add the deny rules only; (c) neither: separation of duties stays a role-file rule.
- **Recommendation:** (a), the red team's default. Today the deny list holds only secret-file reads (`.claude/settings.json`). Agents do not change permission settings without you, so this needs your yes.
- **Default if no answer:** no settings change.
- **Evidence:** audit item 13; `scripts/ci/merge_ready.py` (QA verdict); `.claude/settings.json` `permissions.deny`.
- **Deadline:** 2026-11-10, so the hook ticket can enter Sprint 6 planning.

### A14. A commands-only `CLAUDE.md` (finding F26)

- **Question:** should the repository have a `CLAUDE.md` that lists only the test, lint and check commands and points to the working agreement, the DoR and the DoD, without restating any rule? There is no `CLAUDE.md` today (`ls CLAUDE.md` → no such file).
- **Options:** (a) yes, as a tier 0 docs ticket in Sprint 6; (b) no.
- **Recommendation:** (a) (judgment). Every agent session would find the commands in one place, and with no restated rules there is no second copy to drift.
- **Default if no answer:** no file.
- **Evidence:** audit item 14.
- **Deadline:** 2026-11-10.

### A15. Sprint goal format (finding PO-01)

- **Question:** is the sprint goal one objective (the Scrum Guide's form) or a bullet list?
- **Options:** (a) one goal sentence plus a bullet scorecard, as working-agreement §3 step 2 and sprint-05 §1 already do; (b) a short bullet list, as the EM role file still says.
- **Recommendation:** (a). If you agree, the EM role file wording (kickoff EM-11, deferred) is fixed in a tier 0 docs ticket.
- **Default if no answer:** plans keep (a), and the role file is unchanged.
- **Evidence:** audit item 15; `docs/process/working-agreement.md` §3; kickoff EM-11.
- **Deadline:** 2026-11-10.

## 4. Human inputs: carried items P6-P11, P15, P16 and new items P17-P20

Each of these is a `goal-scorecard.md` §5 row, not a goal metric. Need-by dates come from sprint-05 §0.4. "Still open since" uses `docs/sprints/04/blockers.md` row 1 (2026-10-17): no answer to P6, P7, P8, P10, P11, P15 or P16 had been recorded by the fourth Sprint 4 close.

### P7. Rulebook (OQ-01) and side-out verification

- **Question:** can you supply the rulebook for official scoring and the side-out split? If not, do you accept the fallback "R1 ships unofficial scoring"?
- **Options:** (a) supply the rulebook, and the coach maps it to rule ids in `docs/domain/rules-verified.md`; (b) accept the fallback for R1: the score sheet, stats and plan carry the "unofficial scoring" label (FR-055), and the serve/receive split stays `@needs-verification`; (c) both: the fallback for R1, and the rulebook before R2.
- **Recommendation:** (c). Choose (b) if the rulebook cannot come before R2 planning.
- **Default if no answer:** the product stays as it is today (labelled unofficial, split unverified), and S5-P7 stays not met. That is the current state of the product, not an acceptance on your behalf.
- **Evidence:** `docs/sprints/04/sprint-report.md` §1.2, row S4-DoD-P7; FR-055.
- **Deadline:** 2026-11-10, so ST-082's release notes can state it.

### P15. Human coach review of drills

- **Question:** can a human pickleball coach review the starter drills so they can move to `verified`? If not, do you accept R1 shipping drills at `coach-reviewed` (reviewed by the agent coach) with the human-coach notice?
- **Options:** (a) supply a coach; (b) accept the fallback for R1; (c) both: the fallback for R1, and the coach before real users.
- **Recommendation:** (c).
- **Default if no answer:** drills stay `coach-reviewed` with the notice, and S5-P15 stays not met.
- **Evidence:** `docs/sprints/04/sprint-report.md` §1.2, row S4-DoD-P15 (23 drills at `coach-reviewed`, 0 `verified`); ADR 0051 decision 3.
- **Deadline:** 2026-11-10.

### P8. Budgets, storage quota, GPU (OQ-13)

- **Question:** what are the per-user storage quota, the monthly budgets behind the billing alerts (NFR-022) and the GPU budget for SPIKE-03?
- **Options:** (a) give the values; (b) accept the interim settings for R1 (20 GiB per user, judgment) and say that no GPU spend is approved yet.
- **Recommendation:** (a). Choose (b) if you only want to decide the quota now.
- **Default if no answer:** the interim settings stay, nothing is spent, and SPIKE-03 stays unplanned.
- **Evidence:** `docs/sprints/04/blockers.md` row 1; scorecard row S5-P8.
- **Deadline:** 2026-11-10.

### P17. SLO commitment and error-budget policy (new)

- **Question:** do you accept the SLO targets and the error-budget policy that ST-075c drafts (NFR-041.2, NFR-042.2, NFR-049.1)? An error budget is a commitment, so the team cannot set it.
- **Options:** (a) accept the drafts once ST-075c merges; (b) accept them with changes; (c) defer to the R1 release.
- **Recommendation:** (a).
- **Default if no answer:** the drafts are internal targets only, and S5-P17 stays not met.
- **Evidence:** sprint-05 §0.4; ADR 0057 (PE-5a).
- **Deadline:** 2026-11-12.

### P19. Residual-risk ADR (new)

- **Question:** for every ASVS L2 `Fail` row and every threat-note row marked "Accepted residual", do you accept the risk, require a fix, or defer it? SEC-5 and ST-078a-c draft the ADR, and only a human can accept a residual risk (working-agreement §8).
- **Options:** (a) review the draft ADR and decide row by row; (b) accept none until the legal review (P16) is done.
- **Recommendation:** (a). Residual risks matter only once real users exist, so a row-by-row answer lets the safe rows close now.
- **Default if no answer:** the ADR stays Proposed, the rows stay open, and real users stay off.
- **Evidence:** sprint-05 §0.4; scorecard row S5-P19.
- **Deadline:** 2026-11-12.

### P16. Legal review (NFR-070, US + AU)

- **Question:** will you commission the legal review of the age, footage, consent and retention texts? Does tester footage in the usability session need that review first?
- **Options:** (a) commission it now, and include the tester-footage question; (b) run the usability session with no footage kept beyond the session under the interim consent script, only if your legal adviser says so; (c) defer it, in which case there are no real users and no tester footage.
- **Recommendation:** (a). The team cannot judge the law, and our GDPR and related research is unverified (AQS Gaps).
- **Default if no answer:** feature flags stay off for real users, and no tester footage is kept.
- **Evidence:** `docs/sprints/04/sprint-report.md` §1.2, row S4-DoD-P16; scorecard row S5-P16.
- **Deadline:** before the usability session and before any real user. P9 depends on it.

### P9. Usability testers (OQ-20)

- **Question:** can you book ≥ 5 amateur players for the moderated usability test (NFR-036.1-.3), plus the second reviewer?
- **Options:** (a) book them for a session before 2026-12-22, and the ST-083 kit is ready; (b) run a pilot with 2-3 players that does not count towards NFR-036; (c) run the session after the holidays, and sign R1 off after it.
- **Recommendation:** (a). If that is not possible, (c).
- **Default if no answer:** S5-P9 stays not met, and the R1 readiness recommendation states that median effort (NFR-036 c) is unmeasured.
- **Evidence:** `docs/requirements/open-questions.md` OQ-20 ("Recruitment is a PO action"); scorecard row S5-P9.
- **Deadline:** testers booked by 2026-12-16.

### P20. Real-device iOS Safari and Android Chrome (new; OQ-17)

- **Question:** who runs the ST-079 device checklist on real phones (current and previous major versions)?
- **Options:** (a) the P9 testers on their own phones, in the same session; (b) you, on your own devices; (c) a paid device cloud, which needs P8 budget.
- **Recommendation:** (a). It costs nothing extra.
- **Default if no answer:** emulation evidence only (ST-079), and S5-P20 stays not met.
- **Evidence:** OQ-17 (both browsers release-blocking); scorecard row S5-P20.
- **Deadline:** 2026-12-16.

### P6. Screen-reader pass (NFR-027 b)

- **Question:** can you supply a tester who uses a screen reader daily to run the manual pass over the R1 screens?
- **Options:** (a) one tester before the release-candidate sign-off; (b) accept an R1 release candidate with automated checks only, and the pass before real users.
- **Recommendation:** (a).
- **Default if no answer:** the release notes make no screen-reader or WCAG conformance claim (kickoff PD-4), and S5-P6 stays not met.
- **Evidence:** the earlier rounds are 0 of 24 rows run (`docs/sprints/03/a11y-manual.md`, tallied by `scripts/measure/a11y_manual.py`); retro-02 A4.
- **Deadline:** overdue; the new need-by is 2026-12-16.

### P10. Repository visibility

- **Question:** should the repository stay public?
- **Evidence:** `gh api repos/nhuthuynh/racket-analytics --jq .visibility` → `public` (2026-11-03).
- **Options:** (a) confirm public; (b) make it private (an admin action).
- **Recommendation:** (a) only if you are content with public. The team keeps nothing private in git either way.
- **Default if no answer:** it stays public.
- **Deadline:** sooner is safer.

### P11. Footage bucket and consented footage (OQ-06)

- **Question:** which private footage bucket provider do we use, and where does consented footage for SPIKE-02/05/07 and the QD-GD-04 v1 gold set come from?
- **Options:** (a) choose a provider, and the team plans the spikes at S7 planning; (b) defer R2 vision work.
- **Recommendation:** (a).
- **Default if no answer:** the R2 spikes stay unplanned. ST-084a and ST-084b (which need no footage) go ahead.
- **Evidence:** `docs/sprints/04/sprint-report.md` §1.2, row S4-DoD-P11; scorecard row S5-P11; roadmap SPIKE-07 row ("needs footage, P11").
- **Deadline:** S7 planning.

### P18. R1 release-candidate sign-off (new)

- **Question:** after VERIFY-05, do you sign R1 off as a release candidate?
- **Options:** (a) sign off; (b) sign off with conditions (for example P16 before any real user); (c) do not sign off yet.
- **Recommendation:** decided at the sprint review from the PM's readiness recommendation and the ST-082 release notes.
- **Default if no answer:** there is no release, and R1 stays a candidate.
- **Evidence:** scorecard row S5-P18; sprint-05 §0.4 (REL-1.4).
- **Deadline:** the sprint review on 2026-12-22.

## 5. How answers are recorded

1. Answer in any form, for example "E1: a".
2. The orchestrator quotes your words verbatim in a new addendum of `docs/requirements/po-input-2026-10-05.md`. No agent writes a PO decision (ADR 0047).
3. The ticket that owns each item applies the answer: the roadmap (product-manager), ADR 0054 (SRE), settings and hooks (SRE), role files (EM), and the scorecard §5 rows (RETRO-05).
4. At each status step the EM checks this table against the addenda. An item past its deadline with no answer is reported with its default in the EM status record.
