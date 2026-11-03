# Domain review of the R1 release-candidate copy and notices

- **Reviewer:** pickleball-domain-coach (COACH-5, 2026-11-03), at `main` `8c37e98d`. **Used by:** ST-082 (`docs/releases/r1-rc.md` (planned) and `scripts/ci/check_release_notes.py` (planned): §2 gives the domain wording for the notes), the principal-designer (§1 verdicts), and G05-09 (FR-055.R1 notice).
- **Scope:** player-facing text that makes a pickleball or coaching claim: notices, labels, rules-version lines and coaching lines. Layout, accessibility and tone belong to the principal-designer and are not reviewed here.
- **Rule for every verdict:** a text may not present an unverified rule or coaching claim as fact (`docs/domain/rules-verified.md`: nothing is verified; [DOM G1], [DOM G2]).

## 1. Verdicts on the copy in the RC

| # | Where (file) | Text | Verdict | Note |
|---|---|---|---|---|
| R1 | score sheet (`web/src/components/score-sheet/ScoreSheetTable.tsx`, `UNOFFICIAL_LABEL` in `web/src/lib/tagging/types.ts`); API label (`backend/src/racket/matches/scorebook/domain/projection.py`) | "unofficial scoring (rules not yet verified)" | **Accept** | The FR-055 wording, the same in the web app and the API |
| R2 | score sheet rules line (`ScoreSheetTable.tsx`) | "provisional, not yet checked against the rulebook" (shown for `PROVISIONAL-UNVERIFIED`) | **Accept** | It does not name a federation (ADR 0009 rule 4) |
| R3 | stats page (`web/src/components/stats/StatsDashboard.tsx`) | the same notice, once, before the first card | **Accept** | Matches metric-dictionary rule 0.5 (DR-03 R3-3) |
| R4 | plan page (`web/src/components/plan/PlanView.tsx`; API `backend/src/racket/coaching/schemas.py`) | the same notice while `unofficial` (the side-out serve/receive split is not verified) | **Accept** | FR-055.R1 also covers the plan page. The flag comes from `side_out_verified`, which stays false until P7 |
| R5 | plan page coach notice (`PlanView.tsx`) | "These drills have not yet been checked by a human coach. Warm up first, and stop any drill that hurts." | **Accept** | It states the P15 gap and the two safety rules of checklist §1 C5 and §2. Keep it visible in the usability sessions (`docs/domain/usability-drill-safety.md` U7) |
| R6 | welcome page (`web/src/app/welcome/page.tsx`) | "We can't make line calls or referee your match from one phone." / "Scores follow rules that are not yet checked against the official rulebook, so they are marked 'unofficial'." | **Accept** | It says correctly that the app is not an official |
| R7 | Quick Tag and score-sheet endings (`ENDING_LABELS`) | Winner · Unforced error · Forced error · Fault · Replay | **Accept** | Standard coaching words (judgment). They are endings, not rule claims. "Replay" is used instead of "let", because what counts as a let is a rule question (queue row 10) |
| R8 | Full Tag fault kinds (`web/src/lib/label/view.ts`) | "Two bounce", "Kitchen (non-volley zone)" | **Accept** | Gives the player word and the rulebook term. Labeller role only |
| R9 | stats metric definition line (`web/src/lib/stats/view.ts` `versionLine`) | "Definition version N, checked by our coach." | **Change (minor, COACH-S5-02)** | "Our coach" is the AI coaching role, but next to R5 ("not yet checked by a human coach") a player reads it as a human. Proposed wording: "Definition version N, reviewed by our coaching team; not yet checked by a human coach." Keep "and verified" only for `verified` entries. The final words depend on the P15 answer (`docs/domain/po-fallback-p7-p15.md`) |
| R10 | "Not for me" with no alternative (`web/src/components/plan/PlanFollowThrough.tsx`) | "No other drill fits your setup for this. Your plan is unchanged." | **Accept** | True for both FR-124 rules. ST-081a/b make it rare for `solo+wall` (checklist §3.1.1) |

No text in the RC presents a rule number, an official score or a drill's effect as verified.

## 2. Domain wording for the R1 release notes (ST-082, FR-055.R1, REL-1.1)

ST-082 may shorten the words, but not the claims. Each item names its P-n, as REL-1.1 requires.

1. **Notice (required by FR-055.R1; the checker looks for the phrase "unofficial scoring"):** "Scores are **unofficial scoring (rules not yet verified)**. Release 1 uses the `PROVISIONAL-UNVERIFIED` rules preset. No scoring rule has been checked against the official rulebook yet (waiting on P7)."
2. **Known limitation, scoring (P7):** side-out doubles and singles scoring, the game target and the win-by margin, the server number and the score call follow provisional values. Rally scoring is not offered. A match keeps the preset it was scored under.
3. **Known limitation, coaching (P7):** the plan's split between serving and receiving weaknesses depends on the unverified side-out rule. So the plan page also carries the notice.
4. **Known limitation, drills (P15):** every drill is `coach-reviewed` by the team's coaching role, not by a human coach. No drill claims to improve a metric. Warm up first, and stop any drill that hurts.
5. **Known limitation, what the app does not do:** it makes no line calls, no automatic fault detection and no refereeing. The player marks every rally.

## 3. Follow-ups

| Id | What | Owner | Waits on |
|---|---|---|---|
| COACH-S5-02 (minor) | R9 wording | principal-designer decides the words; senior-frontend-engineer changes `versionLine` and its test in the ticket the EM assigns | P15 answer (EM-ESC-05, need-by 2026-11-10) |
