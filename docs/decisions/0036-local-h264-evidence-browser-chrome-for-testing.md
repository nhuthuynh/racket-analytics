# 0036. Local goal evidence runs in Chrome for Testing, a browser that decodes H.264

- **Status:** Accepted (engineering-manager, under ADR 0030's decision rule; the PO is told, not asked, because this keeps the PO standing rule unchanged)
- **Date:** 2026-10-06
- **Deciders:** engineering-manager
- **Consulted:** senior-qa-engineer (owner of `web/playwright.config.ts` and `e2e/helpers/browser-channel.ts`, decision-log 2026-10-06), sre-devops-engineer (evidence environment)
- **Related:** SRE-S2-05, QA-RV1-07, QA-RV2-07 (review rounds 1 and 2), blockers.md rows 2026-10-06 (QA and the QA update), goal-scorecard G02-05, G02-06 (c), G02-10 (V family), NFR-014, NFR-024, ADR 0029, ADR 0030, ADR 0033

## Context and problem statement

Every accepted upload and the 60 s fixture are H.264/AAC. Playwright's bundled Chromium (`/opt/pw-browsers/chromium-1194`) has no H.264 decoder, so on the local stack E2E-02-04, `seek-first-frame (real video link)` and the V-01 axe check on the real video fail closed. Since `f737e00` the CI `chromium` project launches Google Chrome (`channel: 'chrome'`), but the PO standing rule asks for the goal to be shown on a **live local stack**. The QA blocker asked the EM and the PO to either accept CI Chrome as this evidence or provide an H.264-capable browser locally. `dl.google.com` (Google Chrome .deb) is refused by the egress proxy.

## Decision drivers

- PO standing rule: goal metrics are measured live on the local stack; a CI-only number would be an exception the PO has not granted.
- NFR-024 names desktop Chrome as a target client; the evidence browser should be Chrome, not a stand-in.
- No test or product change: the fix belongs in the environment, not in the specs (no test weakened, no TCR).
- Reproducible: a pinned build with a recorded checksum.

## Considered options

1. **Chrome for Testing (CfT) 141.0.7390.54 placed at `/opt/google/chrome/`, where Playwright's `chrome` channel looks; evidence runs set `PW_CHROMIUM_CHANNEL=chrome`** (chosen).
   - Good: Google's own Chrome build for automation, same major (141) as the bundled Chromium 1194; it decodes H.264 and AAC; reachable from the sandbox (`storage.googleapis.com/chrome-for-testing-public` → 200); the QA helper already accepts `PW_CHROMIUM_CHANNEL=chrome`, so no repository code changes.
   - Bad: an install outside the repository (like `/opt/pw-browsers`); it must be re-provisioned on a fresh sandbox. Mitigation: the steps and the sha256 below; sre-devops-engineer scripts them (routed).
2. **Ask the PO to accept CI Chrome runs as the G02-05 / G02-06 (c) / V-01 evidence.**
   - Good: no local install.
   - Bad: an exception to the standing rule; CI runs are not on the verifier's isolated stack at one recorded head; the PO decision would sit open until the sprint review (2026-11-13).
3. **Serve a VP9 rendition locally** (transcode on upload, or a stand-in). Bad: a product change outside the sprint plan, and it would not test the original the user uploaded. The VP9 stand-in stays supporting evidence only.
4. **WebKit locally.** Bad: Playwright WebKit runs only on CI here (sprint brief), and iOS Safari is not desktop Chrome.

## Decision outcome

Option 1. Option 2 is not needed and is withdrawn from the PO list.

Install (done 2026-10-06 by the engineering-manager; to be scripted by sre-devops-engineer as `scripts/dev-chrome.sh`):

```bash
curl -sS -o chrome.zip https://storage.googleapis.com/chrome-for-testing-public/141.0.7390.54/linux64/chrome-linux64.zip
sha256sum chrome.zip   # 5023ec2b8995b74caa5de0e22d5e30f871c3ecce67a6e52d3c9f9dfed423ed01
python3 -c "import zipfile; zipfile.ZipFile('chrome.zip').extractall('.')"
mkdir -p /opt/google && mv chrome-linux64 /opt/google/chrome && chmod +x /opt/google/chrome/chrome
/opt/google/chrome/chrome --version   # Google Chrome for Testing 141.0.7390.54
```

The scorecard methods for G02-05, G02-06 and G02-10 add `PW_CHROMIUM_CHANNEL=chrome` (decision-log row 2026-10-06, EM). A run without it, or with `/opt/google/chrome/chrome` missing, is not the goal evidence for these rows (fail closed: Playwright stops with "Chromium distribution 'chrome' is not found").

### Consequences

- Good: E2E-02-04, G02-06 (c) and the V-01 axe check on the real video can be measured on the local stack. EM dry-run (native https stack, head `48e1e71`): the full suite gives `93 passed, 0 failed, 6 skipped`, rate 1.0, every required id present, and `seek-first-frame` p95 740.1 ms, n=40, on the reference profile (decision-log row 2026-10-06).
- Good: CI (Google Chrome on the runner) and local (CfT) now run the same browser family.
- Bad: the bundled Chromium stays the default for developers' quick runs, so a developer can still see the two H.264 failures locally without the variable. That is the documented behaviour of `browser-channel.ts`.
- Licence note (judgment): CfT is distributed by Google for testing; it is used only inside the evidence environment and never shipped with the product.

### Confirmation

- Probe: `canPlayType('video/mp4; codecs="avc1.640028"')` → `""` in bundled Chromium 1194, `"probably"` in CfT 141.0.7390.54 (AAC likewise).
- `PW_CHROMIUM_CHANNEL=chrome … playwright test e2e/sprint-02/rally-video.spec.ts e2e/sprint-02/timing.spec.ts` → `7 passed`, including E2E-02-04 and `seek-first-frame on the reference profile (real video link)`.
- The independent verifier repeats the G02-05/06/10 methods with the variable on its own Compose stack.
