# Requirements Brainstorm: Design, UX and Frontend View

- **Status:** Draft for discussion. This feeds `functional.md`, `non-functional.md`, the backlog, and `docs/design/<feature>.md` for each sprint.
- **Date:** 2026-10-03
- **Authors:** the principal-designer and senior-frontend-engineer agents
- **Inputs read:**
  - `docs/specs/2026-10-02-racket-analytics-design.md` (the "spec")
  - `.claude/agents/principal-designer.md` and `.claude/agents/senior-frontend-engineer.md`
  - `docs/research/*.md`
  - `docs/process/*.md`
  - `docs/requirements/brainstorm-product.md` (the "product brainstorm"). Its IDs are reused where they apply.
- **Citation convention:** Sources are cited as `<file>/<ID>`, with the prefixes EP, AQS, DPA and DOM [process/working-agreement.md §0]. Only verified sources are cited. Anything without one is marked **(judgment)**.
- **ID scheme (proposed):**
  - `FR-UX-*` are functional UX requirements.
  - `NFR-A11Y-*`, `NFR-UXP-*` (UX performance) and `NFR-TRUST-*` are design-related NFRs.
  - `CD*` are design challenges to the spec.
  - The BA finalises all of these IDs.

## 0. Evidence caveats specific to design

1. **Usability heuristics are unverified.** We could not fetch Nielsen Norman, Apple HIG, Material 3, Google PAIR or web.dev [DPA Gaps], so none of them is cited here. Our human-AI interaction rules come only from Microsoft HAX G1 to G18 [DPA/DESIGN-11]. Our forms rules come from the GOV.UK Design System [DPA/DESIGN-12, DPA/DESIGN-13].
2. **Only some WCAG criteria are verified.** The verified SCs are 1.2.2, 1.2.3, 1.4.3, 1.4.11, 2.4.11, 2.5.7, 2.5.8 and 3.3.8. The research also confirms the full list of criteria that are new in 2.2 [DPA/DESIGN-01 to DESIGN-09]. Other SCs are named below because the AA target implies them (for example 1.4.1 Use of Color, 2.1.1 Keyboard and 1.3.4 Orientation). Their wording was **not** fetched, so each reference to one is marked (judgment: SC not fetched). QA must check those SCs against the W3C text before they become acceptance criteria.
3. **There is no verified web-performance source.** Core Web Vitals thresholds are not in the research, because web.dev is blocked [DPA Gaps]. DESIGN-16 defines the performance categories but gives no numbers [DPA/DESIGN-16]. Every performance number below is **(judgment)**.
4. **No user research exists yet.** Every effort or time target is a hypothesis. We validate them with the R-01 interviews [brainstorm-product §10] and with the usability tests in §9.
5. **Rules and coaching terms are unverified** [DOM G1, G2]. Any UI copy that states a rule ("fault: serve landed on the kitchen line") needs the domain coach to sign it off against the rulebook before it ships.

## 1. Challenges to the design spec (design evidence)

