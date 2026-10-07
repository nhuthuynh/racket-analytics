// Sprint 3 browser helpers (QA-ACC-3, ST-054). Owner: senior-qa-engineer.
//
// UI ASSUMPTIONS until docs/design/flows-sprint-03.md (PD-1) and DR-03 exist. Every Sprint 3
// spec reads routes, names and copy from HERE, so a design decision is one edit in this file:
// - pages: stats `/matches/{id}/stats` (screen family D), evidence opened from "Show me" (E),
//   delete dialogs on the match page and `/settings/account` (X), Full Tag `/label/matches/{id}` (L)
//   (story cards sprint-03 §14.1);
// - metric cards are labelled by their dictionary name (backend metrics.json "name") as a heading;
// - copy from the Gherkin (sprint-03 §7): "n = 7", "low sample", "Show me", "See all 23",
//   "How is this measured?", "unofficial scoring (rules not yet verified)".
// The worked example's tags AND its numbers come from worked-example.reference.json, generated from
// scripts/measure/statslib.py (never by hand): `cd backend && env -u APP_ENV uv run python -c
// "from tests.support.stats import write_e2e_reference; write_e2e_reference()"`; the guard
// backend/tests/regression/test_e2e_reference.py fails when the file is stale.
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { expect, type Locator, type Page } from '@playwright/test';
import { latestSignInLink, openSignInLink, requestLink } from './sprint-01';
import { MY_SIDE, OTHER_SIDE, type Ending, type JourneyTag } from './sprint-02';

export { UNOFFICIAL, expectNoSidewaysScroll as noSidewaysScroll } from './sprint-02';

export const SCREEN = { dashboard: 'D-01', evidence: 'E-01', deleteMatch: 'X-01', deleteAccount: 'X-02', fullTag: 'L-01' } as const;
export const statsPath = (matchId: string): string => `/matches/${matchId}/stats`;
export const labelPath = (matchId: string): string => `/label/matches/${matchId}`;
export const ACCOUNT_PATH = '/settings/account';

export const METRIC_NAMES: Record<string, string> = {
  'AN-01': 'Rallies won on serve',
  'AN-02': 'Rallies won when receiving',
  'AN-03': 'Points per service turn',
  'AN-04': 'Unforced errors per game',
  'AN-05': 'Serve faults',
  'AN-06': 'Longest scoring run',
  'AN-07': 'How rallies ended',
};
export const PROPORTIONS = ['AN-01', 'AN-02', 'AN-05'] as const;

interface SideRef {
  k?: number; n?: number; value: number | null; low_sample: boolean; count?: number; longest?: number;
  points?: number; turns?: number; rallies: number[];
}
export type Reference = Record<string, Record<'A' | 'B', SideRef>>;
interface RefTag { winning_side: 'A' | 'B' | null; ending: Ending; fault_kind: string | null; responsible_player: string | null }
const REFERENCE_FILE = JSON.parse(
  readFileSync(path.resolve(__dirname, '../sprint-03/worked-example.reference.json'), 'utf8'),
) as { tags: RefTag[]; metrics: Reference };
export const REFERENCE: Reference = REFERENCE_FILE.metrics;

const DICTIONARY = JSON.parse(
  readFileSync(path.resolve(__dirname, '../../../backend/src/racket/sports/pickleball/metrics.json'), 'utf8'),
) as { entries: { id: string; name: string; definition: string; status: string }[] };
export const PUBLISHED = DICTIONARY.entries.filter((e) => e.status === 'coach-reviewed' || e.status === 'verified');
export const DRAFTS = DICTIONARY.entries.filter((e) => e.status === 'draft');
export const definitionOf = (id: string): string => DICTIONARY.entries.find((e) => e.id === id)?.definition ?? '';

const NAME_OF: Record<string, NonNullable<JourneyTag['player']>> = { A1: 'Ivy', A2: 'Dana', B1: 'Carlos', B2: 'Sam' };
const TAGS = REFERENCE_FILE.tags;

/** The coach's worked example (metric-dictionary §2) as T-01 inputs; side A (Ivy, Dana) is "mine". */
export const WORKED_EXAMPLE: readonly JourneyTag[] = TAGS.map((t) => ({
  side: t.winning_side === null ? null : t.winning_side === 'A' ? 'mine' : 'other',
  ending: t.ending,
  ...(t.responsible_player ? { player: NAME_OF[t.responsible_player] } : {}),
}));
const SLOT_MS = 4000;

async function etag(page: Page, matchId: string): Promise<string> {
  const r = await page.request.get(`/api/matches/${matchId}/score-sheet`);
  return r.headers()['etag'] ?? '"0"';
}

/** Tag the worked example through the API (for specs that test what comes after tagging). */
export async function tagWorkedExampleByApi(page: Page, matchId: string): Promise<void> {
  const start = await page.request.post(`/api/matches/${matchId}/games`, {
    headers: { 'If-Match': await etag(page, matchId) }, data: { first_serving_side: 'A', ends_switched: false },
  });
  expect(start.status(), await start.text()).toBe(201);
  for (const [i, tag] of WORKED_EXAMPLE.entries()) {
    const side = tag.side === null ? null : tag.side === 'mine' ? 'A' : 'B';
    const r = await page.request.post(`/api/matches/${matchId}/rallies`, {
      headers: { 'If-Match': await etag(page, matchId) },
      data: {
        start_ms: i * SLOT_MS, end_ms: i * SLOT_MS + 3000, winning_side: side, ending: tag.ending,
        responsible_player: TAGS[i]?.responsible_player ?? null, fault_kind: TAGS[i]?.fault_kind ?? null,
      },
    });
    expect(r.status(), await r.text()).toBe(201);
  }
}

