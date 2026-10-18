# Sprint 4 flows: training plan (P), age question (A), privacy settings (R), over-limit messages (Q)

- **Status:** Draft v0.1, 2026-10-17 (principal-designer, gate ticket PD-4). **Written before any Sprint 4 UI was built** (`ls web/src/app` → no `plan`, no `settings/privacy`, no age page). Design review **DR-04 is opened in §14 and is not yet held.** Until §14 records "held", this file is a proposal, and no Sprint 4 UI ticket (ST-063a/b/c, ST-068b, ST-071, ST-072b) starts without a PO waiver (sprint-04 §0.1, §3.8; ADR 0047 rule 2).
- **Stories:** ST-063a plan page, ST-063b preferences, ST-063c done offline and "Not for me" (family P); ST-068b age question and footage notice (A); ST-071 privacy settings (R); ST-072b over-limit messages (Q).
- **Requirements:** FR-003, FR-008, FR-009, FR-120..FR-124, FR-160; NFR-019, NFR-023, NFR-027, NFR-028, NFR-034, NFR-039, NFR-058.
- **Design sources:** DES FR-UX-03, FR-UX-80, FR-UX-81, FR-UX-90 and the §4 plan states in [`brainstorm-design.md`](../requirements/brainstorm-design.md); HAX [DPA/DESIGN-11]; question pages [DPA/DESIGN-12]; error summary [DPA/DESIGN-13]; targets [DPA/DESIGN-02, DPA/DESIGN-10]; contrast [DPA/DESIGN-03, DPA/DESIGN-04]; focus not obscured [DPA/DESIGN-07]. Everything else is (judgment).
- **Contract and inputs not yet merged on 2026-10-17:** PE-4 (`api-sprint-04.md`: field and code names), COACH-4 (weakness names, catalogue order, equipment and level words), PM-4 (interim wording register for the four flags, P16). Field names below are **placeholders** written as `plan.limited_data`; the FE takes the PE-4 names. Where PE-4 or PM-4 differ, they win and §12 gets a row.
- **Builds on:** [`flows-sprint-01.md`](flows-sprint-01.md) §0 (question pages, error pattern, A-03, F-01, Q-06, Q-07, U-01), [`flows-sprint-03.md`](flows-sprint-03.md) §0 (unofficial notice, numbers in text, low sample, E-01 panel, dialogs, X-00). Tokens: [`tokens.md`](tokens.md), only proven pairs, no new colour. Components: [`component-accessibility-checklist.md`](component-accessibility-checklist.md).
- **Viewport:** 360 CSS px, one hand, courtside (judgment); reflow to 320 px with no sideways scrolling (NFR-034). §11 gives both layouts per screen.

## 0. Conventions (in addition to flows-sprint-01 §0 and flows-sprint-03 §0)

- **Screen ids.** The ticket names "A-01" and "Q-01" are already taken by sign-in and the first setup question (flows-sprint-01 §2, §5), and the axe and target attachments of G04-08 are keyed by screen id. So the new age screens are **A-10/A-11** and the over-limit messages **Q-10** (decision PD-4 row 2). P- and R- are new families.

| Id | Ticket name | Screen | Route | Story |
|---|---|---|---|---|
| P-01 | P-01 | Your training plan | `/plan` | ST-063a |
| P-02 | P-02 | Plan preferences | `/plan/new` | ST-063b |
| P-03 | P-03 | Mark done (offline) and "Not for me" (dialog on P-01) | `/plan` | ST-063c |
| A-10 | A-01 | Are you 18 or over? | `/welcome/age` | ST-068b |
| A-11 | A-01 | You need to be 18 or over (outcome, pending sign-in: no account existed) | `/welcome/age?under=1` | ST-068b |
| A-12 | A-01 | Delete your account? (existing account answered "No") | `/welcome/age/delete` | ST-068b |
| A-13 | A-01 | Your account has been deleted (outcome after A-12) | `/signed-out?deleted=1&under=1` (A-05 route, X-03 text plus one line) | ST-068b |
| (notice) | footage notice | Footage notice on F-01, Q-06 and U-04 | existing routes | ST-068b |
| R-01 | R-01 | Privacy settings | `/settings/privacy` | ST-071 |
| Q-10 | Q-01 | Over-limit messages on Q-07 and U-01 | existing routes | ST-072b |

