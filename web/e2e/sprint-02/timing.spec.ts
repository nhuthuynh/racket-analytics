// ST-039 slice 2 (G02-06; NFR-011, NFR-012 (a)(b), NFR-014): browser timings on the live stack.
// Each sample is attached as `timing-<metric>` with the JSON body {"ms": n};
// scripts/measure/pw_timings.py turns them into p95 values. The scorecard runs this file with
// --repeat-each=20 (G02-06 §4), so every metric gets well over 20 samples.
//
// All times are taken inside the page with the event's own high-resolution timestamp as the
// start (the pointerdown of the tap, or the keydown), and the first animation frame after the
// DOM change as the end, so Playwright's own round trips are not counted:
//   tag-optimistic           ending tap -> the score call on T-01 shows the new score (a)
//   tap-feedback             any tap on the tagging screen -> its visual state changes (b)
//   seek-first-frame         "Watch rally n" -> first video frame presented at the rally, on the
//                            reference profile 9/1.5 Mbit/s and 4x CPU (OQ-17) (c)
//   score-sheet-interactive  warm navigation to S-01 -> its rally controls are hydrated (d)
import { expect, test, type Locator, type Page, type TestInfo } from '@playwright/test';
import {
  MY_SIDE,
  OTHER_SIDE,
  decodableStandIn,
  decodesH264,
  openTagging,
  rangeResponse,
  receivedMatch,
  sheetOf,
  tagJourneyByApi,
} from '../helpers/sprint-02';

test.use({ serviceWorkers: 'block' }); // the stand-in test routes the media request (TCR 2026-10-05)

declare global {
  interface Window {
    __timings?: Record<string, Promise<number>>;
  }
}

async function attach(testInfo: TestInfo, metric: string, ms: number): Promise<void> {
  expect(Number.isFinite(ms) && ms >= 0, `${metric} sample ${ms}`).toBe(true);
  await testInfo.attach(`timing-${metric}`, { body: JSON.stringify({ ms }), contentType: 'application/json' });
}

/**
 * Arm a measurement named ``key``: from the next pointerdown/keydown anywhere in the page to the
 * first animation frame after ``read(root)`` differs from its value now. ``rootSelector`` is a
 * CSS selector for the element to watch (attributes, text and children, whole subtree).
 */
async function arm(page: Page, key: string, rootSelector: string, what: 'text' | 'state'): Promise<void> {
  await page.evaluate(
    ({ key, rootSelector, what }) => {
      const root = document.querySelector(rootSelector);
      if (!root) throw new Error(`no element ${rootSelector}`);
      const read = (): string =>
        what === 'text'
          ? (root.textContent ?? '')
          : [root, ...root.querySelectorAll('*')].map((e) => `${e.getAttribute('aria-pressed')}|${e.className}`).join(';');
      const before = read();
      window.__timings ??= {};
      window.__timings[key] = new Promise<number>((resolve) => {
        let t0: number | null = null;
        const start = (e: Event): void => {
          if (t0 === null) t0 = e.timeStamp;
        };
        document.addEventListener('pointerdown', start, { capture: true, once: true });
        document.addEventListener('keydown', start, { capture: true, once: true });
        const observer = new MutationObserver(() => {
          if (t0 === null || read() === before) return;
          observer.disconnect();
          const began = t0;
          requestAnimationFrame(() => resolve(performance.now() - began));
        });
        observer.observe(root, { subtree: true, childList: true, characterData: true, attributes: true });
      });
    },
    { key, rootSelector, what },
  );
}

async function result(page: Page, key: string): Promise<number> {
  return page.evaluate(
    (k) =>
      Promise.race([
        window.__timings?.[k] ?? Promise.reject(new Error(`not armed: ${k}`)),
        new Promise<number>((_, reject) => setTimeout(() => reject(new Error(`no change seen for ${k} in 10 s`)), 10_000)),
      ]),
    key,
  );
}

