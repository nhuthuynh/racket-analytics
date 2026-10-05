# Sprint 1 flows: sign-in, first run, capture guide, match setup, upload

- **Status:** Draft v0.1, 2026-10-03 (principal-designer). The design review is held as a PR with the domain coach as subject-matter expert (SME), the senior-frontend-engineer (feasibility), the business-analyst (criteria) and the security-privacy-engineer (sign-in, upload) [DPA/DESIGN-15]. This document is part of Sprint 1's Definition of Ready (sprint-00 §4).
- **Stories:**
  - ST-013 sign-in;
  - ST-014 sign-out;
  - ST-015 first run and capture guide;
  - ST-016 match setup;
  - ST-017 resumable upload;
  - ST-018 upload validation;
  - ST-019 quality report (stretch; facts only).
- **Requirements:** FR-001, FR-004, FR-005, FR-011, FR-020..FR-023, FR-025, FR-043, FR-055; NFR-027..NFR-035, NFR-037.
- **Tokens:** `tokens.md`. **Component checklist:** `component-accessibility-checklist.md`. **Coach wording:** `docs/domain/capture-guide-wording.md`.
- **Gherkin:** `docs/sprints/sprint-01.md` §7 and §14. **The copy in this document matches the Gherkin strings exactly.** A copy change here needs the same change there, agreed with QA.
- **Viewport:** designed at 360 CSS px, one-handed, outdoors (DES principle 4, judgment). Layouts reflow down to 320 px (NFR-034).

## 0. Conventions

- **Screen IDs:**
  - `A-` authentication;
  - `F-` first run;
  - `G-` guide;
  - `Q-` setup question pages;
  - `U-` upload;
  - `M-` match.
- **Every screen lists all six states:** Empty, Loading, Error, Offline, Low-confidence and Low-sample (DES §4; designer DoD). Low-confidence and Low-sample are "N/A", with the reason, where no automatic call or metric is on the screen.
- **Question-page pattern** [DPA/DESIGN-12]:
  - "Back" link top left;
  - the `<h1>` is the question;
  - one question;
  - a "Continue" button;
  - "(optional)" on optional fields, and no asterisks.
- **Error pattern** [DPA/DESIGN-13]:
  - "There is a problem" summary at the top, focused on render;
  - one link per error to its field;
  - the same message at the field;
  - `<title>` prefixed "Error: ".
- **Server errors** never show internals. The page shows a generic message plus the `support_ref` from the API error body (NFR-058) [AQS/SEC-04].
- **Live regions:** state changes are announced politely, and focus does not move unless the user must act (checklist §0).

## 1. Flow map

```
            ┌──────────── signed out ─────────────┐
 open app → A-01 Sign in ──send──► A-02 Check your email
                │                       │ open link (same or other device)
                │                       ▼
                │                 A-03 Signing you in… ──ok──► (new account) F-01 What this app does
                │                       │                         │ Continue
                │                       │                         ▼
                │                       │                     G-01 Capture guide ──► M-01 Your matches (empty)
                │                       │                                              │ "Record your first match"
                │                       ├─expired/used─► A-04 This link has expired      ▼
                │                       └─(returning)──► M-01 Your matches            Q-01 … Q-06 ► Q-07 Check your answers
                └─ rate limited: error summary on A-01                                  │ "Create match and upload"
                                                                                        ▼
                                                    U-01 Uploading ⇄ Paused ⇄ Resuming ─► U-02 Checking video ─► M-02 Match (Video received)
                                                         │ rejected                                            ▲
                                                         ▼                                                     │
                                                    U-03 Video not accepted (error summary)                     │
           return later with an unfinished upload: M-01/M-02 "Resume" banner ─► U-04 Choose the same file ──────┘
 menu → Sign out ─► A-05 You have signed out
```

## 2. Sign-in and sign-out (ST-013, ST-014)

### A-01 Sign in

- **Purpose:** get an email address and send a single-use link. There is no password or puzzle (FR-001; **SC 3.3.8** [DPA/DESIGN-06]; NFR-032).
- **Content:**
  - `<h1>` "Sign in or create an account".
  - Label "Email address", with the hint "We'll email you a link to sign in. No password needed."
  - `type=email`, `autocomplete=email`, paste allowed.
  - Button "Send me a link".
- **Same flow for new and returning users.** A-02 is shown whether or not an account exists, so the page does not reveal who has an account (judgment; security-privacy-engineer to confirm in the threat model).