- **States.** Every screen lists Empty, Loading, Error, Offline and Not-found, plus Low-sample where a metric value is printed. "N/A" carries its reason. Low-confidence is N/A in Sprint 4: no automatic call (no vision) reaches these screens.
- **Unofficial.** While the plan says `unofficial: true`, P-01 shows the flows-sprint-03 notice "unofficial scoring (rules not yet verified)" **once, before the first card** (DR-03 R3-3, metric-dictionary rule 0.5). It also covers the side-out part of the serve/receive split, which is unverified (P7).
- **Human-coach notice (interim, ADR 0051 rule 3).** While any drill in the plan is `coach-reviewed` and not `verified`, P-01 shows under the unofficial notice: "These drills have not yet been checked by a human coach. Warm up first, and stop any drill that hurts." It goes when every drill is `verified` (P15).
- **Numbers in text** as flows-sprint-03 §0 ("29%", rates with at most one decimal). Every value carries its n.
- **Flags.** A, R and Q screens appear only when the public config says the flag is on (`feature_age_gate`, `feature_retention_setting`, `feature_training_consent`, `feature_quotas`; names per PE-4). Flag off → the screen does not exist (route is the app's not-found page) and no existing screen changes.
- **Interim wording.** Texts behind the four flags are interim pending the legal review (NFR-070, P16). The UI does not say "interim"; the copy register (§8) and PM-4's register do. PM-4's words replace mine where they differ.
- **Errors**: one `role="alert"` notice at the top of the working area with what happened, what to do and `Reference: <support_ref>` (NFR-058); form errors use the error summary [DPA/DESIGN-13] and the `Error: ` title prefix.
- **Targets:** every control ≥ 24×24 CSS px (SC 2.5.8); "Mark done", "Not for me", "Show me", "Make my plan", "Continue" and "Save" ≥ 48 px high [DPA/DESIGN-10]; ≥ 8 px between adjacent targets. No sticky bar on any Sprint 4 screen (SC 2.4.11).

## 1. Flow map

```
 D-01 Stats ──"Your training plan"──┐      account menu ──"Training plan"──┐
                                    ▼                                      ▼
 P-01 Your training plan ◄──created── P-02 Plan preferences ◄──"Make my plan" / "Change my setup"── P-01
   │ "Show me" (per drill) ──► E-01 panel (rallies behind the cited value) ──► S-01 at the rally
   │ "Mark done" ──online──► done ;  ──offline──► "Saved on this device, will sync" ──online──► done
   │ "Not for me" ──► P-03 dialog (reason optional) ──swap──► new drill focused ; 409 ──► "no other drill fits"
 A-03 Signing you in ──new address or unconfirmed account, age flag on──► A-10 Are you 18 or over? ──yes──► F-01 (with footage notice)
                                                                     ├──no, pending sign-in (403 under_age)──► A-11 (no account created)
                                                                     └──no, existing account (422 confirmation_required)──► A-12 Delete your account?
 A-12 ──"Delete my account" (confirm: delete; 403 under_age)──► A-13 "Your account has been deleted"
      └──"Cancel"──► A-10 (nothing deleted; account stays unconfirmed and gated)
 X-00 Your account / account menu ──"Privacy settings" (flag on)──► R-01
 Q-07 "Create match and upload" ──429 rate_limited──► Q-10 notice on Q-07 (answers kept)
 U-01 upload start ──storage quota refused──► Q-10 notice on U-01 (nothing stored)
```

## 2. P-01 Your training plan (ST-063a; FR-120, FR-122, FR-123)

- **Title** "Your training plan"; `<h1>` the same. Under it: "Made on <date> from <n> tagged matches." and the link "Change my setup" (→ P-02, prefilled).
- **Notices, in this order, before the first card:** unofficial notice (§0); human-coach notice (§0); **limited-data banner** when `plan.limited_data` is set: "Based on limited data from <N> rallies. Tag more matches for a firmer plan." (FR-123; `warning-text` on `warning-surface`, words not colour).
- **"What the plan works on"** (`<h2>`): the top 3 weaknesses as a numbered list (FR-UX-80). Each item: weakness name (COACH-4, from the API), "<x> rallies lost per game" (unit name from the API, ADR 0003), then "On serve: <a> · On receive: <b> · Points given away: <c> per game" (FR-120: points conceded shown separately; words per coach) and "from <g> games". One line under the list, once: "The split between serve and receive is not yet verified." (Gherkin "marked as not yet verified"). A weakness with no drill that fits says "No drill fits your setup for this one." with the link "Change my setup".
- **"Your sessions"** (`<h2>`): "Week 1" and "Week 2" (`<h3>`), each a checklist of sessions "Session 1 of 3 · 30 minutes". Each session lists its drills in order; the first is the warm-up and says "Warm-up".
- **Drill row** (FR-UX-81): name; "<m> minutes · <p> player(s) · Needs: a wall" (or "Needs: nothing extra"); **"Why: <metric name>: <value> of <n> <unit>"**, e.g. "Why: Serve faults: 29% of 7 serves" (FR-122; ST-057); the low-sample tag "low sample" after the value when that metric is low-sample (flows-sprint-03 §0); button **"Show me"** (accessible name "Show me the rallies behind Serve faults, 29%") and button **"Not for me"** (P-03).
- **"Show me"** opens the E-01 panel inline under the row (reuses `EvidencePanel`): the cited rallies (≤ 10), grouped by match ("<match title>, rally 7"), each opening S-01 at that rally (DR-03 R3-4), and "See all n" per match → E-02. The panel takes the plan's `rally_ids`, not a fresh stats read, so it shows what the plan used (stale line as E-01 when `sheet_version` moved).
- **Session done:** a "Mark done" button per session (P-03); a done session shows "Done" with a check icon and "Undo".
- **Nav:** "Your training plan" link on D-01 under the header and "Training plan" in the account menu.

| Screen | State | What the player sees |
|---|---|---|
| P-01 | Empty | 409 `no_tagged_match`: "Tag a match to get a plan. The plan is built from the rallies you tag." Link "Your matches" (M-01). 404 `no_plan` with a tagged match: "You have no plan yet." Button "Make my plan" (→ P-02) |
| P-01 | Loading | Skeleton of the header, notices and 3 weakness lines at their final height (NFR-039), `aria-busy="true"`; polite "Loading your plan" |
| P-01 | Error | Alert "We could not load your plan. Try again." with "Try again" and `Reference:`. A drill row without a citation shows "We could not show why this drill was chosen." in that row, never a blank (ST-063a negative test) |
| P-01 | Offline | Last plan from the service-worker cache with "You are offline. This is your plan as of <time>." "Mark done" still works (P-03); "Not for me", "Show me" and "Change my setup" are disabled with "Needs a connection" in text at full contrast (tokens §3 rule 4). No cached plan → "You are offline and this plan is not saved on this device yet." |
| P-01 | Not-found | 404 on a session or drill id (plan replaced on another device, or deleted match): "Your plan changed on another device. Showing your current plan." and a refetch. Unknown sub-route → app not-found page |
| P-01 | Low-sample | Banner with N (FR-123) and "low sample" on each affected "Why" value; values never hidden |

## 3. P-02 Plan preferences (ST-063b; FR-121)

- **One page, five short questions** with fieldsets, not one question per page (decision PD-4 row 3): a regenerate visit changes one answer, and five pages for that would be slower. `<h1>` "Your practice setup". Prefilled with the last preferences on a regenerate visit.
  1. "How long is each session?" number input, "minutes", hint "Between 15 and 180." (api-sprint-04 §2.1: 15-180).
  2. "How many sessions a week?" radios 1-7.
  3. "How many players, including you?" radios 1, 2, 3, 4.
  4. "What do you have?" checkboxes (optional): "A wall", "Half a court", "A full court", "A ball machine", "Someone to feed balls" (drill-schema `needs`; words per coach).
  5. "Your level" radios "Beginner", "Intermediate", "Advanced" (words per coach).
- Button **"Make my plan"**. Under it: "This replaces your current plan." on a regenerate visit. Weekly limit = minutes × sessions (judgment; PE-4 may add a separate weekly field, then it is question 3 with the hint "Leave blank to use sessions × minutes").
- **409 `no_plan_fits`** (api-sprint-04 §2.1, assembly infeasible): alert at the top, not the error summary (no field is wrong on its own): "No plan fits these settings. Try more minutes, more sessions or more equipment." On a regenerate visit, a second line: "Your current plan is unchanged." Focus moves to the alert; the answers stay; nothing is written.
- **409 `plan_conflict`** (api-sprint-04 §3.4, the plan changed on another device during the request): alert "Your plan changed on another device, so this one was not saved. Your answers are kept." with the button "Make my plan" still enabled (a new press replaces the current plan, as the "This replaces your current plan." line says) and the link "See your current plan" (→ P-01). Focus moves to the alert; nothing is written.
- Validation (422 field codes): "Enter the minutes for each session" / "Enter a number between 15 and 180" / "Choose how many sessions a week" / "Choose how many players" / "Choose your level". Summary links to each field; the field keeps the value.

| Screen | State | What the player sees |
|---|---|---|
| P-02 | Empty | First visit: nothing prefilled, no default chosen (no hidden assumption about the player). 409 `no_tagged_match` on submit: "Tag a match first. Your plan is built from the rallies you tag." with link "Your matches"; the answers stay |
| P-02 | Loading | "Making your plan…" on the button (disabled, `aria-busy`), polite status; ≤ 5 s expected (NFR-019); after 10 s "Still working…" |
| P-02 | Error | Error summary for 422; alert for 409 `no_plan_fits` and 409 `plan_conflict` (texts above); alert with `Reference:` for 5xx; answers kept in every case |
| P-02 | Offline | Form readable and editable; "Make my plan" disabled with "Needs a connection to make your plan." |
| P-02 | Not-found | N/A: P-02 reads no resource by id; an unknown sub-route is the app's not-found page |

## 4. P-03 Mark done offline and "Not for me" (ST-063c; FR-124; HAX G8, G15)

- **Mark done** (per session): online → "Done" at once (optimistic), confirmed by the server; offline → the op is kept on this device and the row says "Saved on this device, will sync" (polite status). Sync on reconnect and on page load; then "Done" and the polite status "Session 2 synced." Pressing twice offline stores one op (idempotent, ST-062). **Undo** → "Not done"; offline undo removes the queued op.
- **"Not for me"** opens a dialog (`role="dialog"`, labelled by its `<h2>` "Swap <drill name>?"): text "We will pick another drill that works on the same thing and fits your session."; optional reason field "Why not? (optional)", 200 characters, with a counter; buttons **Cancel** (focused on open, flows-sprint-03 §0) and **"Swap drill"**. Success → the dialog closes, the new drill replaces the row and **gets focus**, polite status "Swapped for <new name>." The swapped-out drill is not offered again in this plan.
- **409 `no_alternative`**: inside the dialog, alert "No other drill fits your setup for this. Your plan is unchanged." with "Close"; focus moves to the alert.
- **409 `session_done`** (swap on a session already done, e.g. marked done on another device): inside the dialog, alert "This session is already done, so its drills cannot be swapped. Your plan is unchanged." with "Close"; focus moves to the alert. On close, P-01 refetches, the session shows "Done", and focus returns to that session's "Undo".
- **409 `plan_conflict` on swap** (api-sprint-04 §3.4): inside the dialog, alert "Your plan changed on another device. Nothing was swapped." with the button "Reload plan". It closes the dialog and refetches P-01; focus goes to the same drill row if it is still in the plan, else to the `<h1>`. The reason text is not kept (it belonged to a drill that may be gone; judgment).
- **409 `plan_conflict` on mark done or undo**: the op stays queued, P-01 refetches with the polite status "Your plan changed on another device. Showing your current plan.", and the op is sent once more after the refetch. If its session is gone (404), the sync-conflict line below applies.
- **409 `idempotency_key_reused` on mark done** (the device reused an op id for another session; a client fault, not the player's): the queued op gets a new op id and is sent once more, with no message (a new key on that session is allowed, api-sprint-04 §3.1). If that send fails too, the Done Error state applies (op kept). Never a raw code.
- **Sync conflict** (session gone or plan replaced): "We could not save 'done' for a session that is no longer in your plan." in the row area; the op is dropped (data loss is shown, not hidden).

| Screen | State | What the player sees |
|---|---|---|
| P-03 | Empty | N/A: P-03 acts on an existing session or drill; with no plan, P-01's Empty state applies |
| P-03 | Loading | "Swap drill" shows "Swapping…" (disabled); "Mark done" has no spinner (optimistic) |
| P-03 | Error | Done: "We could not save 'done'. It stays on this device and will sync." (op kept, ST-063c negative test); 409 `plan_conflict` and `idempotency_key_reused` as above. Swap: 409 `no_alternative`, `session_done`, `plan_conflict` as above; 5xx → alert in the dialog with `Reference:`, the reason text is kept |
| P-03 | Offline | Done is queued (above). "Not for me" is disabled with "Needs a connection" (a swap needs the library and the server's invariants) |
| P-03 | Not-found | 404 on the session or drill: the sync-conflict line above, then P-01 refetches |

## 5. A-10 / A-11 Age question and the footage notice (ST-068b; FR-003; flag `feature_age_gate`)

- **A-10** (question page [DPA/DESIGN-12]): after A-03, and after any 403 `age_confirmation_required`, in two cases (api-sprint-04 §4): a **pending sign-in** (new address, no account row) and an **existing account whose age is not confirmed** (it may hold matches, videos, tags and stats). The page looks the same in both; the client does not know which case it is until the answer. `<h1>` "Are you 18 or over?" Radios "Yes, I am 18 or over" / "No, I am under 18". Hint: "You need to be 18 or over to have an account. We do not ask for or keep your date of birth." Button "Continue". No "Back" link (there is no earlier page). Nothing else of the app is reachable until answered (routes answer 403 `age_confirmation_required`; the client sends them here).
- **Yes** → F-01, which shows the footage notice (an existing account goes to D-01 instead, judgment: it has seen F-01).
- **No**: the client sends `{"is_adult": false}` **without** `confirm`. Pending sign-in → 403 `under_age` → **A-11**. Existing account → **422 `confirmation_required`** (field `confirm`), nothing changed → **A-12**. This 422 is a step, not an error: the player sees no error summary and no "Error: " title prefix.
- **A-11** (pending sign-in only; its text is false for an existing account, which goes to A-12) `<h1>` "You need to be 18 or over to use this app". "We have not created an account, and we have not kept your email address." What to do instead (PM-4 wording; proposal): "You can come back when you are 18." Link "Close and return to the start" (→ `/`). No way to change the answer from here (the pending sign-in is gone, ST-068a); signing in again asks again.
- **A-12** (existing account answered "No"; the account-deletion page api-sprint-04 §4 requires, built from X-02, flows-sprint-03): `<h1>` "Delete your account?" Text: "You told us you are under 18. You need to be 18 or over to have an account, so we need to delete yours." Then X-02's consequences: "This deletes your account and all your matches: every video, tag, score sheet and stat." / "You will be signed out on every device." / "It cannot be undone." Buttons **"Cancel"** (first in order and focused on load, flows-sprint-03 §0) and **"Delete my account"** (error outline, ≥ 48 px). "Delete my account" sends `{"is_adult": false, "confirm": "delete"}` → 403 `under_age`, cookie cleared → A-13. "Cancel" → A-10 with "No" still chosen; nothing is deleted and the account stays gated (api-sprint-04 §4: "the account stays unconfirmed and gated"); no text invites a different answer (PM-4 rule 4). A page, not a dialog: there is no host page behind it (every other route is gated).
- **A-13** (outcome of A-12; X-03 on the A-05 route): `<h1>` "Your account has been deleted". "You need to be 18 or over to use this app." then X-03's lines: "The app's data on this device has been cleared. Its stored files are removed within 7 days." Link "Close and return to the start" (→ `/`). The client shows A-13 only after it sent `confirm: "delete"` and got 403 `under_age`; it never says "we have not created an account".
- **Footage notice** (flag on), one paragraph with an info icon and the heading "Before you upload" (`<h2>`): "Only upload matches where everyone on the video is 18 or over. Do not upload matches that show children." On F-01 under the promise, on Q-06 above "Choose video", and on U-04 (choosing the file again). Not a checkbox: the notice informs, it does not create consent (judgment; PM-4 and security decide, §14 R4-5).

| Screen | State | What the player sees |
|---|---|---|
| A-10 | Empty | No option chosen → on Continue: summary "Select yes if you are 18 or over" linked to the first radio |
| A-10 | Loading | "Continue" disabled with "Checking…", polite status |
| A-10 | Error | Alert "We could not save your answer. Try again." with `Reference:`; the choice is kept |
| A-10 | Offline | "You are offline. Connect to continue." Continue disabled; the choice is kept |
| A-10 | Not-found | 401/404 (sign-in expired before the answer): A-04 text "This link has expired" with "Send a new link" |
| A-11 | Empty | N/A: an outcome page, it has no data |
| A-11 | Loading | N/A: static text rendered with the answer's response |
| A-11 | Error | If the 403 `under_age` response did not arrive, A-10's Error state applies and A-11 is not shown |
| A-11 | Offline | Static page; the "Close" link works offline (judgment) |
| A-11 | Not-found | Direct visit without a refused answer → redirect to `/` |
| A-12 | Empty | N/A: a confirmation page; it reads no data (the 422 that led here carries none) |
| A-12 | Loading | "Delete my account" shows "Deleting…" (disabled, `aria-busy`), polite status; Cancel disabled while the request runs |
| A-12 | Error | 5xx: alert "Your account was not deleted. Try again." with `Reference:` (X-02 text); nothing changed. A 422 `confirmation_required` here (body sent without `confirm`) → the same alert; never a raw code. 401 → A-10's Not-found state, nothing deleted |
| A-12 | Offline | "You are offline. Connect to delete your account." "Delete my account" disabled with that text; Cancel works |
| A-12 | Not-found | Direct visit without a 422 `confirmation_required` from A-10 → redirect to A-10 (never a delete without the age answer) |
| A-13 | Empty | N/A: an outcome page, it has no data |
| A-13 | Loading | N/A: static text rendered with the delete's response |
| A-13 | Error | If the 403 `under_age` response did not arrive, A-12's Error state applies and A-13 is not shown |
| A-13 | Offline | Static page; the "Close" link works offline (as A-11) |
| A-13 | Not-found | Direct visit without a confirmed delete → X-03's own rule (A-05 text) |

## 6. R-01 Privacy settings (ST-071; FR-008, FR-009; ADR 0006; flags `feature_retention_setting`, `feature_training_consent`)

- Route exists when either flag is on; each section appears only with its own flag. `<h1>` "Privacy settings". Links from X-00 ("Privacy settings") and the account menu.
- **Section 1, "How long we keep your match videos"** (`<h2>`, fieldset): radios "30 days", "90 days (default)", "365 days", "Until I delete them". Text: "This is the video you watch on the score sheet. Your score sheets, stats and plans stay until you delete the match. The original upload is always deleted 30 days after analysis." Button "Save video setting".
  - **Shorter period that passes dates already**: dialog "Change to 30 days?" "The videos of 2 matches are older than 30 days. They will be deleted at the next clean-up, within a day. Their stats, tags and plans stay." Cancel (focused) / "Change to 30 days" (HAX G16).
  - **Deletion dates** (`<h3>` "When each video is deleted"), a list: "<match title>, played <date>: video deleted on <date>" / "kept until you delete it" / "deleted on <date>" (FR-008 "sees each video's deletion date"; `review_video_delete_at`). Dates in the player's local time via `LocalDate`.
- **Section 2, "Help improve the app"** (`<h2>`): one checkbox, **unchecked by default**: "Use my matches and corrections to train and test the app's models". Text: "Off unless you turn it on. You can turn it off at any time. Then your matches are left out of every future training and test set. Sets already made are not changed; they are retired at their next scheduled refresh." (OQ-06, ADR 0023). Button "Save training choice". Both sections save on their own, so one choice never saves the other.
- **Saved:** polite status and a success line with an icon: "Saved. Videos are now kept for 30 days." / "Saved. Your matches will not be used for training."

| Screen | State | What the player sees |
|---|---|---|
| R-01 | Empty | No match yet: the date list says "You have no match videos yet." The settings still save |
| R-01 | Loading | Skeleton of both sections at final height; controls disabled until the current values arrive (never show a default that is not the stored value) |
| R-01 | Error | Load: alert with "Try again" and `Reference:`, no controls shown. Save: alert "We could not save. Your setting is still <old value>." and the control shows the **old value** (ST-071 negative test) |
| R-01 | Offline | Values shown read-only from the last load, "You are offline. Connect to change these settings."; Save buttons disabled with that text |
| R-01 | Not-found | Both flags off → app not-found page. A match in the date list deleted meanwhile → it disappears on refetch, no error |

## 7. Q-10 Over-limit messages (ST-072b; FR-160; NFR-023; flag `feature_quotas`)

- **Match limit** (Q-07 "Create match and upload" → 429 `rate_limited` with `retry_at`): alert above the summary list: "You have started 10 matches in the last hour. You can start a new match at 14:05." (local time, 24-hour `HH:MM` as `uploadRateLimitMessage`; "tomorrow at 00:10" when the date differs). "Your answers are kept." The button stays and works after that time; no auto-retry.
- **No `retry_at`** (ST-072b negative test): "You have started too many matches in a short time. Try again in an hour." Never a raw code.
- **Storage quota** (upload start refused, code per PE-4): alert on U-01: "This video does not fit in your storage. You have used 18.2 of 20 GB, and this video is 3.1 GB. Delete a match you no longer need, or choose a shorter video." Links "Your matches" and "Choose another video". "Nothing from this video was saved." (NOTHING_SAVED, U-03). GB with one decimal; the limit comes from the API, never from copy (the size is P8).
- Flag off → none of these messages; today's limits and copy unchanged.

| Screen | State | What the player sees |
|---|---|---|
| Q-10 | Empty | N/A: a message shown only when the API refuses; no data of its own |
| Q-10 | Loading | N/A: shown with the refusal; Q-07 and U-01 keep their own loading states |
| Q-10 | Error | The message is itself the error state; unknown 429 code → the existing generic upload rate-limit text |
| Q-10 | Offline | N/A: an offline player gets Q-07's / U-01's offline state, never a quota message |
| Q-10 | Not-found | The match of the upload was deleted meanwhile → `DeletedNotice` (flows-sprint-03 X family) instead of the quota message |

## 8. Copy register (proposed; PM-4 owns the interim texts behind the four flags)

| Screen | Text | Status |
|---|---|---|
| P-01 | "unofficial scoring (rules not yet verified)" | as D-01 (DR-03 R3-3) |
| P-01 | "These drills have not yet been checked by a human coach. Warm up first, and stop any drill that hurts." | interim until P15; coach decides (R4-2) |
| P-01 | "Based on limited data from <N> rallies. Tag more matches for a firmer plan." | FR-123 |
| P-01 | "The split between serve and receive is not yet verified." | until P7 |
| P-01 | "Why: <metric name>: <value> of <n> <unit>" | FR-122; names from the API |
| A-10/A-11, notice | §5 texts | interim, PM-4 register, P16 |
| A-12/A-13 | "You told us you are under 18. You need to be 18 or over to have an account, so we need to delete yours." / "You need to be 18 or over to use this app." (other lines reused from X-02, X-03) | proposal; PM-4 register has no row for an existing account yet (PD-FL4-06); interim, P16 |
| R-01 | §6 texts | interim, PM-4 register, P16 |
| Q-10 | §7 texts | FR-160; quota size P8 |

## 9. HAX checklist (Sprint 4 scope) [DPA/DESIGN-11]

| Guideline | Where | Design response |
|---|---|---|
| G1 Make clear what the system can do | P-01 header, P-02 | "Made on <date> from <n> tagged matches"; the plan is built from tagged rallies only, by fixed rules; no claim of AI or video analysis |
| G2 Make clear how well it can do it | P-01 notices, rows | Unofficial notice once; human-coach notice; limited-data banner with N; n on every value; "low sample" in words; split marked not verified |
| G11 Make clear why the system did what it did | P-01 drill rows | "Why: metric: value of n" on every drill, and "Show me" with the cited rallies; a row without a citation is an error, never a blank |
| G8, G15 Efficient dismissal, granular feedback | P-03 | "Not for me" with an optional reason; the swap keeps the session's fit |
| G16 Convey consequences | R-01, P-02 | Shorter-retention dialog names the videos affected; "This replaces your current plan" |
| Others | — | No learning, no automatic call, no LLM text in Sprint 4 (FR-UX-82/84 do not apply yet) |

## 10. WCAG 2.2 AA design-level checklist per screen

"✓" means this file specifies it. Implementation evidence: G04-08 (axe and target checks per family P, A, R, Q; keyboard E2E-04-05; 320/360 px) and the human pass (P6).

| Check | P-01 | P-02 | P-03 | A-10..A-13 | R-01 | Q-10 |
|---|---|---|---|---|---|---|
| Unique title, one `<h1>` (SC 2.4.2) | ✓ | ✓ "Error: " prefix on errors | — (dialog `<h2>`) | ✓ | ✓ | — (host page) |
| Targets ≥ 24 px; primary ≥ 48 px (SC 2.5.8; NFR-028) | ✓ | ✓ whole radio/checkbox row | ✓ | ✓ | ✓ | ✓ links |
| Contrast from proven tokens; disabled-with-reason at full contrast (SC 1.4.3, 1.4.11) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Not colour alone: "low sample", "Done" + icon, "Saved" + icon (SC 1.4.1) | ✓ | — | ✓ | — | ✓ | ✓ words, not colour |
| Label in name (SC 2.5.3) | ✓ "Show me the rallies behind …" | ✓ | ✓ "Swap drill" | ✓ | ✓ | ✓ |
| Keyboard-only; logical order (SC 2.1.1, 2.4.3) | ✓ | ✓ | ✓ focus trapped, returned, new drill focused | ✓ | ✓ | ✓ |
| Focus not obscured, no sticky bar (SC 2.4.11) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| No dragging (SC 2.5.7) | ✓ | ✓ number input, not slider | ✓ | ✓ | ✓ | — |
| Status messages polite, focus kept (SC 4.1.3) | ✓ loading, offline | ✓ "Making your plan…" | ✓ "Saved on this device", "Swapped for …" | ✓ | ✓ "Saved." | ✓ alert |
| Error identification with the fix (SC 3.3.1, 3.3.3) | ✓ | ✓ summary + field | ✓ | ✓ | ✓ old value kept | ✓ time / usage stated |
| Reflow at 320 px (SC 1.4.10; NFR-034) | ✓ §11 | ✓ | ✓ | ✓ | ✓ | ✓ |
| No layout shift on load (NFR-039) | ✓ reserved skeleton | — | — | — | ✓ reserved | — |
| Redundant entry: regenerate prefilled (SC 3.3.7) | — | ✓ | ✓ reason kept on error | — | — | ✓ answers kept |

## 11. Layouts at 320 and 360 CSS px

16 px side gutters (`space.gutter-mobile`), single column, text in rem, no fixed widths.

| Screen | 360 px | 320 px |
|---|---|---|
| P-01 | Notices full width; weakness lines on two lines (name + rate / split); drill row: name, facts line, "Why" line, then "Show me" and "Not for me" side by side (each ≥ 48 px high, 8 px gap) | Same order; the two buttons stack full width; the facts line wraps at "·"; E-01 panel full width under the row |
| P-02 | Radios 1-7 in one row of 48 px targets | Radios 1-7 wrap to two rows; checkboxes one per row; button full width |
| P-03 | Dialog 100% width minus gutters; reason field 4 rows | Same; buttons stack, Cancel first |
| A-10..A-13 | Question page, `content-max` 40 rem; A-12 buttons side by side, Cancel first | Same; radios one per row; A-12 buttons stack, Cancel first |
| R-01 | Sections stacked; date list as a list, not a table | Date list items wrap (title, then date on its own line) |
| Q-10 | Alert full width above Q-07's summary / U-01's file control | Same; links stack |

## 12. Open items and routed

| Id | Item | Owner |
|---|---|---|
| PD-FL4-01 | Field and code names (`limited_data`, side-out-unverified mark, storage-quota code, `retry_at`, plan citation `rally_ids` across matches) | principal-engineer, PE-4 |
| PD-FL4-02 | "Show me" for a plan citation spans matches; E-01 takes `rally_ids` grouped by match. Needs either an evidence read by rally ids or the match id in each citation | principal-engineer, PE-4 |
| PD-FL4-03 | Weakness names, "Points given away", equipment and level words; the human-coach notice | pickleball-domain-coach, COACH-4 |
| PD-FL4-04 | A-11 "what to do instead", the footage notice and R-01 texts | product-manager, PM-4 |
| PD-FL4-06 | A-12/A-13 words for an existing unconfirmed account that answers "No" (PM-4 has rows only for a pending sign-in); whether A-12 "Cancel" back to A-10 is acceptable for the gate (api-sprint-04 §4 keeps the account gated) | product-manager (PM-4 register), security-privacy-engineer (SEC-4) |
| PD-FL4-05 | The ticket map and story cards say "A-01" / "Q-01"; this file uses A-10/A-11 and Q-10 (§0). G04-08's families A and Q mean these ids | principal-engineer (ticket map), senior-qa-engineer (G04-08) |

## 13. Traceability

| Screen | FR / NFR | Gherkin (sprint-04 §7) |
|---|---|---|
| P-01 | FR-120, FR-122, FR-123; NFR-039 | `weakness_ranking.feature`, `drill_rationale.feature`, `limited_data_plan.feature` |
| P-02 | FR-121; NFR-019 | `training_plan.feature` |
| P-03 | FR-124 | `plan_follow_through.feature` |
| A-10..A-13, notice | FR-003 | `age_confirmation.feature` |
| R-01 | FR-008, FR-009 | `video_retention.feature`, `training_consent.feature` |
| Q-10 | FR-160; NFR-023 | `rate_limits.feature` |

## 14. Design review record (DR-04)

| Date | Participants | Outcome |
|---|---|---|
| Opened 2026-10-17; decisions due **end of 2026-10-18** (gate day, ADR 0047 rule 2); escalation to the PO the same day if a blocking cell is empty | principal-designer (chair), senior-frontend-engineer, pickleball-domain-coach (SME), product-manager, security-privacy-engineer, business-analyst | **Not yet held on 2026-10-17.** Asynchronous, in the repository, as DR-03: each decider writes "role: **accept** / **reject** (date): one line of reason" in its cell below and commits it. The chair does not write other roles' cells (ADR 0037 rule 2). Held when every "Decides" role has a cell; a reject returns to the chair the same day |

### 14.1 Agenda (chair's proposals, judgment unless cited)

| # | Item | Proposal | Decides |
|---|---|---|---|
| R4-1 | P-01 layout: notice order, weakness lines with unit, split, points given away, one "not yet verified" line (§2) | Accept | senior-frontend-engineer, pickleball-domain-coach, business-analyst (FR-120, FR-123) |
| R4-2 | Drill row "Why" wording, "Show me" reusing E-01 with the plan's rally ids; the human-coach notice words (§2, §8) | Accept | senior-frontend-engineer, pickleball-domain-coach, product-manager |
| R4-3 | P-02 one page with five questions, no defaults on the first visit, weekly limit = minutes × sessions (§3) | Accept | senior-frontend-engineer, pickleball-domain-coach, business-analyst (FR-121) |
| R4-4 | P-03 optimistic done, offline queue shown in words, swap disabled offline, Cancel focused, new drill focused (§4) | Accept | senior-frontend-engineer, product-manager, security-privacy-engineer (device outbox holds ids only, cleared on sign-out) |
| R4-5 | A-10/A-11 and the footage notice as information, not a checkbox; A-12/A-13 for an existing unconfirmed account answering "No" (§5) | Accept | product-manager, security-privacy-engineer, business-analyst (FR-003) |
| R4-6 | R-01: two independent saves, consent unchecked by default, shorter-retention dialog, date list (§6) | Accept | product-manager, security-privacy-engineer, business-analyst (FR-008, FR-009) |
| R4-7 | Q-10 texts, local `HH:MM`, usage and limit from the API (§7) | Accept | senior-frontend-engineer, product-manager, business-analyst (FR-160) |
| R4-8 | States, HAX G1/G2/G11, WCAG and 320/360 layouts (§2-§11); screen ids A-10/A-11, Q-10 (§0) | Accept | senior-frontend-engineer, business-analyst |

### 14.2 DR-04 decider cells

One row per decider; the decider replaces "pending" with its cells for the items named.

| Role | Items | Opened | Due | Cell |
|---|---|---|---|---|
| principal-designer | R4-1..R4-8 | 2026-10-17 | — | accept (2026-10-17, author) |
| senior-frontend-engineer | R4-1, R4-2, R4-3, R4-4, R4-7, R4-8 | 2026-10-17 | 2026-10-18 | pending |
| pickleball-domain-coach | R4-1, R4-2, R4-3 | 2026-10-17 | 2026-10-18 | pending |
| product-manager | R4-2, R4-4, R4-5, R4-6, R4-7 | 2026-10-17 | 2026-10-18 | pending |
| security-privacy-engineer | R4-4, R4-5, R4-6 | 2026-10-17 | 2026-10-18 | pending |
| business-analyst | R4-1, R4-3, R4-5, R4-6, R4-7, R4-8 | 2026-10-17 | 2026-10-18 | pending |

**Hold status, 2026-10-17 (chair).** All five deciders are agent roles (`.claude/agents/<role>.md` exists for each), none is human-only, so no "not met: waiting on P-n" row applies. The chair's step could not reach them: `ListAgents` on 2026-10-17 → "No reachable agents". Under ADR 0037 rule 2 the chair does not write their cells, so they stay "pending" and DR-04 is **not yet held**. Next step: the orchestrator invokes each decider role with §14.1-§14.2 as its brief; each commits its own cell ("accept/reject (YYYY-MM-DD): reason") on this branch or on a follow-up PR. The check `check_flows.py --review DR-04 --decider <role>` (ticket PD-4b) turns green per role when its cell is written.
