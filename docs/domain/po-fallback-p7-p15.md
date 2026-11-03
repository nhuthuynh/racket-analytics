# Draft PO request: fallbacks for P7 (rulebook) and P15 (human coach review)

- **Author:** pickleball-domain-coach (COACH-5, 2026-11-03). **Status: draft for EM-ESC-05.** The engineering-manager copies it into `docs/sprints/05/po-escalations.md` (planned) and sends it by 2026-11-05 (sprint-05 §3.6, wave 1). Kickoff item COACH-4 says: "Escalate P7 and P15 with explicit fallback". The PO decides; agents do not.
- **Format:** working-agreement §8 (question, options, recommendation, evidence, deadline).

## P7: the 2026 rulebook (OQ-01) for official scoring and the side-out split

- **Question to the PO:** the rulebook is still not supplied. Do you accept that **R1 ships as "unofficial scoring"** if it does not arrive in time?
- **Need-by:** 2026-11-10 for the fallback decision (sprint-05 §0.4). For verification inside Sprint 5, the PDF is needed by 2026-11-10 too. After that, rows 1-7 of the queue cannot be verified, reviewed and merged before VERIFY-05.
- **Evidence:**
  - `docs/domain/rules-verified.md` §1: the agent proxy refuses the rulebook host (`usapickleball.org:443 — connect_rejected`, 2026-10-03). Nothing in §3 is verified.
  - OQ-01 has been open since Sprint 0. It was due at Sprint 3 planning (2026-11-16 in the original calendar) and has been carried through Sprints 2-4.
  - The verification queue is now mapped to rule ids (`docs/domain/rules-verified.md` §5, "FR rule ids" column). So once the PDF arrives, the work per row is known.

| Option | What happens | Cost and risk |
|---|---|---|
| **A (recommended)** | The PO accepts the fallback. R1 ships with the `PROVISIONAL-UNVERIFIED` preset and the "unofficial scoring (rules not yet verified)" notice on the score sheet, stats, plan and release notes (FR-055.R1). Official scoring becomes an R2 item, and it starts the day the PDF arrives | A player cannot use R1 for official or tournament scoring. That was never an R1 promise (`docs/domain/rc-copy-review.md` §2 item 5) |
| B | The PO supplies the 2026 rulebook PDF and the change document (any channel; the coach records the file name and SHA-256 in §4) by 2026-11-10 | The coach verifies rows 1-7. Every row that differs from the provisional value is a requirement change (rules-verified §2 step 3), and it may not fit Sprint 5 |
| C | No decision | P18 (R1 sign-off) has no PO statement on scoring. The release notes check (ST-082) still passes, because the notice is present |

- **Recommendation:** A, and B as soon as possible. A keeps R1 honest. B is still the only way to official scoring (judgment).

## P15: human coach review of the drill library

- **Question to the PO:** no human coach has reviewed the 31 `coach-reviewed` drills. Do you accept that **R1 ships with drills reviewed only by the coaching role (agent)**, with the plan-page notice and the safety notes, until a human coach reviews them?
- **Need-by:** 2026-11-10 (sprint-05 §0.4).
- **Evidence:**
  - Every drill passes `docs/domain/drill-review-checklist.md` §1, which is all (judgment) [DOM G2]. No coaching source is verified.
  - The plan page says "These drills have not yet been checked by a human coach. Warm up first, and stop any drill that hurts." (`docs/domain/rc-copy-review.md` R5).
  - ST-081b adds up to 6 drills at `coach-reviewed`, and none at `verified`.
  - `docs/domain/usability-drill-safety.md`: by default, usability testers do not play drills.

| Option | What happens | Cost and risk |
|---|---|---|
| **A (recommended)** | The PO accepts the fallback. R1 drills stay `coach-reviewed`, and the notice and safety notes stay. The stats wording changes as finding COACH-S5-02 proposes, so that "our coach" is not read as a human | Drill quality is the agent's judgment. The injury risk is reduced, but not removed, by the C5 safety notes and the warm-up rule |
| B | The PO names a human coach (certified, or an experienced club coach) who reviews the library against checklist §1. Reviewed drills move to `verified` | The coach's time is about 31 drills × 5 min (judgment). Their name and qualification are recorded in the drill's `source` |
| C | Drills are hidden in R1 until P15 is answered | The R1 plan has no content, and the Product Goal (upload to plan) fails |

- **Recommendation:** A for R1, and B before any public beta. Please also confirm the stats wording in COACH-S5-02 together with this answer.

## Escalations that need no PO decision now

- No coaching content in the library is judged unsafe. If one is found, it goes to the EM and the PO at once (coach role file). Two wall drills have empty `safety_notes`. They are excluded from the usability sessions and get notes in a new version (COACH-S5-03, minor).
