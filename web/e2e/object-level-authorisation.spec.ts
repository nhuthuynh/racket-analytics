// UI view of tests/features/object_level_authorisation.feature (demo step 6, sprint-00 §12).
// Carlos opening Ivy's match URL sees the same "not found" page as for a missing match.
import { expect, test } from '@playwright/test';
import { expectNoBlockingA11yViolations } from './helpers/axe';
import { createMatch, signInAs } from './helpers/journey';

test('@M0 @story-ST-006 Carlos cannot open Ivy\'s match', async ({ browser }, testInfo) => {
  const ivy = await (await browser.newContext()).newPage();
  await signInAs(ivy, 'Ivy');
  // Distinctive player names: the match has no title since ST-016 (TCR: journey.ts::createMatch).
  const ivysMatch = await createMatch(ivy, ['Ivy', 'Zephyrine']);

  const carlos = await (await browser.newContext()).newPage();
  await signInAs(carlos, 'Carlos');
  await carlos.goto(ivysMatch);
  const notYours = (await carlos.getByRole('main').innerText()).trim();

  await carlos.goto(ivysMatch.replace(/[0-9a-f-]{36}/i, '00000000-0000-4000-8000-000000000000'));
  const missing = (await carlos.getByRole('main').innerText()).trim();

  expect(notYours).toMatch(/not found/i);
  expect(notYours).toEqual(missing);
  expect(notYours).not.toContain('Zephyrine');
  await expectNoBlockingA11yViolations(carlos, testInfo, 'not-found');
});
