// E2E-00-01 walking skeleton (sprint-00 §6; tests/features/walking_skeleton.feature, UI level).
// dev sign-in -> new match -> upload the synthetic fixture -> match page shows
// "Duration 1:00 · 60 fps · 1920×1080", with axe on every page (NFR-027).
// Written first by QA (ST-012): RED until ST-010 (with ST-008, ST-009) lands.
import { expect, test } from '@playwright/test';
import { expectNoBlockingA11yViolations } from './helpers/axe';
import { FIXTURE_CLIP, createMatch, signInAs } from './helpers/journey';

test.describe('@M0 @story-ST-010 walking skeleton', () => {
  test('upload the fixture clip and see its facts', async ({ page }, testInfo) => {
    test.slow(); // upload plus probe of a 60 s clip

    await page.goto('/');
    await expectNoBlockingA11yViolations(page, testInfo, 'sign-in');

    // Empty state as Dana, who never owns a match, so spec order does not matter (QA-R1-04).
    await signInAs(page, 'Dana');
    await expect(page.getByText(/no matches yet/i)).toBeVisible(); // empty state (DoD UI)
    await expectNoBlockingA11yViolations(page, testInfo, 'matches-empty');

    await page.getByRole('link', { name: /new match/i }).click();
    await expectNoBlockingA11yViolations(page, testInfo, 'new-match');

    await signInAs(page, 'Ivy');
    await createMatch(page, 'Skeleton test');
    await page.getByLabel(/match video/i).setInputFiles(FIXTURE_CLIP);

    const progress = page.getByRole('progressbar', { name: /upload/i });
    await expect(progress).toBeVisible();
    await expect(page.getByText(/\d+(\.\d+)? of \d+(\.\d+)? MB/)).toBeVisible(); // % and MB
    await expectNoBlockingA11yViolations(page, testInfo, 'uploading');

    await expect(page.getByText('Video received')).toBeVisible({
      timeout: 120_000,
    });
    await expect(page.getByText('Duration 1:00 · 60 fps · 1920×1080')).toBeVisible({
      timeout: 120_000,
    });
    await expectNoBlockingA11yViolations(page, testInfo, 'match-detail');
  });

  test('progress stays within 0-100% and a reload mid-upload resumes from the server offset', async ({
    page,
  }) => {
    test.slow(); // the resumed upload is followed by the probe
    await signInAs(page, 'Ivy');
    await createMatch(page, 'Reload test');

    // Deterministic "mid-upload" (QA-R1-05): wait for the creation to commit, then hold the
    // first PATCH in the browser so the reload happens while its bytes are in flight.
    let patchHeld!: () => void;
    const firstPatch = new Promise<void>((resolve) => (patchHeld = resolve));
    let held = false;
    await page.route('**/uploads/**', async (route) => {
      if (route.request().method() === 'PATCH' && !held) {
        held = true;
        patchHeld(); // never continued: the reload cancels it, so the server stores nothing
        return;
      }
      await route.fallback();
    });
    const created = page.waitForResponse(
      (r) => r.request().method() === 'POST' && /\/uploads$/.test(new URL(r.url()).pathname),
    );
    await page.getByLabel(/match video/i).setInputFiles(FIXTURE_CLIP);
    const creation = await created;
    expect(creation.status()).toBe(201);
    const location = creation.headers()['location'];
    expect(location).toMatch(/^\/api\/uploads\//); // behind the web's /api rewrite (R1-02)
    const uploadPath = new URL(location ?? '', page.url()).pathname;
    await firstPatch;

    const progress = page.getByRole('progressbar', { name: /upload/i });
    await expect(progress).toBeVisible();
    const now = Number(await progress.getAttribute('aria-valuenow'));
    expect(now).toBeGreaterThanOrEqual(0);
    expect(now).toBeLessThanOrEqual(100);

    await page.reload();
    await page.unroute('**/uploads/**');
    await expect(page.getByText(/uploading/i).first()).toBeVisible();

    // Resume: choosing the same file again asks the server for its offset (HEAD on the same
    // upload URL) and continues there; no second upload is created.
    const seen: string[] = [];
    page.on('request', (r) => {
      if (/\/uploads/.test(r.url())) seen.push(`${r.method()} ${new URL(r.url()).pathname}`);
    });
    await page.getByLabel(/match video/i).setInputFiles(FIXTURE_CLIP);
    await expect(page.getByText('Video received')).toBeVisible({
      timeout: 120_000,
    });
    expect(seen).toContain(`HEAD ${uploadPath}`);
    expect(seen).toContain(`PATCH ${uploadPath}`);
    expect(seen.filter((r) => r.startsWith('POST'))).toEqual([]);
  });
});
