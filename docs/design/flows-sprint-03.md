# Sprint 3 flows: stats dashboard, "Show me" evidence, deletion, Full Tag

- **Status:** Draft v0.1, 2026-10-07 (principal-designer, task PD-1; review round 1, PD-R1S3-01). **Written before any Sprint 3 UI was built** (`ls web/src/app/matches/[matchId]/` → `page.tsx sheet tag`; no `web/src/app/settings` or `web/src/app/label`). Design review **DR-03 is opened in §13 and is not yet held.** Until §13 records "held", this file is a proposal, and no Sprint 3 UI story (ST-047 UI, ST-048, ST-050 UI, ST-051 UI, ST-052 UI) starts unless the PO records a waiver first (sprint-03 §0.1; ADR 0037 rule 2; DoR R7).
- **Stories:** ST-048 stats dashboard (screen family D); ST-047 "Show me" evidence (E); ST-050 delete a match, ST-051 delete my account (X); ST-052 Full Tag (L).
- **Requirements:** FR-006, FR-007, FR-027, FR-055, FR-100..FR-103, FR-150, FR-151; NFR-011, NFR-027, NFR-028, NFR-033, NFR-034, NFR-038, NFR-039, NFR-055, NFR-057, NFR-058, NFR-066.
- **Design sources:** DES FR-UX-70..72 (score sheet, metric card, charts) and FR-UX-90 (deletion) in `docs/requirements/brainstorm-design.md`; HAX [DPA/DESIGN-11]; targets [DPA/DESIGN-02, DPA/DESIGN-10]; contrast [DPA/DESIGN-03, DPA/DESIGN-04]; focus not obscured [DPA/DESIGN-07]; error summary [DPA/DESIGN-13]. Everything else is (judgment).
- **Contract:** `docs/architecture/api-sprint-03.md` (Accepted for build): stats §2, evidence §3, deletion §4, Full Tag §5, codes §6. **Gherkin:** `docs/sprints/sprint-03.md` §7.1-§7.6. **Metric names and "How is this measured?" text come from the API** (`entry.name`, `entry.definition`, from the coach's dictionary `docs/domain/metric-dictionary.md`); the web code holds no metric copy of its own (one source, FR-102).
- **Builds on:** `flows-sprint-01.md` §0 (conventions, A-05, M-01, M-02), `flows-sprint-02.md` §0 (sides, unofficial label, announcements, targets), S-01 and V-01. Tokens: `tokens.md` (only proven pairs are used here; no new colour). Component rules: `component-accessibility-checklist.md`.
- **Red-first tests already written** (QA-ACC-3, `web/e2e/sprint-03/`, assumptions in `web/e2e/helpers/sprint-03.ts`). This file **adopts** their screen ids, routes and Gherkin copy wherever they are sound, so they need no rework; §10 lists the three places where the design differs and routes each to QA.
- **Viewport:** 360 CSS px, one hand (judgment); reflow to 320 px with no sideways scrolling (NFR-034). Full Tag (L) is a laptop-and-keyboard tool used by the team; it still reflows to 320 px.

## 0. Conventions (in addition to flows-sprint-01 §0 and flows-sprint-02 §0)

- **Screen IDs** (used by the axe and target attachments of G03-10 and by `a11y-manual.md`):

| Id | Screen | Route | Story |
|---|---|---|---|
| D-01 | Stats | `/matches/{id}/stats` | ST-048 |
| E-01 | Rallies behind a stat ("Show me" panel, inside D-01) | `/matches/{id}/stats` (no route of its own) | ST-047 |
| E-02 | All rallies behind a stat ("See all n") | `/matches/{id}/stats/{metric_id}/evidence?side=A\|B` | ST-047 |
| X-01 | Delete this match? (dialog on M-02) | `/matches/{id}` | ST-050 |
| X-00 | Your account | `/settings/account` | ST-051 |
| X-02 | Delete your account? (dialog on X-00) | `/settings/account` | ST-051 |
| X-03 | Your account has been deleted | `/signed-out?deleted=1` (A-05 route, other text) | ST-051 |
| L-01 | Full Tag | `/label/matches/{id}` | ST-052 |
| L-02 | Full Tag keys (dialog on L-01) | `/label/matches/{id}` | ST-052 |

- **States.** Every screen lists Empty, Loading, Error, Offline, Low-confidence and Low-sample, plus the two new Sprint 3 states: **Draft hidden** (a metric the coach has not reviewed is not shown, FR-102) and **Deleted** (the match was deleted, here or on another device). "N/A" carries its reason.
- **Unofficial.** While the API says `unofficial: true`, D-01 shows, before the first card, the warning notice "unofficial scoring (rules not yet verified)" (FR-055; metric-dictionary rule 0.5; ADR 0023). One notice per page, not one per card: the same words seven times would be noise to a screen-reader user (judgment). The notice sits in the page header, so it is read before any number.
- **Numbers in text.** Every number a chart shows is also printed as text next to it (NFR-034; FR-UX-72). Percentages are whole numbers ("57%"); ranges are "range 25% to 84%"; rates have at most one decimal and no trailing zero ("2", "1.5").
- **Low sample** (FR-101; ADR 0005; ADR 0041): in **text**, never colour alone, and never hidden. The flagged value is de-emphasised by weight and size only (normal weight, body size, `text-secondary`, 7.35:1 light / 8.69:1 dark), never by lowering contrast below 4.5:1. The flag is a tag in `warning-text` on `warning-surface` (6.86:1) with the words "low sample", followed by the reason from the API (`entry.min_sample`, `low_sample_rule.max_interval_width`), e.g. "Low sample: fewer than 20 rallies, or the range is wider than 30 points. Treat it as a rough guide."
- **Sides:** "Your side (Ivy and Dana)" and "Other side (Carlos and Sam)", as on T-01 and S-01 (flows-sprint-02 §0). Per-player numbers use the match's nicknames; the API gives slots only (`A1`..`B2`) and the client maps them with the match's participants (NFR-057: names never leave the match).
- **Errors on D, E and L** are a single `role="alert"` notice at the top of the working area: what happened, what to do, and `Reference: <support_ref>` when the API gave one (NFR-058). The deletion dialogs use the same notice inside the dialog.
- **Targets:** every control ≥ 24×24 CSS px (SC 2.5.8); primary actions, "Show me", the delete buttons and the Full Tag tag buttons ≥ 48 px high on touch [DPA/DESIGN-10]; ≥ 8 px between adjacent targets.
- **Dialogs** (X-01, X-02, L-02): `role="dialog"`, `aria-modal="true"`, labelled by their `<h2>`; focus moves to the **Cancel** button on open (the safe choice, judgment), is kept inside, and returns to the opener on Esc or Cancel (component checklist, dialogs).

## 1. Flow map

```
 M-02 Match ──"Stats"──► D-01 Stats ──"Show me the n rallies" (per card, per side)──► E-01 panel (≤ 10 rallies)
   │  ▲                   │   ▲                                                         │   └─"See all n" (n > 10)──► E-02 All rallies (pages of 10)
   │  │                   │   └──── back from S-01 (refetch: stats follow corrections)  └─"Rally n …"──► S-01 ?play=<rally_id> → V-01 loads at the rally
   │  │                   └─"How is this measured?" (disclosure in the card)
   │  └─ S-01 "See the stats"
   ├─"Delete match"──► X-01 dialog ──"Delete match"──► M-01 Your matches, notice "The match was deleted. …"
   │                                └─Cancel / Esc ──► M-02 (focus back on "Delete match")
 Account menu ──"Your account"──► X-00 ──"Delete my account"──► X-02 dialog ──"Delete my account"──► X-03 "Your account has been deleted"
 Another device, after the account is deleted ──► next request 401 ──► A-01 Sign in (existing "signed out" path)
 Labeller only: /label/matches/{id} ──► L-01 Full Tag ──"?"──► L-02 keys ; "Export labels" ──► labels-<id>.json download
 Not a labeller, or not the owner, or deleted ──► the not-found page "Page not found" (same as any unknown address, api-sprint-03 §5.1)
```

## 2. Stats (ST-048; FR-100, FR-101, FR-102, FR-055)

### D-01 Stats

- **Entry:** link "Stats" on M-02 (next to "Tag rallies" and "Score sheet", shown once the video is received) and "See the stats" on S-01 below the tables.
- **Header:** "Back to the match"; `<h1>` "Stats"; the match title as a subtitle; `<title>` "Stats: <match title>". Then the unofficial notice (§0). Then one sentence (HAX G1): "These stats come from the rallies you tagged. Change a rally on the score sheet and they change too." with "score sheet" as a link to S-01.
- **Cards:** one `<section>` per published metric, in dictionary order (AN-01..AN-07), labelled by its `<h2>` = `entry.name` (e.g. "Rallies won on serve"). Inside each card:
  1. **Side blocks:** "Your side (…)" then "Other side (…)", side by side from 48em (768 px), stacked below it. Each block prints the value and its numbers (table below), the low-sample tag when flagged, and its "Show me" button.
  2. **"How is this measured?"**: a disclosure button (`aria-expanded`) at the end of the card. It shows `entry.definition` in plain words, then "Smallest sample we trust: 20 rallies." (from `entry.min_sample`; "Not flagged: this describes the match, it is not an estimate." for AN-06, whose `min_sample` is `null`) and "Definition version 0.1, checked by our coach." (HAX G11, G2).
- **What each side block prints** (fields from api-sprint-03 §2.1; examples are the coach's worked example, `web/e2e/sprint-03/worked-example.reference.json`):

| Metric (`entry.name`) | Main value | Supporting text (always shown) |
|---|---|---|
| AN-01 Rallies won on serve | "57%" | "4 of 7 rallies · n = 7 · range 25% to 84%" |
| AN-02 Rallies won when receiving (name pending the coach, COACH-1) | "33%" | "2 of 6 rallies · n = 6 · range 10% to 70%" |
| AN-03 Points per service turn | "2" | "4 points in 2 service turns" |
| AN-04 Unforced errors per game | "2" | "2 unforced errors in 1 game"; then per player "Ivy 1 · Dana 1"; then "player not tagged in 1 rally" when `player_not_tagged` > 0 (Gherkin §7.1) |
| AN-05 Serve faults | "29%" | "2 of 7 serves · n = 7 · range 8% to 64%"; "fault type not tagged in n rallies" when > 0 ("lower bound", metric-dictionary AN-05) |
| AN-06 Longest scoring run | "3 points" | "n = 4 runs"; the run histogram as a list of 5 rows "1 point: 1 run", "2 points: 0 runs", … "5 or more: 0 runs", each with a bar |
| AN-07 How rallies ended | "n = 6 rallies" | a list of 4 rows "Winners: 2 (33%, range 10% to 70%)", "Unforced errors: 2 (…)", "Forced errors: 0 (…)", "Faults: 2 (…)", each with a bar |

- **Bars (AN-06, AN-07):** one horizontal bar per row, in the proven progress pair (fill `primary` on a track outlined in `progress-track`, ≥ 3:1 each, `tokens.md`). No stacked bar and no category colours, so no colour pair needs a new proof (judgment). The printed row text is the content; the bars are `aria-hidden`. The rows are a real list, so no separate data-table toggle is needed (FR-UX-72's purpose is met by the printed list, judgment).
- **n = 0 for a side** (e.g. the other side never served): main value "—", text "No rallies yet · n = 0"; no range; no "Show me" button; text "No rallies behind this yet." instead. A disabled button is not used: it cannot take focus and says nothing about why (judgment).
- **Low sample:** see §0. Example: AN-01, your side: "57%" (de-emphasised), "4 of 7 rallies · n = 7 · range 25% to 84%", tag "low sample", "Low sample: fewer than 20 rallies, or the range is wider than 30 points. Treat it as a rough guide."
- **"Show me":** visible text "Show me the 7 rallies" (n from the side's sample; for AN-04 the number of error rallies, for AN-06 "Show me the runs' rallies"); accessible name starts with the visible words (SC 2.5.3): "Show me the 7 rallies, Rallies won on serve, your side". One button per side, so two per card (E2E-03-02). It opens E-01 below that side block.
- **Layout shift:** while loading, each card's place is reserved at its final height (skeleton blocks of the same size), so the numbers arriving move nothing (NFR-039, timing spec `timing-layout-shift` = 0).

### D-01 states

| State | What the player sees | Source |
|---|---|---|
| Empty: no video yet | "You can see stats once this match's video is received and rallies are tagged." and "Back to the match". No cards | FR-100 |
| Empty: no rally tagged | "No rallies are tagged yet, so there are no stats to show." and the primary link "Tag rallies" (to T-01). No cards, no numbers, no "Show me" (E2E-03-08) | FR-100 |
| Loading | A region with `aria-busy="true"` and a polite status "Loading your stats…"; reserved skeleton cards; no numbers, no "Show me" (E2E-03-08) | NFR-011, NFR-039 |
| Error | Alert "Your stats could not be loaded. Try again. Reference: …" and a "Try again" button that loads again (focus stays on it). No numbers are shown from an earlier load | NFR-058 |
| Offline | Alert "Your stats could not be loaded because the connection dropped. Try again." and "Try again" | NFR-058 |
| Draft hidden: some entries not published | Only published cards. Below the last card: "More stats will appear here once our coach has checked how they are measured." It never names or counts the hidden ones (FR-102; E2E-03-03 checks no draft heading) | FR-102 |
| Draft hidden: none published (`metrics` = `{}`, rallies tagged) | "No stats are ready to show yet. Each stat appears once our coach has checked how it is measured." and "Back to the match". This is not the error state | FR-102; api-sprint-03 §2.1 |
| Low-sample | Tag and reason in text, value de-emphasised, never hidden (§0) | FR-101 |
| Low-confidence | N/A: no automatic call. The one uncertainty in the inputs is the rules preset, shown by the unofficial notice (HAX G2) | FR-055 |
| Deleted (here or on another device) | The stats request answers 404: the not-found page "Page not found" with "Go to your matches" (no hint that the match ever existed, api-sprint-03 §1.1) | NFR-051 |
| Stats follow corrections | No live push. Each visit to D-01 loads fresh numbers (`no-store`); coming back from S-01 after a correction shows the new values (Gherkin §7.1 "A correction changes the stats") | api-sprint-03 §2.1 read repair |

## 3. Evidence (ST-047; FR-103, FR-027, NFR-038)

### E-01 Rallies behind a stat (panel in D-01)

- **Opens with** "Show me …" (a disclosure button, `aria-expanded="true"`; pressing it again closes the panel). Focus stays on the button; the panel follows it directly in reading order, so the next Tab lands on the first rally (keyboard path, E2E-03-06).
- **Content:** an `<h3>` "Rallies behind “Rallies won on serve”, your side"; a list labelled the same way (`aria-label`), with up to 10 items in video order (api-sprint-03 §3.1). Each item is one link: "Rally 3 · game 1 · 0:12" (rally number from the sheet, game, start time m:ss floored).
- **Each link** goes to `S-01` at `/matches/{id}/sheet?play=<rally_id>`: the score sheet scrolls that row into view and opens V-01 for it, which fetches a fresh short-lived link and loads the video at the rally start (NFR-055, NFR-014). The player lands where they can **check the call and correct it** in one more tap (HAX G9, G11; ADR 0043). Playback starts if the browser allows it; otherwise the native play button is focused (no sound starts on its own, judgment).
- **More than 10:** under the list, a link "See all 23" (exact words, Gherkin §7.3) to E-02.

### E-02 All rallies behind a stat

- `<h1>` "Rallies behind “Rallies won on serve”"; subtitle "Your side · 23 rallies"; "Back to the stats" (to D-01, focus returned to that card's heading). The same list items as E-01, 10 per page, with "Next 10 rallies" and "Previous 10 rallies" links (api-sprint-03 §1.2 cursor). The page says "Rallies 11 to 20 of 23".

### E states

| State | E-01 | E-02 |
|---|---|---|
| Empty (n = 0) | Not reachable: no "Show me" when n = 0 (§2) | "No rallies are behind this stat yet." and "Back to the stats" |
| Loading | Inside the panel: `aria-busy="true"` region and status "Loading the rallies…"; the space of 3 items reserved | Same, whole list |
| Error | Alert in the panel "The rallies for this stat could not be loaded. Try again. Reference: …" and "Try again"; no rally links (E2E-03-08) | Same alert at the top |
| Offline | "… could not be loaded because the connection dropped. Try again." | Same |
| Stale (a correction since D-01 loaded: `total` differs from the card's n) | The panel shows the server's list and the line "These stats changed since you opened this page. Reload the stats to see the new numbers." with a "Reload the stats" button | Same line |
| Deleted / unpublished metric (404) | Alert "This stat is no longer available. Reload the stats." | The not-found page |
| Low-sample | The low-sample tag stays on the card above the panel | Subtitle repeats "low sample" when flagged |
| Low-confidence | N/A: every rally is the player's own tag | N/A |
| Draft hidden | Not reachable: an unpublished metric has no card (API 404 for its evidence) | 404 page |

## 4. Delete a match (ST-050; FR-006, NFR-066, ADR 0006)

### X-01 Delete this match? (dialog on M-02)

- **Opener:** M-02, last section "Delete this match" with one line "Deleting removes the video and everything made from it." and a button "Delete match" (outline style in `error` on the page: text and border 6.54:1, a proven pair; ≥ 48 px high). It is placed last, away from "Tag rallies" and "Stats", so it is not pressed by accident (judgment).
- **Dialog:** `<h2>` "Delete this match?"; the match title and date as a line ("Saturday doubles · 3 Oct 2026"); then the consequences (HAX G16; FR-UX-90; Gherkin §7.5):
  - "This deletes the video, tags, score sheet and stats of this match."
  - "It cannot be undone."
  - "The match leaves your account at once. Its stored files are removed within 7 days."
  - When an upload is still in progress: "The upload in progress stops."
- **Buttons:** "Cancel" (focused on open) and "Delete match" (error outline). No typed confirmation (ADR 0043): the dialog that states the consequences is the confirmation step FR-006 asks for, and typing a word adds work without adding understanding (judgment). The client sends `{"confirm": "delete"}` only from this button (api-sprint-03 §4.1).
- **What the FR-UX-90 copy leaves out, on purpose:** "clips" and "Plans keep a note that the match was deleted": neither clips nor plans exist in Sprint 3, and copy must not name what the product lacks (the DR-01 R-2a reasoning). Both come back when those features ship (FR-030, Sprint 4 plans; open item P-3).
- **After 202:** go to M-01 `/matches`; a polite status notice at the top: "The match was deleted. Its stored files are removed within 7 days." The notice does **not** repeat the title: the list must show no trace of the match (journey-v2 checks that "Saturday doubles" is gone). Focus goes to the `<h1>` "Your matches".

### X-01 states

| State | What the player sees | Source |
|---|---|---|
| Deleting | "Delete match" shows "Deleting…" with `aria-busy`; a second press is ignored; Cancel stays usable but does not undo a request already sent | judgment |
| Error | The dialog stays open; alert inside it: "The match was not deleted. Try again. Reference: …". Focus stays on "Delete match", so one more press retries; the alert is announced | NFR-058 |
| Offline | "The match was not deleted because the connection dropped. Try again." | NFR-058 |
| Deleted already (404, e.g. from another device) | Go to M-01 with the notice "This match was already deleted." | api-sprint-03 §4.1 |
| Signed out meanwhile (401) | The existing signed-out path to A-01 | flows-sprint-01 §2 |
| Empty, Low-confidence, Low-sample | N/A: a dialog about one existing match; no metric | — |

## 5. Delete my account (ST-051; FR-007, NFR-066)

### X-00 Your account

- **Entry:** "Your account" in the account menu (above "Sign out"). `<h1>` "Your account"; the line "Signed in as ivy@example.com" (the owner's own address, shown only to them); section `<h2>` "Delete your account" with "This deletes your account and all your matches." and the button "Delete my account" (error outline, ≥ 48 px).

### X-02 Delete your account? (dialog on X-00)

- `<h2>` "Delete your account?"; consequences:
  - "This deletes your account and all your matches: every video, tag, score sheet and stat."
  - "You will be signed out on every device."
  - "It cannot be undone."
  - "Stored files are removed within 7 days."
  - "If you sign in again with the same email address, you start with a new, empty account." (**depends on PM-1**; this is the contract default, api-sprint-03 §4.2. If the PM decides "refused", the line becomes "You will not be able to sign in with this email address again." and FR-007's Gherkin follows.)
- **Buttons:** "Cancel" (focused) and "Delete my account". No typed confirmation (ADR 0043).
- **After 202:** the device is cleared as at sign-out (FR-UX-91; the same clean-up the account menu runs), then **X-03** at `/signed-out?deleted=1`: `<h1>` "Your account has been deleted"; "Nothing from it is kept on this device. Its stored files are removed within 7 days."; link "Sign in". The A-05 page with this text, not a new page.
- **Other devices:** their next request gets 401 and they follow the existing signed-out path to A-01 (FR-007 "signed out everywhere"). No message there names the deletion: the other device may be someone else's view (judgment).

### X-02 states

Same as X-01 (Deleting "Deleting…", Error "Your account was not deleted. Try again. Reference: …", Offline). A 401 on DELETE (the session ended meanwhile) → A-01, nothing deleted (api-sprint-03 §4.2). Empty, Low-confidence, Low-sample N/A.

## 6. Full Tag (ST-052; FR-150, FR-151)

### L-01 Full Tag

- **Who:** only accounts with the labeller role, only on a match they own that has a consent record (api-sprint-03 §5.1). Everyone else gets "Page not found" (FR-150 "not available"; E2E-03-05). **Entry in Sprint 3:** the direct address, from the team's labelling runbook; no link in the player UI, because the client cannot yet tell a labeller from a player (open item P-1).
- **Layout (desktop first, reflows at 320 px):** `<h1>` "Full Tag: <match title>"; the line "Internal labelling tool. Labels are saved as you go."; the video (native controls hidden while stepping, judgment: the custom bar below replaces them); the **frame readout** "Frame 1520 of 3600 · 0:25.33" (plain digits, no thousands separator, so it equals the export's frame numbers; a polite live region that announces only after stepping stops for 500 ms, so holding a key does not flood the screen reader, judgment).
- **Stepping bar** (`role="group"` "Move through the video"): "Previous frame" (`,`), "Next frame" (`.`), "Back 1 second" (Shift+`,`), "Forward 1 second" (Shift+`.`), "Play or pause" (Space). Same frame keys as T-01's key map (flows-sprint-02 K-01). No dragging needed (SC 2.5.7; NFR-030).
- **Tag bar** (`role="group"` "Tag at this frame"), each ≥ 48 px:
  1. "Rally start" (`S`), "Rally end" (`E`): `aria-pressed` toggles; the rally in progress shows "Rally 3: frames 1520 to …".
  2. "Hit" (`H`) → group "Who hit it?" with one button per player nickname (`1`-`4`), grouped "Your side" / "Other side" as on T-01. Optional "Shot details" disclosure with the facet choices of `gold-label-schema.md` §4 (contact, trajectory, intent, technique; one radio group each, all optional).
  3. "Bounce" (`B`) → "Ball in view?" Yes / No; then optional "Where on the court (metres)": two number fields "Across" and "Along" (no pointer needed; empty means `null`, gold-label-schema §4).
  4. After "Rally end": the question **"How did rally 3 end?"**: "Won by" (Your side / Other side), "Who ended it (optional)", and the ending buttons "Winner", "Unforced error", "Forced error", "Fault" (then "Fault kind": serve, foot, two bounce, kitchen (non-volley zone), other), "Replay". **Choosing the ending saves the rally with its hits and bounces** (one request per label, api-sprint-03 §5.2), as on T-01 ("Ending (saves the rally)"). A rally without an outcome is never saved: the export is a gold set, and a guessed default would enter it as truth (judgment; ADR 0043).
- **Events list:** `<h2>` "Rally 3 so far": an ordered list "Hit by Carlos at frame 1530", "Bounce in view at frame 1544", each with "Remove" while the rally is unsaved. Saved rallies are listed under `<h2>` "Saved rallies" ("Rally 1: frames 6 to 70, unforced error by B2, 3 events"). No edit or delete after saving in Sprint 3 (api-sprint-03 §5.2); the list says "Saved labels cannot be changed yet."
- **Esc:** clears the unsaved rally's marks after the question "Drop rally 3 and its 2 events?" (Yes / No).
- **Export:** "Export labels" (secondary) downloads `labels-<match id>.json` (`full-tag-labels/v1`); status "Exported 3 rallies with 41 events." If a rally is unsaved, the export still runs on the saved rallies and the status adds "Rally 4 is not saved yet: choose how it ended to include it." (judgment: never block an export, never include an unsaved rally).
- **Keys:** "?" opens L-02 (the key list, same dialog pattern as K-01, with the single-key switch of SC 2.1.4, "Use single-key shortcuts", on by default and remembered on this device).

### L-01 states

| State | What the labeller sees | Source |
|---|---|---|
| Not a labeller / not the owner / deleted / unknown | "Page not found" (404) | api-sprint-03 §5.1 |
| No consent record (409 `no_consent`) | `<h1>` "Full Tag: <title>"; alert "This match has no consent record for labelling. Nothing can be labelled until the team records consent."; no video, no tag bar | IT-03-11; api-sprint-03 §6.1 |
| Video not ready (409 `match_not_ready`, incl. variable frame rate) | Alert "This match's video is not ready for frame-by-frame labelling." | api-sprint-03 §5.2 |
| Empty | "No rallies labelled yet. Step to the first serve and press Rally start." | — |
| Loading | `aria-busy` region "Loading the match…"; then the video's own loading | — |
| Error (label refused, 422 `invalid_label`) | Alert "This label was not saved: <reason>." per field code: `outside_clip` "the frame is outside the video", `no_rally` "it is outside a rally", `overlaps_rally` "it overlaps rally n", `out_of_order` "it is before the last event of this rally", `not_a_player` "choose a player of this match"; the unsaved marks stay | api-sprint-03 §5.4 |
| Error (other) / Offline | "The label was not saved. Try again. Reference: …" / "… because the connection dropped. Try again." Marks kept | NFR-058 |
| Rate limited (429) | "Too many labels in a short time. Wait a moment, then save again." | api-sprint-03 §5.2 |
| Low-confidence | N/A: every label is the labeller's own | — |
| Low-sample, Draft hidden | N/A: no metric | — |

## 7. Copy register (proposed; the FE ships these strings, the Gherkin keeps its own)

| Screen | String | Gherkin / source | Test that reads it |
|---|---|---|---|
| D-01 | "unofficial scoring (rules not yet verified)" | §7.2; FR-055 | journey-v2, definitions |
| D-01 | "n = 7" | §7.1 | `expectSidePrinted` |
| D-01 | "range 40% to 69%" next to "55%" | §7.1 "The interval is shown" | step module |
| D-01 | "low sample" (tag) and its reason | §7.1; FR-101 | definitions |
| D-01 | "How is this measured?" | §7.2 | definitions |
| D-01 | "player not tagged in 1 rally" | §7.1 | step module |
| D-01 | "No rallies are tagged yet, so there are no stats to show." / "Tag rallies" | — | states (`STATE_COPY.empty`) |
| D-01, E-01 | "Your stats could not be loaded. Try again." / "The rallies for this stat could not be loaded. Try again." / "Try again" | — | states (`STATE_COPY.error`, `.retry`) |
| E-01 | "Show me the 7 rallies"; "Rally 3 · game 1 · 0:12"; "See all 23" | §7.3 | journey-v2, evidence-crawl |
| X-01 | "This deletes the video, tags, score sheet and stats of this match." / "It cannot be undone." | §7.5 | journey-v2 |
| M-01 | "The match was deleted. Its stored files are removed within 7 days." | — | journey-v2 (title absent) |
| X-02 | "This deletes your account and all your matches: every video, tag, score sheet and stat." / "You will be signed out on every device." / "It cannot be undone." | §7.5 | delete-account |
| L-01 | "Full Tag: <title>"; "Frame 1520 of 3600"; "This match has no consent record for labelling." | §7.6; api §6.1 | full-tag |

## 8. HAX checklist (Sprint 3 scope) [DPA/DESIGN-11]

| Guideline | Where | Design response |
|---|---|---|
| G1 Make clear what the system can do | D-01 header | "These stats come from the rallies you tagged." No claim of automatic analysis |
| G2 Make clear how well it can do it | D-01 cards | n on every value, the Wilson range on every proportion, "low sample" in text, the unofficial notice; "checked by our coach" with the definition version |
| G9 Support efficient correction | E-01 → S-01 | Every rally behind a number opens on the score sheet with its video, where Switch winner is one tap; the stats follow on the next visit |
| G10 Scope services when in doubt | D-01 | A small sample is flagged and de-emphasised, not hidden and not turned into advice; drafts are not shown at all (FR-102) |
| G11 Make clear why the system did what it did | D-01, E-01 | "How is this measured?" (the coach's definition) and "Show me" (the rallies behind it) on every card |
| G14 Update and adapt cautiously | D-01 | A definition change is a new dictionary version; the card shows the version it used |
| G16 Convey the consequences of user actions | X-01, X-02 | The dialogs list what goes, that it cannot be undone, and the 7-day purge |
| G18 Notify users about changes | E-01 stale line; D-01 "More stats will appear here once our coach has checked…" | The player is told when the numbers or the set of stats changed |
| G3-G8, G12, G13, G15, G17 | — | No automatic call, recommendation or learning in Sprint 3. L-01 (internal) remembers the single-key setting (G12, G17) |

## 9. WCAG 2.2 AA design-level checklist per screen

"✓" means this file specifies it. Implementation evidence: G03-10 (axe per family D, E, X, L and per D/E state; 24×24 targets; keyboard E2E-03-05, E2E-03-06; reflow at 320 and 360 px) and the human pass (`a11y-manual.md`, waiting on P6).

| Check | D-01 | E-01/E-02 | X-01/X-02 | X-00/X-03 | L-01/L-02 |
|---|---|---|---|---|---|
| Unique title, one `<h1>` | ✓ "Stats: <title>" | ✓ (E-02 own `<h1>`; E-01 `<h3>`) | — (dialog `<h2>`) | ✓ | ✓ (L-02 dialog `<h2>`) |
| Targets ≥ 24 px; primary and tag controls ≥ 48 px (SC 2.5.8; NFR-028) | ✓ | ✓ | ✓ | ✓ | ✓ |
| Contrast from proven tokens only; de-emphasis never under 4.5:1 (SC 1.4.3, 1.4.11) | ✓ | ✓ | ✓ | ✓ | ✓ |
| Not colour alone: "low sample" in words; bars with printed values (SC 1.4.1) | ✓ | ✓ | — | — | ✓ (pressed: filled and a check mark) |
| Label in name: visible words start the accessible name (SC 2.5.3) | ✓ "Show me the n rallies, …" | ✓ | ✓ | ✓ | ✓ |
| Keyboard-only completion; logical order (SC 2.1.1, 2.4.3) | ✓ | ✓ | ✓ (focus trapped, returned) | ✓ | ✓ (all tagging by keys) |
| Character key shortcuts can be turned off (SC 2.1.4) | — | — | — | — | ✓ |
| Focus not obscured: no sticky bar (SC 2.4.11) | ✓ | ✓ | ✓ | ✓ | ✓ (bars in normal flow) |
| No dragging needed (SC 2.5.7) | ✓ | ✓ | ✓ | ✓ | ✓ (frame keys; court position as numbers) |
| Status messages polite, focus kept (SC 4.1.3) | ✓ loading | ✓ loading | ✓ M-01 notice | ✓ | ✓ frame readout, debounced |
| Reflow at 320 px, no sideways scroll (SC 1.4.10; NFR-034) | ✓ stacked sides | ✓ | ✓ | ✓ | ✓ (bars wrap) |
| No layout shift on load (NFR-039) | ✓ reserved cards | ✓ reserved items | — | — | — |
| Error identification with the fix in text (SC 3.3.1, 3.3.3) | ✓ | ✓ | ✓ | — | ✓ per field code |
| Text alternative for charts and video (SC 1.1.1; NFR-033) | ✓ the printed lists | ✓ the rally list is the text of the evidence | — | — | — (internal tool; frames are the content) |

## 10. Differences from the red-first tests and the routed items

The red-first E2E specs assumed this UI (`web/e2e/helpers/sprint-03.ts`, "until PD-1/DR-03"). This file keeps their screen ids D-01, E-01, X-01, X-02, L-01, their routes (`/matches/{id}/stats`, `/settings/account`, `/label/matches/{id}`) and their copy, and adds E-02, X-00, X-03 and L-02. Three points differ; each is routed as a row in `docs/sprints/03/review-rounds.md` (review round 1, principal-designer):

| Id | Severity | Test today | Design | Owner |
|---|---|---|---|---|
| PD-FL3-01 | minor | E2E-03-05 (`full-tag.spec.ts:42-44`) presses "Rally end" and exports at once, expecting the hit in the file | A rally is saved only when its ending is chosen (§6; a gold label never gets a guessed outcome). The spec chooses "Won by" and an ending (e.g. "Winner") after "Rally end", before "Export labels". Needs a TCR row, decided by QA, before the test changes | senior-qa-engineer |
| PD-FL3-02 | minor | `expectSidePrinted` (`helpers/sprint-03.ts`) looks for `String(ref.value)` on AN-03, which prints "1.3333" for 4 points in 3 turns | AN-03 prints at most one decimal ("1.3"); the helper compares the same rounding. The worked example (2.0 → "2") passes either way, so the change is red-safe | senior-qa-engineer |
| PD-FL3-03 | nit | `METRIC_NAMES` in the helper copies the names; `metricCard` finds cards by them | Names come from the API (`entry.name`); AN-02's name is pending COACH-1. The helper reads `metrics.json` names (as `PUBLISHED` already does) so a coach rename changes one file | senior-qa-engineer |

## 11. Open items

| # | Item | Owner | Needed by |
|---|---|---|---|
| P-1 | A labeller link on M-02 needs the role in `GET /me` (e.g. `"roles": ["labeller"]`); not in api-sprint-03 | principal-engineer (contract), then FE | Sprint 4 (Sprint 3 uses the direct address) |
| P-2 | X-02 re-sign-in line depends on PM-1 (new empty account vs refused) | product-manager | DR-03 |
| P-3 | X-01 copy for clips and plans ("Plans keep a note …", FR-006, FR-UX-90) when those features ship | principal-designer | the sprint that ships plans (Sprint 4) |
| P-4 | AN-02's UI name ("Rallies won when receiving" proposed; FR-100 says "side-out %") and the "How is this measured?" words of every entry | pickleball-domain-coach (COACH-1) | DR-03 |
| P-5 | Whether "Forced error" stays a separate AN-07 row while κ ≥ 0.6 is unproven (flows-sprint-02 E-2, DR-02 R2-7) | pickleball-domain-coach, product-manager | DR-02 / DR-03 |

## 12. Traceability

| Gherkin (sprint-03 §7) | Screen | E2E |
|---|---|---|
| §7.1 Starter stats, uncertainty | D-01 | E2E-03-01, E2E-03-03 |
| §7.2 Metric dictionary | D-01 (draft hidden, How is this measured?, unofficial) | E2E-03-03 |
| §7.3 Evidence | E-01, E-02 | E2E-03-01, E2E-03-02, E2E-03-06 |
| §7.5 Deletion | X-01, X-00, X-02, X-03 | E2E-03-01, E2E-03-04 |
| §7.6 Full Tag | L-01, L-02 | E2E-03-05 |
| States (ST-048 card) | D-01, E-01 | E2E-03-08 |

## 13. Design review record (DR-03)

| Date | Participants | Outcome | Findings |
|---|---|---|---|
| 2026-10-07 | principal-designer (author) | Draft written before the build, from the contract, the Gherkin and the red-first specs | §10 PD-FL3-01..03, routed |
| Opened 2026-10-07; decisions due **end of 2026-10-08**; escalation to the PO the same day if a blocking cell is empty (blockers.md P14) | principal-designer (chair), senior-frontend-engineer, pickleball-domain-coach (SME), business-analyst, product-manager, security-privacy-engineer, each invoked by the orchestrator with the brief in §13.2 (ADR 0037 rule 2) | **Not yet held.** Asynchronous, in the repository, like DR-01/DR-02: each decider writes accept or reject with one line of reason in its cell, signed and dated, and commits it (ADR 0022). A decider that cannot write files returns the text; the chair commits it, attributed | — |

### 13.1 Agenda (chair's proposals, judgment unless cited)

| # | Item | Proposal | Decides | Decision |
|---|---|---|---|---|
| R3-1 | D-01 cards, side blocks, printed numbers, bars (§2) | Accept as specified | senior-frontend-engineer (feasibility), business-analyst (FR-100/101/102 acceptance) | principal-designer: accept (2026-10-07, author) |
| R3-2 | Metric words: names, definitions, "Smallest sample we trust", the low-sample reason, AN-04 "player not tagged", AN-07 rows (§2, §7) | Accept; the coach may reword, and the words then live in the dictionary, not in the web code | pickleball-domain-coach | principal-designer: accept (2026-10-07, author) |
| R3-3 | One unofficial notice per page, not per card (§0) | Accept: the same words seven times are noise; the notice is read before any number | product-manager, pickleball-domain-coach | principal-designer: accept (2026-10-07, author) |
| R3-4 | E-01 rally links open S-01 with V-01 at the rally (§3; ADR 0043) rather than a separate video page | Accept: the player can check and correct in the same place (HAX G9) | senior-frontend-engineer, product-manager | principal-designer: accept (2026-10-07, author) |
| R3-5 | Deletion as a dialog with Cancel focused and no typed word (§4, §5; ADR 0043); FR-UX-90 copy without clips and plans | Accept | product-manager, security-privacy-engineer, business-analyst (FR-006 "confirmation page") | principal-designer: accept (2026-10-07, author). security-privacy-engineer: **accept** (2026-10-07, SEC-1). No typed word is needed for security: the CSRF controls are the Origin check (403) and the `__Host-` SameSite cookie, and the server-side `{"confirm":"delete"}` body guards against stray or replayed clients (threat model S3 T-DL-2). Cancel focused on open is the safe default. Leaving clips and plans out of the copy promises nothing the product does not do |
| R3-6 | X-02 re-sign-in line (P-2) | Keep the contract default until PM-1 decides | product-manager | principal-designer: proposal only; PM-1 decides |
| R3-7 | Deletion copy promises: "removed within 7 days", "signed out on every device"; no message on other devices; the address shown on X-00 to its owner | Accept: each is a contract fact (api-sprint-03 §4) | security-privacy-engineer | principal-designer: accept (2026-10-07, author). security-privacy-engineer: **accept, with one amendment** (2026-10-07, SEC-1). "Removed within 7 days" and "signed out on every device" are contract facts (api-sprint-03 §4; T-AC-1, T-DL-8 alert at 6 days). "Stored files" correctly excludes process logs, which hold ids only (T-DL-12). No message on other devices: accept, since that device may be someone else's view. The address on X-00: accept, shown only to its signed-in owner, and the response must carry `Cache-Control: no-store`. **Amendment:** X-03's "Nothing from it is kept on this device." over-promises. `Clear-Site-Data: "cache"` and the client clean-up do not remove browser history or files the user saved (T-DL-12 e). Use "The app's data on this device has been cleared." (owner principal-designer; FE string and E2E-03-04 via a TCR row if a test pins the old line). Separately, a media link already open on another device can keep playing for at most its TTL (≤ 15 min, T-DL-10). This is accepted, and the copy needs no change, because "leaves your account at once" stays true |
| R3-8 | Full Tag: rally saved only with its ending; frame readout without separators; keys; direct address only (§6, P-1) | Accept | senior-frontend-engineer, senior-ml-cv-engineer (consulted: export), security-privacy-engineer (404 for non-labellers, no consent reference shown) | principal-designer: accept (2026-10-07, author). security-privacy-engineer: **accept** (2026-10-07, SEC-1). The server answers 404 to a non-labeller, a non-owner and a deleted match. The control is the role check and the owner filter, not the absence of a link, so a direct address only is fine (T-LB-1). The `no_consent` state shows no consent reference (T-LB-4). Hit buttons show the labeller's own nicknames for their own match, while the export carries slots only. Condition: a test shows a labeller gets 404 on another account's match (SEC-S3-TM-08) |
| R3-9 | States, HAX and WCAG checklists (§2-§6, §8, §9) | Accept | senior-frontend-engineer, business-analyst | principal-designer: accept (2026-10-07, author) |

DR-03 is **held** when every "Decides" role has a cell. A reject sends the item back to the chair, who amends this file and asks again (same day). When held, the chair replaces the "Not yet held" row with the outcome and ticks DoR R7 in sprint-03 §14.2 with a decision-log row.

### 13.2 Decider briefs (DR-01, DR-02 and DR-03 in one invocation per role)

One brief per role, so each decider runs once for all three reviews (ADR 0037 rule 2). Each cell is written in the file named, as "role: **accept** / **reject** (date): one line of reason".

| Role | Cells to decide | Read first |
|---|---|---|
| senior-frontend-engineer | DR-03 R3-1, R3-4, R3-8, R3-9. (DR-01 R-2a/R-2b and DR-02 R2-2/R2-5 are already done.) DR-01 R-1 / DR-02 R2-1: run the screen walk with the chair on the next live stack (method accepted by both) | this file §2-§6, §9; api-sprint-03 |
| pickleball-domain-coach | DR-03 R3-2, R3-3; DR-02 R2-4 (sides and "us/them"), R2-7 (forced vs unforced kept as a button); DR-01 R-4 ("You can still tag this match." as reassurance); flows-sprint-02 PD-FL2-03 rules-line words; the COACH-1 AN-02 name (P-4) | metric-dictionary §1; flows-sprint-02 §0, §12 E-1/E-2; flows-sprint-01 §10.1 |
| business-analyst | DR-03 R3-1, R3-5 (does the X-01 dialog meet FR-006's "confirmation page"?), R3-9; DR-02 R2-3 (`O` for forced error); DR-01 R-3 (codec refusal copy), D-1, D-2 | FR-006, FR-007, FR-100..FR-103, FR-150; flows-sprint-01 §9, §10.1 |
| product-manager | DR-03 R3-3, R3-4, R3-5, R3-6 (with PM-1); DR-02 R2-5 (ending saves, E-3 focus rule), R2-7; DR-01 R-5 (expiry wording, Cancel upload), D-1 | sprint-03 §0.4, PM-1; flows-sprint-02 §13.1 |
| security-privacy-engineer | DR-03 R3-5, R3-7, R3-8; DR-02 R2-6 (V-01 says nothing about the link's lifetime or contents) | api-sprint-03 §4, §5.1; NFR-055, NFR-057 |
