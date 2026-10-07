# Sprint 3 manual screen-reader pass (C3-06; QA-R3-GATE-01 / C-06; NFR-027 (b))

- **Owner:** senior-qa-engineer (plan, script, record). **Tester:** a human with the devices, provided by the product owner (blockers.md row 1, item **P6**, due 2026-11-13, overdue at Sprint 3 start). **Reviewer:** principal-designer.
- **Why:** NFR-027 (b) asks for a manual keyboard and screen-reader checklist (VoiceOver on iOS, TalkBack on Android) on changed screens, 100% complete each sprint. Automated axe runs (G03-10) cannot hear what a screen reader says. The carried finding **QA-R3-GATE-01 / C-06** (major) stays open in `docs/sprints/03/review-rounds.md` until every row below has a result, and it counts in G03-12 unless the PO chose option (b) for P6 (sprint-03 §0.4, P12).
- **Scope:** the 24 rows of the Sprint 1 and Sprint 2 screens (`docs/sprints/02/a11y-manual.md` §3, unchanged, none run yet) plus the Sprint 3 screen families D (stats dashboard), E (evidence), X (deletion) and L (Full Tag), rows 25-38 below.
- **Status (2026-10-06):** **Waiting on P6.** No human tester or device is available to the agents. The plan and the script are ready. Nothing has been run, and no result is invented. Rows 25-38 also wait on the Sprint 3 UI (ST-047, ST-048, ST-050, ST-051, ST-052; DR-03 not held), so their expected text follows `flows-sprint-03.md` once PD-1 writes it; until then the expected text is the Gherkin's (sprint-03 §7) and is marked "(Gherkin)".

## 1. Set-up