| # | Spec says | Evidence | Proposal |
|---|---|---|---|
| CD1 | Calibration is "confirm 4 corners" (spec §3), which in practice means dragging four handles. | Any function that uses dragging must also work with a single pointer and no drag (SC 2.5.7, AA) [DPA/DESIGN-05]. Dragging a tiny handle on a phone also puts the user's finger over the point being placed (judgment). | Use **tap-to-select a point, then tap-to-place**, with a magnifier loupe and arrow-key or on-screen nudge buttons at 1 px and 10 px steps. Dragging stays available as a shortcut, never as the only method. |
| CD2 | The user confirms the four **corners**. | A homography needs at least 4 point correspondences, and more points with RANSAC handle outliers [DOM G6 H1-H2, partly inferred]. With a camera behind the baseline, the near corners often fall outside the frame or behind the tripod's own fence (judgment). | Let the user confirm **any 4 or more named court keypoints**: corners, the NVZ line ends, centre-line ends and net posts. Show the reprojected court lines live as an overlay, so the user *sees* whether the fit is right. That makes the calibration result explainable (HAX G11) [DPA/DESIGN-11]. |
| CD3 | "Every automatic call shows a confidence" (spec §2). | A doubles match is about 150-300 shots per game (product brainstorm C2, judgment). A confidence badge on every one of them is noise. HAX asks to make clear *how well* the system works (G2) and to time services based on context (G3) [DPA/DESIGN-11]. | Show confidence **everywhere it is asked for, but triage it**. The review screen opens on a "Needs your eyes" queue that holds only low-confidence calls, ordered by score impact. High-confidence calls show a quiet indicator that expands on demand. |
| CD4 | Confidence is a number per call (spec §4, `Shot.confidence`). | A raw model probability does not mean a real-world accuracy (judgment). HAX G2 asks that the user understand **how well** the system does [DPA/DESIGN-11]. | Show **3 calibrated bands** in words: "Sure", "Likely" and "Check this". Each band links to "how we know". A band may only be used when it is backed by measured accuracy on the gold set [DOM G8]. For example, "Sure" must be ≥ 95% correct on the gold set (threshold is judgment). The raw % appears only in a details view. Bands are never colour alone (see NFR-A11Y-05). |
| CD5 | Ball landing heatmaps and "height over the net" (spec §4, §5). | A homography is valid **only for points on the plane** [DOM G6 H1]. An airborne ball does not map correctly. | The UI only shows court-mapped positions for **ground-plane events** (feet and bounces). "Height over net" is shown as "not measured" unless a separate method exists. No chart may present an extrapolated airborne point as a court position. |
| CD6 | The ball trajectory is drawn on the video (implied by "clip linking"). | TrackNetV3 outputs **visibility** as a first-class value, and an occluded ball is "not visible", not a guessed position [DOM G3 B4, DOM/CV-01]. | The trajectory overlay shows **gaps** (a dashed segment labelled "ball hidden") where visibility = 0, and is never interpolated silently. This is HAX G2 applied honestly. |
| CD7 | Capture at "1080p at 60 fps or better" (spec §2). | Our accuracy on 30 fps is unknown, and the product brainstorm proposes reporting instead of rejecting (C7). In a PWA, users mostly pick from the camera roll, so the browser does not control capture settings (judgment). | The capture guide becomes a **pre-match checklist** ("Set your camera to 1080p 60fps: here is where on iPhone / Android"), plus a **post-upload quality report** that names the degradation in plain words. It never blocks an upload. |
| CD8 | "Players trust what they can see" (spec §6). Clips are a later milestone (M4). | HAX G11 is "make clear why the system did what it did" [DPA/DESIGN-11]. A Release 1 plan without clips would rest on stats alone. | From R1, every "why" links to **video timestamps** (the rally start time from Quick Tag). Deep-link seeking into the uploaded video costs little and needs no clip extraction. Extracted clips (M4) improve this later. |
| CD9 | Re-processing is supported (`Event` is kept, spec §4). | HAX: "Update and adapt cautiously" (G14) and "Notify users about changes" (G18) [DPA/DESIGN-11]. | A **user correction is never overwritten by re-processing** (judgment, applying G14). When a model update changes past stats, the user sees a "what changed" summary (G18), with a before → after value for each affected metric. |
| CD10 | Review/correct timeline on "Client (mobile PWA / web)" (spec §3). | On a phone, a sticky video player plus a bottom sheet can hide the focused element, which breaks SC 2.4.11 (AA) [DPA/DESIGN-07]. | Mobile review uses a **split layout**: the video is pinned at the top and takes at most 40% of viewport height, and the timeline list scrolls underneath it. Focus management keeps the focused row scrolled into the visible area. No bottom sheet may cover the focused row. |
| CD11 | The capture guide is "shown in the app" (spec §8). | Prerecorded tutorial video needs captions (1.2.2, A) and an audio description or media alternative (1.2.3, A) [DPA/DESIGN-08, DPA/DESIGN-09]. | The capture guide is a **text and illustration checklist first**, with the video as a supplement. The checklist then works as the media alternative. Captions are always on by default. |
| CD12 | The player's own match video is the core content. | SC 1.2.x applying to user-generated footage is an open question [DPA Implications §3]. | Treat the **score sheet and rally list as the text alternative** for the match video (judgment, as DPA proposes). Every rally row is readable without the video: score, server, winner, ending, and shot count when it is known. |

## 2. Design principles (proposed, judgment, derived from the cited sources)

1. **Show the evidence, then the claim.** Every stat, tendency and drill "why" is one tap away from the rallies or clips that produced it [DPA/DESIGN-11 G11; spec §6].
2. **Honest about uncertainty.** Confidence bands, sample sizes and "not measured" states are visible. Nothing is hidden for being uncertain (spec §5) [DPA/DESIGN-11 G2, G10].
3. **Correction is cheaper than complaint.** Fixing any call takes ≤ 2 taps or 2 keystrokes from where it is seen [DPA/DESIGN-11 G9; target is judgment].
4. **One phone, one hand, courtside.** The flows are designed for a 360 CSS px wide viewport, used one-handed and outdoors (judgment).
5. **One question per page** for setup flows [DPA/DESIGN-12].
6. **Accessible by default, not by audit.** WCAG 2.2 AA is a Definition-of-Done item for every UI story [process/definition-of-done.md; DPA/DESIGN-01].

