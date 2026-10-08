# Sprint 2 flows: Quick Tag, key map, score sheet, correction history, rally video

- **Status:** Draft v0.1, 2026-10-06 (principal-designer). **Written after the screens were built** (review round 1, PD-S2R1-03 / PD-R1-06-S2). Sprint-02 §0.1 asked for this file before any Sprint 2 UI story started; it did not exist, and the FE built from the Gherkin and the decision log (decision-log 2026-10-05, senior-frontend-engineer). This version therefore does two jobs: it **specifies** every screen and state, and it **records where the built screens differ** from that specification (§9). The design review DR-02 (§11) is **not yet held**; until it is, this file is a proposal and the Sprint 2 UI stories keep "Design review held" open (sprint-02 §14 DoR row R7).
- **Stories:** ST-027 Quick Tag (screen family T); ST-028a key map, ST-028b remapping (K); ST-029 score call (T, S); ST-030 score sheet (S); ST-031 undo and correction history (S, H); ST-032 corrections and "needs your decision" (S); ST-037 rally video (V).
- **Requirements:** FR-027, FR-048..FR-053, FR-055; NFR-011..NFR-014, NFR-028..NFR-031, NFR-033, NFR-034, NFR-036d, NFR-055, NFR-058.
- **Design sources:** DES FR-UX-60 (layout), FR-UX-61 (key map), FR-UX-62 (score feedback), FR-UX-70 (score sheet) in `docs/requirements/brainstorm-design.md`; HAX [DPA/DESIGN-11]; target sizes [DPA/DESIGN-02, DPA/DESIGN-10]; focus not obscured [DPA/DESIGN-07]; contrast [DPA/DESIGN-03, DPA/DESIGN-04].
- **Contract:** `docs/architecture/api-sprint-02.md` (Accepted) for routes and error codes. **Gherkin:** `docs/sprints/sprint-02.md` §7.1-§7.4, §7.6, §14.3.5, §14.3.6. **The copy in §3-§7 matches the Gherkin strings and the shipped strings exactly** (file and line in §8). A copy change here needs the same change in the Gherkin and the component, agreed with QA.
- **Builds on:** `flows-sprint-01.md` (conventions §0, M-02 match page, U-04). Tokens: `tokens.md`. Component rules: `component-accessibility-checklist.md`.
- **Viewport:** 360 CSS px, one hand, often courtside (judgment); reflow to 320 px (NFR-034). Quick Tag is also used on a laptop with a keyboard (FR-051).

## 0. Conventions (in addition to flows-sprint-01 §0)

- **Screen IDs:** `T-` tagging, `K-` key map, `S-` score sheet, `H-` correction history, `V-` rally video. These are the ids used by the a11y manual script (`docs/sprints/02/a11y-manual.md` rows 18-23) and by the G02-10 axe attachments.
- **Every screen lists all states:** Empty, Loading, Error, Offline, Conflict (another device changed the match), Low-confidence, Low-sample, and, where a rally can be in conflict, **Needs your decision**. Low-confidence and Low-sample are "N/A" with the reason: there is no automatic call and no metric in Sprint 2.
- **The score is never typed by the player.** Every number on T and S comes from the server's replay of the rules (FR-049). The screen may show an **optimistic** score for at most one pending tag; the server's sheet replaces it (NFR-012a).
- **Unofficial label.** While the server says `unofficial: true`, every T and S screen shows "unofficial scoring (rules not yet verified)" (FR-055; ADR 0023: rulebook PDFs to come, preset `PROVISIONAL-UNVERIFIED`).
- **Announcements:** one polite live region per screen (`role="status"`, `aria-atomic`). It is rendered from first paint and only its text changes. Focus never moves because of an announcement (SC 4.1.3, judgment; Gherkin §7.2).
- **Errors on T, K, S:** a single notice with `role="alert"` at the top of the working area that says what happened and what to do, plus `Reference: <support_ref>` when the API gave one (NFR-058). These screens are not forms with fields, so the GOV.UK error summary [DPA/DESIGN-13] applies only to the game-start question T-02.
- **Targets:** every tagging control ≥ 48×48 CSS px with ≥ 8 px gaps (NFR-028; FR-UX-60); every other control ≥ 24×24 (SC 2.5.8), primary actions 48 px [DPA/DESIGN-10].
- **Words for sides:** "Your side (Ivy and Dana)" / "Other side (Carlos and Bo)" on buttons and labels; "us" / "them" in the short score call only (FR-048 example). Never "Team A" or "Side B" (judgment; the coach confirms at DR-02).

## 1. Flow map

```
 M-02 Match (Video received) ──"Tag rallies"──► T-01 Tag rallies ──"Score sheet"──► S-01 Score sheet
        │ no video yet                              │  ▲                                  │   │   │
        ▼                                           │  │ "Start game n"                   │   │   └─"Watch rally n"──► V-01 Rally video (on S-01)
   T-00 "You can tag this match once its            ▼  │                                  │   └─ Switch winner / ending / player (S-01 inline)
        video is received."                    T-02 Who serves first in game n?         │       └─ needs your decision ─► "Move rally n to the next game" | "Remove rally n"
                                                    │ game over (not match over)         └─ H-01 Correction history (section of S-01)
                                                    ▼
                                               T-02 (next game) … T-03 Match over ──"Open the score sheet"──► S-01
 T-01 ──"?" or "Keyboard shortcuts"──► K-01 Key map (dialog) ──Close/Esc──► T-01 (focus back on the opener)
 T-01 / S-01 ── another device changed the match (409 stale_match) ──► same screen, latest sheet, notice
```

