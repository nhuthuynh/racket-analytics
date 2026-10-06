// QA-RV1-07 / SRE-S2-05: the Playwright "chromium" project runs in Google Chrome on CI, because
// Playwright's own Chromium has no H.264 decoder and every accepted upload is H.264/HEVC
// (blockers.md 2026-10-06; NFR-024 names desktop Chrome).
import { describe, expect, it } from 'vitest';
import { chromiumChannel } from '../../e2e/helpers/browser-channel';

describe('chromiumChannel', () => {
  it('uses the bundled Chromium locally when nothing is set (the sandbox has no Chrome)', () => {
    expect(chromiumChannel({})).toBeUndefined();
  });

  it('uses Google Chrome on CI, which decodes the H.264 original', () => {
    expect(chromiumChannel({ CI: 'true' })).toBe('chrome');
  });

  it('lets PW_CHROMIUM_CHANNEL choose, and an empty value means the bundled Chromium', () => {
    expect(chromiumChannel({ PW_CHROMIUM_CHANNEL: 'chrome' })).toBe('chrome');
    expect(chromiumChannel({ CI: 'true', PW_CHROMIUM_CHANNEL: '' })).toBeUndefined();
    expect(chromiumChannel({ CI: 'true', PW_CHROMIUM_CHANNEL: 'msedge' })).toBe('msedge');
  });

  it('refuses a channel name it does not know, instead of silently testing another browser', () => {
    expect(() => chromiumChannel({ PW_CHROMIUM_CHANNEL: 'chrome-typo' })).toThrow(/PW_CHROMIUM_CHANNEL/);
  });
});