## 3. UX flows and functional requirements

### 3.1 Onboarding and sign-in

- **FR-UX-01 Passwordless sign-in.** Sign-in uses a passkey or a magic link. It must not depend on remembering a password or solving a puzzle (SC 3.3.8, AA) [DPA/DESIGN-06]. If passwords are ever added, they must allow paste and password managers [DPA/DESIGN-06]. The magic link token is single-use and is removed from the URL after it is exchanged [AQS/SEC-05 14.2.1].
- **FR-UX-02 First-run promise.** One screen states what the app can and cannot do in v1. For example: "We score your match and show where you lose points. One phone can't make line calls good enough to referee from." This applies HAX G1 and G2 [DPA/DESIGN-11] and uses the spec §2 accuracy posture.
- **FR-UX-03 Age and footage notice.** The interim age confirmation from product brainstorm C12 appears as a question page [DPA/DESIGN-12]. The legal wording is escalated (PO decision).

### 3.2 Capture guide (US-201)

- **FR-UX-10 Checklist.** The guide is no more than 6 checklist items, each with an illustration and alt text that describes its purpose [DPA/DESIGN-10 content descriptions]. The items (domain wording to be confirmed by the coach) cover:
  - placing the tripod behind a baseline
  - elevation ("as high as you safely can")
  - landscape orientation
  - 1080p at 60 fps (spec §2)
  - keeping the whole court in frame
  - avoiding direct sun behind the court (spec §8: backlight)
- **FR-UX-11 Guide video.** The guide video is 30-60 s long and captioned [DPA/DESIGN-08]. The checklist text is its media alternative [DPA/DESIGN-09].
- **FR-UX-12 Platform help.** "How to set 60 fps on my phone" offers expandable iPhone and Android steps (content still to be written, judgment).
- **FR-UX-13 Framing check (Should, R2).** The user can upload a single still frame *before* the match to get a "court visible?" check (judgment). This needs the M1 court detector, so it is R2.

### 3.3 Match setup (one question per page)

- **FR-UX-20 Order of questions.** The setup flow asks, one per page [DPA/DESIGN-12]:
  1. format (doubles or singles)
  2. scoring system (side-out or rally; rally is labelled "provisional option" pending rule verification [DOM G1 R3])
  3. who is on each side (nicknames only; this is privacy C6)
  4. which player is "me"
  5. date (pre-filled)
  6. video
- **FR-UX-21 Page pattern.** Each page has a Back link at the top and a "Continue" button. Optional fields say "(optional)", and required fields carry no asterisks. Known answers are pre-filled from the last match [DPA/DESIGN-12].
- **FR-UX-22 Validation errors.** Errors use the GOV.UK error summary [DPA/DESIGN-13]:
  - the heading "There is a problem", with focus moved to the summary
  - a link from each entry to its field
  - the same wording in the summary and at the field
  - the page title prefixed with "Error:"
- **FR-UX-23 Check answers.** A final "Check your answers" page lists every answer with "Change" links before the upload starts (judgment; this GOV.UK pattern was not in the fetched pages).

### 3.4 Upload (US-202, US-203)

- **FR-UX-30 Resumable upload.** The client follows tus 1.0.0: HEAD for the offset, PATCH from the offset, and on 409 it re-syncs the offset [AQS/STACK-06]. The UI shows:
  - % uploaded and MB of total
  - an estimated time remaining once at least 10 s of throughput has been measured (judgment)
  - a plain-language state: Uploading / Paused: waiting for connection / Resuming / Done
- **FR-UX-31 Leaving during upload.** The user may leave the upload screen and the upload continues while the tab is alive. If the tab or app is closed, the upload resumes from the last offset on the next visit, with no restart. The banner reads "Your upload of 'Sat doubles' is 64% done. Resume?" (judgment). A PWA cannot be relied on to upload in the background after the tab closes (judgment; no verified source either way). The copy must therefore **not** promise a background upload.
- **FR-UX-32 Keep-screen-on hint.** On mobile, a dismissible hint asks the user to keep the screen on during upload for large files (> 1 GB) (judgment).
- **FR-UX-33 Validation failures.** Wrong type, too large or too long uses the error summary pattern [DPA/DESIGN-13] and gives the cap in human units ("Videos up to 2 h 30 min and 8 GB"; the caps come from R-05). Server-side checks are authoritative [AQS/SEC-02].
- **FR-UX-34 "Analysis ready" notification.** The app offers web push, opt-in and asked only *after* the first upload completes [AQS G8.3 STACK-04; timing is HAX G3 "time services based on context", DPA/DESIGN-11]. The app also shows an in-app status, because push is optional.