## 2. Shared score region (T-01, S-01)

- **Game line:** "Game n", or "Match over".
- **Call:** the server's call, e.g. "4-6-1" (three numbers in doubles; format provisional, `@needs-verification`, FR-048, [DOM G1 R6] unverified).
- **Server line (T-01 only):** "Your side serves" / "Other side serves".
- **Unofficial label:** "unofficial scoring (rules not yet verified)" (FR-055), styled as a warning notice on S-01 and as secondary text under the call on T-01.
- **Last-rally line = the live region:** "Rally 7: them. Score 4-6-1." (FR-048, FR-UX-62). For a rally that needs a decision: "Rally 7: them. Needs your decision." For a replay: "Rally 10: replay. Score 5-5-1."

## 3. Quick Tag (ST-027, ST-029; FR-050, FR-048)

### T-00 Tag rallies, video not received (§14.3.5)

- **When:** the match status is not `video_received`.
- **Content:** `<h1>` "Tag rallies"; "You can tag this match once its video is received."; "Back to the match". No tagging controls are rendered, so no rally can be saved (§14.3.5 "no rally is saved").

### T-01 Tag rallies

- **Layout (FR-UX-60):** video on top (native controls, `playsInline`); score region (§2); live region; the rally control bar; then a row "Undo", "Keyboard shortcuts", "Score sheet". The bar is in normal flow, never sticky, so it cannot cover the focused control (SC 2.4.11, NFR-031).
- **Rally control bar** (each group is `role="group"` with a name):
  1. "Rally start", "Rally end": toggle buttons (`aria-pressed`), the time is read from the video's current time.
  2. Group "Won by": "Your side (…)", "Other side (…)": one is pressed at a time.
  3. Group "Who hit it (optional)": one button per player nickname; pressing the pressed one clears it.
  4. Group "Ending (saves the rally)": "Winner", "Unforced error", "Forced error", "Fault", "Replay". **Choosing the ending saves the rally**; there is no separate Save button (fewest taps, NFR-036, judgment). The group name says so, so it is not a surprise (SC 3.2.2, judgment).
- **Pressed state:** filled and a check mark, never colour alone (NFR-034).
- **After a save:** the marks clear, the video keeps playing from the end of the rally, ready for the next start (FR-050 R1), the score updates and the live region speaks (§2). Focus stays on the control the player used (Gherkin §7.2).
- **Order checks on the device, before any request** (shown in the error notice, nothing is sent):
  - "Mark the rally start first." / "Mark the rally end first." / "The rally end must be after its start."
  - "Choose which side won the rally first."
  - "The player who made the error must be on the side that lost the rally." (Gherkin §7.1 "Error attributed to the winning side")
  - "The player who hit the winner must be on the side that won the rally."
  - "This rally starts before the end of rally n. Play on to the next rally, then mark its start."

### T-02 Who serves first in game n?

- **When:** no game started yet, or the last game is over and the match is not.
- **Pattern:** one question [DPA/DESIGN-12]: legend "Who serves first in game n?", two radios ("Your side (…)", "Other side (…)"), button "Start game n". Optional intro line "Game n-1 won by your side." Error: "Choose who serves first in game n." Server failure: "Game n could not be started. Try again. Reference: …".

### T-03 Match over

- "Match over" in the game line; "Match won by your side." / "Match won by the other side."; primary link "Open the score sheet". The control bar is not shown; Undo stays.

### T-01 states

| State | What the player sees | Source |
|---|---|---|
| Empty (no rally yet) | Game line, no call, the bar; live region empty | — |
| Loading | Page load: `/matches` loading view "Loading…" with reserved skeleton rows (C-30). Saving a tag: "Saving…" next to the optimistic call; the controls stay enabled, a second ending press while saving is ignored | NFR-012 |
| Error (not saved) | Notice: "The rally was not saved. Try again. Reference: …"; the marks stay so the player can retry with one press | NFR-058 |
| Error (outcome refused by the server) | "The rally was not saved: check the winner, the ending and the player." | api-sprint-02 §4.2 |
| Error (times overlap) | "The rally was not saved: its times overlap another rally. Mark its start and end again." | api-sprint-02 |
| Offline | "The rally was not saved because the connection dropped. Try again." Marks kept. No offline queue in R1 (judgment; out of scope) | NFR-058 |
| Conflict (409 `stale_match`) | The latest sheet replaces the screen; notice "This match was changed on another device. The latest score is shown; your rally was not saved." | §14.3.5 "Two devices" |
| Game over (409 `game_over`) | "This game is over. Start the next game to go on tagging." then T-02 | api-sprint-02 |
| Needs your decision (409 `decision_needed`) | "Some rallies need your decision first. Open the score sheet to decide." | FR-053 (a) |
| No playable video | Notice (info): see §9 PD-FL2-04 for the proposed copy | NFR-060 |
| Low-confidence | N/A: every call is the player's own; the only uncertainty is the rules preset, shown by the unofficial label | FR-055 |
| Low-sample | N/A: no metric on this screen | — |

## 4. Key map (ST-028a, ST-028b; FR-051, FR-UX-61)

