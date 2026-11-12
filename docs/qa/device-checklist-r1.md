# R1 real-device checklist (NFR-024.4-.5; P20)

- **Status:** v0.1, 2026-11-05 (senior-frontend-engineer, ticket ST-079). Ready for P20.
- **Who runs it:** decided by the PO in P20 ([`po-escalations.md`](../sprints/05/po-escalations.md) §4, P20). The recommendation is option (a): the P9 testers, on their own phones, in the same session. **Deadline 2026-12-16.**
- **What it covers:** the two human items of NFR-024. NFR-024.4 is real iOS Safari, current and previous major version. NFR-024.5 is real Android Chrome, current and previous major version ([`requirements-breakdown.md`](../sprints/05/requirements-breakdown.md), NFR-024; OQ-17: both browsers block the release).
- **What it does not cover:** NFR-024.1-.3. Those are the emulated projects (`chromium`, `webkit`, `android-chrome`), and the nightly `browser-matrix` job measures them (goal-scorecard §4 G05-04). This sheet uses the same critical journeys, so a fail here can be compared with the emulated run.
- **Until it is run:** the scorecard row S5-P20 reads "not met: waiting on P20". Emulation is not evidence for NFR-024.4-.5.

## 1. Before the session

1. One run per **device × browser version**. You need four rows at minimum: iOS Safari current, iOS Safari previous, Android Chrome current, Android Chrome previous. For each row, record the exact version: on iOS, Settings → General → About; in Chrome, Settings → About Chrome.
2. The stack is the R1 release candidate, reached over https. Note its URL and commit in §3.
3. Each tester uses a **test account** made for the session (for example `p20-<n>@example.test`). Never use a personal address. Do not photograph the screen if anyone else's data is on it.
4. Each tester needs a short match video (about 1 min, recorded on the phone) and a few minutes on Wi-Fi.
5. Pass rule for a step: it works the first time, with no reload, and nothing is cut off or hidden at the phone's width. If a step needs a retry, mark it **fail** and write what happened.

## 2. The critical journeys, step by step

The ids match the `@critical` Playwright specs (`web/e2e/helpers/critical-journeys.ts`).

| # | Journey (spec) | Steps on the phone | Pass when |
|---|---|---|---|
| 1 | Sign-in (`web/e2e/sprint-01/sign-in.spec.ts`) | Open the site. Enter the test address and ask for a link. Open the link from the mail app on **the same phone**. | You are signed in. The page asked only for an email address. The link opens the site in the browser under test. |
| 2 | Upload resume, E2E-01-02 (`web/e2e/sprint-01/resumable-upload.spec.ts`) | Create a match and start the video upload. At about 30 %, turn on airplane mode for 10 s, then turn it off. | The upload pauses with a message, then continues from where it stopped (it does not restart from 0 %) and finishes. |
| 3 | Upload to plan, E2E-04-01 (`web/e2e/sprint-04/journey-v3.spec.ts`) | Tag the rallies with Quick Tag. Open the score sheet, then stats, then the plan. Open one "why" link and one "Show me" clip. | Each page opens. The video plays inline. "Why" leads to the metric, and "Show me" plays the clip. |
| 4 | Plan states, E2E-04-02 (`web/e2e/sprint-04/plan-states.spec.ts`) | With a new test account, open the plan before tagging anything. | The page says there is no plan yet and tells you to tag a match first. There is no blank page and no error. |
| 5 | Done offline, E2E-04-03 (`web/e2e/sprint-04/offline-done.spec.ts`) | Open the plan. Turn on airplane mode. Tap "Mark done" on one session and reload the page. Turn airplane mode off. | The session stays marked done after the reload. Once you are back online, it syncs once and shows no duplicate. |
| 6 | Swap with no alternative, E2E-04-04 (`web/e2e/sprint-04/swap-no-alternative.spec.ts`) | Tap "Not for me" on a drill that has no alternative. Close the dialog. | The dialog says no other drill fits. The drill stays. Focus or the screen-reader cursor goes back to "Not for me". |
| 7 | Narrow screen and keyboard, E2E-04-05 (`web/e2e/sprint-04/keyboard-and-narrow.spec.ts`) | Turn the phone upright and set the largest text size the tester normally uses. Open the plan, the swap dialog and the preferences page. If a Bluetooth keyboard is at hand, repeat with Tab/Enter. | No sideways scrolling. Every button can be reached and read. |

## 3. Result sheet (one row per device × browser version × journey)

| Date | Tester (initials) | Device model | OS version | Browser and version | Stack URL and commit | Journey # | Pass / fail | Notes (what happened; no personal data) |
|---|---|---|---|---|---|---|---|---|
| | | | | | | | | |

## 4. After the session

1. A **fail** becomes a defect row in `docs/sprints/<nn>/review-rounds.md`, with severity, the journey #, the device and the version. The senior-frontend-engineer then reproduces it in the matching emulated project (`webkit` or `android-chrome`) and adds a failing `@critical` test before the fix.
2. NFR-024.4 is met when every journey passes on both iOS Safari rows. NFR-024.5 is met when every journey passes on both Android Chrome rows. The verifier records the result in the scorecard row S5-P20, citing this sheet.
