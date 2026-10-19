// E2E-04-04 "Not for me" with no alternative (ST-065; FR-124; flows-sprint-04 §4, 409
// `no_alternative`): inside the dialog an alert says no other drill fits and the plan is
// unchanged, focus moves to it, "Close" returns focus to the row's "Not for me", and the plan the
// API holds is the same version with the same drill. Words: e2e/helpers/sprint-04.ts.
import { expect, test } from '@playwright/test';
import { expectNoBlockingA11yViolations, expectTargetsAtLeast24 } from '../helpers/axe';
import { CITED, PLAN_COPY, PLAN_PATH, SCREEN_P, drillRow, planRead, planReadyAccount } from '../helpers/sprint-04';

test.describe('@M0 @story-ST-065 Swap with no alternative', () => {
  test('E2E-04-04 a drill with no other that fits stays, and the dialog says so', async ({ page }, testInfo) => {
    const { plan } = await planReadyAccount(page);
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
    await expect(row.getByRole('button', { name: `Not for me, ${CITED}` })).toBeFocused();
    await expect(row).toBeVisible();
    const after = await planRead(page);
    expect(after.version).toBe(plan.version);
    expect(JSON.stringify(after.sessions)).toBe(JSON.stringify(plan.sessions));
  });
});