### K-01 Keyboard shortcuts (modal dialog)

- **Opens with:** "?" anywhere on T-01 (except in a text field), or the "Keyboard shortcuts" button. Focus moves to "Close"; Esc or "Close" returns focus to the opener (component checklist, dialogs).
- **Content:** `<h2>` "Keyboard shortcuts"; a two-column table "Key" / "What it does" (caption "Tagging shortcuts", visually hidden), rows: Space "Play or pause the video"; `S` "Rally start"; `E` "Rally end"; `1` "Won by your side"; `2` "Won by the other side"; `3`-`6` "Player: <nickname>"; `W` / `U` / `O` / `F` / `R` "Ending: winner / unforced error / forced error / fault / replay (saves the rally)"; `Z` undo; `J` / `L` −5 s / +5 s; `,` / `.` one frame back / forward; Esc "Clear the marks of the rally being tagged"; `?` this list. (`O` for forced error is an addition to FR-UX-61, which lists W/U/F only; DR-02 item R2-3.)
- **Single-key switch (SC 2.1.4, judgment):** checkbox "Use single-key shortcuts", on by default; hint "When this is off, only Space and Esc work as shortcuts. You can still tag with Tab and Enter." Remembered on this device.
- **Remapping (ST-028b, stretch):** fieldset "Change a key": select "Shortcut to change", button "Choose a new key" then "Press the new key for <action>. Esc cancels."; success in the dialog's status line "<action> is now <KEY>."; refusal as an alert with the reason; "Use the default keys" → "The default keys are back."
- **States:** Empty N/A (always has rows); Loading N/A (no request); Error: refused remap only; Offline N/A (local); Low-confidence / Low-sample N/A.

## 5. Score sheet (ST-030, ST-031, ST-032; FR-049, FR-052, FR-053, FR-055)

### S-01 Score sheet

- **Header:** "Back to the match"; `<h1>` "Score sheet"; match title; unofficial label (warning notice, before the tables, so a screen reader reads it first: a11y manual row 20); rules line (see §9 PD-FL2-03).
- **Tables:** one semantic table per game, caption "Game n" or "Game n, won by your side". Columns: Rally (row header "Rally n"), Start (m:ss, floored), Server ("Your side, server 2"), Score before, Score after, Won by ("No one (replay)" for a replay), Ending, Player ("player not tagged" when skipped, Gherkin §7.1; "Not applicable" for a replay), Notes.
- **Notes cell:** text markers "corrected by you" (Gherkin §7.3) and "needs your decision" (FR-053 (a)), in bold words, never colour alone; then the row's actions.
- **Narrow screens (≤ 48em, 768 px):** each row stacks into labelled lines ("Score after: 4-6-1"); nothing scrolls sideways at 320 and 360 px (Gherkin §7.3 "Narrow phone screen"; G02-10 (d)). Table roles stay explicit so the stacked layout keeps its semantics.
- **Row actions:**
  - "Watch rally n" → V-01.
  - **Switch winner** (1 tap, NFR-036d): visible label and accessible name must agree (see PD-FL2-01). Specified accessible name: "Switch winner, rally n" (visible words first, SC 2.5.3).
  - **Change ending / Change player:** specified as a disclosure "Change ending" that shows the five endings as buttons (and "Change player" with the nicknames and "Not tagged"); one press of an option saves. Two taps in all (NFR-036d), and nothing is saved by moving through a list with the arrow keys (SC 3.2.2; see PD-FL2-02 for the built select).
  - On a "needs your decision" row: "Move rally n to the next game" (primary) and "Remove rally n" (secondary).
- **After any change:** the server's sheet replaces the tables; the live region says "Rally n corrected. The score sheet is up to date.", "Rally n moved to the next game.", "Rally n removed. It stays in the correction history." or "Last change undone."; H-01 reloads. Focus stays on the control used, or, when that row's control is gone, on the next row's first action (judgment; DR-02 item R2-5).
- **Undo:** "Undo last change" below the tables; nothing to undo → "There is nothing to undo."

### S-01 states

| State | What the player sees | Source |
|---|---|---|
| Empty | "No rallies tagged yet." and the primary link "Tag rallies" | FR-049 |
| Loading | `/matches` loading view (C-30); a change in progress: the Undo button is `aria-busy`, a second command is ignored until the first is answered | NFR-013 |
| Error (load) | `/matches` error page: "Sorry, we could not load this page. Try again. Reference: …" and "Try again" (C-30) | NFR-058 |
| Error (change refused) | "Correction failed. Try again. Reference: …"; "Correction was refused: the winner, the ending and the player do not fit together."; "Start the next game on the tagging screen first, then move the rally." | api-sprint-02 |
| Offline | "<Correction / Undo / Decision> failed because the connection dropped. Try again." | NFR-058 |
| Conflict (409 `stale_match`) | Latest sheet shown; "This match was changed on another device. The latest score sheet is shown; check it and try again." | §14.3.5 |
| Needs your decision | Row marker "needs your decision" in words, the two decision buttons; later rallies are kept, never deleted (FR-053 (a), Gherkin §7.4 C-02, C-03, `@needs-verification`) | FR-053 |
| Low-confidence | N/A: no automatic call. The unofficial label carries the one uncertainty (HAX G2) | FR-055 |
| Low-sample | N/A: no metric (stats are Sprint 3) | — |

