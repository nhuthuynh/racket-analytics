# COACH-5 decisions

Per-ticket decision file (working-agreement §3, "Daily sync"). Ticket: COACH-5, "Domain review of RC copy and notices; ledger row for the single-weakness gap; usability drill safety list; P7/P15 fallback request draft; NFR-036.4 call types" (`docs/sprints/sprint-05.md` §3.2). Owner: pickleball-domain-coach. Review tier 0 (ADR 0056). Items: FR-124, FR-055. It gates ST-080, ST-081a, ST-082 and ST-083.

**TDD does not apply.** The ticket changes domain text, a ledger and decisions only (`docs/domain/`, `docs/sprints/05/review-rounds.md`, this file). There is no executable behaviour to drive with a failing test. The behaviour these documents specify is tested red-first in the tickets they gate: ST-081a (coverage rule and swap ITs), ST-080 (tap counter) and ST-082 (release-notes checker). The doc checks run instead (PR description, "Test evidence").

## 1. Outputs

| Output | File |
|---|---|
| Checklist §3.1.1 session-size rule (FR-124.R1-R2, FR-141.R1) | `docs/domain/drill-review-checklist.md` |
| Ledger rows COACH-S5-01 (major), COACH-S5-02 and COACH-S5-03 (minor) | `docs/sprints/05/review-rounds.md` |
| Usability drill safety list (USAB-1.1 input) | `docs/domain/usability-drill-safety.md` |
| P7/P15 fallback request draft (EM-ESC-05 input) | `docs/domain/po-fallback-p7-p15.md` |
| NFR-036.4 call types (ST-080 input; confirms A7) | `docs/domain/fix-call-types.md` |
| Domain review of RC copy and notices; release-notes wording (ST-082, FR-055.R1) | `docs/domain/rc-copy-review.md` |
| Verification queue mapped to `FR-nnn.Rk` (S5-P7) | `docs/domain/rules-verified.md` §5, §5.1 |

## 2. Decisions