| State | Design |
|---|---|
| Empty | The default: an empty field with the hint |
| Loading | The button reads "Sending…" with `aria-busy`, keeps its width, and double submit is blocked |
| Error, validation | Error summary: "Enter an email address in the correct format, like name@example.com" |
| Error, rate limited (IT-01-02) | Error summary: "You have asked for too many links. You can ask for a new link at 14:32." The time is local and absolute, from the API's retry time. Gherkin: "she is told when she can request a new link" |
| Error, server | "Sorry, we could not send a link right now. Try again in a few minutes. Reference: {support_ref}" |
| Offline | Banner: "You're offline. Connect to the internet to get a sign-in link." The button stays enabled; on submit the same text appears in the error summary |
| Low-confidence / Low-sample | N/A: no automatic call or metric |

### A-02 Check your email

- **Content:**
  - `<h1>` "Check your email".
  - "We sent a sign-in link to **ivy@example.com**. It works once and expires in 15 minutes."
  - "Not there? Check your spam folder or **send a new link**." The link returns to A-01 with the address pre-filled.
  - "Use a different email address".
- **Focus** moves to the `<h1>` on arrival. The page announces "Check your email".

| State | Design |
|---|---|
| Empty | N/A (the page always has content) |
| Loading | N/A |
| Error | Resend rate-limited → the same message as A-01, in an error summary on this page |
| Offline | Page stays readable (static). "Send a new link" shows the offline message |
| Low-confidence / Low-sample | N/A |

### A-03 Signing you in…

- **Purpose:** exchange the token. Immediately afterwards, the token is removed from the address bar (`history.replaceState`) [AQS/SEC-05 14.2.1]; NFR-055. This page has no navigation and no content that could leak the URL to third parties (no external assets).
- **Success:**
  - a new account goes to **F-01**;
  - a returning account goes to **M-01**, where the `<h1>` is "Your matches".
- Gherkin (sprint-01 §7.1): after sign-in she "sees 'Record your first match'". M-01's empty state and F-01's call to action both use exactly that phrase.

| State | Design |
|---|---|
| Loading | Text "Signing you in…" with a polite live region. No spinner-only page. If it takes more than 5 s: "This is taking longer than usual." (judgment) |
| Error, expired or used | → **A-04** |
| Error, server | "Sorry, we could not sign you in. Request a new link. Reference: {support_ref}", plus the button "Send a new link" |
| Offline | "You're offline. Connect and open the link again." The token is **not** stored on the device |
| Empty / Low-confidence / Low-sample | N/A |

### A-04 This link has expired

- **Content:**
  - `<h1>` "This link has expired".
  - "Sign-in links work once and only for 15 minutes."
  - Email field pre-filled when the server can safely provide it. It is never read from the URL (judgment; security-privacy-engineer to confirm).
  - Button "Send a new link".
- Gherkin: "she sees 'This link has expired'" and "she is offered a new link". The same page is used for "already used" (the page does not say which, to avoid an oracle; judgment).
- **States:** Loading → as A-01; Error → as A-01; Offline → as A-01; Empty, Low-confidence and Low-sample → N/A.

### Sign-out (ST-014) and A-05 You have signed out

- **Entry:** the account menu (top right, 48 px target), item "Sign out".
- **If an upload is in progress:** an interruption page or dialog asks:
  - `<h1>` "Your upload will stop".
  - "'Sat doubles' is 64% uploaded. If you sign out now, the upload stops. You can resume it later from the match page by choosing the same video."
  - Buttons: "Sign out anyway" (secondary) and "Keep uploading" (primary, focused).
- **A-05:**
  - `<h1>` "You have signed out".
  - "Nothing from your account is kept on this device."
  - Button "Sign in".
- **Behaviour (FR-011):** clear authenticated client storage and service-worker caches for authenticated data. Media is never cached [AQS/SEC-05 14.3.1-14.3.3].
- **Gherkin (sprint-01 §7.1):** after sign-out, offline, "none of Ivy's matches, facts or videos can be seen". Offline after sign-out therefore shows A-01's offline banner, never a cached match list.
- **States:**
  - Loading: "Signing out…", which takes under 1 s.
  - Error: sign-out always clears locally even if the server call fails. The page then says "You have signed out on this device. We couldn't reach the server; your session will end on its own." (judgment; security-privacy-engineer to confirm session expiry).
  - Offline: same as Error.
  - Empty, Low-confidence and Low-sample: N/A.

## 3. First run (ST-015, FR-004)

### F-01 What this app does

- **HAX:**
  - G1, make clear what the system can do;
  - G2, make clear how well it can do it [DPA/DESIGN-11].
