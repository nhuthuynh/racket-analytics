# Component accessibility checklist (WCAG 2.2 AA)

- **Status:** Draft v0.1, 2026-10-03 (principal-designer). It is used in every UI design review and every frontend PR review from ST-010 onward.
- **Target:** WCAG 2.2 Level AA [DPA/DESIGN-01]; NFR-027..NFR-035.
- **Source:** The success criteria (SCs) marked **✓src** were fetched and verified in DPA:
  - 1.2.2 [DPA/DESIGN-08];
  - 1.2.3 [DPA/DESIGN-09];
  - 1.4.3 [DPA/DESIGN-03];
  - 1.4.11 [DPA/DESIGN-04];
  - 2.4.11 [DPA/DESIGN-07];
  - 2.5.7 [DPA/DESIGN-05];
  - 2.5.8 [DPA/DESIGN-02];
  - 3.3.8 [DPA/DESIGN-06];
  - the existence of the 2.2 SCs [DPA/DESIGN-01].

  SCs marked **(nf)** are real WCAG SCs whose text was **not fetched** in our research. Their pass criteria here are (judgment), and the security-privacy-engineer and QA should treat them as such.
- **Patterns:** question pages [DPA/DESIGN-12]; error summary [DPA/DESIGN-13]; content descriptions and 48 dp targets [DPA/DESIGN-10]; automated plus manual testing [DPA/DESIGN-14].
- **Tokens:** `docs/design/tokens.md`.

## How to use it

- Copy the relevant component blocks into the PR description and tick each box with evidence. Evidence is an axe run, a Playwright assertion, or a manual note with the device, browser and screen reader used.
- A box that cannot be ticked is a **Blocking** review finding, unless it is marked "(judgment)" and the PR says why it does not apply.
- The test level for each item is shown as **A** (axe-core, CI), **P** (Playwright assertion), **V** (Vitest) or **M** (manual: keyboard plus VoiceOver iOS and TalkBack Android, NFR-027b).

## 0. Every page

- [ ] **Unique `<title>`** that starts with the page question or name, then " – Racket Analytics". It is prefixed "Error: " when the page shows an error summary [DPA/DESIGN-13]. *P*
- [ ] **One `<h1>`.** On question pages the `<h1>` is the question, or the `<legend>` is the `<h1>` [DPA/DESIGN-12]. *A, M*
- [ ] **Landmarks:** `header`, `main` (one) and `footer`. A "Skip to main content" link is the first focusable element (SC 2.4.1, nf). *A*
- [ ] **`lang="en"`** on `<html>` (SC 3.1.1, nf). *A*
- [ ] **Reflow** at 320 CSS px with no horizontal scrolling (SC 1.4.10, nf; NFR-034). *P (viewport matrix)*
- [ ] **Text resize** to 200% browser zoom without loss of content. All type tokens are in rem (SC 1.4.4, nf). *M*
- [ ] **Orientation:** works in portrait and landscape (SC 1.3.4, nf). *M*
- [ ] **Focus order** follows the reading order. No positive `tabindex` (SC 2.4.3, nf). *M*
- [ ] **Focus visible:** the token ring on every interactive element (SC 2.4.7, nf; ring contrast proven in tokens.md, SC 1.4.11 ✓src). *P, M*
- [ ] **Focus not obscured:** a focused element is never entirely hidden by the sticky header, the sticky upload bar, banners or bottom sheets. Use `scroll-padding` tokens. **SC 2.4.11 ✓src** [DPA/DESIGN-07]; NFR-031. *P: tab through at 360×640 and assert each focused element's box intersects the unobscured viewport*
- [ ] **Colour is never the only signal** (SC 1.4.1, nf; NFR-034). *M: greyscale screenshot review*
- [ ] **Status messages** (upload state, "Link sent", save confirmations) are announced through a polite live region without moving focus (SC 4.1.3, nf). *M*
- [ ] **Consistent help:** the "Help" link is in the same place on every page (SC 3.2.6, new in 2.2; existence ✓src DESIGN-01, text nf). *M*
- [ ] **Timeouts:** none in Sprint 1 flows, except that the sign-in link expires after 15 min. The expiry is stated on the "Check your email" page, and a new link is one tap away (SC 2.2.1, nf). *M*

