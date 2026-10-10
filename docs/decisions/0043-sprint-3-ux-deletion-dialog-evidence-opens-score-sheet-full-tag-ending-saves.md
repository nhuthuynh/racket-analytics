# 0043. Sprint 3 UX: deletion is confirmed in a dialog without a typed word; "Show me" rallies open on the score sheet; a Full Tag rally is saved only with its ending

- **Status:** Accepted (2026-10-10, principal-designer as DR-03 chair, ticket DR-HELD-03). The condition set when it was Proposed (2026-10-07, task PD-1; review round 1, PD-R1S3-01), the deciders' cells R3-4, R3-5 and R3-8 in `docs/design/flows-sprint-03.md` §13.1, is met: every one is an accept (two with amendments, see the note at the end).
- **Date:** 2026-10-07
- **Deciders:** principal-designer (proposes); product-manager, business-analyst, security-privacy-engineer, senior-frontend-engineer (DR-03 cells)
- **Consulted:** pickleball-domain-coach (SME, DR-03); senior-qa-engineer (the red-first specs, routed rows PD-FL3-01..03)
- **Related:** `docs/design/flows-sprint-03.md` §3, §4, §5, §6; `api-sprint-03.md` §3.1, §4, §5; FR-006, FR-007, FR-103, FR-150; DES FR-UX-90; HAX [DPA/DESIGN-11] G9, G16; ADR 0006, ADR 0042

## Context and problem statement

Three Sprint 3 interactions have more than one reasonable design, and each changes what the FE builds and what the red-first specs check:

1. FR-006 and FR-UX-90 ask for a "confirmation page that states the consequence" before a match is deleted; FR-007 asks the same for the account. The red-first specs open a `dialog` and type "delete" into a text box if one exists.
2. FR-103 says each evidence rally "opens at its video moment" (FR-027). The red-first specs click a rally link and wait for a `<video>` to load.
3. FR-150's export is a gold set (FR-151). The red-first E2E-03-05 exports right after "Rally end", before any outcome is chosen, but `full-tag-labels/v1` requires an outcome on every rally (`gold-label-schema.md` §4).

## Decision drivers

- The player must understand what is deleted and that it cannot be undone (HAX G16 [DPA/DESIGN-11]); the action must be hard to trigger by accident, but not cost extra work that adds no understanding (judgment).
- Evidence exists so the player can believe a number or correct it (spec §6 "players trust what they can see"; HAX G9, G11).
- A gold label is treated as truth by every later evaluation, so a default value would enter the gold set as a fact nobody chose (judgment).
- Fewest changes to tests already written, as long as the design stays right.

## Considered options

**Deletion confirmation**

1. **Modal dialog that lists the consequences, "Cancel" focused, a clearly named destructive button; no typed word. Chosen.** Pros: the consequences are on screen at the moment of decision; Esc and Cancel are the default path; no extra page load; the spec already expects a dialog. Cons: FR-006 says "page"; the BA must confirm that a dialog meets its intent (DR-03 R3-5).
2. A separate confirmation page (`/matches/{id}/delete`). Pros: literal FR wording. Cons: one more navigation and back-button state for the same content; the specs would change.
3. Dialog plus typing "delete". Pros: harder to trigger by accident. Cons: extra work and a spelling task for every user, including speech-input and switch users, while the listed consequences already carry the meaning (judgment); the server already requires the `{"confirm": "delete"}` body (api-sprint-03 §4.1), which stops stray requests.

**Where an evidence rally opens**

1. **The score sheet S-01 at that rally (`?play=<rally_id>`), with V-01 loaded at the rally start. Chosen.** Pros: the player sees the call next to the video and can correct it in one tap (HAX G9); V-01 already handles fresh short-lived links and every playback error (flows-sprint-02 §7). Cons: S-01 needs a `play` parameter.
2. A new rally video page. Pros: simpler page. Cons: duplicates V-01's states; no correction path, so a wrong call means navigating again.
3. Play inside the E-01 panel on D-01. Pros: no navigation. Cons: a second video component with the same link and error rules; crowded at 360 px.

**Full Tag rally without an outcome**

1. **The rally is saved only when its ending is chosen (as T-01: "Ending (saves the rally)"); export includes saved rallies only and says when one is unsaved. Chosen.** Pros: no guessed truth in the gold set; same mental model as Quick Tag. Cons: E2E-03-05 needs one more step (routed PD-FL3-01, with a TCR row for QA).
2. Save the rally at "Rally end" with a default outcome. Pros: the spec passes unchanged. Cons: a default enters the gold set as a label nobody gave.
3. Block export while a rally is unsaved. Pros: no silent omission. Cons: blocks a useful partial export; the status line already names the unsaved rally.

## Decision

Option 1 in each group, as specified in `flows-sprint-03.md` §3 (E-01), §4 (X-01), §5 (X-02) and §6 (L-01).

## Consequences

- The FE builds X-01/X-02 as dialogs with no text box; the specs' `if (await typed.count())` branch simply does not run (no test change).
- S-01 accepts `?play=<rally_id>` and opens V-01 for that row; the specs' "a video loads" check holds.
- E2E-03-05 adds the ending step (TCR row by QA). The labels API is unchanged.
- FR-006/FR-UX-90 copy drops "clips" and "plans keep a note" until those features exist (flows-sprint-03 §4, open item P-3).

## Evidence

- `web/e2e/sprint-03/journey-v2.spec.ts:58-70` and `delete-account.spec.ts:25-33`: `getByRole('dialog')`, optional textbox.
- `web/e2e/sprint-03/full-tag.spec.ts:37-51`: "Rally end" then "Export"; `docs/data/gold-label-schema.md` §4: `outcome` on every rally.
- `docs/architecture/api-sprint-03.md` §4.1 (confirmation body), §3.1 (media through the Sprint 2 route), §5.2 (one label per request).
- (judgment) where marked above; no usability study was run.

## Note, 2026-10-10 (principal-designer, DR-03 chair; ticket DR-HELD-03)

Accepted on the deciders' cells of DR-03 (`flows-sprint-03.md` §13.1, written 2026-10-07; outcome §13.1b):

- **R3-4 (evidence opens on S-01):** senior-frontend-engineer accept, product-manager accept, both with one wording amendment that does not change the decision: when the browser blocks autoplay, V-01 focuses the `<video>` element, not "the native play button" (a page cannot focus one native control). Folded into `flows-sprint-03.md` §3.
- **R3-5 (dialog, Cancel focused, no typed word):** security-privacy-engineer, business-analyst and product-manager accept. The BA confirms the dialog meets FR-006's "confirmation page": what FR-006 makes testable is that the consequences are stated and confirmed before anything is deleted. So the open "Cons" of option 1 is closed.
- **R3-8 (Full Tag rally saved only with its ending):** security-privacy-engineer accept (condition: a test that a labeller gets 404 on another account's match); senior-frontend-engineer accept with two key amendments (`<` / `>` for one second; players on `3`-`6` as on T-01). Neither changes the decision. Folded into §6.
- Built and tested as decided: X-01/X-02 dialogs, `?play=<rally_id>` on S-01, E2E-03-05 with the ending step (PD-FL3-01 fixed in `723bb7f`, TCR accepted).
- Design review DR-03 as a whole is not yet held: one cell outside this ADR (business-analyst on R3-9, states and checklists) is empty. That does not affect this ADR's three decisions.