### 3.5 Footage quality report (US-204)

- **FR-UX-40 Report contents.** After upload, the report shows fps, resolution, duration and, in R2, a court-visibility estimate. For each problem it names the **consequence**, not the defect. Example: "30 fps: shot types may be less accurate. Score and rally stats are unaffected." This applies HAX G16 "convey the consequences of user actions" [DPA/DESIGN-11].
- **FR-UX-41 Analysis level.** A degraded analysis gets an explicit level badge: "Full analysis", "Rally and score only" or "Manual tagging only". This is the spec §8 graceful degradation, made visible [AQS implications: degradation is an explicit state].

### 3.6 Court calibration (M1)

- **FR-UX-50 Auto-detect first.** The system proposes court keypoints and overlays the full court model on a still frame. The user chooses "Looks right" or "Adjust" (HAX G8/G9, efficient dismissal and correction) [DPA/DESIGN-11].
- **FR-UX-51 Adjust mode without dragging** [DPA/DESIGN-05]:
  - Point chips ("Near-left corner", "Kitchen line, left"…). Each chip is a ≥ 48 dp target [DPA/DESIGN-10].
  - Select a chip, then tap the frame to place the point. A 3× loupe shows while placing.
  - Nudge buttons and arrow keys move the point 1 px; Shift moves it 10 px.
  - Dragging is also supported.
  - Every placement re-renders the reprojected court lines in < 100 ms (judgment).
- **FR-UX-52 Fit quality.** The fit is shown as a band ("Good fit", "Check the far baseline") and backed by the reprojection error threshold the ML engineer documents [DOM implications: Homography]. If a minimum of 4 points is not met, Continue is disabled and the reason is stated.
- **FR-UX-53 Keyboard and screen reader path.** Each point is a list item with x/y spin buttons. The overlay is decorative to assistive technology, and the list is the accessible representation (judgment).
- **FR-UX-54 Overlay contrast.** The court overlay meets 3:1 against the frame [DPA/DESIGN-04]. Because the frame changes, lines are drawn with a 2-tone stroke (light core, dark halo) (judgment).

### 3.7 Quick Tag (R1) and the review/correct timeline (R2-R3)

- **FR-UX-60 Quick Tag layout.** The video is on top. Below it is a rally control bar with Rally start, Rally end, Winner side (us/them) and Ending (winner / unforced error / fault). Every control is ≥ 48 dp [DPA/DESIGN-10] with ≥ 8 dp spacing (judgment). The bar never overlaps the focused control [DPA/DESIGN-07].
- **FR-UX-61 Keyboard map.** The keyboard map is shown in-app with `?`:
  - Space: play/pause
  - `,` / `.`: step one frame
  - `J`/`L`: −5/+5 s
  - `S`/`E`: rally start/end
  - `1`/`2`: winner side
  - `W`/`U`/`F`: ending
  - `Z`: undo

  Single-key shortcuts can be turned off or remapped (judgment: SC 2.1.4 Character Key Shortcuts, not fetched). The keyboard path gives results identical to tapping (US-401 scenario).
- **FR-UX-62 Score feedback.** After each tag, the computed score is shown and also announced through a polite live region ("Rally 7: them. Score 4-6-1."). Score calling follows the coach-verified format [DOM G1 R6, unverified].
- **FR-UX-63 Review queue (R2+).** "Needs your eyes" lists calls in band "Check this", sorted by **score impact first** (rally winner, server, fault), then by stat impact (CD3). Each item shows:
  - the clip, auto-looping 2 s before to 1 s after the event (judgment)
  - the system's call and its band
  - one-tap "Correct" and "Change to…" options with the 2-3 most likely alternatives (HAX G9) [DPA/DESIGN-11]
- **FR-UX-64 Full timeline.** The timeline is a vertical list of rallies (not a horizontal scrubber, which conflicts with SC 2.5.7 on mobile) [DPA/DESIGN-05]. Each row shows:
  - the score before → after
  - the server
  - the winner
  - the ending
  - a band icon *and* text
  - a "corrected by you" marker (spec §4 `corrected_by_user`)

  Expanding a rally shows its shots.