- **Copy correction (important):** the FR-004 example ("We score your match and show where you lose points. One phone can't make line calls…") implies automatic scoring. **R1 has no computer vision** (ADR 0002; roadmap §1 principle 3): the player tags who won each rally, and the app keeps the score.

  Promising automatic scoring in R1 would break HAX G2. Proposed R1 copy:
  - `<h1>` "What Racket Analytics does".
  - "**You** mark who won each rally while you watch your video. **We** keep the score and show where your points are won and lost."
  - "We can't make line calls or referee your match from one phone."
  - "Scores follow rules that are **not yet checked against the official rulebook**, so they are marked 'unofficial'." (FR-055)
  - "Only you can see your videos." (FR-UX-100; NFR-064)
  - Button "Show me how to film" → G-01. Secondary link "Record your first match" → M-01 (the Gherkin phrase).
  - Gherkin (§7.2): "she sees what the app does and what it cannot do, in plain words" / "she can continue to the capture guide".
- The copy change is logged for the PM and BA: FR-004's example text should be updated. Decision log, 2026-10-03.

| State | Design |
|---|---|
| Empty / Loading | Static page, no data; N/A |
| Error | N/A, no request. If the "first run seen" flag fails to save, the page shows again next time (harmless) |
| Offline | Works offline (static, precached shell; it contains no authenticated data) |
| Low-confidence / Low-sample | N/A |

## 4. Capture guide (ST-015, FR-020)

### G-01 How to film your match

- **Wording:** `docs/domain/capture-guide-wording.md` (coach draft; sign-off is due Sprint 1 D3). The design uses that wording unchanged.
- **Layout (mobile):**
  - `<h1>` "How to film your match".
  - Intro: "6 things to check before the first serve."
  - An ordered list of **6 items** (`<ol>`). Each item has an illustration (alt text from the wording doc), a bold instruction (the item text, not a heading element, to keep the outline flat) and a "why" line. Gherkin: "no more than 6 instructions".
  - Safety line under item 2.
  - Disclosure "How to record at 60 fps on my phone" (`<details>`, generic text only until the device check).
  - Guide video: native controls, **captions on by default** (`<track default>`), no autoplay [DPA/DESIGN-08]. The line above the video reads "Everything in the video is in the checklist above." [DPA/DESIGN-09]; NFR-033.
  - Primary button "Record your first match" → Q-01. Secondary link "Back to your matches".
- The guide is always reachable later from the Help link (consistent placement) and from M-01's empty state.

| State | Design |
|---|---|
| Empty | N/A (static content) |
| Loading | Illustrations have reserved dimensions (no layout shift). The video poster frame shows until it plays |
| Error, video fails to load | "The video can't play right now. Everything in it is in the checklist above." The checklist is the alternative, so nothing is lost |
| Offline | Checklist and illustrations are precached (judgment: small SVGs). The video is not cached (size), so the offline message equals the video-error message |
| Low-confidence / Low-sample | N/A |

## 5. Match setup (ST-016, FR-021, FR-005, FR-043)

### M-01 Your matches

- **Empty state:**
  - `<h1>` "Your matches".
  - "No matches yet."
  - Primary button "Record your first match" → Q-01.
  - Link "How to film your match" → G-01.
- **With matches:** a list of cards. Each card shows the name, date, status ("Uploading 64%", "Video received", "Upload stopped at 64%") and a link. An unfinished-upload banner appears at the top (§6, U-04).
- **States:**
  - Loading: skeleton rows with reserved height.
  - Error: "Sorry, we could not load your matches. Try again. Reference: {support_ref}", plus a "Try again" button.
  - Offline: "You're offline. Your matches will appear when you reconnect." Authenticated lists are not cached (NFR-067; ST-010 service worker rule).
  - Low-confidence and Low-sample: N/A.

### Setup question pages (one question per page [DPA/DESIGN-12])

The order follows FR-021. Answers from the last match are pre-filled where it is safe: format, scoring system and nicknames. The date defaults to today.

**There is no "title" question.** FR-021 does not ask for one. The match is auto-named "{Format} · {date}", for example "Doubles · 3 Oct 2026", and can be renamed later. This is a decision-log row; the BA should confirm.