| Item | Value |
|---|---|
| Stack | The Sprint 3 Compose stack over https (goal scorecard §4.0), at the head the verifier records. The tester opens `https://<host>:<port>` on the phone over the local network, or a tunnelled https URL the SRE provides. |
| Devices | iPhone with the current iOS and Safari, using VoiceOver. Android phone with Chrome, using TalkBack. Each is one column in §3. |
| Account | A fresh account per device (magic link to a Mailpit address the QA engineer reads out). For rows 35-38 the QA engineer grants the labeller role and the match's consent record with the labeller-admin CLI (ST-052) before the tester starts. |
| Data | The worked example of the metric dictionary (14 rallies, `scripts/measure/statslib.py` `STATS_TAGS`), tagged by the QA engineer through the API before rows 25-31, so the numbers heard can be compared with the reference: "Rallies won on serve" 57%, n = 7 (Ivy's side). |
| Fixture | `fixtures/clips/synthetic-60s/clip.mp4` (60 s, H.264; no people). |
| Copy reference | `docs/design/flows-sprint-01.md`, `flows-sprint-02.md`, and `flows-sprint-03.md` (PD-1) when it exists. |

## 2. What each row checks

The five checks of the Sprint 2 manual (§2 there): arrival, reading order, controls, changes, errors. A row passes only if all five pass. Any failure becomes a finding with the device, the screen reader and the exact words heard. Sprint 3 adds one check for D and E:

6. **Numbers in words:** every value is read with its sample size and, where flagged, "low sample", without relying on colour or position (NFR-034, FR-101); a bar (AN-07) is read as its printed values, not as an image without text.

## 3. Script and results

Rows 1-24: `docs/sprints/02/a11y-manual.md` §3, same steps and expected text, results recorded here.

| # | Screen / state | VoiceOver iOS | TalkBack Android |
|---|---|---|---|
| 1-24 | Sprint 1 and Sprint 2 screens (Sprint 2 manual §3) | not run (0 of 24) | not run (0 of 24) |

Sprint 3 screens:

| # | Screen / state | Steps for the tester | Expected | VoiceOver iOS | TalkBack Android |
|---|---|---|---|---|---|
| 25 | D-01 Stats, loaded | Open "Saturday doubles", then "Stats" | The heading is announced; "unofficial scoring (rules not yet verified)" is read before the first metric (Gherkin); each card reads its name, then per side the value, "n = …" and the range | not run | not run |
| 26 | D-01 low sample | Swipe to "Rallies won on serve" | "57%", "n = 7" and "low sample" are read for your side (Gherkin §7.1, §7.2); nothing is announced only by colour | not run | not run |
| 27 | D-01 "How is this measured?" | Activate it on "Rallies won when receiving" | Announced as a button with its expanded state; the plain-language definition is read next | not run | not run |
| 28 | D-01 AN-07 bar | Swipe to "How rallies ended" | Each segment's ending and count are read as text (NFR-034) | not run | not run |
| 29 | D-01 / E-01 empty, loading and error | A match with no rallies; then a slow reload; then a reload with the network off (and "Show me" with the network off) | The empty state says why there are no stats and offers "Tag rallies"; loading is announced once, not repeated; the error is announced as an alert with "Try again" as a button (E2E-03-08 checks the same states automatically, PD-R1S3-03) | not run | not run |
| 30 | E-01 Show me | "Show me" on "Rallies won on serve" | A list named after the metric; "7 items"; each item reads "Rally n" with its score or time | not run | not run |
| 31 | E-01 open a rally | Activate the first rally | The rally video region is announced; "Starts at m:ss"; the player controls are named | not run | not run |
| 32 | X-01 Delete match dialog | Match page, "Delete match" | The dialog is announced with its title; it says the video, tags, score sheet and stats will be deleted and cannot be restored (Gherkin §7.5); focus is inside the dialog; Cancel returns focus to "Delete match" | not run | not run |
| 33 | X-01 deleted | Confirm the deletion | The result is announced (for example "Match deleted"); the match list no longer reads the match | not run | not run |
| 34 | X-02 Delete account | Settings, "Delete account", confirm | The dialog states the consequences and that you will be signed out; after confirming, the sign-in page heading is announced | not run | not run |
| 35 | L-01 Full Tag, player | As a normal player, open the Full Tag address | "Not found" (FR-150), no hint that the tool exists | not run | not run |
| 36 | L-01 Full Tag, no consent | As a labeller, a match without a consent record | The page says the match cannot be labelled and why | not run | not run |
| 37 | L-01 frame stepping | As a labeller on a consented match, use the frame buttons | "Previous frame" and "Next frame" are buttons; the frame number change is announced politely | not run | not run |
| 38 | L-01 tag a hit and export | Mark a rally, a hit by Carlos, export | Each saved label is announced; "Export" is a button; the result says the file was saved | not run | not run |

## 4. Result

- **Rows run:** 0 of 38 on VoiceOver and 0 of 38 on TalkBack.
- **Findings:** none yet (nothing run).
- **Disposition:** QA-R3-GATE-01 / C-06 stays **Open** (waiting on P6). The agents cannot run it: there is no device or human tester in the session. Recorded so that G03-12 counts it, as sprint-03 §0.4 says, unless the PO chooses option (b) for P6 in writing.
- **Disposition at review round 1 (senior-qa-engineer, 2026-10-07):** the PO chose option (b) for P6 (`po-input-2026-10-05.md` addendum, P12). QA-R3-GATE-01 / C-06 stays **Open** and is reported as sprint-DoD row **S3-DoD-P6 "not met: waiting on P6"** (sprint-03 §9.1, decision-log 2026-10-07); it is not counted in G03-12. Until every row has a result, no sprint report may call Sprint 3 "fully WCAG-checked": the automated part (axe 0 serious/critical and the 24x24 rule on D, E, X and L, including the D/E empty, loading and error states of E2E-03-08) is the only accessibility evidence, and NFR-027 (b) is **not met** for Sprint 3.
- **Reconciliation at review round 2 (engineering-manager, 2026-10-07; ADR 0030 rule 1):** QA-R3-GATE-01 / C-06 is **deferred** to sprint-DoD row S3-DoD-P6, not Open, so it is **not counted in G03-12** (one disposition, not two). The "stays Open" wording above is superseded. Nothing else changes: 0 of 38 rows have run, NFR-027 (b) is not met for Sprint 3, and no report may call the sprint fully WCAG-checked.
