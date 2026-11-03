# Sprint 5 flows: degraded and error states (N), sign-out with unsent marks (X-04), release-notes copy, usability task screens, WCAG 2.2 gap list

- **Status:** Draft v0.1, 2026-11-03 (principal-designer, gate ticket PD-5). Design review **DR-05 is opened in §13 and is not yet held**: the decider cells are scheduled with dates, and each decider writes its own cell (ADR 0037 rule 2). Kickoff rule PD-1: a design gate is "merged **and** held".
- **Stories served:** ST-075 (what a player sees when R1 is unhealthy), ST-076 and ST-082 (restore and rollback seen from the phone), ST-078e (sign-out clears the device, form lock before hydration, no media in the service worker), ST-080 (fix a call in ≤ 2), ST-082 (release-notes copy), ST-083 (usability task screens, item USAB-1.1). No new route and no new feature: Sprint 5 changes states and words on existing screens.
- **Requirements:** FR-011, FR-055 (FR-055.R1), FR-124 (FR-124.R3-.R4); NFR-027, NFR-028, NFR-034, NFR-036.1-.4, NFR-041, NFR-045, NFR-050.7-.8, NFR-058, NFR-067.2-.3; REL-1.1; USAB-1.1 (`docs/sprints/05/requirements-breakdown.md`).
- **Design sources:** HAX [DPA/DESIGN-11]; error summary [DPA/DESIGN-13]; targets [DPA/DESIGN-02, DPA/DESIGN-10]; contrast [DPA/DESIGN-03, DPA/DESIGN-04]; focus not obscured [DPA/DESIGN-07]; WCAG 2.2 source [ASB/RPD-05]; SC 3.2.6 [ASB/RPD-06]; SC 3.3.7 [ASB/RPD-07]; conformance needs every A and AA criterion on every page of a process [ASB/RPD-08]; SC 4.1.1 removed [ASB/RPD-09]; automated and manual evidence [ASB/RPD-10]; design reviews [ASB/RPD-11]. Everything else is (judgment).
- **Inputs read on `main` at `8c37e98d`:** ADR 0057 (SLOs), ADR 0058 (backup, restore, rollback; §6 accepted residual), `docs/security/threat-notes-sprint-05.md` (T5-UT-1..4, T5-RB-3), `web/src/app/error.tsx`, `web/src/app/matches/error.tsx`, `web/public/offline.html`, `web/public/sw.js`, `web/src/lib/session/clear.ts`, `web/src/components/AccountMenu.tsx`. Not merged yet: COACH-5 (call types for NFR-036.4, row A7; drill safety list), ST-082 (`docs/releases/r1-rc.md` (planned)), ST-083 (`docs/design/usability-test-kit-r1.md` (planned)). Where they differ from this file, COACH-5 wins on domain words and §11 gets a row.
- **Builds on:** [`flows-sprint-01.md`](flows-sprint-01.md) §0 (error pattern, A-05, U-01), [`flows-sprint-02.md`](flows-sprint-02.md) (T-01, S-01, V-01), [`flows-sprint-03.md`](flows-sprint-03.md) §0 (unofficial notice, X-00..X-03), [`flows-sprint-04.md`](flows-sprint-04.md) (P-01..P-03, Q-10). Tokens: [`tokens.md`](tokens.md), proven pairs only, no new colour. Components: [`component-accessibility-checklist.md`](component-accessibility-checklist.md).
- **Viewport:** 360 CSS px, one hand, courtside (judgment); reflow to 320 px, no sideways scrolling (NFR-034).

## 0. Conventions (in addition to flows-sprint-01..04 §0)

- **Screen ids.** `N-` is a new family: service states that can appear on any page. X-04 extends the X family. Usability tasks are `UT-1`..`UT-4`; they reuse existing screens and add none.

| Id | Name | Where | Story |
|---|---|---|---|
| N-01 | Service problem (page could not load) | route error boundary, every route (`web/src/app/error.tsx`, `web/src/app/matches/error.tsx`) | ST-075 |
| N-02 | Can't reach the service (device online, no answer) | offline page and route error boundary | ST-075, ST-076 |
| N-03 | Action failed (a save was refused by a server error) | inline on the screen that saved | ST-075 |
| N-04 | Taking longer than usual | inline loading state of any read | ST-074, ST-075 |
| N-05 | Video needs a connection | V-01, G-01 video | ST-078e |
| N-06 | A newer or older version is running (after a deploy or a rollback) | route error boundary | ST-082 |
| X-04 | Some changes are not sent yet (sign-out with unsent marks) | dialog from the account menu | ST-078e |
| (pattern) | Form not ready yet (before hydration) | every form with `onSubmit` | ST-078e |

