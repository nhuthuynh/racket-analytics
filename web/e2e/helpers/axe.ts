// Accessibility helper for Playwright journeys (ST-004; NFR-027; DPA/DESIGN-14).
// Gate: 0 serious or critical axe-core violations against WCAG 2.2 AA tags.
import AxeBuilder from '@axe-core/playwright';
import { expect, type Page, type TestInfo } from '@playwright/test';

const WCAG_TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'];
const BLOCKING = new Set(['serious', 'critical']);

export async function expectNoBlockingA11yViolations(
  page: Page,
  testInfo: TestInfo,
  label: string,
): Promise<void> {
  const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
  await testInfo.attach(`axe-${label}.json`, {
    body: JSON.stringify(results.violations, null, 2),
    contentType: 'application/json',
  });
  const blocking = results.violations
    .filter((v) => v.impact != null && BLOCKING.has(v.impact))
    .map((v) => ({ id: v.id, impact: v.impact, nodes: v.nodes.map((n) => n.target.join(' ')) }));
  expect(blocking, `axe serious/critical violations on ${label}`).toEqual([]);
}

// G01-10 / NFR-028 (WCAG 2.2 SC 2.5.8): every visible interactive target is at least 24x24 CSS
// px. Measured on the page as it is, so error states count too (PD-V1-01). Attached as JSON so
// the scorecard can read the count from the Playwright report.
export async function expectTargetsAtLeast24(page: Page, testInfo: TestInfo, label: string): Promise<void> {
  const small = await page.evaluate(() =>
    [...document.querySelectorAll('a[href], button, input:not([type="hidden"]), select, textarea, [role="radio"], [role="button"], [role="link"], summary')]
      .map((el) => ({ el, r: el.getBoundingClientRect() }))
      .filter(({ r }) => r.width > 0 && r.height > 0 && (r.width < 24 || r.height < 24))
      .map(({ el, r }) => `${el.tagName.toLowerCase()}${el.className ? `.${String(el.className).split(' ').join('.')}` : ''} "${(el.textContent ?? '').trim().slice(0, 40)}" ${Math.round(r.width)}x${Math.round(r.height)}`),
  );
  await testInfo.attach(`targets-${label}.json`, { body: JSON.stringify(small, null, 2), contentType: 'application/json' });
  expect(small, `targets below 24x24 CSS px on ${label} (NFR-028)`).toEqual([]);
}
