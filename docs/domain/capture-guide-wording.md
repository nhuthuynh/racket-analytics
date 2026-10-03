# Capture guide wording (draft for FR-020 / ST-015)

- **Status:** `draft`, 2026-10-03 (pickleball-domain-coach). The sign-off is due on Sprint 1 D3 (sprint-01 §4) after the design review with the principal-designer.
- **Requirement:** FR-020 says the checklist has no more than 6 illustrated items, each with alt text. A captioned 30-60 s video supplements it, and the checklist is the video's text alternative. Expandable help covers 60 fps on iPhone and Android. The domain coach signs off the wording.
- **Related:** spec §2 (one phone on a tripod, 1080p60), spec §8 (backlight); DES FR-UX-10..12; NFR-033, NFR-035; `docs/design/flows-sprint-01.md` screen G-01.
- **Evidence posture:** this is **filming advice, not a pickleball rule**. No item depends on the rulebook, so nothing here waits for OQ-01. The advice comes from the spec (§2, §8) and the design brainstorm. Where the wording goes beyond them, it is marked **(judgment)**. **No item is sourced from a coaching or filming authority**: none is verified in our research [DOM G2].
- **Plain-language rules (judgment):**
  - each item is one instruction in the imperative, ≤ 12 words;
  - then one "why" line in terms of what the player gets;
  - no jargon. Use "baseline" and "court lines", not "homography" or "calibration".

## 1. Checklist (6 items)

| # | Instruction (heading) | Why (one line) | Illustration alt text (purpose, unique) | Source |
|---|---|---|---|---|
| 1 | Put your phone on a tripod behind one baseline. | From behind the court we can see every rally from serve to the last shot. | Phone on a tripod standing behind the middle of one baseline, facing the net. | spec §2; FR-020 |
| 2 | Raise it as high as you safely can. | Height shows the far side of the court and the gap between players. | Tripod extended to head height or above, with the whole far court visible over the net. | spec §2; FR-020; height benefit is (judgment) |
| 3 | Turn the phone sideways (landscape). | The whole court fits across the screen. | Phone held sideways on the tripod mount. | FR-020 |
| 4 | Record in 1080p at 60 frames per second. | Fast shots stay sharp enough to see later. | Camera settings screen with "1080p" and "60 fps" selected. | spec §2; FR-020. The "why" is (judgment) until SPIKE-04/R2 data |
| 5 | Check that all four court corners are on screen. | If a corner is cut off, parts of the court cannot be analysed. | Phone screen showing the whole court, with the four corners marked. | FR-020 ("whole court in frame"); "four corners" is (judgment), coach wording |
| 6 | Avoid filming towards the sun. | Bright light behind the court hides the ball and the players. | Two small pictures: the sun behind the far court crossed out; the sun behind the camera ticked. | spec §8 (backlight); FR-020 |

**Safety line (shown under item 2, judgment, escalated to PM for wording):** "Keep the tripod and its legs off the court and out of walkways. Never climb a fence or a chair to raise it."

**Why the safety line:** "as high as you safely can" invites people to improvise. The coach role escalates any advice that could cause injury (agent definition). This is not a rule claim.

## 2. Notes under the checklist (not counted in the 6 items)

- **Battery and storage (judgment):** "A 90-minute match at 1080p 60 fps can use several gigabytes. Charge your phone and free up space first."
  - The figure is withheld until ST-025 measures MB per minute on ≥ 5 phone models (R-05).
  - Until then, say "several gigabytes" only.
- **People you film (escalated, not drafted here):** whether to tell other players they are being filmed is a privacy and consent matter (OQ-06; spec §8). Its wording belongs to the PM and the security-privacy-engineer. The coach recommends a short courtesy line, but that line is not a domain fact.
- **Video text alternative line** (NFR-033, [DPA/DESIGN-09]): "Everything in the video is in the checklist above."

## 3. Expandable help: "How to record at 60 fps on my phone"

**UNVERIFIED.** The menu paths below are background knowledge. They have not been checked on devices, and phone makers change menus between OS versions. They must be checked on the ST-025 reference phones (≥ 5 models) by the senior-ml-cv-engineer, and against OQ-17 (reference devices), before ST-015 merges. Until then, the generic text is shipped and the device-specific lines stay hidden.

- **Generic (ships):** "Open your camera's video settings and choose 1080p (also called Full HD) at 60 fps. If you can't find 60 fps, record at 30 fps: you can still tag your match, but some later results may be less accurate."
- **iPhone (UNVERIFIED, hidden until checked):** "Settings > Camera > Record Video > 1080p HD at 60 fps."
- **Android (UNVERIFIED, hidden until checked):** "In the Camera app, open Video, then the settings or resolution menu, and pick 1080p and 60 fps. The names differ between phone makers."

The 30 fps sentence is consistent with FR-025 / ST-019, which says the report explains consequences and never blocks. "Some later results may be less accurate" avoids promising anything about R1, which has no automatic analysis (ADR 0002).

## 4. Guide video script (30-60 s; captions on by default, [DPA/DESIGN-08])

| Time | Picture | Caption (= spoken words) |
|---|---|---|
| 0-5 s | Empty court from behind a baseline | "Here's how to film a match we can analyse." |
| 5-15 s | Tripod set up behind the middle of the baseline and raised | "Put your phone on a tripod behind one baseline, as high as you safely can." |
| 15-25 s | Phone turned to landscape; settings show 1080p 60 | "Turn it sideways and record in 1080p at 60 frames per second." |
| 25-35 s | Screen shows the whole court with four corners marked | "Check that all four court corners are on screen." |
| 35-45 s | Sun behind the far court crossed out; sun behind the camera ticked | "Avoid filming towards the sun." |
| 45-50 s | Recording starts | "Start recording before the first serve. That's it." |

The video shows only an empty court or consenting team members (OQ-06). [Non-speech audio: none; background music is not used, so captions carry all the information.]

## 5. Sign-off

| Date | Who | Status | Notes |
|---|---|---|---|
| 2026-10-03 | pickleball-domain-coach | `draft` | Written. Waiting for the design review (principal-designer) and the ST-025 device check for §3 |
| D3 Sprint 1 | pickleball-domain-coach | `signed-off` (planned) | — |
