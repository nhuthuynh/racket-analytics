// Sprint 4 browser helpers (ST-065). Owner: senior-qa-engineer.
//
// Every Sprint 4 spec reads the P-01..P-03 words, routes and the plan setup from HERE, so a design
// or library change is one edit in this file:
// - words: docs/design/flows-sprint-04.md §2-§4 (as built in components/plan/*, ST-063a..c);
// - setup: the P-02 answers every spec uses (30 minutes, 2 sessions a week, 2 players, a wall and
//   half a court, intermediate). For the coach's worked example the plan is deterministic
//   (rules-only assembly, ST-056): week 1 session 1 is a warm-up and CITED, session 2 a warm-up,
//   SWAPPABLE and CITED. SWAPPABLE has another drill for its weakness. Since QA-VERIFY04R3-01
//   (a second wall drill per target) CITED has one too, so the no-alternative case (E2E-04-04,
//   409 `no_alternative`) uses NO_ALTERNATIVE_SETUP, where NO_ALTERNATIVE is the one AN-02 drill
//   that fits (decisions/QA-VERIFY04R3-01.md).
import { expect, type Locator, type Page } from '@playwright/test';
import { receivedMatch } from './sprint-02';
import { tagWorkedExampleByApi } from './sprint-03';

export const PLAN_PATH = '/plan';
export const PLAN_NEW_PATH = '/plan/new';
export const SCREEN_P = { plan: 'P-01', setup: 'P-02', swap: 'P-03' } as const;

export const PLAN_COPY = {
  noPlan: 'You have no plan yet.',
  tagFirst: /Tag a match first/,
  limited: (rallies: number) => `Based on limited data from ${rallies} rallies. Tag more matches for a firmer plan.`,
  loading: 'Loading your plan…',
  error: 'We could not load your plan. Try again.',
  changed: 'Your plan changed on another device. Showing your current plan.',
  queued: 'Saved on this device, will sync',
  synced: (index: number) => `Session ${index} synced.`,
  needsConnection: 'Needs a connection',
  noAlternative: 'No other drill fits your setup for this. Your plan is unchanged.',
} as const;

/** The P-02 answers, as the API body (api-sprint-04 §2.1) and as the page's words. */
export const SETUP = {
  minutes_per_session: 30,
  sessions_per_week: 2,
  players_available: 2,
  equipment: ['wall', 'half_court'],
  level: 'intermediate',
} as const;

/** Cites AN-02 "Rallies won when receiving". */
export const CITED = 'Deep return strokes against a wall';
/** SETUP with a full court instead of a wall and half a court: one AN-02 drill fits (E2E-04-04). */
export const NO_ALTERNATIVE_SETUP = { ...SETUP, equipment: ['full_court'] } as const;
/** Cites AN-02 under NO_ALTERNATIVE_SETUP; no other drill fits it (409 `no_alternative`). */
export const NO_ALTERNATIVE = 'Deep return to a target zone';
/** Has another drill for the same weakness in its session (E2E-04-01 swap). */
export const SWAPPABLE = 'Safe-margin target dinks';

/** P-02 answered by pointer with SETUP; stops before "Make my plan". */
export async function answerPlanSetup(page: Page): Promise<void> {
  await expect(page.getByRole('heading', { level: 1, name: 'Your practice setup' })).toBeVisible();
  await page.getByLabel('How long is each session?').fill(String(SETUP.minutes_per_session));
  await page.getByRole('group', { name: 'How many sessions a week?' }).getByLabel(String(SETUP.sessions_per_week), { exact: true }).check();
  await page.getByRole('group', { name: 'How many players, including you?' }).getByLabel(String(SETUP.players_available), { exact: true }).check();
  await page.getByLabel('A wall').check();
  await page.getByLabel('Half a court').check();
  await page.getByLabel('Intermediate').check();
}

export interface PlanBody {
  id: string;
  version: number;
  limited_data: { rallies: number } | null;
  sessions: { id: string; index: number; week: number; done: boolean; assignments: { id: string; drill: { name: string }; citation: { low_sample: boolean } | null }[] }[];
}

/** The plan as the API holds it (GET /me/plan through the web origin). */
export async function planRead(page: Page): Promise<PlanBody> {
  const r = await page.request.get('/api/me/plan');
  expect(r.status(), await r.text()).toBe(200);
  return (await r.json()) as PlanBody;
}

/** A fresh account with the worked example tagged on a received match and a plan made with `setup`. */
export async function planReadyAccount(
  page: Page,
  setup: typeof SETUP | typeof NO_ALTERNATIVE_SETUP = SETUP,
): Promise<{ matchId: string; plan: PlanBody }> {
  const matchId = await receivedMatch(page, 'Saturday doubles');
  await tagWorkedExampleByApi(page, matchId);
  const made = await page.request.post('/api/me/plan', { data: setup });
  expect(made.status(), await made.text()).toBe(201);
  return { matchId, plan: (await made.json()) as PlanBody };
}

/** A drill row on P-01 by drill name (the first, in plan order). */
export function drillRow(page: Page, name: string): Locator {
  return page.locator('li[id^="drill-"]').filter({ has: page.locator('strong', { hasText: name }) }).first();
}

/** Week 1's session `index` on P-01 ("Session 1 of 2 · 30 minutes"). */
export function sessionOf(page: Page, index: number): Locator {
  const title = `Session ${index} of ${SETUP.sessions_per_week} · ${SETUP.minutes_per_session} minutes`;
  return page.locator('section').filter({ has: page.getByRole('heading', { level: 4, name: title }) }).first();
}

/** "Why: <metric>: <value> of|over <n> <unit>" → its parts; null when any part is missing (FR-122). */
export function parseWhy(text: string): { metric: string; value: string; n: number } | null {
  const m = /^Why: ([^:]+\S): (\S+) (?:of|over) (\d+) \S/.exec(text.trim());
  if (!m || /^\d/.test(m[1] ?? '')) return null;
  return { metric: m[1] ?? '', value: m[2] ?? '', n: Number(m[3]) };
}

/** The parsed "why" of one drill row on P-01. */
export async function whyOf(row: Locator): Promise<ReturnType<typeof parseWhy>> {
  return parseWhy((await row.getByText(/^Why: /).first().textContent()) ?? '');
}

/** Press Tab until `focused()` holds; the number of presses, or an error naming the target. */
export async function tabUntil(
  press: () => Promise<void>,
  focused: () => Promise<boolean>,
  { max = 100, target }: { max?: number; target: string },
): Promise<number> {
  for (let presses = 0; ; presses++) {
    if (await focused()) return presses;
    if (presses >= max) throw new Error(`Tab did not reach ${target} in ${max} presses`);
    await press();
  }
}

/**
 * Wait until the service worker controls the page and has kept this plan for offline reads: a
 * reload through it stores the /plan shell and the plan read (public/sw.js, network first).
 */
export async function untilPlanKeptOffline(page: Page): Promise<void> {
  await page.evaluate(async () => {
    await navigator.serviceWorker.ready;
  });
  if (!(await page.evaluate(() => navigator.serviceWorker.controller !== null))) await page.reload();
  await expect.poll(() => page.evaluate(() => navigator.serviceWorker.controller !== null)).toBe(true);
  await page.reload();
  await expect(page.getByRole('heading', { level: 2, name: 'Your sessions' })).toBeVisible();
  await expect
    .poll(() =>
      page.evaluate(async () => {
        const cache = await caches.open('ra-plan-v1');
        return Boolean((await cache.match('/plan')) && (await cache.match('/api/me/plan')));
      }),
    )
    .toBe(true);
}
