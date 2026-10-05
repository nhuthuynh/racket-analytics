// Binds tests/features/upload_validation.feature (ST-018; sprint-01 §7.5, §14.3.6) in the
// browser: the U-03 copy. Every outcome is also bound at API level
// (backend/tests/features/test_upload_validation.py). Red until ST-018.
import { expect, test } from '@playwright/test';
import {
  answerSetup,
  createAndUpload,
  ELF_BYTES,
  expectErrorSummary,
  LONG_CLIP,
  PDF_BYTES,
  signInByLink,
  writeBytes,
} from '../helpers/sprint-01';

const CASES = [
  { name: 'a PDF renamed to match.mp4', file: 'match.mp4', bytes: PDF_BYTES, message: 'This file is not a video we can read' },
  { name: 'a program renamed to match.mov', file: 'match.mov', bytes: ELF_BYTES, message: 'This file is not a video we can read' },
];

test.describe('Upload validation', () => {
  for (const c of CASES) {
    test(`Reject invalid files: ${c.name}`, async ({ page }, testInfo) => {
      const file = await writeBytes(testInfo.outputPath('media'), c.file, c.bytes);
      await signInByLink(page);
      await answerSetup(page, { format: 'Singles', players: ['Ivy', 'Carlos'], me: 'Ivy', file });
      await page.getByRole('button', { name: 'Create match and upload' }).click();
      await expectErrorSummary(page, c.message);
      await expect(page.getByText('Nothing from this file was saved.')).toBeVisible();
      await expect(page.getByRole('link', { name: 'Choose a different video' })).toBeVisible();
    });
  }

  test('Reject invalid files: a 12 GB video', async () => {
    test.skip(true, 'A 12 GB file cannot be handed to the browser in CI; the client size check is a Vitest unit test (FE) and the server check is bound at API level');
  });

  test('Reject invalid files: a 4-hour video', async ({ page }) => {
    await signInByLink(page);
    await answerSetup(page, { format: 'Singles', players: ['Ivy', 'Carlos'], me: 'Ivy', file: LONG_CLIP });
    await page.getByRole('button', { name: 'Create match and upload' }).click();
    await expect(page.getByRole('alert').filter({ hasText: 'There is a problem' })).toBeVisible({ timeout: 120_000 });
    await expect(page.getByRole('alert')).toContainText('Videos must be 2 hours 30 minutes or shorter');
  });

  test('A valid phone video is accepted', async ({ page }) => {
    await signInByLink(page);
    await answerSetup(page, { format: 'Doubles', players: ['Ivy', 'Dana', 'Carlos', 'Sam'], me: 'Ivy' });
    await createAndUpload(page);
    await expect(page.getByText('Video received')).toBeVisible({ timeout: 120_000 });
  });

  test('Declared size above the cap', async () => {
    test.skip(true, 'Server-side refusal of Upload-Length; bound at API level (backend/tests/features/test_upload_validation.py) and IT-01-09');
  });

  test('No video check for a refused file', async ({ page }, testInfo) => {
    const file = await writeBytes(testInfo.outputPath('media'), 'match.mp4', PDF_BYTES);
    await signInByLink(page);
    await answerSetup(page, { format: 'Singles', players: ['Ivy', 'Carlos'], me: 'Ivy', file });
    await page.getByRole('button', { name: 'Create match and upload' }).click();
    await expectErrorSummary(page, 'This file is not a video we can read');
    await page.reload();
    await expect(page.getByText('No video yet')).toBeVisible();
    await expect(page.getByText('Checking video…')).toHaveCount(0);
  });
});
