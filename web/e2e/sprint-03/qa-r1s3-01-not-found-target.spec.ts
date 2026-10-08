// Binds tests/features/not_found_touch_target.feature (QA-R1S3-01; NFR-028, WCAG 2.2 SC 2.5.8;
// G03-10 b). E2E-03-06 measured "Go to your matches" at 178x21 CSS px at 320/360 px: a standalone
// link, so the inline exception does not apply. Layout only exists in a browser, so the size is
// measured here; the unit test checks the class and the CSS rule.
import { expect, test } from '@playwright/test';
import { expectNoBlockingA11yViolations, expectTargetsAtLeast24 } from '../helpers/axe';
import { signInByLink } from '../helpers/sprint-01';

const MISSING_MATCH = '/matches/00000000-0000-4000-8000-000000000000';
const TOUCH_TARGET_PX = 48; // --size-target-touch (docs/design/tokens.json)

test.describe('@M0 @story-ST-048 @nfr-028 QA-R1S3-01 not-found touch target', () => {
  for (const width of [320, 360]) {
    test(`the way back from a missing match at ${width} px is a touch-sized link`, async ({ page }, testInfo) => {
      await signInByLink(page);
      await page.setViewportSize({ width, height: 740 });
      // The match page renders the one not-found page in its stream (HTTP status is not this
      // ticket's concern); the heading proves which page this is.
      await page.goto(MISSING_MATCH);
      await expect(page.getByRole('heading', { level: 1 })).toHaveText('Page not found');

      const back = page.getByRole('main').getByRole('link', { name: 'Go to your matches' });
      await expect(back).toHaveAttribute('href', '/matches');
      const box = await back.boundingBox();
      expect(box, 'the link is laid out').not.toBeNull();
      expect(box!.width, 'target width (NFR-028)').toBeGreaterThanOrEqual(24);
      expect(box!.height, 'target height (NFR-028)').toBeGreaterThanOrEqual(24);
      expect(Math.round(box!.height), 'the 48 px touch token').toBeGreaterThanOrEqual(TOUCH_TARGET_PX);

      await expectTargetsAtLeast24(page, testInfo, `not-found-${width}`);
      await expectNoBlockingA11yViolations(page, testInfo, `not-found-${width}`);
    });
  }
});
