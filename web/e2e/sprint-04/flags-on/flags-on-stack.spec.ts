// The `flags-on` Playwright project (ST-065; PE-4 §10; PLAN-04 decision "flag-on E2E runs in a
// flags-on project, nightly and by the verifier"). It runs only with PW_PROJECTS=flags-on on a
// stack started with the four FEATURE_* variables set (scorecard G04-07). The flag tickets add
// their specs to this directory: E2E-04-06 age (ST-068b), E2E-04-07 privacy settings, E2E-04-08
// over-limit. This guard fails closed: a flags-on run against a flags-off stack would test the
// wrong product, so it says so instead of letting the flag specs fail one by one.
import { expect, test } from '@playwright/test';
import { FLAG_NAMES } from '../../helpers/projects';

test.describe('@story-ST-065 flags-on stack', () => {
  test('the stack under test has every Sprint 4 feature flag on (GET /config/public)', async ({ request }) => {
    const answer = await request.get('/api/config/public');
    expect(answer.status(), await answer.text()).toBe(200);
    const { features } = (await answer.json()) as { features: Record<string, boolean> };
    expect(Object.keys(features).sort()).toEqual([...FLAG_NAMES].sort());
    expect(Object.entries(features).filter(([, on]) => on !== true).map(([name]) => name), 'flags off').toEqual([]);
  });
});
