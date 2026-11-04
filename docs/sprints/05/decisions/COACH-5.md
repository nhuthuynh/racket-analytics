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
| 2026-11-04 | pickleball-domain-coach | **Review round 2 (QA-R2-1): the swap guarantee counts only drills that fit the smallest slot.** A drill is swap-counted when it is counted (checklist §3.1) and its `duration_min` ≤ m, the smallest `duration_min` among the profile's counted drills (m = 10 for `solo+wall` at 30 min). Each ST-081b drill must have `duration_min` ≤ 10. ST-081a's check counts with this filter, and its IT adds the negative case (an extra AN-02 drill of `duration_min` 12 keeps AN-02 red) | §4 below; checklist §3.1.1 | `TrainingPlan.swap` also needs `duration_min` ≤ room, and room can be 10 under a 12-minute cap. Room ≥ the current drill's minutes ≥ m, so the filter is exact for every slot without simulating sessions. The finding is right; round 1's PE-COACH5-2 said the same and was not addressed |
| 2026-11-04 | pickleball-domain-coach | **Review round 2 (QA-R2-2): new finding COACH-S5-05 (major).** The business-analyst qualifies FR-124.R1 and FR-141.R1 before ST-081a is marked Ready (proposed text in §5). The engineering-manager puts the narrowing (first press per target per plan, `solo+wall` only) to the PO in Sprint 5 as an EM-ESC item. Release-notes item 5 ships its first-press claim only if the check and the ITs are green on the RC library | `docs/sprints/05/requirements-breakdown.md` FR-124.R1 (no first-press qualifier), FR-141.R1 ("fewer than 2"); checklist §3.1.1 | Without it, ST-081a's atomic rule and its IT contradict each other, and an FR is narrowed with no BA or PO record. This PR cannot edit the breakdown (BA-owned) or `po-escalations.md` (EM-owned) |

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

## 4. Evidence for QA-R2-1 (review round 2)

`TrainingPlan.swap` gives a new drill `min(duration_max, drill_cap, room)` minutes and skips it when that is below its `duration_min`, with `room = minutes_budget − Σ other drills` (`backend/src/racket/coaching/plan/domain/model.py`). In a single-weakness AN-02 plan the sessions alternate warm-ups: `pb.warm-up.shadow-footwork` (8 min) + a 12-minute drill + a 10-minute drill, so position 3 has room 30 − 8 − 12 = 10, below the cap of 12. Reproduction on the domain over the real `content/drills` plus one hypothetical AN-02 solo wall drill (a copy of `pb.return.wall-return` with a new id and `duration_min` D; the id decides where it sorts in the pool). One press per slot, a fresh plan per press, every weakness slot of the 6 sessions of the single-weakness plan and of the 5 two-weakness plans that pair AN-02 with another target (`cited=set(TARGETS)`, as IT-04-18):

```
$ cd backend && uv run python <scratch>/repro_r2.py ../content/drills
AN-02 + pb.return.a-hypothetical duration_min=12: first-press 409s = 0 []
AN-02 + pb.return.a-hypothetical duration_min=10: first-press 409s = 0 []
AN-02 + pb.return.z-hypothetical duration_min=12: first-press 409s = 3 ['AN-02 s0 pos3 room10', 'AN-02 s2 pos3 room10', 'AN-02 s4 pos3 room10']
AN-02 + pb.return.z-hypothetical duration_min=10: first-press 409s = 0 []
AN-01 (3 swap-counted drills): first-press 409s = 0 []
AN-05 (3 swap-counted drills): first-press 409s = 0 []
```

With the old filter (`duration_min` ≤ cap 12) the AN-02 cell counts 3 and passes S + 1, yet the first press at position 3 answers 409 in sessions 0, 2 and 4 (zero-based) when the 12-minute drill sorts last, as the finding says. With the swap-counted filter (`duration_min` ≤ m = 10) that cell counts 2 and stays red, and every cell that passes (AN-01, AN-05 on `main`; AN-02 with a 10-minute third drill) swaps on every first press. Code is identical to `main` at `8c37e98d`; this PR changes no code.

## 5. Proposed rule text for the business-analyst (QA-R2-2, COACH-S5-05)

Proposals only; the business-analyst owns `docs/sprints/05/requirements-breakdown.md` and words the final rules before ST-081a's DoR. The PO decides whether the narrowing is acceptable for R1 (via the engineering-manager's EM-ESC item).

- **FR-124.R1 (proposed):** "When a player presses "Not for me" for the first time for a weakness in a plan that trains one weakness, with a fail-the-build profile (`solo+wall`, 30 min, intermediate) and a library that passes FR-141.R1, the API returns a different drill that targets the same metric and fits the player's preferences. A later press for the same weakness in that plan may answer `409 no_alternative` with the plan unchanged."
- **FR-141.R1 (proposed):** "The coverage check fails naming the cell when any metric × level × profile cell of a fail-the-build profile, single-target plans included, has fewer than S + 1 swap-counted drills (3 for `solo+wall` at 30 min: fitting, not a warm-up, `duration_min` ≤ the profile's smallest drill `duration_min`). Other profiles are advisory rows."
