// Shared steps for the walking-skeleton journeys. Selectors are role/label based on purpose:
// they double as an accessibility contract with the front end (ST-010). Changing one is a
// test change and goes through the senior-qa-engineer.
import { expect, type Page } from '@playwright/test';
import path from 'node:path';
import { answerSetup } from './sprint-01';

export const FIXTURE_CLIP = path.resolve(
  __dirname,
  '../../../fixtures/clips/synthetic-60s/clip.mp4',
);

// Dev players (ST-006 picker). They are shared by every run on a stack, so they are used only
// for journeys that never start an upload: an unfinished upload counts toward the per-owner
// quota (T-UV-7) and a reused stack would reach 429 (PD-R2-03). Empty states and uploads use a
// fresh magic-link account instead (helpers/sprint-01.ts signInByLink, uniqueEmail).
export async function signInAs(page: Page, name: 'Ivy' | 'Carlos' | 'Dana'): Promise<void> {
  // Since ST-013 the sign-in page sends a signed-in visitor to their matches, so switching
  // player in one context must sign the previous one out first, or the next steps run as them.
  await page.context().clearCookies();
  await page.goto('/');
  await page.getByRole('button', { name: new RegExp(`^(sign in as )?${name}$`, 'i') }).click();
  await expect(page.getByRole('heading', { name: /matches/i })).toBeVisible();
}

// Sprint 1 (ST-016): there is no title question any more; the match is set up with Q-01..Q-07
// and "Create match and upload" creates it and starts the upload of `file` at once. Returns the
// match URL. The server names the match (flows D-2), so callers identify it by URL or by the
// player names (TCR: journey.ts::createMatch).
export async function createMatch(
  page: Page,
  players: [string, string] = ['Ivy', 'Carlos'],
  file: string = FIXTURE_CLIP,
): Promise<string> {
  await answerSetup(page, { format: 'Singles', players, me: players[0], file });
  await page.getByRole('button', { name: 'Create match and upload' }).click();
  await expect(page).toHaveURL(/\/matches\/[0-9a-f-]{36}(\?|#|$)/);
  await expect(page.getByRole('heading', { name: 'Video upload' })).toBeVisible();
  return page.url();
}
