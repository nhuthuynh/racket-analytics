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