| Date | Who | Decision | Evidence | Why |
|---|---|---|---|---|
| 2026-11-03 | pickleball-domain-coach | **Coverage threshold per profile cell = S + 1 drills**, where S is the most weakness drills one session of that profile can hold (S = 2 for `solo+wall` at 30 min, so 3). This one rule replaces the known limit of the pair rule (cases a and b) and includes the pair rule | Hand count at `8c37e98d` (checklist §3.1.1): AN-01 3, AN-05 3, AN-02 2, AN-04 2, AN-07:fault 2, AN-07:forced-error 2 for `solo+wall` × intermediate. `backend/src/racket/coaching/drills/coverage.py` `MIN_DRILLS` = 2 today | A session holds at most S drills of the swapped target, so one more drill is free **for the first press of that target in a plan**. Later presses also lose the drills already swapped out (`excluded_drills`), so the k-th press needs S + k (§3, PE-COACH5-1). A count is simpler to check and to explain than per-pair rules (judgment) |
| 2026-11-03 | pickleball-domain-coach | **FR-141.R1's "fewer than 2 fitting drills" is read as 2 alternatives besides the swapped drill**, which is S + 1 = 3 in all for `solo+wall` | requirements-breakdown §2 FR-141.R1; the negative Example fails under both readings | Under the literal reading (2 in all), a single-weakness swap still dead-ends, which is the COACH-1 gap |
| 2026-11-03 | pickleball-domain-coach | **The profile set stays `solo+wall` (intermediate) for Sprint 5.** Other players × equipment profiles are advisory rows in ST-081a's output | ST-081b may add at most 6 drills (kickoff COACH-3). Closing 4 short cells takes 4 | A longer-session profile (S = 4) would need about 2 more drills in each of 6 cells. That is not possible within the limit |
| 2026-11-03 | pickleball-domain-coach | **COACH-S5-01 is major**, Open, owned by ST-081a/b | Kickoff COACH-1; VERIFY-04-r3, Sprint 4 goal row 1, step 9 (`docs/sprints/04/decisions/QA-VERIFY04R3-01.md`) | The player-facing "Not for me" control dead-ends on a supported setup. The Sprint 5 open-majors metric needs it closed before the sprint closes |
| 2026-11-03 | pickleball-domain-coach | **A7 confirmed with one addition:** the call types are CT-1 rally winner, CT-2 ending, CT-3 fault (to and from) and CT-4 responsible player (added). Fault subtype, rally times, score and game start are not counted | `web/src/components/score-sheet/RallyCorrections.tsx` has three controls: "Switch winner", "Change ending", "Change player". Quick Tag does not set a fault subtype (`grep -n fault_kind web/src/components/tagging/QuickTag.tsx` → none) | Per-player error stats are player-facing (FR-050). Fault subtype is not a player control in R1 |
| 2026-11-03 | pickleball-domain-coach | **Usability sessions: no physical drill by default.** An optional try-out uses class A drills only (9 drills, 2 of them warm-ups) | `docs/domain/usability-drill-safety.md` §1-§2. Every one of the 31 reviewed drills is classed (script check below) | NFR-036.1-.3 measure app effort. Play adds injury risk and gives no data (judgment) |
| 2026-11-03 | pickleball-domain-coach | **RC copy: 9 accepted, 1 change (COACH-S5-02, minor).** The release-notes domain wording is given for ST-082 | `docs/domain/rc-copy-review.md` §1-§2 | "Checked by our coach" next to "not yet checked by a human coach" invites a misreading |
| 2026-11-03 | pickleball-domain-coach | **Queue rule ids `FR-nnn.Rk` are numbered in FR text order.** They are labels for the verification work and make no rule claim. FR-055.R1 keeps the meaning it has in the breakdown | `docs/domain/rules-verified.md` §5.1 | The S5-P7 row asks for the mapping. The FR Gherkin has unnumbered `Rule:` lines |
| 2026-11-03 | pickleball-domain-coach | **P7 and P15: recommend option A (ship with the fallback) for both**, and B as soon as possible | `docs/domain/po-fallback-p7-p15.md` | Agents cannot supply the rulebook or a human coach. The fallback keeps R1 honest and does not block the Product Goal |
| 2026-11-04 | pickleball-domain-coach | **Review round 1 (PE-COACH5-1): the S + 1 guarantee is stated exactly as "the first 'Not for me' per target per plan"; the threshold stays S + 1; no new swap rule.** ST-081a's ITs pin it: first press swaps, press N − S + 1 on one plan answers `409 no_alternative` with the plan unchanged. The rest is COACH-S5-04 (minor, Sprint 6) | §3 below; checklist §3.1.1 | S + 2 = 4 per cell needs 10 more drills, over ST-081b's 6. Offering a turned-down drill again goes against the player's choice and ST-062 (judgment) |

## 3. Evidence for PE-COACH5-1 (review round 1)

`TrainingPlan.swap` (`backend/src/racket/coaching/plan/domain/model.py`) treats `{session drills} | {old drill} | excluded_drills` as taken, and a swapped-out drill joins `excluded_drills` for the whole plan. Reproduction on the domain over the real `content/drills` (code identical to `main` at `8c37e98d`; this PR changes no code), a single-weakness plan with the G04-01 preferences (1 player, `wall`, 30 min, 3 per week, intermediate), session 1, presses on positions 2 then 3:

```
$ cd backend && uv run python <scratch>/repro.py
AN-01 held [2, 3] | press1@2:ok->pb.serve.wall-target-serves@1 press2@3:409
AN-02 held [2, 3] | press1@2:409
AN-04 held [2, 3] | press1@2:409
AN-05 held [2, 3] | press1@2:ok->pb.serve.wall-target-serves@1 press2@3:409
AN-07:fault held [2, 3] | press1@2:409
AN-07:forced-error held [2, 3] | press1@2:409
```

AN-01 and AN-05 have N = 3 = S + 1: the first press swaps, the second answers 409, as the finding says. The other four targets have N = 2 and fail on the first press (the four short cells of checklist §3.1.1). The script builds the plan with `assemble([PlanWeakness("w-1", t, 1)], G04_01, library)` and calls `plan.swap(..., cited=set(TARGETS))`, as IT-04-18 does.