/** Seek the T-01 video to ``seconds`` and wait until it has moved there. */
async function seekTo(page: Page, seconds: number): Promise<void> {
  await page.evaluate(async (s) => {
    const v = document.querySelector('video');
    if (!v) throw new Error('no video on T-01');
    await new Promise<void>((done) => {
      v.addEventListener('seeked', () => done(), { once: true });
      v.currentTime = s;
    });
  }, seconds);
}

/**
 * Tag the worked example on T-01 by taps, one 4 s slot per rally (14 rallies fit the 60 s clip).
 * Fault kinds (rallies 2, 6 and 12 of the example) cannot be set on T-01, so they are set
 * afterwards through the API correction route (the stats then equal the reference exactly).
 */
export async function tagWorkedExampleOnT01(page: Page, matchId: string): Promise<void> {
  const bar = page.getByRole('group', { name: 'Tag the rally' });
  const ending = { winner: 'Winner', unforced_error: 'Unforced error', forced_error: 'Forced error', fault: 'Fault', replay: 'Replay' };
  for (const [i, tag] of WORKED_EXAMPLE.entries()) {
    await seekTo(page, (i * SLOT_MS) / 1000 + 0.2);
    await bar.getByRole('button', { name: 'Rally start' }).click();
    await seekTo(page, (i * SLOT_MS) / 1000 + 3);
    await bar.getByRole('button', { name: 'Rally end' }).click();
    if (tag.side) await bar.getByRole('button', { name: tag.side === 'mine' ? MY_SIDE : OTHER_SIDE }).click();
    if (tag.player) await bar.getByRole('button', { name: tag.player, exact: true }).click();
    await bar.getByRole('button', { name: ending[tag.ending], exact: true }).click();
    await expect(page.getByRole('status').filter({ hasText: new RegExp(`^Rally ${i + 1}:`) }).first()).toBeVisible();
  }
  const sheet = (await (await page.request.get(`/api/matches/${matchId}/score-sheet`)).json()) as {
    rows: { rally_id: string }[];
  };
  for (const [i, t] of TAGS.entries()) {
    if (!t.fault_kind) continue;
    const kind = t.fault_kind;
    const r = await page.request.patch(`/api/matches/${matchId}/rallies/${sheet.rows[i]?.rally_id}`, {
      headers: { 'If-Match': await etag(page, matchId) }, data: { field: 'fault_kind', value: kind },
    });
    expect(r.status(), await r.text()).toBe(200);
  }
}

/** The card of one metric on D-01: the section or article whose heading is the metric's name. */
export function metricCard(page: Page, id: string): Locator {
  const name = METRIC_NAMES[id] ?? id;
  return page
    .locator('section, article, li')
    .filter({ has: page.getByRole('heading', { name, exact: true }) })
    .first();
}

/** One side's block inside a card: Ivy's side is "Your side", the other "Other side". */
export function sideOf(card: Locator, side: 'A' | 'B'): Locator {
  return card.locator('[data-side], div, li, tr').filter({ hasText: side === 'A' ? /Your side/ : /Other side/ }).last();
}

export const pct = (v: number | null): string => (v === null ? '—' : `${Math.round(v * 100)}%`);

/** What a card must print for one side, from the reference (NFR-034: numbers in text). */
export async function expectSidePrinted(card: Locator, id: string, side: 'A' | 'B'): Promise<void> {
  const ref = REFERENCE[id]?.[side];
  if (!ref) throw new Error(`no reference for ${id} ${side}`);
  const block = sideOf(card, side);
  if ((PROPORTIONS as readonly string[]).includes(id)) {
    if (ref.value !== null) await expect(block).toContainText(pct(ref.value));
    await expect(block).toContainText(`n = ${ref.n}`);
  } else if (id === 'AN-04') {
    await expect(block).toContainText(String(ref.count));
  } else if (id === 'AN-06') {
    await expect(block).toContainText(String(ref.longest));
  } else if (id === 'AN-03') {
    await expect(block).toContainText(String(ref.value));
  } else {
    await expect(block).toContainText(`n = ${ref.n}`);
  }
  if (ref.low_sample) await expect(block).toContainText(/low sample/i);
}

/** Run the labeller-admin CLI on the stack under test (E2E_ADMIN_CMD, e.g. a `docker compose exec` prefix). */
export function admin(args: string[]): void {
  const cmd = process.env.E2E_ADMIN_CMD;
  if (!cmd) throw new Error('E2E_ADMIN_CMD is not set: the labeller-admin CLI of the stack under test (ST-052)');
  const [bin, ...pre] = cmd.split(' ').filter(Boolean);
  execFileSync(bin ?? '', [...pre, ...args], { stdio: 'pipe', timeout: 60_000 });
}

/** Sign in with the ``nth`` link sent to ``email`` (a second device, or after deletion): waits
 * until that many emails exist, so an earlier, used link is never opened (E2E-03-04). */
export async function signInWithNthLink(page: Page, email: string, nth: number): Promise<void> {
  await requestLink(page, email);
  await openSignInLink(page, new URL(await latestSignInLink(email, nth)));
}
