// E2E-03-02 evidence crawl, one metric and side at a time (ST-054 QA; NFR-038 a and b). Kept apart
// from the spec so e2e/sprint-03/evidence-crawl-harness.spec.ts can run it against a fixture page.
import type { Page } from '@playwright/test';
import { METRIC_NAMES, REFERENCE, metricCard, statsPath } from './sprint-03';

/** Crawl one metric and side of the worked example's stats; returns what is wrong (empty = fine). */
export async function crawlSide(page: Page, matchId: string, id: string, side: 'A' | 'B'): Promise<string[]> {
  const problems: string[] = [];
  await page.goto(statsPath(matchId));
  const card = metricCard(page, id);
  if (!(await card.textContent())?.includes('n =') && id !== 'AN-04' && id !== 'AN-06') {
    problems.push(`${id}: no "n =" printed`);
  }
  const buttons = card.getByRole('button', { name: /Show me/ });
  if ((await buttons.count()) < 2) { problems.push(`${id}: fewer than 2 "Show me" (one per side)`); return problems; }
  await buttons.nth(side === 'A' ? 0 : 1).click();
  const refs = REFERENCE[id]?.[side].rallies ?? [];
  const list = page.getByRole('list', { name: new RegExp(METRIC_NAMES[id] ?? id) });
  const shown = Math.min(10, refs.length);
  if ((await list.getByRole('listitem').count()) !== shown) problems.push(`${id} ${side}: items != ${shown}`);
  if (refs.length > 10 && !(await page.getByText(`See all ${refs.length}`).count())) {
    problems.push(`${id} ${side}: no "See all ${refs.length}"`);
  }
  if (shown > 0) {
    const href = await list.getByRole('link').first().getAttribute('href');
    if (!href) problems.push(`${id} ${side}: first rally has no link`);
  }
  return problems;
}
