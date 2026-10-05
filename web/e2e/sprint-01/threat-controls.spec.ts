// Threat-model controls that are verified in the browser (docs/security/threat-model-sprint-01.md
// §2-§3; ADR 0022 rule 4: threat controls are acceptance criteria). SEC-R4-S1-03: T-ML-5 and
// T-UV-10 were marked C (verified) but the tests their cells name did not exist.
import { expect, test, type Page } from '@playwright/test';
import {
  answerSetup,
  createAndUpload,
  latestSignInLink,
  openSignInLink,
  paddedClip,
  requestLink,
  SIGNED_IN_URL,
  signInByLink,
  uniqueEmail,
} from '../helpers/sprint-01';

// Fires on any script run from markup: an alert dialog or a global set by the handler.
const XSS = '<img src=x onerror=alert(document.domain)>';
const NICK_XSS = '<img src=x onerror=alert(1)>'; // nicknames are at most 30 characters

function watchForScript(page: Page): () => string[] {
  const fired: string[] = [];
  page.on('dialog', async (d) => {
    fired.push(`dialog: ${d.message()}`);
    await d.dismiss();
  });
  return () => fired;
}

test.describe('Threat controls (Sprint 1)', () => {
  test('T-ML-5: fetching the sign-in link twice does not spend it', async ({ page, playwright }) => {
    const email = uniqueEmail();
    await requestLink(page, email);
    const link = new URL(await latestSignInLink(email));

    // A mail scanner fetches the link without running scripts. The token is in the fragment, so
    // the server never sees it; the page is static until its script runs (ADR 0025).
    const scanner = await playwright.request.newContext({ baseURL: test.info().project.use.baseURL, ignoreHTTPSErrors: true });
    for (const n of [1, 2]) {
      const response = await scanner.get(`${link.pathname}${link.hash}`);
      expect(response.status(), `scanner GET ${n}`).toBe(200);
      expect(await response.text()).not.toContain(link.hash.slice('#token='.length));
    }
    await scanner.dispose();

    // The person then opens the same link and is signed in: the exchange answered 200.
    const exchange = page.waitForResponse((r) => r.url().endsWith('/auth/exchange') && r.request().method() === 'POST');
    await openSignInLink(page, link);
    expect((await exchange).status()).toBe(200);
    await expect(page).toHaveURL(SIGNED_IN_URL);
  });

  test('T-UV-10: a nickname and a file name made of markup render as text', async ({ page, context }, testInfo) => {
    const fired = watchForScript(page);
    const file = await paddedClip(testInfo.outputPath('media'), 16, `${XSS}.mp4`);
    await page.route('**/uploads/**', async (route) => {
      if (route.request().method() === 'PATCH') return route.abort(); // keep the upload unfinished
      await route.continue();
    });
    await signInByLink(page);
    await answerSetup(page, { format: 'Singles', players: [NICK_XSS, 'Carlos'], me: 'Carlos', file });

    const main = page.locator('main');
    await expect(main).toContainText(NICK_XSS); // Q-07 shows the nickname and the file name as text
    await expect(main).toContainText(`${XSS}.mp4`);
    await createAndUpload(page);
    const matchUrl = page.url();

    // Return visit: the resume prompt names the stored file (U-04). Nicknames render only in
    // setup (Q-03..Q-07), checked above; the Sprint 1 match page does not show them.
    const again = await context.newPage();
    const firedAgain = watchForScript(again);
    await again.goto(matchUrl);
    await expect(again.locator('main')).toContainText(`${XSS}.mp4`);

    for (const p of [page, again]) {
      expect(await p.locator('main img[src="x"]').count()).toBe(0);
    }
    expect([...fired(), ...firedAgain()]).toEqual([]);
  });
});
