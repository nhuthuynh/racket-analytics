// E2E-00-01 walking skeleton (sprint-00 §6; tests/features/walking_skeleton.feature, UI level).
// magic-link sign-in -> new match -> upload the synthetic fixture -> match page shows
// "Duration 1:00 · 60 fps · 1920×1080", with axe on every page (NFR-027).
// Written first by QA (ST-012): RED until ST-010 (with ST-008, ST-009) lands.
import { expect, test } from '@playwright/test';
import { expectNoBlockingA11yViolations } from './helpers/axe';
import { FIXTURE_CLIP, createMatch } from './helpers/journey';
import { signInByLink } from './helpers/sprint-01';

test.describe('@M0 @story-ST-010 walking skeleton', () => {
  test('upload the fixture clip and see its facts', async ({ page }, testInfo) => {
    test.slow(); // upload plus probe of a 60 s clip

    await page.goto('/');
    await expectNoBlockingA11yViolations(page, testInfo, 'sign-in');

    // Empty state as a fresh magic-link account, which owns nothing whatever ran before
    // (QA-R1-04; testing-strategy rule 10). A shared dev player such as Dana can be given a
    // match by any earlier run, so the empty state is no longer checked with one.
    await signInByLink(page);
    await page.goto('/matches');
    await expect(page.getByText(/no matches yet/i)).toBeVisible(); // empty state (DoD UI)
    await expectNoBlockingA11yViolations(page, testInfo, 'matches-empty');

    // Sprint 1 first-run copy (ST-015): the empty state links to Q-01 as "Record your first match".
    await page.getByRole('link', { name: 'Record your first match' }).click();
    await expectNoBlockingA11yViolations(page, testInfo, 'new-match');

    // The upload runs as the same fresh account, not as a shared dev player (PD-R2-03): every
    // unfinished upload counts toward the per-owner quota (T-UV-7), so a player shared across
    // runs reaches 429 on a reused stack after a few interrupted runs.
    await page.goto('/matches');
    // Hold the first chunk until the uploading state has been checked (C-04, QA-R3-E2E-01):
    // a fixed delay made this a race on a fast stack (the upload could finish inside it).
    // The held PATCH is continued afterwards, so the upload completes normally.
    let releasePatch!: () => void;
    const released = new Promise<void>((resolve) => (releasePatch = resolve));
    let patchHeld!: () => void;
    const firstPatch = new Promise<void>((resolve) => (patchHeld = resolve));
    let held = false;
    await page.route('**/uploads/**', async (route) => {
      if (route.request().method() === 'PATCH' && !held) {
        held = true;
        patchHeld();
        await released;
      }
      await route.fallback();
    });
    await createMatch(page); // ST-016: setup with the clip, then "Create match and upload"
    await firstPatch;

    const progress = page.getByRole('progressbar', { name: /upload/i });
    await expect(progress).toBeVisible();
    await expect(page.getByText(/\d{1,3}% · [\d.]+ [KMG]?B of [\d.]+ [KMG]B/)).toBeVisible(); // % and MB
    await expectNoBlockingA11yViolations(page, testInfo, 'uploading');
    releasePatch();

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
    // A fresh magic-link account (PD-R2-03; testing-strategy rule 10): if this journey stops
    // between the held PATCH and the resume, its unfinished upload must not use up a shared
    // player's quota and fail later runs with 429.
    await signInByLink(page);
    await page.goto('/matches');

    // Deterministic "mid-upload" (QA-R1-05): wait for the creation to commit, then hold the
    // first PATCH in the browser so the reload happens while its bytes are in flight. Since
    // ST-016 the upload starts from setup ("Create match and upload"), so the route and the
    // response wait are set up before the match is created.
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
    await createMatch(page);
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
    // U-04: the match page offers to continue with the same video (no URL kept on the device).
    await expect(page.getByText(/To continue, choose the same video/)).toBeVisible();

    // Resume: choosing the same file again asks the server for its offset (HEAD on the same
    // upload URL) and continues there; no second upload is created.
    const seen: string[] = [];
    page.on('request', (r) => {
      if (/\/uploads/.test(r.url())) seen.push(`${r.method()} ${new URL(r.url()).pathname}`);
    });
    await page.getByLabel('Choose video').setInputFiles(FIXTURE_CLIP);
    await expect(page.getByText('Video received')).toBeVisible({
      timeout: 120_000,
    });
    expect(seen).toContain(`HEAD ${uploadPath}`);
    expect(seen).toContain(`PATCH ${uploadPath}`);
    expect(seen.filter((r) => r.startsWith('POST'))).toEqual([]);
  });
});
