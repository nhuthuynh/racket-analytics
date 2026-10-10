// UI view of tests/features/object_level_authorisation.feature (demo step 6, sprint-00 §12).
// Carlos opening Ivy's match URL sees the same "not found" page as for a missing match.
import { expect, test } from '@playwright/test';
import { expectNoBlockingA11yViolations } from './helpers/axe';
import { createMatch, signInAs } from './helpers/journey';
import { signInByLink, uniqueEmail } from './helpers/sprint-01';

test('@M0 @story-ST-006 Carlos cannot open Ivy\'s match', async ({ browser }, testInfo) => {
  // Ivy is a fresh magic-link account (PD-R2-03): createMatch starts an upload, and an upload
  // left unfinished by a slow or interrupted run must not use up a shared player's quota.
  // Carlos stays a dev player (ST-006 picker); he never uploads here.
  const ivy = await (await browser.newContext()).newPage();
  await signInByLink(ivy, uniqueEmail('ivy'));
  await ivy.goto('/matches');
  // Distinctive player names: the match has no title since ST-016 (TCR: journey.ts::createMatch).
  const ivysMatch = await createMatch(ivy, ['Ivy', 'Zephyrine']);

  const carlos = await (await browser.newContext()).newPage();
  await signInAs(carlos, 'Carlos');
  // The match page streams (/matches/loading.tsx): "Page not found" replaces the Loading…
  // fallback after page.goto resolves, so wait for it before reading (CI-E2E-MAIN-RED).
  const heading = carlos.getByRole('heading', { level: 1 });
  await carlos.goto(ivysMatch);
  await expect(heading).toHaveText('Page not found');
  const notYours = (await carlos.getByRole('main').innerText()).trim();

  await carlos.goto(ivysMatch.replace(/[0-9a-f-]{36}/i, '00000000-0000-4000-8000-000000000000'));
  await expect(heading).toHaveText('Page not found');
  const missing = (await carlos.getByRole('main').innerText()).trim();

  expect(notYours).toMatch(/not found/i);
  expect(notYours).toEqual(missing);
  expect(notYours).not.toContain('Zephyrine');
  await expectNoBlockingA11yViolations(carlos, testInfo, 'not-found');
});
