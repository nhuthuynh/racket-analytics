// ST-054 timing spec (QA; scorecard G03-07; NFR-011, NFR-014, NFR-039). Each run attaches one
// sample per metric as `timing-<metric>` with {"ms": n}, read by scripts/measure/pw_timings.py
// (run with --repeat-each=20 for >= 20 samples):
//   dashboard-interactive  warm: navigation start -> every shown metric card's "Show me" hydrated
//                          and visible (target p95 <= 2,000 ms);
//   show-me-first-frame    reference profile 9/1.5 Mbit/s and 4x CPU (Chromium, CDP): the tap on a
//                          rally in "Show me" -> first frame presented, playing, at the rally start
//                          (target p95 <= 1,500 ms);
//   layout-shift           summed CLS x 1000 from navigation until the last card is rendered
//                          (target p95 = 0).
// UI assumptions: e2e/helpers/sprint-03.ts (until PD-1/DR-03).
import { expect, test, type Page, type TestInfo } from '@playwright/test';
import { receivedMatch } from '../helpers/sprint-02';
import { PUBLISHED, statsPath, tagWorkedExampleByApi } from '../helpers/sprint-03';

declare global {
  interface Window { __s3?: { interactiveAt?: number; cls?: number; firstFrame?: Promise<number> } }
}

async function attach(testInfo: TestInfo, metric: string, ms: number): Promise<void> {
  expect(Number.isFinite(ms), `${metric}: ${ms}`).toBe(true);
  await testInfo.attach(`timing-${metric}`, { body: JSON.stringify({ ms }), contentType: 'application/json' });
}

/** Watch from navigation start: when every card's "Show me" is hydrated and visible; CLS. */
async function instrument(page: Page, cards: number): Promise<void> {
  await page.addInitScript((cards) => {
    const s3: NonNullable<Window['__s3']> = { cls: 0 };
    window.__s3 = s3;
    new PerformanceObserver((list) => {
      for (const e of list.getEntries() as (PerformanceEntry & { value: number; hadRecentInput: boolean })[]) {
        if (!e.hadRecentInput && s3.interactiveAt === undefined) s3.cls = (s3.cls ?? 0) + e.value;
      }
    }).observe({ type: 'layout-shift', buffered: true });
    const tick = (): void => {
      const ready = [...document.querySelectorAll('main button')].filter(
        (b) => /Show me/.test(b.textContent ?? '') && (b as HTMLElement).offsetParent !== null
          && Object.keys(b).some((k) => k.startsWith('__reactProps$')),
      );
      if (ready.length >= cards) s3.interactiveAt = performance.now();
      else requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }, cards);
}

async function measured(page: Page): Promise<{ interactiveAt: number; cls: number }> {
  await expect.poll(() => page.evaluate(() => window.__s3?.interactiveAt ?? null), { timeout: 15_000 }).not.toBeNull();
  return page.evaluate(() => ({ interactiveAt: window.__s3!.interactiveAt!, cls: window.__s3!.cls ?? 0 }));
}

test.describe('@M0 @story-ST-054 Sprint 3 timings', () => {
  test('dashboard-interactive (warm) and layout-shift', async ({ page }, testInfo) => {
    expect(PUBLISHED.length, 'no coach-reviewed metric (COACH-1)').toBeGreaterThan(0);
    const matchId = await receivedMatch(page, 'Timing stats');
    await tagWorkedExampleByApi(page, matchId);
    await instrument(page, PUBLISHED.length * 2); // one "Show me" per metric and side
    await page.goto(statsPath(matchId)); // cold: fills caches, not measured
    await measured(page);
    await page.goto(statsPath(matchId));
    const { interactiveAt, cls } = await measured(page);
    await attach(testInfo, 'dashboard-interactive', interactiveAt);
    await attach(testInfo, 'layout-shift', Math.round(cls * 1000));
  });

  test.describe('reference profile (CDP throttling)', () => {
    test.skip(({ browserName }) => browserName !== 'chromium', 'CDP throttling is Chromium-only; WebKit timings are out of the ST-054 scope');

    test('show-me-first-frame', async ({ page }, testInfo) => {
      expect(PUBLISHED.length, 'no coach-reviewed metric (COACH-1)').toBeGreaterThan(0);
      const matchId = await receivedMatch(page, 'Timing show me');
      await tagWorkedExampleByApi(page, matchId);
      await page.goto(statsPath(matchId));
      await expect(page.getByRole('heading', { level: 1 })).toContainText(/stats/i);
      const cdp = await page.context().newCDPSession(page);
      await cdp.send('Network.enable');
      await cdp.send('Network.emulateNetworkConditions', {
        offline: false, latency: 20, downloadThroughput: (9 * 1024 * 1024) / 8, uploadThroughput: (1.5 * 1024 * 1024) / 8,
      });
      await cdp.send('Emulation.setCPUThrottlingRate', { rate: 4 });
      await page.getByRole('button', { name: /Show me/ }).first().click();
      const first = page.getByRole('link', { name: /Rally \d+/ }).first();
      const n = Number(/Rally (\d+)/.exec((await first.textContent()) ?? '')?.[1]);
      const startS = ((n - 1) * 4000) / 1000; // tagWorkedExampleByApi: rally n starts at (n-1) x 4 s
      await page.evaluate((startS) => {
        const s3 = (window.__s3 ??= {});
        s3.firstFrame = new Promise<number>((resolve, reject) => {
          let t0: number | null = null;
          document.addEventListener('pointerdown', (e) => { t0 ??= e.timeStamp; }, { capture: true, once: true });
          const hooked = new WeakSet<HTMLVideoElement>();
          let done = false;
          const watch = (): void => {
            if (done) return;
            document.querySelectorAll('video').forEach((video) => {
              if (hooked.has(video)) return;
              hooked.add(video);
              video.addEventListener('error', () => { if (!done) reject(new Error(`video error ${video.error?.code}`)); }, { once: true });
              const frame = (): void => {
                video.requestVideoFrameCallback((_now, meta) => {
                  if (done) return;
                  if (t0 !== null && !video.paused && Math.abs(meta.mediaTime - startS) < 1.5) { done = true; resolve(performance.now() - t0); }
                  else frame();
                });
              };
              frame();
            });
            requestAnimationFrame(watch);
          };
          watch();
        });
      }, startS);
      await first.click();
      const ms = await page.evaluate(() => window.__s3!.firstFrame!);
      await attach(testInfo, 'show-me-first-frame', ms);
    });
  });
});
