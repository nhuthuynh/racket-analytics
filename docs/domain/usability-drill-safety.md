# Usability test: drill safety list (R1, NFR-036 kit)

- **Owner:** pickleball-domain-coach (COACH-5, 2026-11-03). **Used by:** ST-083 (`docs/design/usability-test-kit-r1.md` (planned), USAB-1.1 "safety-reviewed drill list"), the moderator of the P9 sessions, and ST-081b (each new drill gets a class in §2).
- **Basis:** `docs/domain/drill-review-checklist.md` §1 C5 (QD-DR-04) and §2 (warm-up rule). Threat notes `docs/security/threat-notes-sprint-05.md` §4 (T5-UT-1 adults only, T5-UT-4 demo accounts). Library on `main` at `8c37e98d` (`content/drills/`). **Every rule here is (judgment).** No coaching source is verified [DOM G2], and no human coach has reviewed the drills (P15).
- **Scope:** the moderated usability test of NFR-036.1-.3 measures effort in the app: Quick Tag, fixing calls, and the time from upload to plan. **It does not need anyone to play a drill.** This list says what a tester may *read* in the app, and what a tester may *try* if the kit adds an optional physical step.

## 1. Rules for the session (binding on the kit)

| # | Rule | Why |
|---|---|---|
| U1 | **Default: no physical drill in the session.** Testers read their plan, open a drill, press "Not for me" and mark a session done in the app. Nobody plays. | NFR-036.1-.3 measure app effort, so physical play adds injury risk and gives no data (judgment) |
| U2 | If the kit adds an optional "try one drill" step, the tester **may only choose a drill of class A in §2**. The moderator stops the step if the tester says something hurts, feels dizzy or is short of breath. | C5: stop if dizzy or in pain |
| U3 | **Warm-up first.** Before any class A drill, the tester does `pb.warm-up.shadow-footwork` (5 min, no equipment) or `pb.warm-up.wall-rally` (5 min, wall). | Checklist §2: every session starts with exactly one warm-up |
| U4 | **Adults only (18+), as T5-UT-1 requires.** A tester who says they have a current injury, a heart or breathing condition, or has been told not to exercise takes part in the app tasks only (U1). The moderator asks this before the session. The kit records only "app tasks only", never the condition. | Escalation rule in the coach role file: content that could cause injury goes to the EM and the PO. The kit keeps no health data (T5-UT-2) |
| U5 | Space: for a wall drill, a clear 3 m × 3 m area in front of the wall, no loose balls on the floor, flat non-slip shoes. Phones are put down before swinging. | The rebound and trip risks in the class A notes (`pb.return.wall-return-and-split`: "clear the floor of loose balls") |
| U6 | **Class B and class C drills are never played in the session**, even if the tester's plan shows them. The tester may read them. | §2 |
| U7 | The coach notice on the plan page ("These drills have not yet been checked by a human coach. Warm up first, and stop any drill that hurts.") stays visible during the session. The moderator does not explain it away. | PD-4 interim notice; P15 |

## 2. Classes per drill (latest version on `main`)

- **A, may try:** solo, needs nothing or a wall, beginner level allowed, soft or low intensity, and a non-empty `safety_notes` that says so.
- **B, read only:** fine to read in a plan, but not for a test session, because it needs a partner, a court or a feeder, or eye protection, or because it is high-intensity hands work.
- **C, read only, with a content follow-up:** the drill's own safety text is missing or not enough for unsupervised play (finding COACH-S5-03).

| Drill | Class | Reason |
|---|---|---|
| `pb.warm-up.shadow-footwork` | A (warm-up) | no equipment; "no sprints, no jumps, no backpedalling" |
| `pb.warm-up.wall-rally` | A (warm-up) | soft, below head height |
| `pb.dink.wall-soft-dinks` | A | soft pace, no speed-ups |
| `pb.serve.wall-target-serves` | A | low intensity; let rebounds go |
| `pb.serve.wall-routine-ladder` | A | low intensity; clear space for rebounds |
| `pb.serve.wall-serve-and-ready` | A | low to moderate intensity; no backpedal |
| `pb.volley.wall-line-volleys` | A | soft, below head height |
| `pb.third-shot.wall-let-it-bounce` | A | soft pace; do not lunge |
| `pb.return.wall-return-and-split` | A | walk forward, never sprint; clear floor |
| `pb.return.wall-return-and-block` | A | soft to medium, deep high return; walk in, never sprint or backpedal; clear floor (ST-081b) |
| `pb.dink.wall-two-wing-dinks` | A | soft pace, no speed-ups, below head height (ST-081b) |
| `pb.volley.wall-dink-then-step-back` | A | soft, below head height; short steps back facing the wall, no hop or lunge (ST-081b) |
| `pb.warm-up.cooperative-dinks` | B | needs a partner and a half court |
| `pb.reset.wall-reset-blocks` | B | eye protection; the rebound comes back fast |
| `pb.reset.wall-half-volley-resets` | B | intermediate only; low balls at the feet need knee bend under time pressure, so not for an untrained tester (ST-081b) |
| `pb.volley.wall-hands-battle` | B | eye protection; high-intensity hands work, intermediate only |
| `pb.dink.safe-target-dinks`, `pb.volley.line-volleys-no-step-in`, `pb.reset.block-the-drive`, `pb.reset.transition-reset-feeds`, `pb.return.deep-return-target`, `pb.third-shot.let-it-bounce-drops` | B | partner or feeder and a court |
| `pb.dink.error-free-dink-game`, `pb.dink.line-fault-game`, `pb.reset.speed-up-defence-game`, `pb.reset.transition-battle` | B | speed-ups at close range; eye protection |
| `pb.game.fault-free-game`, `pb.return.receive-pressure-game`, `pb.return.return-and-move-in`, `pb.serve.serve-and-third`, `pb.serve.pressure-ladder` | B | live rallies or a full court; lobs; advanced content |
| `pb.serve.consistency-ladder`, `pb.serve.deep-target` | B | full court needed (no safety trigger) |
| `pb.return.wall-return` | C | solo wall drill with empty `safety_notes`; deep return strokes against a wall send the ball back fast (COACH-S5-03) |
| `pb.drive.wall-margin` | C | solo wall drives with empty `safety_notes`; drives at a wall are the fastest rebound in the library (COACH-S5-03) |
| `pb.fixture.*` | — | `draft` test fixtures; never shown to players |

Hand-checked against the drill files at `8c37e98d`: 34 drill directories, 31 `coach-reviewed` drills and 3 `pb.fixture.*` drafts. Every reviewed drill is in exactly one row above. ST-081b (2026-11-12) adds 4 rows: 38 drill directories, 35 `coach-reviewed` drills.

## 3. Changes

- A new drill version (ST-081b or later) gets a row in §2 in its own PR. Until it has one, it is class B.
- A class C drill becomes A or B only after a new version adds `safety_notes` and the coach reviews it again (checklist §1 C5, QD-DR-02).