| Page | `<h1>` question | Controls | Validation and messages (exact strings) |
|---|---|---|---|
| Q-01 | "Is this a doubles or singles match?" | Radios: "Doubles", "Singles" | None chosen → "Select doubles or singles" (summary link → first radio). Gherkin §7.3: "There is a problem" with a link to the format question; title "Error: …" |
| Q-02 | "Which scoring system did you play?" | Radios: "Side-out scoring (traditional)"; "Rally scoring (provisional)", `aria-disabled`, with the hint "Not available yet. It becomes available once the rules are verified." in `warning-text` on `warning-surface`, full contrast (tokens §3 rule 4) | None chosen → "Select a scoring system". **No definition of either system is shown.** A definition is a rule claim and is **UNVERIFIED** (coach; rules-verified §5 priority 1). Gherkin §7.3, "Rally scoring is not yet available" |
| Q-03 | "Who played?" | Doubles: fieldset "Side A", with "Player 1" and "Player 2"; fieldset "Side B", with "Player 1" and "Player 2". Singles: "Side A player" and "Side B player". Hint on each fieldset: "Use a first name or nickname. Do not enter contact details." (FR-005) | Doubles side missing a name → "Each side needs two players". Singles → "Each side needs one player". A nickname that looks like an email address or phone number → **warning, not error**: "This looks like contact details. Use a nickname instead." (judgment; sprint-01 §5 `Participants` test 3). Max length 30 → "Nickname must be 30 characters or fewer" (judgment) |
| Q-04 | "Which player are you?" | Radios listing the 4 or 2 nicknames, with side labels ("Ivy (Side A)") | None chosen → "Choose one player as \"me\"". Two "me" markers cannot happen with radios. The Gherkin row "four nicknames with two marked 'me'" is an API-level validation (IT-01-05), and its message is shared |
| Q-05 | "When was the match played?" | Date input (day, month, year), pre-filled with today | Invalid → "Enter a real date". A future date → "The date must be today or in the past" |
| Q-06 | "Choose the match video" | A file button "Choose video" (`accept="video/mp4,video/quicktime"`; advisory only, the server is authoritative). Hint: "MP4 or MOV, up to 10 GB and 2 hours 30 minutes." The caps are **provisional until ST-025 / R-05** and come from config, never hard-coded in copy. Privacy line: "Only you can see this video." | No file → "Choose a video file". File larger than the cap (from `File.size`, checked client-side and again by the server) → "Videos must be 10 GB or smaller". Type or duration rejections come from the server (U-03) |
| Q-07 | "Check your answers" | A summary list: Format, Scoring system, Players, You, Date, Video (file name and size). Each row has "Change<span hidden> format</span>" (48 px), which returns to its page and then back to Q-07. Button: **"Create match and upload"** | Gherkin §7.3: "each answer is listed with a 'Change' link" |

**Common states for Q-01..Q-07:**

| State | Design |
|---|---|
| Empty | First visit with no previous match: no pre-fill except today's date |
| Loading | "Continue" shows "Saving…" while the draft is saved. Pages render without network waits, because answers are kept in client state until Q-07 (judgment; FE to confirm) |
| Error | Error summary per the pattern above. On a server error at "Create match and upload": "Sorry, we could not create your match. Your answers are kept. Try again. Reference: {support_ref}" |
| Offline | Questions can still be answered. At Q-07 the button is replaced by "You're offline. Connect to create the match and start the upload." Answers are kept |
| Low-confidence / Low-sample | N/A |

**Keyboard path:** Tab to the first radio, use the arrow keys to choose, Tab to "Continue", press Enter. The whole setup flow can be completed keyboard-only (E2E-01-03; NFR-034, NFR-030).

## 6. Upload (ST-017, ST-018; FR-022, FR-023)

### U-01 Uploading (match page, upload panel)

- **Content:**
  - `<h1>` = the match name.
  - Panel heading "Video upload".
  - `<progress>` with visible text: "**64%** · 1.9 GB of 3.0 GB".
  - State line (live region): **Uploading** / **Paused: waiting for connection** / **Resuming** / **Upload complete**. These are the exact Gherkin strings (§7.4).
  - Time estimate "About 12 minutes left". It is shown **only after 10 s of measured throughput** (FR-022; Gherkin "no time estimate" before 10 s) and updates at most every 5 s (judgment).
  - "Only you can see this video."
- **Leaving:** "You can use other pages while this tab stays open. If you close it, you can resume later from this page by choosing the same video."
  - This copy **never** promises an upload continues after the tab is closed (FR-022, OQ-18 recommendation; SPIKE-06 may change it).
- **Large files (> 1 GB):** a dismissible hint: "Keep your screen on until the upload finishes." (FR-UX-32, judgment)
- **Controls:** "Pause" / "Resume" (48 px). "Cancel upload" (secondary) opens a confirmation: "Cancel this upload? The part already sent will be deleted." with "Cancel upload" and "Keep uploading".
- **Announcements:** state changes are announced. The percentage is announced at most every 10%.
- **Damaged chunk** (checksum mismatch, IT-01-06): invisible to the user. The client re-sends from the server's offset. If 3 consecutive retries fail: "Paused: we're having trouble sending your video. Retrying…" (judgment).

### U-02 Checking video

- **Content:** state "Checking video…". "We're reading the video's details. This usually takes less than a minute." (judgment)
  - The probe job is enqueued only after the final byte is stored (NFR-060).