## 1. Button

- [ ] A native `<button>`, or `<a>` for navigation. Never a `div` with a click handler (SC 4.1.2, nf). *A*
- [ ] The accessible name equals or starts with the visible label (SC 2.5.3, nf). *A*
- [ ] Target ≥ 24×24 CSS px everywhere (**SC 2.5.8 ✓src**). Primary controls are ≥ 48×48 CSS px (`size.target-touch`) [DPA/DESIGN-10]; NFR-028. *P (target-size check)*
- [ ] Label contrast ≥ 4.5:1, and the boundary ≥ 3:1 against the page (**SC 1.4.3, 1.4.11 ✓src**), from proven token pairs only. *A + tokens proof*
- [ ] A "disabled" button that blocks progress is avoided. Use enabled "Continue" with validation and an error summary [DPA/DESIGN-13]. Where an option is unavailable, use `aria-disabled="true"`, keep it focusable, show the reason visibly, and keep full contrast (tokens.md §3 rule 4). *M*
- [ ] A busy state ("Sending…") keeps the button width, sets `aria-busy`, and prevents double submit. *V*

## 2. Link

- [ ] The link text says where it goes out of context ("Change format", not "Change"). Visually hidden text is allowed: `Change<span class="visually-hidden"> format</span>` (SC 2.4.4, nf). *A, M*
- [ ] Underlined by default. Colour alone does not mark a link (SC 1.4.1, nf). *M*
- [ ] Inline text links are exempt from 24 px (SC 2.5.8 exception ✓src). Standalone links, such as "Change" and "Back", meet 24 px, and 48 px on the check-answers page. *P*
- [ ] A link that opens a new tab says so ("opens in a new tab"). Avoid this in Sprint 1. *M*

## 3. Text input (email, nickname, date)

- [ ] Has a visible `<label for>`. A placeholder is never the label (SC 1.3.1, 3.3.2, nf). *A*
- [ ] Hint text is linked with `aria-describedby`. The nickname hint reads "Use a first name or nickname. Do not enter contact details" (FR-005). *A*
- [ ] Uses `autocomplete="email"` and `type="email"` for email (SC 1.3.5, nf). Paste is allowed, and nothing blocks password managers (**SC 3.3.8 ✓src** [DPA/DESIGN-06]). *A, P*
- [ ] Optional fields say "(optional)". There are no asterisks [DPA/DESIGN-12]. *M*
- [ ] Error state: the message sits above the input, starts with a visually hidden "Error:", is linked by `aria-describedby`, and the input gets `aria-invalid="true"` plus a 4 px `error` border [DPA/DESIGN-13]. *A, V*
- [ ] Redundant entry: answers known from the last match are pre-filled, and the user is never asked twice for the same thing in one flow (SC 3.3.7, new in 2.2; existence ✓src, text nf) [DPA/DESIGN-12]. *M*
- [ ] Text ≥ 16 px. Height is 48 px. *P*

## 4. Radio group and checkbox

- [ ] `<fieldset>` with `<legend>`. On a question page the legend is the `<h1>` question [DPA/DESIGN-12]. *A*
- [ ] The whole row (control plus label) is the target, ≥ 48 px high. *P*
- [ ] The control boundary uses `border-control` (≥ 3:1), and the checked state is shown by shape (a dot or tick), not colour only (**SC 1.4.11 ✓src**). *tokens proof, M*
- [ ] Arrow keys move within a radio group, Space selects, and Tab leaves the group (native behaviour; no custom widget). *M*
- [ ] An unavailable option (rally scoring) follows the button rule for `aria-disabled`, with its reason in the hint (FR-043). *A, M*

## 5. Error summary [DPA/DESIGN-13]

- [ ] Shown at the top of `main` after a failed submit, with the heading "There is a problem". *P*
- [ ] It receives focus on render (`tabindex="-1"`, `role="alert"` is not needed when focus moves). *P*
- [ ] Each entry is a link to its field's input (the first input of a group). The wording is the same in the summary and at the field. *P*
- [ ] The page `<title>` is prefixed with "Error: ". *P*
- [ ] The border uses the `error` token, 4 px. *tokens proof*

