# Sprint 2 manual screen-reader pass (C-06; NFR-027 (b))

- **Owner:** senior-qa-engineer (plan, script, record). **Tester:** a human with the devices, provided by the product owner (blockers.md row 1, item **P6**, due 2026-11-13). **Reviewer:** principal-designer.
- **Why:** NFR-027 (b) asks for a manual keyboard and screen-reader checklist (VoiceOver on iOS, TalkBack on Android) on changed screens, 100% complete each sprint. Automated axe runs (G02-10) cannot hear what a screen reader says. Carried Sprint 1 finding **QA-R3-GATE-01** (major) stays open in `review-rounds.md` until every row below has a result. It counts in G02-11, not in G02-10.
- **Status (2026-10-06):** **Waiting on P6.** No human tester or device is available to the agents. The plan and the script are ready. Nothing below has been run, and no result is invented.

## 1. Set-up

| Item | Value |
|---|---|
| Stack | The Sprint 2 Compose stack over https (goal scorecard §4.0), at the head the verifier records. The tester opens `https://<host>:<port>` on the phone over the local network, or a tunnelled https URL the SRE provides. |
| Devices | iPhone with the current iOS and Safari, using VoiceOver. Android phone with Chrome, using TalkBack. Each is one column in §3. |
| Account | A fresh account per device (magic link to a Mailpit address the QA engineer reads out). |
| Fixture | `fixtures/clips/synthetic-60s/clip.mp4` (60 s, H.264) for upload, Quick Tag and rally video. The 30 fps clip `fixtures/clips/phone-profiles-v1/h264-mp4-1080p30.mp4` is used for the M-02 quality report. |
| Copy reference | `docs/design/flows-sprint-01.md` (A, F, G, Q, M, U screens). Sprint 2 screens use the copy the FE ships until `flows-sprint-02.md` exists. |

## 2. What each row checks

For every screen and state, the tester checks five things. A row passes only if all five pass. Any failure becomes a finding, with the device, the screen reader and the exact words heard.

1. **Arrival:** the page or state is announced by its `<h1>` or its title, and focus lands where the flow says.
2. **Reading order:** swiping through the page reads every piece of content once, in visual order, with no unlabelled control.
3. **Controls:** every button, link, radio and field is announced with its name, role and state (pressed, selected, expanded, invalid).
4. **Changes:** a status change (upload percentage, "Paused", a saved tag, a score, an error summary) is announced without moving focus away, unless the flow says focus moves.
5. **Errors:** an error summary is announced, its link moves focus to the field, and the field is announced as invalid with its message.

## 3. Script and results

Sprint 1 screens (carried, QA-R3-GATE-01) come first. The Sprint 2 screens follow (NFR-027 (b): changed screens).

| # | Screen / state | Steps for the tester | Expected (from the flows) | VoiceOver iOS | TalkBack Android |
|---|---|---|---|---|---|
| 1 | A-01 Sign in | Open the site signed out | "Sign in or create an account", heading level 1; one email field labelled "Email address"; button "Send me a link" | not run | not run |
| 2 | A-01 error, 429 | Request 6 links for one address | Error summary "There is a problem" announced; link "You can ask for a new link at hh:mm" moves focus to the field | not run | not run |
| 3 | A-02 Check your email | Submit a valid address | Focus on the heading "Check your email", which is announced; the address is read; "send a new link" is a button | not run | not run |
| 4 | A-03 Signing you in | Open the emailed link | The heading is announced; no token is read out from the address bar after the exchange | not run | not run |
| 5 | A-04 Link expired / used | Open a used link | The heading names the problem; the "Send a new link" action is reachable next | not run | not run |
| 6 | A-05 Signed out | Account menu, then "Sign out" | "You have signed out" announced; the menu button is announced as a menu button with its expanded state | not run | not run |
| 7 | F-01 What this app does | First sign-in of a new account | The heading, then "Record your first match" link | not run | not run |
| 8 | G-01 How to film your match | Open the guide | The video has captions and a text alternative; the illustrations have text descriptions | not run | not run |
| 9 | Q-01..Q-07 Match set-up | Create a doubles match | Each question page: the question is the heading or the legend; radios are announced with their group; "Continue" | not run | not run |
| 10 | Q-03 error | Enter three players for doubles | Error summary with "Each side needs two players"; the link moves focus to the field | not run | not run |
| 11 | U-01 Uploading | Create the match and upload | "Uploading" state announced; the percentage is announced at most every 10%; "Pause" button state | not run | not run |
| 12 | U-01 Paused (offline) | Turn on airplane mode mid-upload | "Paused: waiting for connection", then "Resuming" and "Uploading" when back online | not run | not run |
| 13 | U-01 Stopped / Try again | (Only with the QA engineer forcing a server error) | The error text and its support reference are read; "Try again" is a button | not run | not run |
| 14 | U-03 Video not accepted | Choose a PDF renamed `.mp4` | Error summary "This file is not a video we can read"; "Nothing from this file was saved." | not run | not run |
| 15 | U-04 Resume banner | Close the tab mid-upload, come back | "Your upload of '…' is n% done." and the "Resume upload" button | not run | not run |
| 16 | M-01 Your matches | After an upload | Each card: name, date and status are read as one item with its link | not run | not run |
| 17 | M-02 Match with facts and report | The 30 fps clip | "Video received"; the facts line; the "Footage quality" region and its text; "Tag rallies" and "Score sheet" links | not run | not run |
| 18 | T-01 Quick Tag | "Tag rallies", start game 1, tag 6 rallies | Buttons announced with their pressed state; after each tag the polite announcement "Rally n: …" with the new score, focus stays on the controls (E2E-02-03 checks the text only) | not run | not run |
| 19 | K-01 Key map | On a phone with a keyboard, or skip with a reason | The dialog is announced with its title; focus is trapped and returns to "Keyboard shortcuts" on close | not run | not run |
| 20 | S-01 Score sheet | "Score sheet" | "unofficial scoring (rules not yet verified)" is read before the table; one table per game with its caption; row headers "Rally n"; cells read with their column headers | not run | not run |
| 21 | S-01 correction | Switch the winner of rally 2 | The change and the re-scored rallies are announced; "Undo" is reachable | not run | not run |
| 22 | H-01 Correction history | Open the history | A list; each entry reads field, old value and new value, who and when | not run | not run |
| 23 | V-01 Rally video | "Watch rally 3" | The region "Rally 3 video" and "Starts at m:ss" are announced; the player controls are named | not run | not run |
| 24 | Needs your decision | A correction that ends a game early (QA engineer prepares the match) | "Needs your decision" is read on each kept rally, with both actions as buttons | not run | not run |

## 4. Result

- **Rows run:** 0 of 24 on VoiceOver and 0 of 24 on TalkBack.
- **Findings:** none yet. Each failure goes to `review-rounds.md` as an Open row, owned by the senior-frontend-engineer (or the principal-designer for copy).
- **Closure:** QA-R3-GATE-01 closes only when every row has a result on both readers and every resulting finding is fixed or deferred to a named row.