- **Then M-02:** status **"Video received"** (Gherkin §7.5). The facts appear: "Duration 1:00 · 60 fps · 1920×1080" (format from Sprint 0 E2E-00-01).
  - The quality report (ST-019, stretch) adds consequence lines. Example: "Recorded at 30 fps: some later results may be less accurate. You can still tag this match." It never blocks (FR-UX-40, HAX G16).

### U-03 Video not accepted (ST-018)

- An error summary on the upload panel (or on Q-06 when the client already knows), with the heading "There is a problem". The exact strings come from the Gherkin (§7.5):
  - not a readable video, judged by content and not the extension: "This file is not a video we can read";
  - too large: "Videos must be 10 GB or smaller";
  - too long: "Videos must be 2 hours 30 minutes or shorter".
- Each message is followed by a "Choose a different video" link → the file button.
- **Nothing is kept from a rejected file, and the page says so:** "Nothing from this file was saved." (NFR-060; Gherkin "no match video is stored from that file"). The caps are provisional (R-05) and come from config.

### U-04 Resume an unfinished upload (return visit)

- **Trigger:** the server reports an unfinished upload session for one of the user's matches. Server state is the source of truth, because sign-out clears local storage (FR-011). Dependency for the BE: the match read model exposes the upload offset and expiry. principal-engineer to confirm in ST-017.
- **Banner on M-01 and M-02:**
  - "Your upload of 'Sat doubles' is 64% done."
  - Button "Resume upload".
  - Text "It will be kept until {date, time}" (from `Upload-Expires`).
  - Gherkin §7.4: "she is offered to resume from 64%".
- **Resume:** "To continue, choose the same video: **Sat doubles.mp4 (3.0 GB)**." The browser cannot reopen the file by itself after the tab was closed (judgment; SPIKE-06 confirms). The user taps "Choose video". The client checks name, size and last-modified date, then HEAD returns the offset and the upload continues from it (tus [AQS/STACK-06]).
  - Different file → error summary: "This is not the same video. Choose 'Sat doubles.mp4' (3.0 GB), or cancel this upload and start again."
  - Expired session → "This upload expired on {date}. Start the upload again." The expired session is removed (Sprint 2, ST-038).

### Upload states summary

| State | Design |
|---|---|
| Empty | No video yet: on M-02 the panel shows "No video yet" with "Choose video". The match exists without a video |
| Loading | U-01 progress (never a spinner alone); U-02 "Checking video…" |
| Error | U-03 validation; server error: "Sorry, the upload stopped because of a problem on our side. Your progress is saved. Try again. Reference: {support_ref}" with "Try again" |
| Offline | "Paused: waiting for connection". It resumes automatically when the connection returns and announces "Resuming", then "Uploading" (Gherkin §7.4, "Connection drops mid-upload") |
| Low-confidence | N/A in R1. Probe facts are read from the file, not inferred. A VFR flag, if shown, is a fact ("Variable frame rate") |
| Low-sample | N/A: no metric |

## 7. HAX checklist (Sprint 1 scope) [DPA/DESIGN-11]

| Guideline | Where | Design response |
|---|---|---|
| G1 Make clear what the system can do | F-01 | Says plainly that the user tags and the app keeps score; no automatic analysis in R1 |
| G2 Make clear how well the system can do it | F-01, Q-02, every score sheet later | "We can't make line calls…"; "unofficial" scoring until the rules are verified (FR-055) |
| G10 Scope services when in doubt | Q-02 | Rally scoring is shown but not selectable, with the reason |
| G16 Convey the consequences of user actions | U-03, ST-019 report, sign-out with an upload running | The consequence is stated ("Nothing from this file was saved"; "the upload stops") |
| G8, G9 Efficient dismissal and correction | Q-07 "Change" links; banners dismissible | Every answer can be changed in 1 tap from the check page |
| G3, G4, G5, G6, G7, G11..G15, G17, G18 | — | No automatic call, recommendation or learning in Sprint 1 screens. These are applied in Sprint 2 (Quick Tag, score sheet) and R2 |

## 8. WCAG 2.2 AA design-level checklist per screen

Component rules: `component-accessibility-checklist.md`. "✓" means the design specifies it, "—" means not applicable. Implementation evidence comes at PR time.

