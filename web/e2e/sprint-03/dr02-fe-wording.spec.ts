// DR-02-FE (DR-02 R2-2): flows-sprint-02 §9 PD-FL2-03 (S-01 rules line in words) and PD-FL2-05
// (T-01 undo named like S-01), on the live stack. Binds the second and third rules of
// tests/features/dr02_fe_follow_ups.feature.
import { expect, test } from '@playwright/test';
import { openTagging, receivedMatch, tagJourneyByApi } from '../helpers/sprint-02';

test.describe('@story-DR-02 S-01 and T-01 wording (PD-FL2-03, PD-FL2-05)', () => {
  test('PD-FL2-03 the S-01 rules line says the provisional rules in words, not the preset id', async ({ page }) => {
    const matchId = await receivedMatch(page, 'PD-FL2-03 rules line');
    await tagJourneyByApi(page, matchId);
    await page.goto(`/matches/${matchId}/sheet`);
    await expect(page.getByText('Rules: provisional, not yet checked against the rulebook')).toBeVisible();
    await expect(page.getByText('PROVISIONAL-UNVERIFIED')).toHaveCount(0);
  });

  test('PD-FL2-05 the T-01 undo button is named "Undo last change", as on S-01', async ({ page }) => {
    await openTagging(page, await receivedMatch(page, 'PD-FL2-05 T-01 undo'));
    await expect(page.getByRole('button', { name: 'Undo last change', exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: /^Undo$/ })).toHaveCount(0);
  });
});