## 6. Correction history (ST-031; FR-052)

### H-01 Correction history (section of S-01)

- `<h2>` "Correction history"; an ordered list (`aria-label` "Correction history"), oldest first, one line per change in words: "Rally 5: ending changed from winner to forced error at 14:32" (Gherkin §7.4: rally, field, old value, new value); "Rally 5 removed"; "Rally 22: moved from game 2 to game 1"; "Rally 23 removed (your decision)"; "A game was started"; "Undone: Rally 5: won by changed from your side to the other side".
- Values are tag values only, never free text (match-aggregate §6). "Who" is always the signed-in owner in R1, so it is not repeated on each line (judgment).
- **States:** Empty "No changes yet."; Loading "Loading the history…"; Error "The correction history could not be loaded." with "Reload the history"; Offline: same as Error; Low-confidence / Low-sample N/A.

## 7. Rally video (ST-037; FR-027, NFR-014, NFR-055)

### V-01 Rally n video (section on S-01)

- Opened by "Watch rally n". A **fresh** short-lived link is fetched on every press (NFR-055: TTL ≤ 15 min, no session token in the URL); the link is never shown as text.
- Region `<h2>` "Rally n video", native video controls, "Starts at m:ss". Plays from the rally start (Gherkin §7.6 "plays from 14:32"); focus moves to the video so keyboard users land on its controls (the player asked for it, so the move is expected; judgment).
- **States:**
  - Loading: the browser's own video loading; the button stays usable.
  - Error (link could not be had): "The video for rally n could not be opened. Try again. Reference: …".
  - Error (link expired or changed, §7.6, §14.3.6): "This video link no longer works. Choose 'Watch rally n' again." Choosing it again works (Gherkin §7.6).
  - Error (browser cannot decode, QA-S2-UI-03): "This browser cannot play this video. Try another browser, such as Safari or Chrome. The score sheet still works here." (copy review asked in decision-log 2026-10-06: accepted by the designer, see §9).
  - Empty / Offline: offline gives the "could not be opened" message; Low-confidence / Low-sample N/A.
- Captions: the video is the player's own recording with no speech to caption; the score sheet is its text alternative (NFR-033, [DPA/DESIGN-09]).

## 8. Copy register (shipped string → source)

| Screen | String | Shipped in | Gherkin / FR |
|---|---|---|---|
| T-00 | "You can tag this match once its video is received." | `web/src/app/matches/[matchId]/tag/page.tsx`; `lib/tagging/messages.ts` | §14.3.5 |
| T-01 | "Rally 7: them. Score 4-6-1." | `lib/tagging/view.ts` `tagLine` | FR-048 (`@needs-verification`) |
| T-01 | "The player who made the error must be on the side that lost the rally." | `lib/tagging/reducer.ts` | §7.1 |
| T-01, S-01 | "unofficial scoring (rules not yet verified)" | `lib/tagging/types.ts` `UNOFFICIAL_LABEL` | §7.3, FR-055 |
| S-01 | "player not tagged" | `components/score-sheet/ScoreSheetTable.tsx` | §7.1 |
| S-01 | "corrected by you", "needs your decision" | same | §7.3, FR-053 |
| H-01 | "Rally 5: ending changed from winner to forced error" | `lib/tagging/view.ts` `historyText` | §7.4 |
| V-01 | "This video link no longer works. Choose 'Watch rally n' again." | `components/score-sheet/ScoreSheetView.tsx` | §7.6 |

## 9. Differences between this specification and the built screens (2026-10-06)

Found by reading the shipped components at `971c4d7` against §3-§7 (not yet walked on the live stack; that is DR-02 item R2-1). Each is routed to its owner as an Open row in `docs/sprints/02/review-rounds.md` (review round 1, principal-designer). If one repeats a PD-S2R1 finding, the ids are aliases.

| Id | Severity | Screen | Built | Specified | Owner |
|---|---|---|---|---|---|
| PD-FL2-01 | major | S-01 | "Switch winner" has `aria-label` "Rally n: change the winner to your side", which does not contain the visible words "Switch winner" (`RallyCorrections.tsx:27-28`). Speech-input users who say "click Switch winner" get no match: SC 2.5.3 Label in Name (Level A, judgment: WCAG text not fetched) | Accessible name starts with the visible label: "Switch winner, rally n" (the "to your side / the other side" part may follow) | senior-frontend-engineer |
| PD-FL2-02 | major | S-01 | The ending and player corrections are `<select>`s that save on `change` (`RallyCorrections.tsx:35-37`, `:45-47`). In browsers that fire `change` while arrowing through a closed select (Chromium and Firefox on Windows, judgment), each arrow key saves a correction, re-scores the match and adds a history line. The selects also have no visible label, only the current value | Disclosure "Change ending" / "Change player" with one button per option; one press saves (§5). Keeps ≤ 2 taps (NFR-036d) and nothing saves on navigation (SC 3.2.2) | senior-frontend-engineer |
| PD-FL2-03 | minor | S-01 | "Rules: PROVISIONAL-UNVERIFIED" shows the internal preset id (`ScoreSheetTable.tsx` rules line) | "Rules: provisional, not yet checked against the rulebook" while the preset is `PROVISIONAL-UNVERIFIED`; the preset name after OQ-01 | senior-frontend-engineer (copy confirmed by the coach at DR-02) |
| PD-FL2-04 | minor | T-01 | No playable video: "The video cannot be played here right now. Rally times come from this page's clock." The player is not told that those times will not match the video, so V-01 later starts at the wrong moment | "The video cannot be played here right now. Reload the page to try again. If you tag without it, the rally times will not match the video." | senior-frontend-engineer |
| PD-FL2-05 | nit | T-01, S-01 | "Undo" on T-01, "Undo last change" on S-01 for the same command | "Undo last change" on both | senior-frontend-engineer |