| Check | A-01..A-05 | F-01 | G-01 | M-01 | Q-01..Q-07 | U-01..U-04 |
|---|---|---|---|---|---|---|
| Unique title; "Error:" prefix on error | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| One `<h1>`; the question is the `<h1>` / legend | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Targets ≥ 24 px, primary ≥ 48 px (SC 2.5.8 ✓src; NFR-028) | ✓ | ✓ | ✓ | ✓ | ✓ (radio rows, "Change" links) | ✓ (Pause, Resume, Cancel, Choose video) |
| Contrast from proven tokens only (SC 1.4.3 / 1.4.11 ✓src; NFR-029) | ✓ | ✓ | ✓ | ✓ | ✓ (provisional option at full contrast) | ✓ (progress fill and track proven) |
| Focus not obscured by sticky bars (SC 2.4.11 ✓src; NFR-031) | ✓ | — | ✓ | ✓ (banner) | ✓ | ✓ (sticky upload panel uses scroll-padding) |
| No cognitive-function test at sign-in (SC 3.3.8 ✓src; NFR-032) | ✓ | — | — | — | — | — |
| Captions by default and a media alternative (SC 1.2.2 / 1.2.3 ✓src; NFR-033) | — | — | ✓ | — | — | — |
| Content descriptions / alt text (NFR-035) [DPA/DESIGN-10] | — | — | ✓ (wording doc) | ✓ (status icons have text) | — | ✓ |
| No dragging needed (SC 2.5.7 ✓src; NFR-030) | — | — | — | — | — | ✓ (file button; drag-and-drop is extra only) |
| Error summary pattern (NFR-037) [DPA/DESIGN-13] | ✓ | — | — | — | ✓ | ✓ |
| Keyboard-only completion (nf; NFR-034) | ✓ | ✓ | ✓ | ✓ | ✓ (E2E-01-03) | ✓ |
| Polite live announcements (nf) | ✓ (A-02, A-03) | — | — | ✓ (banner) | — | ✓ (state line) |
| Reflow at 320 px (nf; NFR-034) | ✓ | ✓ | ✓ | ✓ | ✓ (doubles fieldsets stack) | ✓ |
| Not colour alone (nf) | ✓ | ✓ | ✓ | ✓ (status words) | ✓ ("provisional" in words) | ✓ (state words, % text) |

## 9. Open items and dependencies

| # | Item | Owner | Needed by |
|---|---|---|---|
| D-1 | FR-004 example copy implies automatic scoring; R1 copy proposed in F-01 | product-manager + business-analyst | ST-015 start |
| D-2 | No "title" question; auto-name "{Format} · {date}" | business-analyst (confirm vs FR-021) | ST-016 start |
| D-3 | Resume must work from **server** state (match read model exposes offset and expiry), because sign-out clears local data | principal-engineer, senior-backend-engineer | ST-017 design |
| D-4 | A-01 shows A-02 regardless of whether an account exists; A-04 does not distinguish expired from used | security-privacy-engineer (threat model) | ST-013 start |
| D-5 | Upload caps in copy are provisional (10 GB / 150 min) and come from config | senior-ml-cv-engineer (ST-025 / R-05) | ST-018 merge |
| D-6 | 60 fps device steps hidden until checked on reference phones | senior-ml-cv-engineer, pickleball-domain-coach | ST-015 merge |
| D-7 | Upload copy after SPIKE-06 (background tab, screen lock) may change U-01's "leaving" text | senior-frontend-engineer (SPIKE-06) | Sprint 1 D3 |
| D-8 | Courtesy line about filming other players (consent) | product-manager, security-privacy-engineer (OQ-06) | ST-015 merge |

## 10. Design review record

| Date | Participants | Outcome | Findings |
|---|---|---|---|
| 2026-10-03 | principal-designer (author) | Draft written | Self-check against the designer DoD: every screen has its states; WCAG and HAX checklists applied; copy aligned with the Gherkin strings |
| Sprint 0 D8 (planned) | + pickleball-domain-coach (SME), senior-frontend-engineer, business-analyst, security-privacy-engineer | Not held. DoR P7 stayed open while ST-013..ST-019 were built (review round 1 finding PD-R1-06) | — |
| 2026-10-06 (scheduled by the engineering-manager, 2026-10-05; format and fallback date decided by the chair 2026-10-05, §10.2) | principal-designer (chair, records the outcome), pickleball-domain-coach, senior-frontend-engineer, business-analyst, security-privacy-engineer, product-manager (R-5, D-1, D-8) | **Scheduled, not yet held.** Asynchronous, in the repo (§10.1 "Decision at review" column); decisions due by end of 2026-10-06; if any cell is still empty then, P7 carries to Sprint 2 with a hard date of 2026-11-02 (§10.2) | Agenda: (1) walk A-01..A-04, F-01, G-01, Q-01..Q-07, M-01/M-02, U-01..U-04 against the built screens; (2) confirm or reject the two FE deviations in `docs/sprints/01/decision-log.md` (U-04 "different file" copy without "or cancel this upload and start again" while Cancel upload is hidden until Sprint 2; resume banner on M-01 only); (3) ST-018 fourth refusal string for codecs; (4) ST-019 copy without a "Tag this match" button; (5) D-1..D-8 still open; (6) added by the engineering-manager on 2026-10-05 (PD-R2-04): pickleball-domain-coach signs off `docs/domain/capture-guide-wording.md`, which is still `draft` and was due on Sprint 1 D3. The coach updates that doc's §5 sign-off row; ST-015 keeps it in `open` until then. Input to the chair (principal-designer view in PD-R1-06, judgment): accept both U-04 deviations, because copy must not offer an action the page lacks, and amend U-04. The principal-designer replaces this row with the outcome and makes any U-04 amendment |