- **FR-UX-65 Consequences of a correction.** Before saving a correction that changes later scores, the app says so: "This changes the score of the next 12 rallies" (HAX G16). After saving, it shows which stats changed (HAX G18) [DPA/DESIGN-11]. Every correction can be undone (US-403).
- **FR-UX-66 Identity fix.** In doubles, the identity fix is a one-time "Who is who" step: tap each of 4 player thumbnails and assign a nickname, with exactly 2 per side enforced [DOM G4 P4]. A swap mid-match is fixed with one "Swap these two from here on" action (judgment). No face recognition anywhere (spec §8).
- **FR-UX-67 Feedback reason (granular, HAX G15).** On a correction, an optional single-tap reason can be given: "ball hidden", "wrong player", "wrong shot type" or "other". It feeds training data [DPA/DESIGN-11 G13, G15]. It never blocks saving.

### 3.8 Score sheet and stats dashboard (US-304, US-501, US-502)

- **FR-UX-70 Score sheet.** The score sheet is a semantic HTML table with a caption, column headers and row headers (rally #). It is readable at 360 px width by stacking columns into labelled rows (judgment). This is the text alternative for the match (CD12).
- **FR-UX-71 Metric card.** Every metric card shows:
  - the value
  - **n** (the sample size)
  - a "low sample" label when n is below the threshold (spec §5; the n < 10 rallies threshold from US-501 is judgment)
  - a "How is this measured?" link
  - a "Show me" link to the rallies behind it (principle 1)

  Low-sample metrics are visually de-emphasised but never hidden, and the label is in text.
- **FR-UX-72 Charts.** Every chart has:
  - a visible data-table toggle (judgment: text alternative, SC 1.1.1 not fetched)
  - marks with ≥ 3:1 contrast against adjacent colours and the background [DPA/DESIGN-04]
  - a non-colour encoding: direct labels, patterns or shapes (judgment: SC 1.4.1 not fetched)
- **FR-UX-73 Heatmaps.** Heatmaps use **no more than 5 binned levels**, each carrying a printed value or label on the court cell. A colour-blind-safe sequential ramp is used whose adjacent steps reach 3:1 where possible. Where they cannot, the printed labels carry the information [DPA/DESIGN-04; the bin count is judgment]. The court-zone grid follows the court model (kitchen and transition zones per the sport plug-in, spec §3).
- **FR-UX-74 Trends.** Trends show the last 5 matches as a dot plot with n per point. A change is labelled "too few rallies to tell" unless both samples meet the threshold (product brainstorm US-1102).

### 3.9 Training plans (US-601, US-1101, US-1102)

- **FR-UX-80 Plan overview.** The overview lists, in plain language, the top 3 point leaks the plan targets, each with points lost per match and n (spec §6 step 1). It then shows the sessions as a checklist.
- **FR-UX-81 Drill card.** A drill card shows:
  - the name, duration, number of players and equipment
  - a "Why this drill" sentence naming the metric and its value, linked to the rallies (spec §6; HAX G11)
  - "Done" and "Not for me" buttons

  "Not for me" is dismissal with an optional reason (HAX G8, G15) and swaps in an alternative drill from the library [DPA/DESIGN-11].
- **FR-UX-82 Plan source.** When the LLM wrote the "why", a small "Written by AI from your stats" label appears (HAX G1/G2). If the LLM path fails, the rules-only fallback plan (product brainstorm C10) looks identical apart from a plainer "why". The user never sees an error state for an LLM failure.
- **FR-UX-83 Plan efficacy.** After the next match, plan efficacy shows before → after with n for each targeted metric. The app does not claim improvement unless both samples meet the threshold (US-1102).
- **FR-UX-84 Global control (HAX G17).** A setting turns AI-written explanations off and uses rules-only text [DPA/DESIGN-11].

### 3.10 My data (J5)

- **FR-UX-90 Video list.** The list shows each video with its size, its retention date and a "Delete" button. Deletion uses a confirmation page that states the consequence: "Deletes the video, clips, tags and stats for this match. Plans keep a note that the match was deleted." (HAX G16).
- **FR-UX-91 Logout.** Logout clears authenticated data from client storage and service-worker caches [AQS/SEC-05 14.3.1]. Media URLs are short-lived signed URLs and are never cached by the service worker (judgment, from AQS/SEC-05 14.3.2 `no-store` and AQS/STACK-04 service-worker cache rules).

## 4. Screen state inventory (required by the designer Definition of Done)

Every screen in scope must specify these states. A missing state fails the design review (principal-designer DoD).

| Screen | Empty | Loading | Error | Low-confidence | Low-sample | Offline |
|---|---|---|---|---|---|---|
| Upload | "No matches yet" plus a guide link | progress (FR-UX-30) | error summary [DPA/DESIGN-13] | – | – | paused, resumes automatically |
| Quality report | – | skeleton | generic message, no stack traces [AQS/SEC-04 16.5.1] | – | – | cached last report |
| Calibration | – | "Finding court lines…" | "Couldn't find the court. Place the points yourself" | fit band "Check" | – | still frame works offline (judgment) |
| Review queue | "Nothing to check" | per item | retry | the default content | – | read-only |
| Score sheet | "Tag your first rally" | skeleton rows | retry | band per row | – | read-only cached |
| Dashboard | "Upload a match to see stats" | skeleton | retry | – | label + n | read-only cached |
| Plan | "Need 1 tagged match" | skeleton | rules-only fallback | – | "Based on limited data (n rallies)" | read-only cached, mark done queued |

An analysis job runs for minutes or longer (NFR-UXP-07), so the "Analysing" state is shown as a page with stages and an estimate, never a spinner (judgment).

## 5. Accessibility NFRs (WCAG 2.2 AA)

| ID | Requirement | Measure / test | Source |
|---|---|---|---|
| NFR-A11Y-01 | Conformance target: WCAG 2.2 Level AA for all user-facing screens | axe-core in CI on every PR, plus a manual keyboard and screen-reader pass each sprint on changed screens | [DPA/DESIGN-01, DPA/DESIGN-14] |
| NFR-A11Y-02 | Pointer targets ≥ 24×24 CSS px everywhere. Touch targets for primary and tagging controls ≥ 48×48 CSS px (48 dp) | Automated target-size check in Playwright (judgment: custom check), plus review | [DPA/DESIGN-02, DPA/DESIGN-10] |
| NFR-A11Y-03 | Text contrast ≥ 4.5:1, or ≥ 3:1 for large text, including text drawn over video, which gets a scrim | axe-core plus manual checks on video overlays | [DPA/DESIGN-03] |
| NFR-A11Y-04 | UI components, focus indicators, chart marks, heatmap cells and court overlays ≥ 3:1 against adjacent colours | Design token check, plus manual checks on 3 reference frames (sunny, shaded, indoor) | [DPA/DESIGN-04] |
| NFR-A11Y-05 | Confidence bands, low-sample flags, winners and errors are never conveyed by colour alone (text, icon or shape too) | Design review; greyscale screenshot test (judgment) | judgment (SC 1.4.1 not fetched); supports [DPA/DESIGN-11 G2] |
| NFR-A11Y-06 | No function requires dragging: calibration, timeline seeking, trimming, reordering | E2E tests that complete each flow with taps and keys only | [DPA/DESIGN-05] |
| NFR-A11Y-07 | Focused elements are never fully hidden by the sticky video, the tag bar, banners or bottom sheets | Playwright test: tab through each screen at 360×640 and assert the focused element's bounding box intersects the visible, unobscured viewport | [DPA/DESIGN-07] |
| NFR-A11Y-08 | Sign-in has no cognitive function test (passkey or magic link) | E2E plus review | [DPA/DESIGN-06] |
| NFR-A11Y-09 | Tutorial videos are captioned and have a text alternative. The match video's text alternative is the score sheet | Content checklist | [DPA/DESIGN-08, DPA/DESIGN-09]; CD12 judgment |
| NFR-A11Y-10 | Every interactive feature works with a keyboard alone, including Quick Tag, review and calibration | E2E keyboard-only journeys | judgment (SC 2.1.1 not fetched); US-401 scenario |
| NFR-A11Y-11 | Content descriptions state purpose, are unique within lists, and do not repeat the role. Decorative overlays are hidden from assistive technology | Review, plus axe "accessible name" rules | [DPA/DESIGN-10] |
| NFR-A11Y-12 | Score changes and upload state changes are announced through polite live regions without moving focus | Manual screen-reader test (VoiceOver iOS, TalkBack Android) | judgment (SC 4.1.3 not fetched) |
| NFR-A11Y-13 | Layout works in portrait and landscape and reflows at 320 CSS px wide with no two-direction scrolling, except the video itself | Playwright viewport matrix 320 / 360 / 768 / 1280 | judgment (SC 1.3.4 and 1.4.10 not fetched) |
| NFR-A11Y-14 | Autoplaying review clips loop for no more than 5 s unless the user asks for more, and can be paused | Review | judgment (SC 2.2.2 not fetched) |

## 6. UX performance NFRs (all numbers are judgment; categories from [DPA/DESIGN-16])

The reference device and network for these targets is a mid-range Android phone (about 4 GB RAM) on a 4G connection throttled to 9 Mbps down / 1.5 Mbps up in Playwright/Lighthouse lab runs. The QA lead confirms this profile. All the numbers below are judgment.

| ID | Requirement | Target |
|---|---|---|
| NFR-UXP-01 | Time to an interactive score sheet or dashboard (product brainstorm NFR-PERF-01) | p95 ≤ 2.0 s on a warm visit; ≤ 3.5 s on a cold visit |
| NFR-UXP-02 | Tag or correction tap → updated score visible (NFR-PERF-02) | p95 ≤ 200 ms. The score update is optimistic and confirmed by the server |
| NFR-UXP-03 | Seek from a rally row or "Show me" link → video playing at that moment | p95 ≤ 1.5 s on 4G |
| NFR-UXP-04 | Input responsiveness for any tap or key on the tagging screens | p95 ≤ 100 ms to visual feedback |
| NFR-UXP-05 | JavaScript sent for the first route | ≤ 200 KB gzip; charting and video libraries are lazy-loaded |
| NFR-UXP-06 | Upload overhead: client throughput reaches ≥ 90% of measured network uplink; chunk size adapts between 5 MB and 50 MB | Network-throttled E2E |
| NFR-UXP-07 | User-visible analysis estimate shown on the "Analysing" page, and its accuracy | The estimate is within ±30% of the actual time for 80% of jobs (ties to NFR-PERF-03) |
| NFR-UXP-08 | Layout stability: no content shift when stats or scores load | Skeletons have reserved dimensions; visual regression test |

## 7. Trust and explainability NFRs

| ID | Requirement | Measure | Source |
|---|---|---|---|
| NFR-TRUST-01 | Every automatic call that is shown has a confidence band, and every band is backed by measured accuracy on the gold set for the current `pipeline_version` | Model-quality test layer publishes per-band accuracy; the UI reads the bands from config | [DPA/DESIGN-11 G2]; [DOM G8] |
| NFR-TRUST-02 | Bands are well calibrated: observed accuracy for "Sure" ≥ 95%, "Likely" 80-95%, "Check this" < 80% on the gold set (thresholds are judgment) | Re-measured every model release; a release that violates a band is blocked | judgment, applying [DPA/DESIGN-11 G2] |
| NFR-TRUST-03 | Every metric, tendency and drill "why" links to ≥ 1 rally or video moment, up to 10, with a "see all n" option | E2E: crawl the dashboard and plan and assert every insight has a working evidence link | spec §6; [DPA/DESIGN-11 G11] (NFR-TRACE-01) |
| NFR-TRUST-04 | Every displayed metric shows its n. A metric below the threshold is labelled "low sample", and no plan or efficacy claim relies on it alone | Unit tests on metric view-models | spec §5; [DPA/DESIGN-11 G10] |
| NFR-TRUST-05 | User corrections are never overwritten by re-processing. A re-processing that changes displayed values produces a "what changed" notice | Integration test: correct, re-process, assert the correction persisted and the notice was emitted | [DPA/DESIGN-11 G14, G18] |
| NFR-TRUST-06 | AI-written text is labelled as such. It names only drills and metrics that exist (validated server-side) | Contract test plus coaching evals | [DPA/DESIGN-11 G1]; [AQS implications SEC-08 API10]; [DPA/AI-05] |
| NFR-TRUST-07 | Review effort (R3): median "Needs your eyes" queue ≤ 15 items per game; median review time ≤ 5 min per match | Product analytics on beta users | judgment; supports spec M3 and product brainstorm J1 |
| NFR-TRUST-08 | No face recognition, and no inference of identity, age or other personal attributes is ever shown. Player labels are user-assigned nicknames | Design review checklist item | spec §8; [DPA/DESIGN-11 G6] (mapping judgment, as DPA notes) |

## 8. Privacy and security requirements with a design surface

- **FR-UX-100 Privacy statement.** "Private by default" is stated on the upload page: "Only you can see this video." Sharing does not exist in the MVP (product brainstorm §12). There are therefore no share links, and no IDs or tokens appear in shareable URLs [AQS/SEC-05 14.2.1].
- **FR-UX-101 Authorisation.** The client never decides authorisation. A 404 for someone else's match renders the same "not found" page as a missing match [AQS/SEC-03 8.3.1, AQS/SEC-09].
- **FR-UX-102 Error copy.** Error copy is generic and actionable, with no stack traces or IDs beyond a short support reference [AQS/SEC-04 16.5.1].
- **FR-UX-103 Opponent nicknames.** The nickname field has helper text: "Use a nickname. Don't enter contact details." (product brainstorm C6).

## 9. Design validation plan (how we test the design itself)

| What | Method | When | Pass |
|---|---|---|---|
| Quick Tag speed (US-401) | Moderated test, ≥ 5 players, tagging one recorded game on their own phone | Sprint that ships Quick Tag | median ≤ 5 s per rally; ≤ 1 mis-tag per 20 rallies (judgment) |
| Calibration without drag | Same panel, with one keyboard-only session and one screen-reader session | M1 sprint | ≥ 4/5 complete calibration within 2 min (judgment) |
| Confidence comprehension | 5-second test plus questions: "What does 'Likely' mean?" | Before the R2 review queue ships | ≥ 4/5 explain it as "probably right, worth a glance" (judgment) |
| Plan trust | Show a plan with "why" links; ask "Would you do this drill? Why?" | Before R1 exit | ≥ 4/5 cite the stat or the clip in their answer (judgment) |
| Accessibility | axe-core in CI; manual VoiceOver and TalkBack pass; keyboard-only E2E | Every sprint | 0 serious or critical axe violations; manual checklist complete [DPA/DESIGN-14] |
| Design review | A PR on `docs/design/<feature>.md` before implementation, with the domain coach as an SME reviewer | Before each UI sprint | Review outcome recorded [DPA/DESIGN-15] |

Recruitment needs a human (designer boundary: real-user research is escalated to the EM or human).

## 10. Design deliverables per release (input to sprint planning)

| Release | Design artefacts (`docs/design/`) |
|---|---|
| R1 | `onboarding-signin.md`, `capture-guide.md`, `match-setup.md`, `upload.md`, `quality-report.md`, `quick-tag.md`, `score-sheet.md`, `starter-dashboard.md`, `plan-rules-only.md`, `my-data.md`, plus design tokens (colour with contrast proofs, type scale, spacing, 48 dp target grid) and the confidence/sample component spec |
| R2 | `calibration.md`, `identity-fix.md`, `review-queue.md`, `analysing-status.md`, `plan-llm-why.md`, `reprocessing-notice.md` |
| R3 | `full-timeline.md`, `clip-player.md`, `patterns-dashboard.md`, `heatmaps.md` |

Each artefact completes the WCAG 2.2 AA and HAX checklists from the principal-designer DoD. The UX decisions with alternatives get ADRs: confidence bands (CD4), the no-drag calibration (CD1/CD2) and the vertical timeline (FR-UX-64).

## 11. Suggested Gherkin seeds (for the BA)

```gherkin
Feature: Court calibration without dragging
  Rule: Every calibration point can be placed with taps or keys only
    Scenario: Place a point by tapping
      Given the automatic court fit is marked "Check the far baseline"
      When Ivy selects "Far-left corner" and taps its position on the frame
      Then the court lines redraw through the new point
      And the fit quality is shown in words
```

```gherkin
Feature: Confidence on automatic calls
  Rule: Low-confidence calls that affect the score are reviewed first
    Scenario: Review queue order
      Given the analysis has 3 "Check this" calls, one of them a rally winner
      When Ivy opens "Needs your eyes"
      Then the rally-winner call is listed first
      And each call shows its band in words
```

```gherkin
Feature: Corrections survive re-processing
  Rule: A user's correction is never overwritten by a new model version
    Scenario: Re-process after correction
      Given Ivy corrected rally 7's winner
      When the match is re-processed with a new model version
      Then rally 7 still shows her correction
      And she sees a summary of what changed in her stats
```

## 12. Open questions for the human product owner

1. **Confidence bands (CD4).** Do you accept 3 word bands backed by gold-set accuracy instead of raw percentages? This makes NFR-TRUST-02 a release gate for models.
2. **Evidence links from R1 (CD8).** Should we commit to timestamp deep links from R1, before clip extraction exists?
3. **Calibration redesign (CD1/CD2).** Do you approve replacing "confirm 4 corners" with "confirm any 4 or more named court points, no dragging required"?
4. **Reference device and network.** Is the proposed mid-range Android on throttled 4G acceptable? Should iPhone Safari also be a release-blocking test target?
5. **Usability test recruitment.** Can you recruit ≥ 5 amateur players for moderated tests at the R1 exit and before the R2 review queue?
6. **Upload copy (FR-UX-31).** Background upload after closing the tab is not reliable in a PWA (judgment). Do you accept "resume on return" copy, or is a native wrapper needed earlier than the spec says?
7. **Language and locale.** Is v1 English only? This affects copy length budgets and score-calling formats.
