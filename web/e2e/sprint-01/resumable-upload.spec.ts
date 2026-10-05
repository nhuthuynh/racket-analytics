// Binds tests/features/resumable_upload.feature (ST-017; sprint-01 §7.4, §14.3.5) in the browser,
// including E2E-01-02 (network cut mid-upload). Copy: flows U-01, U-04. The 3 GB video of the
// Gherkin is a 48 MiB padded fixture, and the 2-minute cut is 10 s: the behaviour is the same,
// the run time is not (judgment). Red until ST-017.
import { expect, test } from '@playwright/test';
import { answerSetup, createAndUpload, LONG_CLIP, paddedClip, signInByLink, uploadPercent } from '../helpers/sprint-01';

test.describe('Resumable upload', () => {
  test('Connection drops mid-upload (E2E-01-02)', async ({ page, context }, testInfo) => {
    const file = await paddedClip(testInfo.outputPath('media'), 48);
    // A local stack takes the 48 MiB in about a second, so the 40% point could pass unseen.
    // 400 ms per chunk makes it observable; the transfer itself is unchanged (TCR row 21).
    await page.route('**/uploads/**', async (route) => {
      if (route.request().method() === 'PATCH') await new Promise((r) => setTimeout(r, 400));
      await route.fallback();
    });
    await signInByLink(page);
    await answerSetup(page, { format: 'Singles', players: ['Ivy', 'Carlos'], me: 'Ivy', file });
    await createAndUpload(page);
    await expect.poll(() => uploadPercent(page), { timeout: 60_000 }).toBeGreaterThanOrEqual(40);
    const before = await uploadPercent(page);

    await context.setOffline(true);
    await expect(page.getByText('Paused: waiting for connection')).toBeVisible();
    await page.waitForTimeout(10_000);
    await context.setOffline(false);

    await expect(page.getByText('Uploading', { exact: true })).toBeVisible();
    expect(await uploadPercent(page)).toBeGreaterThanOrEqual(before);
    await expect(page.getByText('Video received')).toBeVisible({ timeout: 120_000 });
  });

  test('Return after closing the tab', async ({ page, context }, testInfo) => {
    const file = await paddedClip(testInfo.outputPath('media'), 48);
    await signInByLink(page);
    await answerSetup(page, { format: 'Singles', players: ['Ivy', 'Carlos'], me: 'Ivy', file });
    await createAndUpload(page);
    await expect.poll(() => uploadPercent(page), { timeout: 60_000 }).toBeGreaterThanOrEqual(30);
    await page.close();

    const again = await context.newPage();
    await again.goto('/');
    const banner = again.getByText(/Your upload of '.+' is (\d{1,2})% done\./);
    await expect(banner).toBeVisible();
    await expect(again.getByRole('button', { name: 'Resume upload' })).toBeVisible();
    await expect(again.getByText(/It will be kept until/)).toBeVisible();
  });

  test('A damaged chunk is not kept', async ({ page }, testInfo) => {
    const file = await paddedClip(testInfo.outputPath('media'), 16);
    // The first chunk reaches the server with an Upload-Checksum that does not match its bytes,
    // exactly what the server sees when bytes are damaged on the way. Only the header is
    // rewritten: WebKit's route interception does not expose a Blob/File request body, so the
    // earlier "flip a byte of the body" version never fired there (QA-R1-05, TCR row of this date).
    // The real server must refuse the chunk (460, nothing kept) and the client must resend it.
    const WRONG_SHA256 = `sha256 ${Buffer.alloc(32, 0xab).toString('base64')}`;
    let corrupted = false;
    const patchStatuses: number[] = [];
    page.on('response', (r) => {
      if (r.request().method() === 'PATCH' && /\/uploads\//.test(r.url())) patchStatuses.push(r.status());
    });
    await page.route('**/uploads/**', async (route) => {
      const request = route.request();
      const headers = request.headers();
      if (!corrupted && request.method() === 'PATCH' && headers['upload-checksum']) {
        corrupted = true;
        await route.continue({ headers: { ...headers, 'upload-checksum': WRONG_SHA256 } });
        return;
      }
      await route.continue();
    });
    await signInByLink(page);
    await answerSetup(page, { format: 'Singles', players: ['Ivy', 'Carlos'], me: 'Ivy', file });
    await createAndUpload(page);
    await expect(page.getByText('Video received')).toBeVisible({ timeout: 120_000 });
    expect(corrupted).toBe(true);
    expect(patchStatuses[0]).toBe(460); // checksum mismatch: the damaged chunk was not kept
    expect(patchStatuses.slice(1).every((s) => s === 204)).toBe(true);
  });

  test('Time estimate appears only after measuring', async ({ page }, testInfo) => {
    const file = await paddedClip(testInfo.outputPath('media'), 48);
    await page.route('**/uploads/**', async (route) => {
      if (route.request().method() === 'PATCH') await new Promise((r) => setTimeout(r, 3_000));
      await route.continue();
    });
    await signInByLink(page);
    await answerSetup(page, { format: 'Singles', players: ['Ivy', 'Carlos'], me: 'Ivy', file });
    await createAndUpload(page);
    await expect(page.getByText(/\d{1,3}% · [\d.]+ [KMG]B of [\d.]+ [KMG]B/)).toBeVisible();
    await expect(page.getByText(/left$/)).toHaveCount(0);
  });

  test('A different file is chosen to resume', async ({ page, context }, testInfo) => {
    const file = await paddedClip(testInfo.outputPath('media'), 48);
    let uploadUrl = '';
    page.on('request', (r) => {
      if (r.method() === 'PATCH' && /\/uploads\//.test(r.url())) uploadUrl = r.url();
    });
    await signInByLink(page);
    await answerSetup(page, { format: 'Singles', players: ['Ivy', 'Carlos'], me: 'Ivy', file });
    await createAndUpload(page);
    await expect.poll(() => uploadPercent(page), { timeout: 60_000 }).toBeGreaterThanOrEqual(30);
    await page.close();

    // A PATCH still in flight when the tab closes can land afterwards and move the server offset
    // (QA-V1-02: 'is 42% done' read too early, 1 failure in 14 runs under load). Read the
    // percentage only once the server offset has stopped changing for a full interval.
    expect(uploadUrl).not.toBe('');
    const serverOffset = async (): Promise<number> => {
      const head = await context.request.head(uploadUrl, { headers: { 'Tus-Resumable': '1.0.0' } });
      expect(head.status()).toBe(200);
      return Number(head.headers()['upload-offset']);
    };
    let settled = -1;
    await expect
      .poll(async () => {
        const now = await serverOffset();
        const stable = now === settled;
        settled = now;
        return stable;
      }, { intervals: [1_000], timeout: 30_000 })
      .toBe(true);

    const again = await context.newPage();
    await again.goto('/');
    const before = (await again.getByText(/is (\d{1,2})% done/).innerText()).match(/(\d{1,2})%/)?.[1];
    await again.getByRole('button', { name: 'Resume upload' }).click();
    await again.getByLabel('Choose video').setInputFiles(LONG_CLIP);
    await expect(again.getByText(/This is not the same video/)).toBeVisible();
    expect(await serverOffset()).toBe(settled); // the other file sent nothing
    await again.goto('/');
    await expect(again.getByText(new RegExp(`is ${before}% done`))).toBeVisible();
  });

  test('The unfinished upload has expired', async () => {
    test.skip(true, 'Needs a 24-hour wait; bound at API level with UPLOAD_EXPIRY_SECONDS=1 (backend/tests/features/test_resumable_upload.py)');
  });

  test("Carlos tries to send data to Ivy's upload", async () => {
    test.skip(true, 'No UI path for another user; bound at API level and in the BOLA matrix (backend/tests/features/test_resumable_upload.py)');
  });

  test('Upload page wording', async ({ page }, testInfo) => {
    const file = await paddedClip(testInfo.outputPath('media'), 16);
    await page.route('**/uploads/**', async (route) => {
      if (route.request().method() === 'PATCH') return; // keep the page in the uploading state
      await route.continue();
    });
    await signInByLink(page);
    await answerSetup(page, { format: 'Singles', players: ['Ivy', 'Carlos'], me: 'Ivy', file });
    await createAndUpload(page);
    const text = await page.locator('main').innerText();
    expect(text).toContain('If you close it, you can resume later from this page by choosing the same video.');
    expect(text).not.toMatch(/(continues?|keeps? (going|uploading)|in the background)[^.]*(after|when)[^.]*clos/i);
  });
});
