# 0028. Phone-browser uploads: "resume on return", no background-upload promise (SPIKE-06, partial data)

- **Status:** Proposed (the real-device half of SPIKE-06 is still to run; see "Open")
- **Date:** 2026-10-05
- **Deciders:** senior-frontend-engineer (author); principal-engineer, principal-designer (reviewers); human product owner for OQ-18 (native wrapper or not)
- **Consulted:** senior-backend-engineer (tus server, ADR 0011), security-privacy-engineer (no URL or file data on the device)
- **Related:** SPIKE-06, OQ-18, FR-022, NFR-016, NFR-026, ST-017, flows-sprint-01 U-01/U-04 and D-7, ADR 0011, ADR 0019, api-sprint-01 §5.2 and §6

## Context and problem statement

Players upload 1-9 GB phone videos from a mobile browser. SPIKE-06 asks how often an 8 GB tus upload completes on current iOS Safari and Android Chrome with the screen locked, the tab in the background, and the tab closed and reopened, and whether that justifies a native wrapper earlier than planned (OQ-18). U-01's "leaving" copy depends on the answer (flows D-7).

The sandbox where this spike ran has no phones, no iOS Safari and no Android Chrome, and its Playwright WebKit build is missing (`browserType.launch: Executable doesn't exist at /opt/pw-browsers/webkit-2215/pw_run.sh`). So this ADR records (1) what the shipped client does, (2) desktop-engine proxy measurements against the local stack, and (3) the protocol for the device runs. It does **not** contain phone completion rates.

## Decision drivers

- FR-022: survive a dropped connection and a closed tab; never start over.
- OQ-18 recommendation (accepted, ADR 0023): honest "resume on return" copy in R1.
- FR-011 / NFR-067: sign-out leaves nothing on the device, so the resume state cannot live in browser storage.
- NFR-016: chunk size adapts between 5 and 50 MB.

## Considered options

1. **Resume on return from server state** (chosen): the server's match read model holds the upload offset, length, expiry, file name, last-modified time and a SHA-256 of the first MiB; the player re-picks the same file and the client continues with HEAD then PATCH. Copy promises nothing after the tab closes.
2. **Background upload in a service worker** (Background Fetch API): would let uploads continue with the tab closed where supported.
3. **Native wrapper now** (Expo or similar with OS background transfer).
4. **Do nothing** (Sprint 0 client: URL kept in localStorage by tus-js-client).

## Decision outcome

Chosen option 1 for R1, pending the device data. Option 4 is ruled out by FR-011 (sign-out clears storage, so the stored URL is lost) and by the "no upload URL on the device" rule. Option 2 is not chosen (judgment, not verified in this spike): Background Fetch is a download-oriented API with limited browser support, and it would need its own tus-compatible chunking. Option 3 stays the OQ-18 question for the PO once the device runs exist.

## Evidence

### What the shipped client does (ST-017, commit `722f0c5`)

- Server state is the resume source: `upload.resume_url`, `offset`, `length`, `expires_at`, `file_name`, `file_last_modified_ms`, `head_sha256` (api-sprint-01 §5.2). Nothing is stored in the browser (`storeFingerprintForResuming: false`).
- Offline → pause (abort without terminate); online → HEAD then PATCH from the server offset.
- Every PATCH has `Upload-Checksum: sha256`; a damaged chunk (460) is re-sent from the server offset.
- Chunk size starts at the policy minimum and is set after each chunk to about 10 s at the measured rate, within the policy bounds.
- Unit evidence: `pnpm test:unit` → 28 files, 231 tests passed (`tus-transfer.test.ts`, `match-upload.test.tsx`).

### Proxy measurements (desktop Chromium 1194 headless, local stack, 2026-10-05)

Stack: API, worker, Postgres 16, SeaweedFS and Next.js production build on one 4-CPU sandbox; dev chunk bounds 5-8 MiB. File: the synthetic 60 s clip padded with an ISO-BMFF `free` box to 1 GiB (`paddedClip` from `web/e2e/helpers/sprint-01.ts`). Command: a scratch Playwright spec (`SPIKE_MB=1024 PW_PROJECTS=chromium npx playwright test e2e/zz-spike06.spec.ts`, not committed) → `3 passed (2.3m)`.

| Scenario | Result |
|---|---|
| S1 foreground, uninterrupted | 1024 MiB in 25.6 s (40.0 MiB/s); "Video received" after the probe |
| S2 another tab brought to front | completed in 21.7 s; **but** `document.visibilityState` stayed `visible` in headless Chromium, so this does not measure background throttling |
| S3 tab closed at 30% (PATCH slowed by 150 ms to make 30% observable), reopened | M-01 banner "Your upload of 'Singles · 5 Oct 2026' is 30% done."; after choosing the same file the remaining 70% finished in 15.8 s and the probe accepted the file |
| E2E-01-02 shape (48 MiB, offline 10 s at ≥ 40%, PATCH slowed 400 ms) | Paused: waiting for connection → Uploading → Video received; `1 passed (26.2s)` |

These show that the resume path and the checksum path work end to end in a desktop engine. They say nothing about iOS Safari or Android Chrome behaviour with the screen locked or the tab backgrounded.

## Consequences

- U-01 keeps the flows copy: "You can use other pages while this tab stays open. If you close it, you can resume later from this page by choosing the same video." (E2E "Upload page wording" passes.) D-7 stays open until the device runs.
- Large-file hint "Keep your screen on until the upload finishes." stays (FR-UX-32).
- Good: works after sign-out and on another device; no file or URL data on the device. Bad: the player must re-pick the file after a closed tab.

## Open (blocks status Accepted)

Device protocol, to be run by a person with the devices (OQ-17 browser matrix), ≥ 3 runs each, 8 GB file over Wi-Fi, recording completion (yes/no), bytes at interruption, time to resume, and whether the page reloaded:

1. iOS Safari (current and previous major) and Android Chrome (current): foreground, screen on.
2. Same, screen locked after 10% for 5 minutes, then unlocked.
3. Same, tab backgrounded (switch to another app) for 5 minutes.
4. Same, tab closed at about 50% and reopened within 24 h: resume by choosing the same file.

Decision rule for OQ-18 (proposal): if case 4 completes in ≥ 95% of runs and cases 2-3 resume without user action in ≥ 80%, keep the PWA for R1; otherwise put the native-wrapper option to the PO with this data. Logged as a blocker in `docs/sprints/01/blockers.md`.
