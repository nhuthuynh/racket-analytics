// Which browser the Playwright "chromium" project launches (QA-RV1-07 / SRE-S2-05).
// Playwright's own Chromium has no H.264 decoder, and every accepted upload is H.264/HEVC, so
// E2E-02-04, G02-06 (c) and the V-01 axe check on the real video can only run in a browser that
// decodes it. CI uses Google Chrome (installed on the GitHub runner image; NFR-024 names desktop
// Chrome). Locally the sandbox has no Chrome, so the bundled Chromium stays the default there.
// PW_CHROMIUM_CHANNEL overrides both; an empty value means the bundled Chromium.
const KNOWN = new Set(['chrome', 'chrome-beta', 'chrome-dev', 'msedge', 'msedge-beta', 'msedge-dev']);

export function chromiumChannel(env: Record<string, string | undefined>): string | undefined {
  const asked = env.PW_CHROMIUM_CHANNEL ?? (env.CI ? 'chrome' : '');
  if (asked === '') return undefined;
  if (!KNOWN.has(asked)) {
    throw new Error(`PW_CHROMIUM_CHANNEL=${asked} is not a Playwright channel (${[...KNOWN].join(', ')})`);
  }
  return asked;
}
