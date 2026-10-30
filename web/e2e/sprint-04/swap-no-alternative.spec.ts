// E2E-04-04 "Not for me" with no alternative (ST-065; FR-124; flows-sprint-04 §4, 409
// `no_alternative`): inside the dialog an alert says no other drill fits and the plan is
// unchanged, focus moves to it, "Close" closes the dialog, and the plan the API holds is the same
// version with the same drill. Then the dialog rule of flows-sprint-03 §0 (P-03 row of
// flows-sprint-04 §9: "focus trapped, returned"): Close, Cancel and Esc give focus back to the
// row's "Not for me". Words and NO_ALTERNATIVE_SETUP: e2e/helpers/sprint-04.ts.
import { expect, test } from '@playwright/test';
import { expectNoBlockingA11yViolations, expectTargetsAtLeast24 } from '../helpers/axe';
import {
  NO_ALTERNATIVE as CITED,
  NO_ALTERNATIVE_SETUP,
  PLAN_COPY,
  PLAN_PATH,
  SCREEN_P,
  drillRow,
  planRead,
  planReadyAccount,
} from '../helpers/sprint-04';

test.describe('@M0 @story-ST-065 Swap with no alternative', () => {
  test('E2E-04-04 a drill with no other that fits stays, and the dialog says so', async ({ page }, testInfo) => {
    const { plan } = await planReadyAccount(page, NO_ALTERNATIVE_SETUP);
    await page.goto(PLAN_PATH);
    const row = drillRow(page, CITED);
    await row.getByRole('button', { name: `Not for me, ${CITED}` }).click();
    const dialog = page.getByRole('dialog', { name: `Swap ${CITED}?` });
    await dialog.getByRole('button', { name: 'Swap drill' }).click();

    const alert = dialog.getByRole('alert');
    await expect(alert).toHaveText(PLAN_COPY.noAlternative);
    await expect(alert).toBeFocused();
    await expectNoBlockingA11yViolations(page, testInfo, `${SCREEN_P.swap}-no-alternative`);
    await expectTargetsAtLeast24(page, testInfo, `${SCREEN_P.swap}-no-alternative`);

    await dialog.getByRole('button', { name: 'Close' }).click();
    await expect(page.getByRole('dialog')).toHaveCount(0);
    await expect(row).toBeVisible();
    const after = await planRead(page);
    expect(after.version).toBe(plan.version);
    expect(JSON.stringify(after.sessions)).toBe(JSON.stringify(plan.sessions));
  });

  // Defect QA-ST065-01 (decisions/ST-065.md), red first in Chromium: focus landed on <body>.
  test('E2E-04-04 focus returns to "Not for me" after Close, Cancel and Esc', async ({ page }) => {
    await planReadyAccount(page, NO_ALTERNATIVE_SETUP);
    await page.goto(PLAN_PATH);
    const opener = drillRow(page, CITED).getByRole('button', { name: `Not for me, ${CITED}` });
    const dialog = page.getByRole('dialog', { name: `Swap ${CITED}?` });
    for (const close of ['Close', 'Cancel', 'Escape'] as const) {
      await opener.click();
      if (close === 'Close') {
        await dialog.getByRole('button', { name: 'Swap drill' }).click();
        await expect(dialog.getByRole('alert')).toHaveText(PLAN_COPY.noAlternative);
        await dialog.getByRole('button', { name: 'Close' }).click();
      } else if (close === 'Cancel') await dialog.getByRole('button', { name: 'Cancel' }).click();
      else await page.keyboard.press('Escape');
      await expect(page.getByRole('dialog')).toHaveCount(0);
      await expect(opener, `focus after ${close}`).toBeFocused();
    }
  });
});
