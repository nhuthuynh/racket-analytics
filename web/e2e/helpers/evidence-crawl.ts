// E2E-03-02 evidence crawl, one metric and side at a time (ST-054 QA; NFR-038 a and b). Kept apart
// from the spec so e2e/sprint-03/evidence-crawl-harness.spec.ts can run it against a fixture page.
//
// Every read is a retrying assertion (PE-R1-ST054-01, SRE-R1-01): D-01's cards, the "Show me"
// buttons' hydration and E-01's rallies all arrive after `goto` or the tap, so a one-shot count()
// or textContent() would fail a slow page that is right, or pass an empty side before its list
// arrives. A failed check is collected (all problems in one report) instead of stopping the crawl.
import { expect, type Locator, type Page } from '@playwright/test';
import { METRIC_NAMES, REFERENCE, metricCard, sideOf, statsPath } from './sprint-03';

const WAIT = { timeout: 10_000 };

/** E-01 when a side has n > 0 but no rally behind its number (flows-sprint-03 §3, EvidenceList). */
export const EVIDENCE_EMPTY = 'No rallies are behind this stat yet.';

/**
 * The sample size a side block prints (NFR-038 b; flows-sprint-03 §2 table): "n = x" for every
 * metric except AN-04, whose sample is its games and is printed as "x unforced errors in y games".
 * AN-06 is descriptive (never flagged) but still prints "n = x" (metric-dictionary AN-06).
 */
export function samplePrinted(id: string, side: 'A' | 'B'): RegExp {
  const ref = REFERENCE[id]?.[side];
  if (!ref) throw new Error(`no reference for ${id} ${side}`);
  if (id === 'AN-03') return new RegExp(`n = ${ref.turns}(?!\\d)`);
  if (id === 'AN-04') return new RegExp(`in ${ref.games} games?(?!\\d)`);
  return new RegExp(`n = ${ref.n}(?!\\d)`);
}

/** Open a "Show me" disclosure: a tap before hydration does nothing, so tap until it is expanded. */
async function expand(button: Locator): Promise<void> {
  await expect(async () => {
    if ((await button.getAttribute('aria-expanded')) !== 'true') await button.click();
    await expect(button).toHaveAttribute('aria-expanded', 'true', { timeout: 1_000 });
  }).toPass(WAIT);
}

/** On D-01, open E-01 for one metric and side; returns its list of rallies. */
export async function openEvidence(page: Page, id: string, side: 'A' | 'B'): Promise<Locator> {
  const buttons = metricCard(page, id).getByRole('button', { name: /Show me/ });
  await expect(buttons, `${id}: one "Show me" per side`).toHaveCount(2, WAIT);
  await expand(buttons.nth(side === 'A' ? 0 : 1));
  return page.getByRole('list', { name: new RegExp(METRIC_NAMES[id] ?? id) });
}

/** Crawl one metric and side of the worked example's stats; returns what is wrong (empty = fine). */
export async function crawlSide(page: Page, matchId: string, id: string, side: 'A' | 'B'): Promise<string[]> {
  const problems: string[] = [];
  const check = async (problem: string, assertion: () => Promise<unknown>): Promise<boolean> => {
    try {
      await assertion();
      return true;
    } catch {
      problems.push(`${id} ${side}: ${problem}`);
      return false;
    }
  };
  const sample = samplePrinted(id, side);
  const refs = REFERENCE[id]?.[side].rallies ?? [];
  const shown = Math.min(10, refs.length);
  let list: Locator | undefined;
  await page.goto(statsPath(matchId));
  await check(`sample size not printed (${sample.source})`, () => expect(sideOf(metricCard(page, id), side)).toContainText(sample, WAIT));
  if (!(await check('"Show me" missing or does not open (one per side, aria-expanded)', async () => {
    list = await openEvidence(page, id, side);
  })) || !list) return problems;
  const rallies = list.getByRole('listitem');
  if (shown === 0) {
    // Settled first, then counted: an empty side must say so, not merely show nothing yet.
    await check(`no "${EVIDENCE_EMPTY}"`, () => expect(page.getByText(EVIDENCE_EMPTY)).toBeVisible(WAIT));
    await check('rallies listed, expected none', () => expect(rallies).toHaveCount(0, { timeout: 1_000 }));
    return problems;
  }
  await check(`rallies listed != ${shown}`, () => expect(rallies).toHaveCount(shown, WAIT));
  if (refs.length > 10) await check(`no "See all ${refs.length}"`, () => expect(page.getByText(`See all ${refs.length}`)).toBeVisible(WAIT));
  // NFR-038 a: the evidence link works, i.e. the first rally opens a video that plays (not just an href).
  await check('first rally does not open a playable video', async () => {
    await list!.getByRole('link').first().click();
    await expect
      .poll(() => page.evaluate(() => {
        const v = document.querySelector('video');
        return v !== null && v.error === null && v.readyState >= 2;
      }), WAIT)
      .toBe(true);
  });
  return problems;
}
