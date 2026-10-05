// Binds tests/features/footage_quality_report.feature (ST-019 stretch; sprint-01 §7.6; FR-025,
// flows M-02) in the browser. The wording itself is pinned by Vitest
// (web/tests/unit/quality-report.test.tsx); this journey proves the report appears on the real
// match page for a probed 30 fps upload and never blocks (QA-R2-03).
import path from 'node:path';
import { expect, test } from '@playwright/test';
import { answerSetup, createAndUpload, signInByLink } from '../helpers/sprint-01';

// 1080p at 30 fps, constant frame rate, 2 s (fixtures/clips/phone-profiles-v1/manifest.json).
const CLIP_1080P30 = path.resolve(
  __dirname,
  '../../../fixtures/clips/phone-profiles-v1/h264-mp4-1080p30.mp4',
);

test.describe('@M0 @story-ST-019 Footage quality report', () => {
  test('30 fps video', async ({ page }) => {
    test.slow(); // upload plus probe

    // Given Ivy uploaded a 1080p video recorded at 30 fps (a fresh account: testing-strategy rule 10)
    await signInByLink(page);
    await answerSetup(page, { format: 'Singles', players: ['Ivy', 'Carlos'], me: 'Ivy', file: CLIP_1080P30 });
    await createAndUpload(page);
    await expect(page.getByText('Video received')).toBeVisible({ timeout: 120_000 });

    // When the quality report is shown
    const report = page.getByRole('region', { name: 'Footage quality' });
    await expect(report).toBeVisible({ timeout: 120_000 });

    // Then it says which results may be less accurate and which are unaffected
    await expect(report).toContainText('Recorded at 30 fps');
    await expect(report).toContainText('may be less accurate');
    await expect(report).toContainText('Your score and rally stats are unaffected.');
    await expect(report).not.toContainText('Recorded at 1920×1080'); // 1080p is not reported
    await expect(page.getByText(/· 30 fps · 1920×1080$/)).toBeVisible(); // the probed facts

    // And she can continue to tag the match: the report is information, not an error or a gate
    await expect(report).toContainText('You can still tag this match.');
    await expect(page.getByRole('alert').filter({ hasText: 'There is a problem' })).toHaveCount(0);
    await expect(report.getByRole('button')).toHaveCount(0); // nothing to acknowledge or dismiss
  });
});
