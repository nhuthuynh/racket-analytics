// E2E-03-04 delete my account (ST-051; FR-007, NFR-066; Gherkin §7.5). Ivy is signed in on two
// devices (two browser contexts, the same address); she deletes her account after a
// confirmation that states the consequences; both devices are signed out; signing in again
// with the same address shows no matches (PM-1 default). UI assumptions: helpers/sprint-03.ts.
import { expect, test } from '@playwright/test';
import { expectNoBlockingA11yViolations, expectTargetsAtLeast24 } from '../helpers/axe';
import { SIGNED_IN_URL, signInByLink, uniqueEmail } from '../helpers/sprint-01';
import { ACCOUNT_PATH, SCREEN, signInWithNthLink } from '../helpers/sprint-03';

test.describe('@M0 @story-ST-051 @nfr-066 Delete my account', () => {
  test('E2E-03-04 the confirmation states the consequences; both devices signed out; signing in again is empty', async ({ browser }, testInfo) => {
    test.setTimeout(180_000);
    const email = uniqueEmail('ivy');
    const phone = await (await browser.newContext()).newPage();
    const laptop = await (await browser.newContext()).newPage();
    await signInByLink(phone, email);
    await signInWithNthLink(laptop, email, 2);
    const created = await phone.request.post('/api/matches', {
      data: { title: 'To be deleted', format: 'doubles', participants: [
        { slot: 'A1', nickname: 'Ivy', is_me: true }, { slot: 'A2', nickname: 'Dana', is_me: false },
        { slot: 'B1', nickname: 'Carlos', is_me: false }, { slot: 'B2', nickname: 'Sam', is_me: false }] },
    });
    expect(created.status()).toBe(201);

    await phone.goto(ACCOUNT_PATH);
    await phone.getByRole('button', { name: /Delete (my )?account/ }).click();
    const dialog = phone.getByRole('dialog');
    for (const what of [/matches/i, /videos?/i, /cannot be (undone|restored)/i, /signed out/i]) await expect(dialog).toContainText(what);
    await expectNoBlockingA11yViolations(phone, testInfo, SCREEN.deleteAccount);
    await expectTargetsAtLeast24(phone, testInfo, SCREEN.deleteAccount); // NFR-028 on X-02 (PD-R1S3-03)
    const typed = dialog.getByRole('textbox');
    if (await typed.count()) await typed.fill('delete');
    await dialog.getByRole('button', { name: /Delete/ }).last().click();

    for (const device of [phone, laptop]) {
      expect((await device.request.get('/api/me')).status()).toBe(401);
      await device.goto('/matches');
      await expect(device).not.toHaveURL(SIGNED_IN_URL);
    }
    await signInWithNthLink(laptop, email, 3);
    const listed = (await (await laptop.request.get('/api/matches')).json()) as { items: unknown[] };
    expect(listed.items).toEqual([]);
  });
});