- **One rule for every degraded state (judgment):** say what happened, what is kept, what to do; never blame the player; never show internals; show `Reference: <support_ref>` only when the API gave one (`ref_` + 16 hex, as `matches/error.tsx` already filters, NFR-058). Never claim more than the system knows: during an outage the app cannot know that "your matches are safe", so it does not say so (ADR 0058 §6: up to 24 h of changes can be undone by a restore).
- **Offline vs. unreachable.** "Offline" only when `navigator.onLine === false`. A network failure or a 502/503/504 while the device is online is "can't reach the service" (N-02). Today both show the offline wording (§1).
- **Kept input.** No degraded state clears what the player typed or chose (SC 3.3.7 [ASB/RPD-07]): setup answers, a tag, a correction, a swap reason, settings. A retry re-sends the same values.
- **Targets and focus:** as flows-sprint-04 §0. "Try again" and "Reload" ≥ 48 px high [DPA/DESIGN-10]; alerts are `role="alert"` and do not move focus unless the page itself failed (N-01, N-02, N-06: focus on `<h1>`).
- **States table format.** Each screen lists Empty, Loading, Error, Offline and Not-found; "N/A" carries its reason. Low-confidence and Low-sample are N/A in Sprint 5: no automatic call and no new metric reaches these screens.

## 1. Flow map and what changes

```
 any route ──load fails, 5xx, online──► N-01 "Sorry, there is a problem" ──"Try again"──► same route
          ──fetch fails or 502/503/504, online──► N-02 "Racket Analytics is not answering" ──"Try again"
          ──device offline──► existing offline states (A-05 offline page, P-01 "as of", M-01 offline)
          ──chunk/script load fails after a deploy or rollback──► N-06 "This page has changed" ──"Reload"
 any save ──5xx──► N-03 inline alert, input kept ──"Try again" (same values)
 any read ──> 1 s──► skeleton/"Loading…" ──> 10 s──► N-04 "This is taking longer than usual"
 V-01 / G-01 video ──offline or media fetch fails──► N-05 (rest of the page works)
 account menu "Sign out" ──outbox has unsent marks──► X-04 ──"Stay signed in" (focus) / "Sign out anyway"──► A-05
                         ──active upload──► existing "Your upload will stop" dialog (unchanged)
```

| Today on `main` (`8c37e98d`) | Problem | Change (owner) |
|---|---|---|
| `offline.html` serves **every** failed navigation: "You're offline. Connect to the internet to get a sign-in link." / "Sign in or create an account" | A signed-in player whose device is online sees a sign-in page during an outage or a restore; wrong cause, wrong action | N-02 wording on the static page, which covers both causes (it cannot know which): §2.2 (senior-frontend-engineer, ST-078e or a follow-up) |
| `app/error.tsx` prints any `error.digest` as "Reference" and says "Your matches and videos are safe." | A Next digest is not a support reference; the safety claim is not known during an outage (ADR 0058 §6) | N-01: same `ref_` filter as `matches/error.tsx`; drop the claim (senior-frontend-engineer) |
| Sign-out clears IndexedDB (`lib/session/clear.ts`), which holds the plan outbox (flows-sprint-04 R4-4) | "Done" marks made offline and not yet sent are lost without a word | X-04 dialog (§3) (senior-frontend-engineer, ST-078e) |
| P-01 offline line "You are offline. This is your plan as of <time>." also shows when the API is down (the service worker serves the kept copy on a network error) | Wrong cause | P-01 line when online: "We can't reach Racket Analytics. This is your plan as of <time>." (FR-124.R3 text unchanged when offline) |

## 2. N family: degraded and error states (ST-075, ST-076, ST-082)

### 2.1 N-01 Service problem