### 10.1 Chair's pre-read for the 2026-10-06 review (PD-R1-06, prepared 2026-10-05)

The review has **not** been held, so this section does not record an outcome and P7 stays open. It gives a proposed disposition for each agenda item so that the review can run in one pass, or asynchronously as a PR: each participant writes accept or reject (with a reason) in the last column. When every row has a decision, the chair replaces the 2026-10-06 row above with the outcome and makes the copy changes. Proposals are the principal-designer's view (judgment) unless an evidence column cites otherwise.

| # | Agenda item | Proposed disposition | Evidence today | Decides | Decision at review |
|---|---|---|---|---|---|
| R-1 | Walk A-01..A-04, F-01, G-01, Q-01..Q-07, M-01/M-02, U-01..U-04 against the built screens | Run it on the local HTTPS stack, one screen at a time, against §8 (WCAG) and §7 (HAX). Record findings as rows here | Not done: needs the running stack and the participants | all | |
| R-2a | U-04 "different file" copy without "or cancel this upload and start again" | **Accept.** Amend U-04 to: "This is not the same video. Choose 'Sat doubles.mp4' (3.0 GB)." Put the clause back when "Cancel upload" ships (`DELETE /uploads/{id}`, Sprint 2). Copy must not offer an action the page lacks | decision-log 2026-10-05 senior-frontend-engineer (ST-017 U-04); E2E "A different file is chosen to resume" | principal-designer, senior-frontend-engineer | |
| R-2b | Resume banner on M-01 only, not on M-02 | **Accept.** On M-02 the upload panel already asks for the same video, so a banner would repeat it. Amend U-04 "Banner on M-01 and M-02" to "Banner on M-01; on M-02 the panel shows the resume prompt" | same decision-log row | principal-designer, senior-frontend-engineer | |
| R-3 | ST-018 fourth refusal string (codec) | Accept if it follows the U-03 pattern: what is wrong, then what to do, then "Choose a different video" and "Nothing from this file was saved." Add it to U-03 verbatim from the shipped string | To be read from the shipped component at the review | principal-designer, business-analyst | |
| R-4 | ST-019 copy without a "Tag this match" button | Accept for Sprint 1: tagging does not exist yet, so the quality line must not point to it. Keep "You can still tag this match." only if the coach agrees it reads as reassurance, not as a link | U-02 text above; R-2a reasoning | principal-designer, pickleball-domain-coach | |
| R-5 | Quota, conflict and rate-limit states in §6 (PD-R2-02, PD-R3-05) | Add to the §6 states summary: **Quota (429 on create):** panel stays idle ("No video yet", chooser); error summary "You have too many unfinished uploads. Finish one of them from Your matches, then try again.", link to `/matches`. **Conflict before any byte (409):** panel stays idle. **Failure after bytes sent:** progress and "Stopped" stay. Proposed: keep the shipped copy; PM decides on stating the expiry or pulling Cancel forward | review-rounds PD-R2-02 row; decision-log 2026-10-05 senior-frontend-engineer (PD-R2-01/02) | principal-designer, product-manager | |
| R-6 | F-01 link target and the 42 px menu link (PD-R2-06) | The menu link must reach 48 px on touch (§0, [DPA/DESIGN-10]); 42 px passes SC 2.5.8 (24 px) but misses our touch target. Proposed: fix in Sprint 2, as a minor | review-rounds PD-R2-06 row | senior-frontend-engineer | |
| R-7 | Coach sign-off of `capture-guide-wording.md` (item 6) | **Already closed outside the review**: signed off 2026-10-05; the review may change layout, not words | `sed -n 3p docs/domain/capture-guide-wording.md` → `signed-off`; review-rounds PD-R1-05 row | pickleball-domain-coach | Closed 2026-10-05 (coach) |

Open items D-1..D-8 (§9), status on 2026-10-05:

| # | Status | Evidence | Proposed at review |
|---|---|---|---|
| D-1 | Copy in place; needs PM/BA confirmation | `web/src/app/welcome/page.tsx` says the user tells the app who won each rally and the score is unofficial (no automatic-scoring claim) | PM + BA confirm; close |
| D-2 | Built as proposed (format · date on M-01 cards) | `web/src/app/matches/page.tsx:64` | BA confirms against FR-021; close |
| D-3 | **Closed** (principal-engineer, 2026-10-05) | decision-log row: match read model returns `upload` (offset, expiry, `resume_url`, file name) | — |
| D-4 | **Closed** (security-privacy-engineer, 2026-10-05) | decision-log row "Flows D-4 confirmed"; threat-model-sprint-01 T-ML-6 | — |
| D-5 | Open: caps stay provisional from config | blockers.md ST-025 row (needs PO phone clips) | Keep open; owner senior-ml-cv-engineer |
| D-6 | Open: device steps stay hidden | `capture-guide.ts` line 3 comment; capture-guide-wording §5 (device paths out of scope) | Keep open; same blocker as D-5 |
| D-7 | Open | blockers.md SPIKE-06 row (no real devices); ADR 0028 Proposed | Keep open; U-01 "leaving" copy unchanged |
| D-8 | Open: no consent courtesy line shipped. **Product-manager decision 2026-10-05 (review round 2, PD-R2R-03): ship it.** G-01 shows, as a second `notice` next to the safety line, exactly: **"Film only people who agree to be filmed. Don't upload matches with anyone under 18."** The minors sentence is not optional: it is the PO-accepted OQ-05 recommendation ("The capture guide asks users not to upload matches with minors", `open-questions.md` OQ-05; ADR 0023), which the shipped guide lacks (`grep -n -i 'minor\|under 18\|consent' web/src/lib/content/capture-guide.ts` → no matches). The consent sentence is (judgment) from OQ-06 and spec §8 and the coach's recommendation (capture-guide-wording §5 'People you film'). It is a courtesy, not a legal claim: no words about law, rights or compliance until the US/AU legal review (OQ-05). **ST-015 is not DoD-done until the line ships** (senior-frontend-engineer, test-first: a red test that G-01 shows the exact string, then the constant in `capture-guide.ts`) | capture-guide-wording §5 sign-off excludes the consent line (PM/security own it); OQ-05 accepted recommendation | **PM: accept (above).** security-privacy-engineer: still to accept or reject the wording (does it promise or disclose anything it should not?). Then D-8 closes |

### 10.2 Format and date of the review (chair's decision, 2026-10-05, review round 2: PD-R1-06, QA-R2V-12)

The finding asks for one of two things: hold the review asynchronously as a PR, or carry it with a date. The chair decides both the format and a dated fallback, so the review cannot drift again. This does **not** hold the review: P7 stays open until every §10.1 "Decision at review" cell is filled.

1. **Format: asynchronous, in the repo, not as a GitHub PR.** Each participant writes accept or reject with one line of reason in the §10.1 cell for each item they decide (owners per the EM convening row in `docs/sprints/01/blockers.md`) and commits it under ADR 0022. Why not a PR (judgment): agents do not push, and GitHub `sprint-01` is 30 commits behind local (blockers.md item P1), so a PR would show stale screens and copy. This differs from the role rule "design reviews held as PRs" [DPA/DESIGN-15] only in where the comments live; the review keeps the same participants, the coach as SME, and a written decision per item. Once the PO answers P1 and the branch is pushed, later design reviews go back to PRs.
2. **Date: decisions due by end of 2026-10-06.** R-1 (walk the built screens) needs the senior-frontend-engineer on the local HTTPS stack; the other items are decisions on written proposals and need no meeting.
3. **Fallback, with a date: if any cell is empty at end of 2026-10-06,** the chair records "not held" here with the items left, and P7 carries to Sprint 2 as the proposed carry-over row in `docs/sprints/sprint-02.md` (principal-designer, size XS). **Hard date: Sprint 2 planning, 2026-11-02.** No Sprint 2 UI story (Quick Tag, score sheet) starts before it, because those flows extend U-04 and the §6 states.
4. **Until it is held:** stories ST-013, ST-015..ST-019 keep "Design review P7 not yet held" in `open`; the U-04 amendment (R-2a, R-2b) and the §6 quota, conflict and rate-limit copy (R-5; PE-R3-03, PD-R2-02) stay **proposals**, and the shipped copy stays as built. The chair does not mark any of them confirmed.
5. **When every cell is filled,** the chair replaces the 2026-10-06 row in §10 with the outcome (held, date, participants, P7 closed or the items left), amends U-04 and §6, and the done-check in the EM convening row of `docs/sprints/01/blockers.md` passes.
