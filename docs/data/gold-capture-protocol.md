# Capture protocol for team-recorded gold and fixture footage (ST-040)

Owner: senior-ml-cv-engineer. Reviewers: security-privacy-engineer (consent, threat note R8), pickleball-domain-coach (court and play), senior-qa-engineer (testability). Status on 2026-10-06: **Proposed; no footage is collected under it yet.**

Sources: FR-151, OQ-05 and OQ-06 as decided in ADR 0023 (jurisdictions **US and AU**; until the legal pass, gold and fixture footage only from team-recorded matches with written consent from everyone filmed), NFR-070 (legal review before real users), spec §8 (no face recognition), QD §8 and QD-GD-04, brainstorm-engineering §5.2 item 7 and §5.3, `gold-label-schema.md`, `phone-fixtures.md` §3 (same recording rules for phones).

> **Not legal advice.** The consent wording in §3 is a team draft. The legal review (NFR-070) must check it for the US (including state privacy laws relevant to video and biometrics) and for AU (Privacy Act 1988, APPs) before any footage is recorded under it (ADR 0023). This file does not claim that it meets either law.

## 1. What may be recorded, and when

| Footage | Allowed now? | Condition |
|---|---|---|
| Synthetic clips (FFmpeg test sources) | Yes | `consent_status: synthetic`, `shows_people: false` (the check refuses people in a synthetic set) |
| Empty court (nobody in frame) | Yes (ADR 0023, OQ-06) | `shows_people: false`; stop or crop if anyone walks into frame |
| Team members playing, everyone filmed has signed §3 | **Only after the legal review signs off the form** (NFR-070) | `consent_status: consented`; per clip `consent_record` and `consent_jurisdiction` (US or AU) |
| Real users' matches, public video, bystanders | **No** | Needs `TrainingConsent` (FR-009, context map R9) and the legal review; the check refuses any other `consent_status` |
| SportsMOT or other CC BY-NC sets | Evaluation only | DOM/CV-09; never in a training split |

## 2. Recording rules

1. **People in frame:** only signed participants. If a bystander, a child or a person on a neighbouring court is recognisable, discard the clip (do not blur and keep: the raw file would still exist).
2. **Venue split (QD-GD-04):** give each venue a code (`VEN-<country>-<n>`, e.g. `VEN-AU-01`; no street address in the manifest). Decide the venue's split (`train`, `val`, `test`) **before** labelling, and keep every clip of a venue in that split. A vision set needs ≥ 3 held-out (`test`) venues with clips; the check fails otherwise.
3. **Spread (testing-strategy §6, judgment):** across venues vary light (outdoor sun, backlight, indoor), camera height (tripod at ~1.5 m and elevated if possible), fence occlusion and courts with neighbouring play (multi-court audio, QD-GD-07).
4. **Framing (brainstorm-engineering §5.2 item 7, judgment):** the whole court with both NVZ lines and both baselines in frame; far baseline width ≥ 25% of the frame width.
5. **Settings:** 1080p at 60 fps where the phone offers it (capture guide); note the menu path. Copy originals by cable or "original quality" export; never via messaging apps (they re-encode).
6. **Clip length:** fixture clips ≤ 60 s (QD-GD-07); gold clips per match or per game. A committed clip over 15 MiB goes to Git LFS or the object store (SRE decision, P6).
7. **Record per clip** (a row in the capture sheet, which becomes the manifest's `clips`): file, venue code, split, date, phone model and setting, who is in frame (slot letters only, e.g. `A1 A2 B1 B2`), consent record IDs, jurisdiction.

## 3. Consent form (draft for the legal review)

One form per person filmed, signed before recording, kept by the team lead outside the repository (the manifest stores only the form ID, e.g. `CF-2026-001`, never the person's name).

> **Video recording consent: racket-analytics team footage**
>
> 1. I agree to be filmed playing pickleball on [date] at [venue code] by the racket-analytics team.
> 2. The video and labels made from it (rally boundaries, hits, bounces, shot types, outcomes, and a player slot such as "A1") will be used to **evaluate and train** the team's video analysis models. Labels do not contain my name.
> 3. No face recognition is used; I am identified only by a per-match slot (spec §8).
> 4. The video is stored in the team's private storage and gold-set repository, which only team members can read. It is not published.
> 5. I can withdraw my consent at any time by contacting [team contact]. After withdrawal my clips are left out of **every new version** of the gold sets; frozen versions already used in evaluation reports are deleted or kept only as allowed by the retention decision (ADR 0006 follow-up, open). Effects of withdrawal on models already trained are an open legal question (dataset context canvas, "Open questions").
> 6. I am 18 or older. (Minors are not filmed under this protocol.)
> 7. Jurisdiction where I am filmed: ☐ United States, state: ____ ☐ Australia, state/territory: ____
>
> Name, signature, date. Form ID: CF-____-___

Open points for the legal review (NFR-070), listed so they are not decided by this draft: biometric-law reach of pose keypoints in US states; APP 3 / APP 5 notice wording for AU; whether training use needs a separate tick box from evaluation use; retention period after withdrawal.

## 4. From footage to a checked gold set

1. Lay out `fixtures/gold/<set-id>/clips/…`, label with Full Tag (FR-150) into `labels/<clip>.json`; a double-labelled clip (≥ 20% of a vision set) gets `labels/<clip>.second.json` from a second labeller.
2. Compute κ per facet on the double-labelled clips and fill `agreement`; admit a shot facet only at κ ≥ 0.7 on ≥ 300 shots (QD-TX-03). Labels may carry only admitted facets.
3. Write `manifest.json` (fields in `gold-label-schema.md` §2), with role IDs for labellers.
4. Run `cd backend && uv run racket-manifest-check ../fixtures/gold/<set-id>`; it must print `OK … gold set (<purpose>)`. CI runs the same check with the merge-base manifest.
5. Freeze: from then on any file change needs a version bump, and for a set used in an eval report an ADR (FR-151, NFR-078).

## Changelog

| Date | Who | Change |
|---|---|---|
| 2026-10-06 | senior-ml-cv-engineer | Written with ST-040 (US and AU consent per ADR 0023; legal review NFR-070 still required) |