- **Title** "Error: Sorry, there is a problem"; `<h1>` "Sorry, there is a problem with the service". Body: "We could not load this page. Try again in a few minutes." Then `Reference: <support_ref>` when present. Button "Try again" (calls the boundary's reset). Link "Go to your matches" for a signed-in player.
- On `/matches` keep the existing words ("Sorry, we could not load your matches. Try again.").

### 2.2 N-02 Can't reach the service

- **Route boundary (online):** `<h1>` "Racket Analytics is not answering"; "Your device is online, but our service did not answer. Try again in a few minutes. Nothing on this device has been deleted." Button "Try again".
- **Static offline page** (service worker, no account data, cannot tell offline from unreachable): banner "You're offline, or Racket Analytics is not answering."; `<h1>` "We can't load this page"; "Check your connection, then reload this page. If you were signed in, you still are." No sign-in heading on this page any more (A-05's sign-in-offline case keeps its own words on A-01).
- **During a restore or rollback** (ADR 0058 rule 4, REL-1.2) the player sees N-02; there is no maintenance page in R1 (no real users, judgment). §11 PD-FL5-04.

### 2.3 N-03 Action failed

- Inline `role="alert"` at the top of the working area, same place as the screen's existing errors: "<Action> did not save because of a problem on our side. Try again." + reference. `<Action>` is the screen's verb: "Your tag", "Your correction", "Your answer", "Your settings", "The swap". "Mark done" keeps its own outbox path (P-03): a 5xx leaves the mark queued, "Saved on this device, will sync".
- Input kept; "Try again" re-sends the same values; focus stays on the control that was used (SC 4.1.3).

### 2.4 N-04 Taking longer than usual

- 0-1 s: nothing (no flash). 1-10 s: the screen's reserved skeleton and polite "Loading…" (NFR-039). After 10 s: polite status "This is taking longer than usual." and a "Try again" button; the skeleton stays (no layout shift). Thresholds are judgment; NFR-010 p95 300 ms means players should almost never see N-04.

### 2.5 N-05 Video needs a connection

- The service worker never stores media (ST-078e, NFR-067). On V-01 and G-01 offline: "This video needs a connection. The rest of this page works offline." G-01 keeps its checklist (its text alternative). No retry loop.

### 2.6 N-06 This page has changed

- After a deploy or a rollback, an old page can fail to load its scripts. `<h1>` "This page has changed"; "Racket Analytics was updated while this page was open. Reload to continue. Answers on this page may need to be entered again." Button "Reload". The last sentence is honest about SC 3.3.7: setup answers live in memory only (`MatchSetup.tsx`). §11 PD-FL5-03 asks whether to keep them in `sessionStorage` instead.

### 2.7 States

| Id | State | Spec |
|---|---|---|
| N-01 | Empty | N/A: the state replaces the page's content |
| N-01 | Loading | N/A: shown only after a load failed; "Try again" shows the page's own Loading |
| N-01 | Error | this screen |
| N-01 | Offline | becomes N-02 / the offline page |
| N-01 | Not-found | N/A: a 404 is the not-found page, never N-01 |
| N-02 | Empty | N/A: no content to show |
| N-02 | Loading | "Try again" shows the page's own Loading |
| N-02 | Error | this screen |
| N-02 | Offline | static page wording covers it |
| N-02 | Not-found | N/A |
| N-03 | Empty | N/A: needs a save |
| N-03 | Loading | the control shows "Saving…" (existing per screen) |
| N-03 | Error | this notice; a 4xx keeps the screen's own error words |
| N-03 | Offline | the screen's existing offline words (flows-sprint-02 §5, P-03 outbox) |
| N-03 | Not-found | the target was deleted: the screen's existing 404 words |
| N-04 | Empty | N/A |
| N-04 | Loading | this state |
| N-04 | Error | becomes N-01 / N-02 |
| N-04 | Offline | the page's offline state |
| N-04 | Not-found | N/A |
| N-05 | Empty | N/A |
| N-05 | Loading | native video controls |
| N-05 | Error | V-01's existing "This video link no longer works" when online |
| N-05 | Offline | this notice |
| N-05 | Not-found | N/A |
| N-06 | Empty | N/A |
| N-06 | Loading | the browser reload |
| N-06 | Error | this screen |
| N-06 | Offline | the offline page |
| N-06 | Not-found | N/A |
| X-04 | Empty | not shown when the outbox is empty |
| X-04 | Loading | "Signing out…" (existing) |
| X-04 | Error | outbox unreadable: dialog says "We could not check for unsent changes." and keeps both buttons |
| X-04 | Offline | this dialog is most likely offline; text names it (§3) |
| X-04 | Not-found | N/A |

## 3. X-04 Sign-out with unsent marks, and the form lock (ST-078e)

- **X-04 trigger:** "Sign out" when the plan outbox holds ≥ 1 unsent mark. (An active upload keeps the existing "Your upload will stop" dialog; with both, the upload dialog comes first.)
- **Dialog** `<h2>` "Some changes are not sent yet"; "You marked <n> session(s) done while offline. They have not reached Racket Analytics yet. If you sign out now, they are lost from this device." When offline, add "Connect to the internet and wait for 'Synced' to keep them." Buttons: **"Stay signed in"** (focused on open, the safe choice) and "Sign out anyway". Esc = Stay. Focus returns to "Your account".
- **Sign-out result** unchanged: A-05 "The app's data on this device has been cleared." (words never promise more than the clean-up does, DR-03 R3-7).
- **Form not ready yet (pattern).** Until hydration, a form's submit control is `aria-disabled="true"` with its normal label, plus a polite status "Getting the form ready…" after 1 s; on hydration the status clears. No layout shift; full-contrast text (not greyed), because a disabled-looking control with no reason fails players on slow phones (judgment). A tap before hydration does nothing and is not lost silently: the status is the reason.

## 4. Release-notes copy (ST-082; REL-1.1, FR-055.R1)

Text for `docs/releases/r1-rc.md` (planned). ST-082 owns the file and `scripts/ci/check_release_notes.py` (planned); these are the player-facing words, plain language, no WCAG conformance claim (kickoff PD-4).

| Block | Copy |
|---|---|
| Title | "Racket Analytics R1 release candidate" |
| First line (FR-055.R1, verbatim notice) | "unofficial scoring (rules not yet verified)": "Scores and stats follow the rules as we understand them. A rulebook check is still to come, so treat them as unofficial." |
| What you can do | "Record a match and upload it." · "Tag each rally quickly (Quick Tag) and fix any call in two taps or fewer." · "See your score sheet and the changes you made." · "See stats with how many rallies each one is based on, and the rallies behind every number." · "Get a 2-week training plan made from your tagged rallies, with the reason for every drill." · "Mark sessions done, even offline." · "Delete a match or your whole account." |
| Turned off in this release (flags, default off) | "Age question (`FEATURE_AGE_GATE`)", "Choosing how long videos are kept (`FEATURE_RETENTION_SETTING`)", "Consent to use your matches for training (`FEATURE_TRAINING_CONSENT`)", "Upload and match limits (`FEATURE_QUOTAS`)": each "off by default; waits on a legal review (P16)" (quotas: "and on agreed limits (P8)") |
| Known limitations (each with its P-n) | "Scoring is unofficial until the rulebook is checked (P7)." · "The serve/receive split is not yet verified (P7)." · "Drills have not yet been checked by a human coach. Warm up first, and stop any drill that hurts (P15)." · "No real player has tested this release yet (P9)." · "Not yet checked with a screen reader on a phone (P6) or on real iPhones and Android phones (P20)." · "If we ever restore from a backup, changes from the last 24 hours, including deletions, can be undone (ADR 0058)." · "Do not upload real matches yet: this is a preview (P16)." |
| Accessibility | "We design for WCAG 2.2 AA and run automated checks on every change. We do not claim conformance: a manual screen-reader check is still to come (P6)." |

The "unofficial scoring" wording and drill lines are domain claims: pickleball-domain-coach confirms (COACH-5, DR-05 R5-3).

## 5. Usability task screens (ST-083; USAB-1.1, NFR-036.1-.4)

Screens and states for the moderated session (P9). ST-083 writes the kit (`docs/design/usability-test-kit-r1.md` (planned)); this section fixes which screens each task uses, the start state, the success state and what is observed. Set-up per SEC-5 T5-UT-4: a pre-seeded demo account on a local stack reset between testers (`make demo`), no real sign-in address; screen-only capture, no face or voice (T5-UT-1, until P16).

| Task | Item | Start screen and state | Screens walked | Success state (stop the clock) | Observed |
|---|---|---|---|---|---|
| UT-1 Quick Tag | NFR-036.1, .2 | T-01, game 1 started, 0 rallies tagged, a match video of ≥ 20 rallies | T-01 (and K-01 only if the tester asks) | 20 rallies tagged; T-01 call line shows rally 20 | seconds per rally (median); mis-tags per 20 against the moderator's key |
| UT-2 Upload to plan | NFR-036.3 | M-01 with the seeded demo match only | M-01 → Q-01..Q-07 → U-01 → U-02 → M-02 → T-02 → T-01 → S-01 → D-01 → P-02 → P-01 | P-01 shows the first drill and its "Why" line | minutes, start to success; where the tester stalls > 30 s |
| UT-3 Fix a call | NFR-036.4 (observed; ST-080 counts it automatically) | S-01 with one planted wrong call per call type (rally winner, fault, rally ending; COACH-5 row A7) | S-01 (and T-01 review) | the row shows "corrected by you" and the live region confirms | taps/keys per call type; hesitation |
| UT-4 Trace a drill (not a gate) | Product Goal "traceable" | P-01 of the demo plan | P-01 → E-01 → S-01 at the rally | tester names the rally behind a drill | success yes/no; words the tester uses |

- **Task cards** (read aloud, no UI words): UT-1 "Tag what happened in each rally of this game, as you would after playing." UT-2 "You just played this match. Get a training plan from it." UT-3 "One of these calls is wrong. Put it right." UT-4 "Why did the app suggest this drill? Show me."
- **Screen states the kit must prepare:** UT-1 and UT-2 need a match video with people in it; until P16 and P11 settle footage, the session cannot record or use tester footage (T5-UT-1, T5-UT-3). §11 PD-FL5-01. UT-3 needs a seeded wrong call per type (QA seeds through the API, as the a11y manual script does).
- **Safety:** drills shown in UT-2 and UT-4 come from COACH-5's safety-reviewed list; the human-coach notice stays visible (P15).
- **No new screen state** is added for testers: the session uses R1 as shipped, so findings are about R1 (judgment).

## 6. HAX checklist (Sprint 5 scope) [DPA/DESIGN-11]

| Guideline | Where | Design response |
|---|---|---|
| G1 What the system can do | release notes §4 | Lists what R1 does in player words; no AI or video-analysis claim (R1 has no vision, ADR 0002) |
| G2 How well it can do it | release notes §4; N-family | "unofficial scoring" first; limitations with P-n; degraded states say what is not known |
| G9 Efficient correction | UT-3; ST-080 | Any call fixed in ≤ 2 taps or keys (NFR-036.4), measured per call type |
| G11 Why | UT-4 | Drill "Why" and "Show me" walked by testers |
| G18 Notify users about changes | N-06; release notes | A changed version is named and a reload offered; nothing changes silently mid-task |
| Others | — | No new automatic call, learning or LLM text in Sprint 5 |

## 7. WCAG 2.2 AA per-SC gap list (kickoff PD-4)

**Scope:** every R1 page family (A, F, G, Q, U, M, T, K, S, H, V, D, E, X, L, P, R, Q-10, N). WCAG 2.2 has 31 Level A and 24 Level AA criteria; AA conformance needs all 55 on every page of a complete process [ASB/RPD-08]. The component checklist names 27 of them. **This list is not a conformance claim.** "Spec" = a flows file says how; "Auto" = an automated check exists (axe with WCAG 2.2 AA tags in `web/e2e/helpers/axe.ts`, the 24 px target helper, keyboard and 320 px specs); "Manual" = the human pass, **not run for any SC (P6)** [ASB/RPD-10]. SC 4.1.1 is not listed: removed from WCAG 2.2 [ASB/RPD-09]. "In list" = in the component checklist.

| SC | Lvl | In list | Spec | Auto | Gap / action (owner) |
|---|---|---|---|---|---|
| 1.1.1 Non-text content | A | no | yes (icons with words, G-01 images) | axe | add to checklist (PD) |
| 1.2.1 Audio/video only | A | no | — | — | N/A: no audio-only or silent video content of ours; player match video is user content (judgment) |
| 1.2.2 Captions (prerecorded) | A | yes | G-01 | partly (captions on at mount) | manual check of caption text (P6) |
| 1.2.3 Audio description or alternative | A | yes | G-01 checklist | — | manual (P6) |
| 1.2.4 Captions (live) | AA | no | — | — | N/A: no live media |
| 1.2.5 Audio description (prerecorded) | AA | no | — | — | **gap**: the guide video has no audio description; either its narration covers all visual steps or one is added (PD with coach; ticket next sprint) |
| 1.3.1 Info and relationships | A | yes | yes | axe | manual (P6) |
| 1.3.2 Meaningful sequence | A | no | yes (order per screen, §11 layouts) | keyboard specs | add to checklist (PD) |
| 1.3.3 Sensory characteristics | A | no | yes (words, not "the green button") | — | **gap**: no check; add a copy-review row to the checklist (PD) |
| 1.3.4 Orientation | AA | yes | yes | — | **gap**: no test in landscape (ST-079 device checklist, P20) |
| 1.3.5 Identify input purpose | AA | yes | A-01 `autocomplete="email"` | axe | Q-03 nicknames `autocomplete="off"`: names of other players too (judgment, DR-05 R5-5) |
| 1.4.1 Use of colour | A | yes | yes | — | manual (P6) |
| 1.4.2 Audio control | A | no | no autoplay | — | N/A while nothing plays on its own |
| 1.4.3 Contrast (minimum) | AA | yes | proven token pairs | axe, `contrast_check.py` | — |
| 1.4.4 Resize text | AA | yes | rem text | axe (viewport) | **gap**: no 200 % zoom test (QA) |
| 1.4.5 Images of text | AA | no | none used | — | add to checklist (PD) |
| 1.4.10 Reflow | AA | yes | §11 per sprint | 320 px specs | — |
| 1.4.11 Non-text contrast | AA | yes | tokens | partly | court overlays N/A until R2 |
| 1.4.12 Text spacing | AA | no | — | — | **gap**: no spacing-override test (QA, next sprint) |
| 1.4.13 Content on hover or focus | AA | no | no tooltips | — | add to checklist (PD) |
| 2.1.1 Keyboard | A | yes | yes | keyboard specs | — |
| 2.1.2 No keyboard trap | A | no | dialogs return focus | partly (ST-085 close paths) | add to checklist (PD) |
| 2.1.4 Character key shortcuts | A | no | K-01 single-key switch off/remap | — | **gap**: no test that the switch turns them off (QA) |
| 2.2.1 Timing adjustable | A | yes | sign-in link 15 min (security; new link on A-04) | — | judgment: essential limit with recovery (DR-05 R5-5) |
| 2.2.2 Pause, stop, hide | A | no | no moving content | — | N/A |
| 2.3.1 Three flashes | A | no | none | — | N/A |
| 2.4.1 Bypass blocks | A | yes | skip link | axe | — |
| 2.4.2 Page titled | A | no | "Error: " prefix | axe | add to checklist (PD) |
| 2.4.3 Focus order | A | yes | yes | keyboard specs | — |
| 2.4.4 Link purpose | A | yes | yes | axe | — |
| 2.4.5 Multiple ways | AA | no | menu + links | — | **gap**: not reviewed; M-01 list and account menu are the two ways (PD review) |
| 2.4.6 Headings and labels | AA | no | yes | — | add to checklist (PD) |
| 2.4.7 Focus visible | AA | yes | tokens | — | manual (P6) |
| 2.4.11 Focus not obscured | AA | yes | no sticky bars | — | — |
| 2.5.1 Pointer gestures | A | yes | no multipoint | — | — |
| 2.5.2 Pointer cancellation | A | no | native buttons | — | add to checklist (PD) |
| 2.5.3 Label in name | A | yes | yes | — | manual (P6) |
| 2.5.4 Motion actuation | A | no | none | — | N/A |
| 2.5.7 Dragging movements | AA | yes | no drag | — | court calibration N/A until R2 |
| 2.5.8 Target size (minimum) | AA | yes | ≥ 24 px, primary ≥ 48 | target helper | — |
| 3.1.1 Language of page | A | yes | `lang="en"` | axe | — |
| 3.1.2 Language of parts | AA | no | English only | — | N/A |
| 3.2.1 On focus | A | no | no change on focus | — | add to checklist (PD) |
| 3.2.2 On input | A | no | changes need "Continue"/"Save" | — | add to checklist (PD) |
| 3.2.3 Consistent navigation | AA | no | one header | — | add to checklist (PD) |
| 3.2.4 Consistent identification | AA | no | same names (copy registers) | — | add to checklist (PD) |
| **3.2.6 Consistent help** | A | yes | see below | — | **gap**: no test; static offline page and N-02 have no account menu (allowed: help absent, not reordered) |
| 3.3.1 Error identification | A | no | error summary | E2E per form | add to checklist (PD) |
| 3.3.2 Labels or instructions | A | no | question pages | — | add to checklist (PD) |
| 3.3.3 Error suggestion | AA | no | fix in every message | — | add to checklist (PD) |
| 3.3.4 Error prevention (legal, financial, data) | AA | no | X-01, X-02, A-12 confirm; R-01 dialog | E2E | add to checklist (PD) |
| **3.3.7 Redundant entry** | A | yes | see below | partly | **gap**: setup answers lost on reload (N-06) |
| 3.3.8 Accessible authentication | AA | yes | magic link, no cognitive test | — | — |
| 4.1.2 Name, role, value | A | yes | yes | axe | manual (P6) |
| 4.1.3 Status messages | AA | yes | polite regions per screen | partly | manual (P6) |

**SC 3.2.6 Consistent help [ASB/RPD-06].** Help mechanisms in R1: the account-menu link "How to film your match" (self-help, every signed-in page, header, same place); "How is this measured?" is in-context help on D-01, not a site-wide mechanism (judgment). No human contact or contact form exists, so a `Reference:` code has nowhere to go (usability gap, not a WCAG failure; PD-FL5-05). N-01, N-03..N-06 and X-04 render inside the layout, so the menu keeps its place. Evidence to add: an E2E check that on each signed-in page family the account-menu items appear in the same order and before `<main>` (senior-qa-engineer; PD-FL5-06).

**SC 3.3.7 Redundant entry [ASB/RPD-07].** Met by design: Q-07 "Change" returns prefilled; Q-10 keeps answers after a 429 (flows-sprint-04 §7); P-02 regenerate prefilled; P-03 reason kept on error; N-03 keeps input on every 5xx. Exception, documented: A-04 asks for the email again because the address is never stored on the device (security, NFR-055; D-4). Gap: setup answers live in memory, so a reload (N-06, or the player's own) loses them (PD-FL5-03).

## 8. Copy register (proposed)

| Screen | Text | Status |
|---|---|---|
| N-01 | "Sorry, there is a problem with the service" / "We could not load this page. Try again in a few minutes." | replaces the "safe" claim |
| N-02 | "Racket Analytics is not answering" / "Your device is online, but our service did not answer. Try again in a few minutes. Nothing on this device has been deleted." | new |
| N-02 (static) | "You're offline, or Racket Analytics is not answering." / "We can't load this page" / "Check your connection, then reload this page. If you were signed in, you still are." | replaces `offline.html` words |
| P-01 | "We can't reach Racket Analytics. This is your plan as of <time>." | online-but-unreachable variant of FR-124.R3 |
| N-03 | "<Action> did not save because of a problem on our side. Try again." | new |
| N-04 | "This is taking longer than usual." | new |
| N-05 | "This video needs a connection. The rest of this page works offline." | new |
| N-06 | "This page has changed" / "Racket Analytics was updated while this page was open. Reload to continue. Answers on this page may need to be entered again." | new |
| X-04 | "Some changes are not sent yet" / "You marked <n> session(s) done while offline. …" / "Stay signed in" / "Sign out anyway" | new |
| Form lock | "Getting the form ready…" | new |
| Release notes | §4 | PM and coach confirm (R5-3) |

## 9. Accessibility notes per new state

| Check | N-01 | N-02 | N-03 | N-04 | N-05 | N-06 | X-04 | Form lock |
|---|---|---|---|---|---|---|---|---|
| Title / `<h1>` (SC 2.4.2) | "Error: " prefix | "Error: " prefix | host page | host page | host page | "Error: " prefix | dialog `<h2>` | host page |
| Announce (SC 4.1.3) | focus `<h1>` | focus `<h1>` | alert | polite | polite | focus `<h1>` | dialog | polite |
| Input kept (SC 3.3.7) | — | — | yes | yes | — | warns | — | yes |
| Targets ≥ 48 px primary (SC 2.5.8) | yes | yes | yes | yes | — | yes | yes | — |
| Words, not colour (SC 1.4.1) | yes | yes | yes | yes | yes | yes | yes | not greyed |
| Reflow 320 px (SC 1.4.10) | yes | yes | yes | yes | yes | yes | buttons stack, "Stay" first | yes |

## 10. Traceability

| Item | Screens | Test owner |
|---|---|---|
| ST-075 (NFR-041 drill) | N-01, N-02, N-03 | sre-devops-engineer drill shows N-01 on an injected 5xx (`X-Racket-Fault`, test stack only) |
| ST-078e (NFR-067.2-.3, NFR-050.8) | X-04, N-05, form lock | senior-frontend-engineer: `web/e2e/sprint-05/logout-hygiene.spec.ts` (planned) |
| ST-080 (NFR-036.4) | S-01, T-01 (UT-3) | senior-qa-engineer: `web/e2e/sprint-05/fix-call-taps.spec.ts` (planned) |
| ST-082 (REL-1.1, FR-055.R1) | release notes §4; N-06 | sre-devops-engineer, checker |
| ST-083 (USAB-1.1) | UT-1..UT-4 | principal-designer |
| FR-124.R3 | P-01 unreachable line | senior-frontend-engineer (ST-085) |

## 11. Open items and routed

| Id | Item | Owner |
|---|---|---|
| PD-FL5-01 | UT-1 and UT-2 need a match video with people; tester footage waits on P16 and P11 (T5-UT-1, T5-UT-3). Options: a consented team video, or the session runs UT-1/UT-2 only after P16 | product-manager (EM-ESC-05), security-privacy-engineer |
| PD-FL5-02 | NFR-036.4 call types (A7) | pickleball-domain-coach (COACH-5) |
| PD-FL5-03 | Keep setup answers in `sessionStorage` so a reload keeps them (SC 3.3.7); cleared on sign-out by `clear.ts` | senior-frontend-engineer, security-privacy-engineer |
| PD-FL5-04 | No maintenance page for restore/rollback in R1; needed before any real-user beta | sre-devops-engineer, product-manager |
| PD-FL5-05 | No contact path for a `Reference:` code | product-manager |
| PD-FL5-06 | E2E check for SC 3.2.6 (menu order per signed-in family), 1.4.12 text spacing, 1.4.4 200 % zoom, 2.1.4 key switch | senior-qa-engineer (next sprint ticket) |
| PD-FL5-07 | Guide video audio description (SC 1.2.5) | principal-designer, pickleball-domain-coach |
| PD-FL5-08 | 28 of the 55 SCs are not in `component-accessibility-checklist.md`: add the 21 that apply (16 "add to checklist", 5 gaps); the 7 N/A rows stay here with their reason | principal-designer (follow-up PR, one section per family, PD-6) |

## 12. Not in scope

Any new route or feature; a WCAG conformance claim; running the usability session (P9); the screen-reader pass (P6); real-device checks (P20).

## 13. Design review record (DR-05)

| Date | Participants | Outcome |
|---|---|---|
| Opened 2026-11-03; cells due **2026-11-05** (wave 1 merge-by, sprint-05 §3.6); escalation to the PO in EM-ESC-05 the same day if a cell is empty | principal-designer (chair), senior-frontend-engineer, product-manager, pickleball-domain-coach, security-privacy-engineer, sre-devops-engineer, senior-qa-engineer | **Not yet held on 2026-11-03.** Asynchronous, in the repository: each decider writes "accept / reject (YYYY-MM-DD): one line of reason" in its own cell and commits it. The chair does not write other roles' cells (ADR 0037 rule 2). Held when every row has a dated cell; a reject returns to the chair the same day. Gates: ST-083 (kit), and the copy in ST-078e, ST-080, ST-082 |

### 13.1 Agenda (chair's proposals, judgment unless cited)

| # | Item | Proposal | Decides |
|---|---|---|---|
| R5-1 | N-01..N-06: offline vs. unreachable, no safety claim, `ref_` filter, input kept, 1 s / 10 s thresholds (§1, §2) | Accept | senior-frontend-engineer, sre-devops-engineer, product-manager |
| R5-2 | X-04 dialog with "Stay signed in" focused; form lock with status text, not greyed (§3) | Accept | senior-frontend-engineer, security-privacy-engineer |
| R5-3 | Release-notes copy, limitations with P-n, no conformance claim (§4) | Accept | product-manager, pickleball-domain-coach, sre-devops-engineer |
| R5-4 | Usability task screens UT-1..UT-4, start and success states, footage constraint (§5) | Accept | pickleball-domain-coach, security-privacy-engineer, senior-qa-engineer, product-manager |
| R5-5 | WCAG per-SC gap list incl. 3.2.6 and 3.3.7; Q-03 autocomplete and link-expiry judgments (§7) | Accept | senior-frontend-engineer, senior-qa-engineer |

### 13.2 DR-05 decider cells

Scheduled: one row per decider; the decider replaces "pending" with its cell for the items named, by the Due date.

| Role | Items | Opened | Due | Cell |
|---|---|---|---|---|
| principal-designer | R5-1..R5-5 | 2026-11-03 | — | accept (2026-11-03): author |
| senior-frontend-engineer | R5-1, R5-2, R5-5 | 2026-11-03 | 2026-11-05 | pending |
| product-manager | R5-1, R5-3, R5-4 | 2026-11-03 | 2026-11-05 | pending |
| pickleball-domain-coach | R5-3, R5-4 | 2026-11-03 | 2026-11-05 | pending |
| security-privacy-engineer | R5-2, R5-4 | 2026-11-03 | 2026-11-05 | pending |
| sre-devops-engineer | R5-1, R5-3 | 2026-11-03 | 2026-11-05 | pending |
| senior-qa-engineer | R5-4, R5-5 | 2026-11-03 | 2026-11-05 | pending |

**Hold status, 2026-11-03 (chair).** All six deciders are agent roles; none is human-only. `ListAgents` on 2026-11-03 → "No reachable agents", so the chair could not collect cells in this step. `check_docs.py` (PRC-3.4) runs `check_flows.py --decider` on this file for every row, so this PR stays **draft** until each decider commits its cell on branch `s05/pd-5-flows-sprint-05-md-degraded-error-states`, or the PO grants a waiver (CI-DOC-CHECK decision row 5). The check is not changed.