## 6. Progress (upload)

- [ ] A native `<progress>`, or `role="progressbar"` with `aria-valuenow`, `aria-valuemin`, `aria-valuemax` and `aria-valuetext` ("64%, 1.9 GB of 3.0 GB"). *A, V*
- [ ] The percentage and MB are also visible as text. A bar is never the only signal (FR-022). *P*
- [ ] Fill vs track ≥ 3:1, and track outline vs page ≥ 3:1 (**SC 1.4.11 ✓src**). *tokens proof*
- [ ] **Announcements are throttled.** State changes ("Paused: waiting for connection", "Uploading", "Upload complete") are announced politely. The percentage is announced at most every 10% (judgment), never on each tick. *M*
- [ ] No animation under `prefers-reduced-motion`. *M*

## 7. Banner and notification (info, warning, provisional, resume)

- [ ] A `region` with an accessible name, or `role="status"` when it appears dynamically. It never steals focus unless it needs a decision. *A, M*
- [ ] Body and link contrast are proven on `info-surface` / `warning-surface`. *tokens proof*
- [ ] A dismiss control is ≥ 24 px with the name "Dismiss <what>". *P*
- [ ] Banners do not cover focused content (SC 2.4.11 ✓src). *P*

## 8. Disclosure (expandable help, for example "How to set 60 fps on my phone")

- [ ] A native `<details>`/`<summary>`, or a button with `aria-expanded` and `aria-controls`. *A*
- [ ] The summary text describes the content. The target is ≥ 48 px high. *P*

## 9. Image and illustration (capture guide)

- [ ] Informative illustrations have alt text that states the **purpose**, unique within the list and without "image of" (NFR-035) [DPA/DESIGN-10]. *A, M*
- [ ] Decorative images use `alt=""` / `aria-hidden="true"`. *A*
- [ ] Graphics that convey information have ≥ 3:1 for the parts needed to understand them (**SC 1.4.11 ✓src**). *M*

## 10. Video (capture-guide video)

- [ ] Captions are on by default. They are synchronised and include meaningful non-speech audio (**SC 1.2.2 ✓src** [DPA/DESIGN-08]). *M*
- [ ] The checklist text on the same page is the media alternative, and the page says so ("Everything in this video is in the checklist above") (**SC 1.2.3 ✓src** [DPA/DESIGN-09]); NFR-033. *M*
- [ ] No autoplay with sound. Native controls or controls that are keyboard operable and ≥ 24 px (SC 2.1.1, nf). *M*
- [ ] Caption text over video sits on the `scrim` token (7.00:1 worst case). *tokens proof*

## 11. Sign-in (authentication)

- [ ] No password, puzzle, CAPTCHA or transcription step (**SC 3.3.8 ✓src** [DPA/DESIGN-06]); NFR-032. *P, M*
- [ ] The email field allows paste and autofill. *P*
- [ ] The "Check your email" page names the address the link was sent to, the 15-minute expiry, and how to get a new link. *P*

## 12. Dragging and gestures

- [ ] No Sprint 1 flow requires dragging, swiping, pinching or multipoint gestures (**SC 2.5.7 ✓src**; SC 2.5.1, nf); NFR-030. Upload uses a file picker button. Drag-and-drop on desktop is an extra path, never the only one. *P (taps-and-keys journey)*

## 13. Sign-off record (per design doc or PR)

| Screen or component | Reviewer | Date | Result | Evidence |
|---|---|---|---|---|
| Tokens v0.1 (contrast) | principal-designer | 2026-10-03 | 55/55 pairs pass | `python3 docs/design/tools/contrast_check.py` → exit 0 |
| Sprint 1 flows (sign-in, first run, capture guide, setup, upload) | principal-designer | 2026-10-03 | Design-level checklist applied per screen in `flows-sprint-01.md` §8 | `flows-sprint-01.md` |
| ST-010 PWA shell | principal-designer | at PR | pending | axe run + manual pass |