const SCORE = '[role="group"][aria-label="Score"]';
const BAR = '[role="group"][aria-label="Tag the rally"]';

async function timedTap(page: Page, testInfo: TestInfo, button: Locator, label: string): Promise<void> {
  await arm(page, label, BAR, 'state');
  await button.click();
  await attach(testInfo, 'tap-feedback', await result(page, label));
}

test.describe('@story-ST-039 Browser timings (G02-06)', () => {
  test('tag-optimistic and tap-feedback on Quick Tag', async ({ page }, testInfo) => {
    test.slow();
    const matchId = await receivedMatch(page, 'Timing tags');
    await openTagging(page, matchId);
    const bar = page.getByRole('group', { name: 'Tag the rally' });

    // 8 rallies, never a replay, so every ending changes the call; winners alternate so the
    // game never ends (side-out scoring: only the serving side scores).
    for (let n = 1; n <= 8; n += 1) {
      const winner = n % 2 === 1 ? MY_SIDE : OTHER_SIDE;
      await timedTap(page, testInfo, bar.getByRole('button', { name: 'Rally start' }), `start-${n}`);
      await page.waitForTimeout(5); // rally times come from the page clock without a video
      await timedTap(page, testInfo, bar.getByRole('button', { name: 'Rally end' }), `end-${n}`);
      await timedTap(page, testInfo, bar.getByRole('button', { name: winner }), `side-${n}`);

      await arm(page, `call-${n}`, `${SCORE} .quick-tag__call`, 'text');
      await arm(page, `score-${n}`, SCORE, 'text');
      await bar.getByRole('button', { name: 'Winner', exact: true }).click();
      await attach(testInfo, 'tag-optimistic', await result(page, `call-${n}`));
      await attach(testInfo, 'tap-feedback', await result(page, `score-${n}`));
      await expect(page.getByRole('status').filter({ hasText: new RegExp(`^Rally ${n}:`) }).first()).toBeVisible();
    }
    expect((await sheetOf(page, matchId)).rows).toHaveLength(8); // every optimistic tag was saved
  });

  test('score-sheet-interactive, warm', async ({ page }, testInfo) => {
    const matchId = await receivedMatch(page, 'Timing sheet');
    await tagJourneyByApi(page, matchId);
    // Record, from navigation start, the first frame in which a rally control is hydrated
    // (React has attached its handlers) and visible.
    await page.addInitScript(() => {
      const w = window as unknown as { __interactiveAt?: number };
      const tick = (): void => {
        const button = [...document.querySelectorAll('main table button, main button')].find(
          (b) => (b as HTMLElement).offsetParent !== null && Object.keys(b).some((k) => k.startsWith('__reactProps$')),
        );
        if (button && document.querySelector('main table')) w.__interactiveAt = performance.now();
        else requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    });
    await page.goto(`/matches/${matchId}/sheet`); // cold: compiles nothing, fills caches; not measured
    await expect(page.getByRole('table', { name: 'Game 1' })).toBeVisible();
    for (let i = 0; i < 3; i += 1) {
      await page.goto(`/matches/${matchId}/sheet`);
      await expect.poll(() => page.evaluate(() => (window as unknown as { __interactiveAt?: number }).__interactiveAt ?? null)).not.toBeNull();
      const ms = await page.evaluate(() => (window as unknown as { __interactiveAt: number }).__interactiveAt);
      await attach(testInfo, 'score-sheet-interactive', ms);
    }
  });

  async function throttle(page: Page): Promise<void> {
    // Reference profile (OQ-17): 9 Mbit/s down, 1.5 Mbit/s up, 4x CPU slowdown. Chromium only.
    const cdp = await page.context().newCDPSession(page);
    await cdp.send('Network.enable');
    await cdp.send('Network.emulateNetworkConditions', {
      offline: false,
      latency: 20,
      downloadThroughput: (9 * 1024 * 1024) / 8,
      uploadThroughput: (1.5 * 1024 * 1024) / 8,
    });
    await cdp.send('Emulation.setCPUThrottlingRate', { rate: 4 });
  }

  /** From the tap on "Watch rally n" to the first frame presented, playing, at the rally start. */
  async function armFirstFrame(page: Page, startS: number): Promise<void> {
    await page.evaluate((startS) => {
      window.__timings ??= {};
      window.__timings.seek = new Promise<number>((resolve, reject) => {
        let t0: number | null = null;
        document.addEventListener('pointerdown', (e) => { t0 ??= e.timeStamp; }, { capture: true, once: true });
        // S-01 can hold one video per opened rally: hook every video, old and new, and take the
        // first frame any of them presents, playing, at this rally's start.
        const hooked = new WeakSet<HTMLVideoElement>();
        let done = false;
        const hook = (video: HTMLVideoElement): void => {
          hooked.add(video);
          video.addEventListener('error', () => { if (!done) reject(new Error(`video error ${video.error?.code}`)); }, { once: true });
          const frame = (): void => {
            video.requestVideoFrameCallback((_now, meta) => {
              if (done) return;
              if (t0 !== null && !video.paused && Math.abs(meta.mediaTime - startS) < 1.5) {
                done = true;
                resolve(performance.now() - t0);
              } else frame();
            });
          };
          frame();
        };
        const watch = (): void => {
          if (done) return;
          document.querySelectorAll<HTMLVideoElement>('main video').forEach((v) => { if (!hooked.has(v)) hook(v); });
          requestAnimationFrame(watch);
        };
        watch();
      });
    }, startS);
  }

  async function seekSamples(page: Page, testInfo: TestInfo, matchId: string, metric: string): Promise<void> {
    const rows = (await sheetOf(page, matchId)).rows;
    // The page CSP allows media from its own origin only, so the link must be served there.
    const link = await page.request.get(`/api/matches/${matchId}/rallies/${rows[2]!.rally_id}/media`);
    expect(link.status(), await link.text()).toBe(200);
    const origin = new URL(String(((await link.json()) as { url: string }).url), page.url()).origin;
    expect(origin, 'the media link is not on the web origin: SRE-MEDIA (blockers.md 2026-10-05)').toBe(new URL(page.url()).origin);
    for (const n of [3, 5]) {
      await armFirstFrame(page, rows[n - 1]!.start_ms / 1000);
      await page.getByRole('button', { name: `Watch rally ${n}` }).click();
      await attach(testInfo, metric, await result(page, 'seek'));
    }
  }

  test('seek-first-frame on the reference profile (real video link)', async ({ page }, testInfo) => {
    const matchId = await receivedMatch(page, 'Timing video');
    await tagJourneyByApi(page, matchId);
    await page.goto(`/matches/${matchId}/sheet`);
    expect(await decodesH264(page), 'this browser cannot decode the H.264 original (blockers.md 2026-10-06)').toBe(true);
    await throttle(page);
    await seekSamples(page, testInfo, matchId, 'seek-first-frame');
  });

  test('seek-first-frame with the decodable stand-in (supporting, not the G02-06 (c) measure)', async ({ page }, testInfo) => {
    // Chromium has no H.264 decoder, so the presigned link is answered with a VP9 copy of the
    // fixture. A routed response skips the network emulation, so only the 4x CPU applies: this
    // shows the page's seek-and-play path, not the link's delivery (metric name kept separate).
    const matchId = await receivedMatch(page, 'Timing stand-in');
    await tagJourneyByApi(page, matchId);
    const body = await decodableStandIn();
    await page.route(/X-Amz-Signature=/, (route) => route.fulfill(rangeResponse(route.request().headers()['range'], body)));
    await page.goto(`/matches/${matchId}/sheet`);
    await throttle(page);
    await seekSamples(page, testInfo, matchId, 'seek-first-frame-standin');
  });
});
