// A-01 before hydration (CI-SIGNIN-HYDRATION). Found on PR #105's webkit E2E run 39055141846:
// "Too many link requests" timed out on its first "Check your email" with no sign-in email
// sent. The server-rendered form was tappable before React attached onSubmit, so the tap was
// a native GET submit (/?email=<address>, the address in the URL against AQS/SEC-05) and no
// request reached the API. This spec holds the page's JavaScript so the window is wide and
// deterministic in every browser, then checks the form waits for hydration.
import { expect, test, type Page } from '@playwright/test';
import { uniqueEmail } from '../helpers/sprint-01';

// page.route must see the chunk and API requests in WebKit too (route-isolation rule).
test.use({ serviceWorkers: 'block' });

/** Hold every Next.js chunk until the returned release() is called. */
async function holdHydration(page: Page): Promise<() => void> {
  let release!: () => void;
  const gate = new Promise<void>((resolve) => (release = resolve));
  await page.route('**/_next/static/chunks/**', async (route) => {
    await gate;
    await route.continue();
  });
  return release;
}

test.describe('@story-ST-013 Sign-in form before hydration', () => {
  test('a tap before hydration neither submits natively nor puts the address in the URL', async ({ page }) => {
    const release = await holdHydration(page);
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    const field = page.getByLabel('Email address');
    const button = page.getByRole('button', { name: 'Send me a link' });
    await expect(button).toBeVisible();
    await expect(button).toBeDisabled();
    await expect(field).toBeDisabled();
    await button.click({ force: true }); // what a too-early tap does
    await expect(page).not.toHaveURL(/[?&]email=/);
    release();
  });

  test('once hydrated, the same page sends the link', async ({ page }) => {
    const sent: string[] = [];
    await page.route('**/api/auth/links', async (route) => {
      sent.push(route.request().postData() ?? '');
      await route.fulfill({ status: 202, body: '' });
    });
    const release = await holdHydration(page);
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    await expect(page.getByRole('button', { name: 'Send me a link' })).toBeDisabled();
    release();
    const email = uniqueEmail();
    await page.getByLabel('Email address').fill(email); // waits until the field is enabled
    await page.getByRole('button', { name: 'Send me a link' }).click();
    await expect(page.getByRole('heading', { level: 1, name: 'Check your email' })).toBeVisible();
    expect(sent).toEqual([JSON.stringify({ email })]);
    await expect(page).not.toHaveURL(/[?&]email=/);
  });
});
