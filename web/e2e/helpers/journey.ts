// Shared steps for the walking-skeleton journeys. Selectors are role/label based on purpose:
// they double as an accessibility contract with the front end (ST-010). Changing one is a
// test change and goes through the senior-qa-engineer.
import { expect, type Page } from '@playwright/test';
import path from 'node:path';

export const FIXTURE_CLIP = path.resolve(
  __dirname,
  '../../../fixtures/clips/synthetic-60s/clip.mp4',
);

// Dana never gets a match from any spec, so empty states can be checked in any spec order
// (QA-R1-04). Ivy and Carlos accumulate matches across specs.
export async function signInAs(page: Page, name: 'Ivy' | 'Carlos' | 'Dana'): Promise<void> {
  await page.goto('/');
  await page.getByRole('button', { name: new RegExp(`^(sign in as )?${name}$`, 'i') }).click();
  await expect(page.getByRole('heading', { name: /matches/i })).toBeVisible();
}

export async function createMatch(page: Page, title: string): Promise<string> {
  await page.getByRole('link', { name: /new match/i }).click();
  await page.getByLabel(/title/i).fill(title);
  await page.getByLabel(/format/i).selectOption({ label: 'Doubles' });
  await page.getByRole('button', { name: /create match/i }).click();
  await expect(page.getByRole('heading', { name: title })).toBeVisible();
  return page.url();
}