Accepted as built (designer, 2026-10-06): the V-01 "cannot play" copy (QA-S2-UI-03), the T-02 one-question form, the K-01 dialog, the per-game tables with stacked rows, the decision buttons' words, and H-01 without a "who" column.

## 10. HAX checklist (Sprint 2 scope) [DPA/DESIGN-11]

| Guideline | Where | Design response |
|---|---|---|
| G1 Make clear what the system can do | T-01, S-01 | The player tags; the app only replays the rules. No automatic rally detection in R1 (FR-050, FR-087 is R2) |
| G2 Make clear how well it can do it | T-01, S-01 | "unofficial scoring (rules not yet verified)" on every score; the rules line (PD-FL2-03) |
| G8 Support efficient dismissal | T-01 | Esc clears the marks; pressing a chosen player again clears it |
| G9 Support efficient correction | S-01 | Switch winner in 1 tap; ending and player in 2 (NFR-036d); "Undo last change" for any change |
| G11 Make clear why the system did what it did | S-01 | Score before and after and the server on every row; "needs your decision" says why a rally is not scored |
| G12 Remember recent interactions | K-01 | Single-key setting and remapped keys remembered on the device |
| G16 Convey the consequences of user actions | T-01 ending group "(saves the rally)"; S-01 "Remove rally n" announcement "It stays in the correction history." | The consequence is in the label or the announcement |
| G17 Provide global controls | K-01 | Single-key shortcuts on/off; remapping |
| G3-G7, G10, G13-G15, G18 | — | No automatic call, recommendation or learning in Sprint 2 |

## 11. WCAG 2.2 AA design-level checklist per screen

"✓" means this file specifies it; "✗" means the built screen differs (§9). Implementation evidence comes from G02-10 (axe, targets, keyboard, reflow) and the human run C-06 (`a11y-manual.md` rows 18-23).

| Check | T-00..T-03 | K-01 | S-01 | H-01 | V-01 |
|---|---|---|---|---|---|
| Unique title ("Tag rallies: <match>", "Score sheet: <match>"); one `<h1>` | ✓ | — (dialog `<h2>`) | ✓ | — (section `<h2>`) | — (section `<h2>`) |
| Targets ≥ 24 px; tagging and correction controls ≥ 48 px (SC 2.5.8; NFR-028) | ✓ | ✓ | ✓ | — | ✓ |
| Contrast from proven tokens only; pressed state not colour alone (SC 1.4.3, 1.4.11; NFR-029) | ✓ | ✓ | ✓ | ✓ | ✓ |
| Focus not obscured: no sticky bar over the controls (SC 2.4.11; NFR-031) | ✓ | ✓ | ✓ | ✓ | ✓ |
| Keyboard-only completion (NFR-034; E2E-02-02) | ✓ | ✓ (focus trapped, returned) | ✓ | ✓ | ✓ |
| Character key shortcuts can be turned off (SC 2.1.4) | ✓ | ✓ | — | — | — |
| Label in name (SC 2.5.3) | ✓ | ✓ | ✗ PD-FL2-01 | — | ✓ |
| No change of setting on input (SC 3.2.2) | ✓ (the ending group says it saves) | ✓ | ✗ PD-FL2-02 | — | — |
| Polite announcements, focus kept (SC 4.1.3; E2E-02-03) | ✓ | ✓ (status line) | ✓ | — | ✓ |
| No dragging needed (SC 2.5.7; NFR-030) | ✓ | — | ✓ | — | ✓ (native controls; frame and 5 s keys on T-01) |
| Reflow at 320 px, no sideways scroll (NFR-034; G02-10 (d)) | ✓ | ✓ | ✓ (stacked rows) | ✓ | ✓ |
| Markers in words, not colour alone | — | — | ✓ | ✓ | — |
| Text alternative for the video (NFR-033) | — | — | ✓ (the sheet is the alternative) | — | ✓ |

## 12. Open items

| # | Item | Owner | Needed by |
|---|---|---|---|
| E-1 | Score call format (three numbers, "us/them") is provisional; the coach verifies it (FR-048, `@needs-verification`) | pickleball-domain-coach | Rulebook PDFs (OQ-01), Sprint 3 planning 2026-11-16 |
| E-2 | Endings: is "Forced error" kept separate in the UI while κ ≥ 0.6 is unproven (FR-050)? Proposed: keep the button, merge in analytics only | pickleball-domain-coach, product-manager | DR-02 |
| E-3 | Focus target after a decision removes the row's controls (§5) | senior-frontend-engineer | DR-02 |
| E-4 | Offline tagging queue: out of scope for R1; T-01 says the rally was not saved | product-manager | R2 planning |

## 13. Design review record (DR-02)

