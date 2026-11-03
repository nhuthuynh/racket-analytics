# Pre-Sprint 5 doc audit: open items

- **Owner:** engineering-manager
- **Audit dates:** 2026-10-31 (audit, red team, doc tests) to 2026-11-03 (PO decisions)
- **Decided by:** ADR 0056; PO answers quoted in `docs/requirements/po-input-2026-10-05.md`, addendum "Audit decisions (PO 2026-11-03)"
- **Research register:** `docs/research/agentic-sdlc-best-practices.md` (prefix ASB)

This is the audit record that ADR 0056 decision 4 points to. It is agent text, not a PO decision: the PO's own words are only in `po-input-2026-10-05.md`.

## 1. What the audit produced

- 62 findings on the role files and process docs, plus 12 red-team challenges to the original design (§3).
- The drafting step on `drafts/docs-audit` recorded 73 dispositions: 28 applied, 28 applied as modified by the red team, 15 not applied because they need a PO decision (§2), and 2 not applied because they belong to another doc group (ALL-01, ALL-02, applied in the role-file PR).
- The PO accepted the 56 applied dispositions on 2026-11-03 ("Accept draft as is"). They ship in PR #183 (research register), PR #184 (process docs) and PR #185 (role files).

## 2. The 15 dispositions left for the PO

Several findings appear in more than one file, so the 15 dispositions cover 7 questions. "Status" says whether a PO answer of 2026-11-03 settles the question; an item marked **open** waits for the PO and is asked at Sprint 5 planning.

| # | Finding id(s) | File(s) | Question | Status |
|---|---|---|---|---|
| 1-3 | F24, PE-03, PO-02 | working-agreement §6, principal-engineer.md, engineering-manager.md | Should review depth scale with risk? | **Answered:** "Tier by risk" (ADR 0056 decision 2). The tier text is in working-agreement §6 and the DoD. The role files PE-03 and PO-02 target are updated in PR #185 or a Sprint 5 ticket. |
| 4-6 | F25, ALL-03 (two groups) | working-agreement §9, the 7 engineering role files | How are changes to instruction files tested: a mechanical doc check in CI, before/after evals, or both? | **Partly answered:** Tier 0 needs "automated doc checks" (ADR 0056 decision 2), and the doc-check CI job is a Sprint 5 ticket (ADR 0056 consequences). **Open:** whether before/after transcript evals are required for behavioural role-file changes. |
| 7-11 | CROSS-QA-AS-SENIOR (working-agreement, DoD), CROSS-02, QA-01, BE-01 | working-agreement §6, definition-of-done.md, senior-*.md, principal-engineer.md | Does a senior-qa-engineer APPROVE fill the senior slot in `merge_ready.py`? | **Answered for tier 1:** "principal + QA test + CI" (ADR 0056 decision 2). **Open:** QA-01's second question, whether a green CI run on the head SHA counts as "ran every suite"; and the `merge_ready.py` tier ticket, which must decide how the script reads the tier. BE-01 and QA-01 role-file wording follows once those are settled. |
| 12 | F08 | working-agreement §3 | Which "plan and brainstorm skills" did the 2026-10-31 instruction mean: (a) the installed product-management brainstorm and sprint-planning skills, (b) Claude Code plan mode, or (c) new repo skills under `.claude/skills/`? | **Open.** Default until answered (judgment): (a). |
| 13 | F11 (with F02) | `.claude/settings.json`, `scripts/ci/merge_ready.py` | Add deny rules for `enable_pr_auto_merge` and force-push, and a PreToolUse hook that allows `merge_pull_request` only when `merge_ready.py` passes? Should `merge_ready.py` also require the senior-qa-engineer verdict on tier 1 and 2 PRs? | **Open.** Red-team default: the deny rules now, documented as guards against mistakes, and an SRE ticket with tests for the merge hook. The QA verdict is folded into the `merge_ready.py` tier ticket; until then the DoD QA item is not enforced by the script. |
| 14 | F26 | `CLAUDE.md` | Add a commands-only `CLAUDE.md` (test, lint and check commands plus pointers to the working agreement, DoR and DoD, with no restated rules)? | **Open.** |
| 15 | PO-01 | engineering-manager.md | Is the sprint goal one objective (Scrum Guide) or a bullet list? | **Open** for the PO. Working-agreement §3 step 2 already uses the recommended default (one goal sentence with a bullet scorecard); the EM role file still says "short bullet list". |

Two prerequisites the drafting step also listed are closed: the PO's 2026-10-31 instruction is now quoted verbatim (po-input addendum "Way of working"), and the network allowlist for the 34 unverified sources stays the PO's call (research register, research gaps).

## 3. Red-team challenges to the original design

The drafting step did not implement these; they are design challenges for the PO. Each row summarises the red team's challenge of 2026-10-31; its full counter-argument and evidence were not committed, so a ticket that takes one up restates them.

| # | Challenge | Red-team verdict | Status |
|---|---|---|---|
| R1 | Team shape: 12 role agents against about 5 standing agents | PO decides | **Answered:** "Keep 12 roles", measure cost per PR for a sprint (ADR 0056 decision 1; working-agreement §10). |
| R2 | Full review panel on every PR | PO decides | **Answered:** "Tier by risk" (ADR 0056 decision 2). |
| R3 | Prose rules against deterministic enforcement: label each MUST "enforced by <check>" or "guidance" and turn repeat offenders into checks | change | **Open.** Candidate Sprint 5 ticket; the retro template §7b "Rules to remove" now asks the question each sprint. |
| R4 | The Definition of Ready as a hard pull gate | change | **Open.** |
| R5 | Two-week Scrum sprints against goal-bounded Kanban increments | PO decides | **Answered:** "Keep sprints", with WIP limits and flow metrics (ADR 0056 decision 3; working-agreement §3 "Flow and WIP limits", §10). |
| R6 | PR size limits: drop the ~100 target or relabel it, track the waiver share | modify | **Open.** The waiver share can be read from the §10 metrics once Sprint 5 closes. |
| R7 | TDD and the full test triple for docs, config and process tickets | change | **Partly answered** by tier 0 (ADR 0056 decision 2); the docs checks themselves are the Sprint 5 doc-check ticket. |
| R8 | Spec-driven development: is the design spec living or frozen? | change | **Open.** |
| R9 | Role-prompt length and structure | modify | **Open.** Targeted fixes ship in PR #185; no rewrite for length. |
| R10 | Human-gated P-rows as one standing "PO inbox" | PO decides | **Open.** |
| R11 | Goal-measurement ceremony: scorecard methods tested red-first, verification capped | change | **Open.** |
| R12 | The audit itself: triage, not a rewrite, grouped into PRs by risk tier | PO decides | **Answered in part** by "Accept draft as is" and the three PRs (#183, #184, #185). |

## 4. How items close

An open item closes when the PO answers it (quoted verbatim in `po-input-2026-10-05.md`) or when a Sprint 5 ticket ships it. The engineering-manager updates the Status column in the PR that closes the item and lists the remaining open items at each sprint kickoff (working-agreement §3, planning step 1).