| Date | Participants | Outcome | Findings |
|---|---|---|---|
| 2026-10-06 | principal-designer (author) | Draft written after the build, from the shipped components and the Gherkin | §9 PD-FL2-01..05, routed in `review-rounds.md` |
| Opened 2026-10-06; decisions due end of 2026-10-07; hard date 2026-11-02 (the DR-01 hard date, sprint-02 §0.1) | principal-designer (chair), pickleball-domain-coach (SME), senior-frontend-engineer, business-analyst, product-manager; security-privacy-engineer for R2-6 | **Not yet held.** Same asynchronous format as `flows-sprint-01.md` §10.2: each participant writes accept or reject with one line of reason in the "Decision" column below and commits it under ADR 0022. While any cell is empty, the Sprint 2 UI stories (ST-027..ST-032, ST-037 FE) keep "Design review held" open (sprint-02 DoR R7) and §9 stays a proposal | — |

### 13.1 Agenda (chair's proposals, judgment unless cited)

| # | Item | Proposal | Decides | Decision |
|---|---|---|---|---|
| R2-1 | Walk T-00..T-03, K-01, S-01, H-01, V-01 on the local HTTPS stack against §3-§7 and §11 | Run with the FE at the next live run; add any new difference to §9 | all | principal-designer: accept the method; walk not run yet (2026-10-06, review round 2). Input for the walk, re-checked statically against the shipped code: PD-RV2-01 / PD-FL2-04 T-01 notice copy matches §9 word for word (`QuickTag.tsx:40-43`), FE live run shows it for a 403 link and an undecodable codec; BE-RV1-FE-01 T-02 refusal "Scoring for this match format is not available yet." (`messages.ts:8`), no retry offered, as §3 requires for a refusal no retry fixes; PD-FL2-01 S-01 name "Switch winner, rally n, to …" starts with the visible words (`RallyCorrections.tsx:80-83`). PD-RV2-02: no row exists in the repository (`grep -rn PD-RV2-02 docs` → none), so nothing to walk for it. senior-frontend-engineer: **accept the method** (2026-10-06, Sprint 3). Live-run input, not the walk itself: on a Compose stack over HTTPS (`racket-fe3`, https://localhost:43000, web built from the `sprint-03` tree after `3f13b05`) `PW_PROJECTS=chromium npx playwright test e2e/sprint-01 e2e/sprint-02 e2e/sprint-03` → 86 passed, 6 skipped, 3 failed: `rally-video.spec.ts:34` and `timing.spec.ts:222` (Playwright Chromium cannot decode the H.264 original, SRE-S2-05; V-01 is walked in WebKit or Chrome) and E2E-03-07 (its own setup ran past the 60 s clip, fixed in the spec). The screen-by-screen walk with the chair against §11 is still to do. product-manager: **accept the method** (2026-10-07, Sprint 3 DR-02-PM): walking the built screens on the live HTTPS stack is the only check that matches the PO standing rule (a goal works on a live stack, not only in unit tests); the PM does not need to attend, the FE and the chair run it. senior-frontend-engineer: **walk run; accept the built screens, one minor finding** (2026-10-07, P14). Method as DR-01 R-1 (`flows-sprint-01.md` §10.1). Walked: T-00 (match without video: no tagging controls), T-02 and its error ("Choose who serves first in game 1." in the summary and on the fieldset), T-01 empty and after 6 rallies tagged by keys only (call "Rally 6: us. Score 5-0-2.", serving side's score first, "Your side serves"; order check "Mark the rally end first."), K-01 (focus on "Close" at open, Esc returns focus to "Keyboard shortcuts", single-key switch on), S-01 with the PD-FL2-03 rules line, Switch winner on rally 2 (focus stays on "Switch winner", status "Rally 2 corrected. The score sheet is up to date.", "corrected by you"), H-01 ("Rally 2: won by changed from the other side to your side at …"), V-01 (video focused, `readyState` 4, starts at the rally; played from the repo's VP9 stand-in because Playwright Chromium has no H.264 decoder, SRE-S2-05). Every screen: 0 axe violations, 0 px sideways scroll at 320 px, no tagging control under 48 px. **Finding (minor, FE):** on the T-02 error state the "Other side" radio input measures 23×24 px (the error border narrows the fieldset); the label row is the larger target, but the repo's own 24 px check (`e2e/helpers/axe.ts` `expectTargetsAtLeast24`) counts inputs and would fail there. **Not walked:** T-03 (the 60 s fixture ends before two games reach 11; E2E covers the match-over state) and V-01 on the H.264 original (WebKit or Chrome). pickleball-domain-coach: **accept the method** (2026-10-07, P14): the walk shows what the coach asked for in R2-4: the call reads "us" for the winner while the numbers stay in call order, serving side first ("Score 5-0-2" with "Your side serves" beside it), so a player can check the app against what was called on court. business-analyst: **accept the method** (2026-10-07, P14): the walked strings are the Gherkin's (FR-055 "unofficial scoring (rules not yet verified)" on T-01 and S-01; FR-052 "corrected by you" and the history line with rally, field, old and new value), so the walk is evidence for those acceptance criteria, not a new requirement |
| R2-2 | §9 PD-FL2-01..05 | Accept all five as specified | senior-frontend-engineer | senior-frontend-engineer: **accept all five** (2026-10-06, Sprint 3 DR-02-FE). Feasible as specified; each is a copy or control change inside S-01/T-01 with no API change. Built: PD-FL2-01 (`RallyCorrections.tsx`, name "Switch winner, rally n, to …"), PD-FL2-02 (disclosure with option buttons, PD-S2R1-02), PD-FL2-04 (T-01 notice, PD-RV2-01). Still to build, FE follow-ups: PD-FL2-03 (rules line copy; the coach confirms the words, R2-4) and PD-FL2-05 ("Undo last change" on T-01); each changes an accepted test's expected string (`score-sheet.test.tsx:91`, `quick-tag-undo.test.tsx:37`), so each waits for its row in `docs/sprints/03/test-change-requests.md` to be decided first (retro 2 M4) |
| R2-3 | `O` for "forced error" (FR-UX-61 lists W/U/F only) | Accept: forced error is an FR-050 ending and needs a key | business-analyst | business-analyst: **accept** (2026-10-07, Sprint 3 DR-02-BA, review round 1 PD-RV2-DR-BA). FR-050 has five endings (winner, unforced error, forced error, fault, replay), and FR-051 requires keyboard tagging to give the same result as tapping; FR-UX-61's W/U/F (a brainstorm source written before conflict K8 added forced error and replay) cannot express two of them, so a key for each is required, not optional. `O` is free in the map and does not clash with `F`. Requirement change made: FR-051 now says the key map covers every FR-050 input, including `O` (forced error), `R` (replay) and `3`-`6` (responsible player), and that `W`/`U`/`O`/`F`/`R` save the rally (R2-5). Evidence that it is built and tested: `web/src/lib/tagging/keymap.ts:44` `ending_forced_error: 'o'`; `web/tests/unit/tagging-keymap.test.ts:42` asserts `o` → `ending_forced_error`. The forced vs unforced split in **analytics** stays gated by κ ≥ 0.6 (FR-050; R2-7); the key only records the tag |
| R2-4 | Words "Your side (…)" / "Other side (…)" and "us/them" in the call | Accept for R1; verify with the call format (E-1) | pickleball-domain-coach | pickleball-domain-coach: **accept** (2026-10-07, Sprint 3 DR-02-COACH): "Your side (Ivy and Dana)" / "Other side (Carlos and Bo)" is how a player thinks of their own match, and "us"/"them" for the rally winner reads the way doubles partners talk (judgment; no coaching source verified, DOM G2). Condition, from the call format (E-1, still UNVERIFIED, DOM G1 R6): the score numbers stay in call order, **serving side's score first**, then the receiving side's, then the server number, as the engine prints them (`tagLine` in `web/src/lib/tagging/view.ts` uses `score_after`); never re-ordered to "us first", because a player checks the app against what was called on court. Since "us"/"them" names the winner, not the first number, the server line ("Your side serves" / "Other side serves") stays next to the call on T-01 so the first number has an owner (non-blocking suggestion to the chair: after a side-out the announcement could add "Other side serves."). **PD-FL2-03 rules line: accept** "Rules: provisional, not yet checked against the rulebook" while the preset is `PROVISIONAL-UNVERIFIED`: true today (rules-verified.md §5: no row verified; ADR 0023: PDFs to come) and it names no federation (ADR 0009 rule 4). After verification the line names the edition, e.g. "Rules: USA Pickleball 2026", only when every row of that preset is verified |
| R2-5 | Ending press saves the rally, no Save button; focus rule after a decision (E-3) | Accept both | senior-frontend-engineer, product-manager | senior-frontend-engineer: **accept both** (2026-10-06, Sprint 3 DR-02-FE). (1) The ending press saves: built that way since ST-027 (one action per rally, NFR-012); undo is one key (`z`) or one tap, E2E-02-05. (2) E-3 focus rule: after a decision removes the row's controls, focus moves to the next row's first action, or to "Undo last change" when no row follows; a refused decision keeps focus on the control used. Built as the DR-02 FE follow-up (`ScoreSheetView.tsx`; `web/tests/unit/dr02-e3-focus-after-decision.test.tsx`, `web/e2e/sprint-03/focus-after-decision.spec.ts`). product-manager: **accept both** (2026-10-07, Sprint 3 DR-02-PM, review round 1 PD-RV2-DR-PM). (1) The ending press saves: a Save button would double the work per rally on the screen the player uses most, and one action per rally is what NFR-012 times; the safety net is undo by one key (`z`) or one tap (E2E-02-05) plus the correction history, so a wrong press costs one action, not a lost rally (HAX G9, easy correction) (judgment). No scope change. (2) E-3 focus rule: accept as built; keyboard and screen-reader users must not lose their place after a decision, and it needs no new scope. Evidence: `cd web && npx vitest run tests/unit/dr02-e3-focus-after-decision.test.tsx tests/unit/tagging-keymap.test.ts` → 2 files, 12 tests passed |
| R2-6 | V-01 messages say nothing about the link's lifetime or its contents | Accept: no URL shown, no expiry time shown (NFR-055) | security-privacy-engineer || security-privacy-engineer: **accept** (2026-10-07, Sprint 3 DR-02-SEC). The signed media URL is a bearer secret (NFR-069; threat model S2 T-MD-1..3). Showing it or its expiry time gives the user nothing they need and invites copying or sharing it. V-01 keeps the generic "reload the video" message, and a reload asks for a fresh link (T-MD-1). Condition: no V-01 state, error text, `title`, tooltip or console message contains the URL, its query or its expiry time. The existing log/URL controls (T-MD-2, T-MD-3) cover the rest |
| R2-7 | E-2 forced vs unforced error in the UI | Keep the button; analytics decides later | pickleball-domain-coach, product-manager | pickleball-domain-coach: **accept** (2026-10-07, Sprint 3 DR-02-COACH): keep "Forced error" as its own button. Whether the opponent forced the mistake is the most useful coaching fact in an error, and it can only be captured at tagging time; merging later is a version bump that loses nothing, splitting later is impossible (ADR 0044 rule 4; metric-dictionary D-2). The working definition stays "(judgment, UNVERIFIED)" and the κ ≥ 0.6 check on 200 rallies gates `verified` for AN-04/AN-07, not the button. product-manager: **accept** (2026-10-07, Sprint 3 DR-02-PM, review round 1 PD-RV2-DR-PM): keep the "Forced error" button in R1. Scope and priority: no extra build (it ships, `keymap.ts` `ending_forced_error: 'o'`), and the tag cannot be recovered later if we do not capture it now (coach above). Condition, for trust (HAX G2, product principle "confidence shown"): until κ ≥ 0.6 on 200 rallies is measured, no stats card, evidence view or training plan presents forced vs unforced as a verified split; AN-04/AN-07 show it only with the unverified label of the metric dictionary, or fold it into "errors". This also answers flows-sprint-03 P-5 for DR-03 (judgment) |

### 13.2 Status on 2026-10-06: not held yet; disposition under ADR 0030 (chair, review round 2: PD-R1-06-S2 / DR-02, PD-R1-06, PD-R2R-02, QA-R2V-12, DR-01)

- **Not held.** The R2-1..R2-7 Decision cells hold only the chair's R2-1 entry; every other decider's cell is empty, and so are the senior-frontend-engineer, business-analyst, pickleball-domain-coach and product-manager cells of DR-01 (`flows-sprint-01.md` §10.1, R-2a, R-2b, R-3, R-4, R-5, D-1, D-2). The chair does **not** write decisions for other roles (as in `flows-sprint-01.md` §10.3): a decision the decider did not make would close "Design review held" on paper only.
- **Consequence, unchanged:** ST-027..ST-032 and ST-037 (FE) keep "Design review held" (DoR R7, DoD) in `open` and are **not DoD-done**; §9 PD-FL2-02..05 stay proposals until R2-2 is decided (PD-FL2-01 and PD-FL2-04 are already built as proposed, R2-1 input above).
- **Disposition under ADR 0030 (rule 1, "deferred to a named backlog row with an owner and a sprint"):** DR-02 is tracked under the committed Sprint 2 row DR-01 (sprint-02 §3) and DoR R7 ("DR-01 held, then the Sprint 2 flows reviewed"); owner principal-designer (chair); Sprint 2. Each empty cell is routed to its decider as an Open row in `docs/sprints/02/review-rounds.md` (review round 2, principal-designer). No new ADR: ADR 0030 already holds the deferral rule, and its number is taken.
- **Dates:** DR-02 decisions are due by end of **2026-10-07** (not yet passed today, 2026-10-06). If any DR-02 cell is still empty then, the chair records "not held" here and DR-02 rides on DR-01's **hard date 2026-11-02**; if DR-01 or DR-02 is still not held on 2026-11-02, the chair escalates to the engineering-manager and the human PO (role rule: escalate what needs people the chair cannot convene), and the Sprint 2 UI stories close at the sprint review as not DoD-done for this item.
- **When every cell is filled,** the chair replaces the "Not yet held" row in §13 with the outcome, moves the accepted §9 items into §3-§7, and ticks DoR R7.

### 13.3 Status on 2026-10-07 (chair, Sprint 3 review round 1: PD-R1-06 / PD-R2R-02 / QA-R2V-12 / DR-01 / DR-02 / PE-S2-R3-06, C3-09)

- **Still not held.** Filled: R2-2 (FE, accept all five), R2-5 (FE, accept both; the E-3 focus rule is built). Empty: R2-1 walk (FE with the chair; method accepted), R2-3 (business-analyst), R2-4 (pickleball-domain-coach), R2-5 (product-manager), R2-6 (security-privacy-engineer), R2-7 (coach, product-manager). The chair does not fill other roles' cells (§13.2).
- **Decision (chair):** hold DR-02 **this sprint**, together with DR-01 and DR-03, with one brief per decider (`flows-sprint-03.md` §13.2) that the orchestrator runs as a scheduled decider task (ADR 0037 rule 2; sprint-03 §3.3 DR-02-COACH/-BA/-PM/-SEC). **Due end of 2026-10-08.** If a cell is still empty then: "not held" is recorded here and the PO is asked (blockers.md P14) to choose (a) wait or (b) a recorded waiver for the Sprint 3 UI stories. The routed decider rows PD-RV2-DR-COACH/-BA/-PM/-SEC stay with their deciders; only a decision written in this file closes them.
- **R2-1 walk not run in this round:** no live stack and the disk is under the Compose build floor (see `flows-sprint-01.md` §10.4).
- **Review round 2 (2026-10-07, PD-R1-06):** the disk reason no longer decides it (the floor applies only to a Compose build; a local-process stack behind the committed Caddyfile is enough, `docs/sprints/03/smoke.md`). The walk waits on the senior-frontend-engineer, with whom the method was accepted; business-analyst R2-1 cell still pending. Status and request: `flows-sprint-03.md` §13.1a.
