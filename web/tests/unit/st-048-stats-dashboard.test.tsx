// ST-048 D-01 stats dashboard and ST-047 E-01 "Show me" (FR-100..FR-103, FR-055; NFR-034, NFR-038,
// NFR-039, NFR-058; flows-sprint-03 §2, §3). Negative and state cases first: error (alert, Try
// again, no numbers), loading (busy region, no numbers), empty (no request, link to tagging),
// nothing published; then the cards and the evidence panel.
import { act, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { StatsDashboard, type StatsApi } from '@/components/stats/StatsDashboard';
import { ApiError } from '@/lib/api/client';
import type { Match } from '@/lib/api/types';
import { parseStats } from '@/lib/stats/parse';
import type { Evidence, Stats } from '@/lib/stats/types';
import { WORKED_BODY } from './fixtures/stats';

const ID = '0b8f6c1e-3f3a-4c55-9a51-8d1f0e7d2a10';
const RALLY = (n: number) => `7d0c6c1e-3f3a-4c55-9a51-8d1f0e7d2a${String(n).padStart(2, '0')}`;
const REF = 'ref_0123456789abcdef';
const match: Match = {
  id: ID, title: 'Saturday doubles', format: 'doubles', status: 'video_received', media: null,
  created_at: 'x', updated_at: 'x', upload: null, rejection: null,
  participants: [
    { slot: 'A1', nickname: 'Ivy', is_me: true }, { slot: 'A2', nickname: 'Dana', is_me: false },
    { slot: 'B1', nickname: 'Carlos', is_me: false }, { slot: 'B2', nickname: 'Sam', is_me: false },
  ],
};
const stats = (): Stats => parseStats(structuredClone(WORKED_BODY));
const evidence = (over: Partial<Evidence> = {}): Evidence => ({
  metricId: 'AN-01', side: 'A', total: 7, sheetVersion: 15, nextCursor: null,
  items: [1, 3, 4].map((n) => ({ number: n, rally_id: RALLY(n), game: 1, start_ms: (n - 1) * 4000, end_ms: (n - 1) * 4000 + 3000 })),
  ...over,
});

function api(over: Partial<StatsApi> = {}): StatsApi {
  return { stats: vi.fn(async () => stats()), evidence: vi.fn(async () => evidence()), ...over };
}

async function loaded(a: StatsApi = api()) {
  render(<StatsDashboard match={match} rallyCount={14} api={a} />);
  await screen.findByRole('heading', { name: 'Rallies won on serve' });
  return a;
}

describe('D-01 states (E2E-03-09)', () => {
  it('error: one alert with fixed words and the reference, a Try again button, and no numbers', async () => {
    const a = api({ stats: vi.fn().mockRejectedValueOnce(new ApiError(503, 'unavailable', REF)).mockResolvedValue(stats()) });
    render(<StatsDashboard match={match} rallyCount={14} api={a} />);
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(`Your stats could not be loaded. Try again. Reference: ${REF}`);
    expect(alert).not.toHaveTextContent(/unavailable|503/);
    expect(screen.queryByRole('button', { name: /Show me/ })).toBeNull();
    expect(screen.queryByText(/n = \d+/)).toBeNull();

    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(await screen.findByRole('heading', { name: 'Rallies won on serve' })).toBeVisible();
    expect(screen.queryByRole('alert')).toBeNull();
    expect(a.stats).toHaveBeenCalledTimes(2);
  });

  it('offline: says the connection dropped', async () => {
    render(<StatsDashboard match={match} rallyCount={14} api={api({ stats: vi.fn().mockRejectedValue(new ApiError(0, 'network_error')) })} />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Your stats could not be loaded because the connection dropped. Try again.');
  });

  it('loading: a busy region with a polite status, no numbers and no Show me; then none busy', async () => {
    let answer: (s: Stats) => void = () => {};
    const a = api({ stats: vi.fn(() => new Promise<Stats>((r) => { answer = r; })) });
    const { container } = render(<StatsDashboard match={match} rallyCount={14} api={a} />);
    const busy = container.querySelector('[aria-busy="true"]');
    expect(busy).not.toBeNull();
    expect(within(busy as HTMLElement).getByRole('status')).toHaveTextContent('Loading your stats…');
    expect(screen.queryByRole('button', { name: /Show me/ })).toBeNull();
    await act(async () => answer(stats()));
    expect(await screen.findByRole('heading', { name: 'Rallies won on serve' })).toBeVisible();
    expect(container.querySelector('[aria-busy="true"]')).toBeNull();
  });

  it('empty, no rally tagged: says so, links to tagging, asks the API nothing and prints no number', () => {
    const a = api();
    render(<StatsDashboard match={match} rallyCount={0} api={a} />);
    expect(screen.getByText('No rallies are tagged yet, so there are no stats to show.')).toBeVisible();
    expect(screen.getByRole('link', { name: 'Tag rallies' })).toHaveAttribute('href', `/matches/${ID}/tag`);
    expect(a.stats).not.toHaveBeenCalled();
    expect(screen.queryByText(/n = \d+/)).toBeNull();
  });

  it('empty, no video yet: says when stats appear and links back to the match', () => {
    const a = api();
    render(<StatsDashboard match={{ ...match, status: 'awaiting_upload' }} rallyCount={0} api={a} />);
    expect(screen.getByText("You can see stats once this match's video is received and rallies are tagged.")).toBeVisible();
    expect(screen.getByRole('link', { name: 'Back to the match' })).toHaveAttribute('href', `/matches/${ID}`);
    expect(a.stats).not.toHaveBeenCalled();
  });

  it('nothing published (metrics {}) is not an error: says stats appear once the coach has checked them', async () => {
    render(<StatsDashboard match={match} rallyCount={14} api={api({ stats: vi.fn(async () => ({ ...stats(), metrics: [] })) })} />);
    expect(await screen.findByText('No stats are ready to show yet. Each stat appears once our coach has checked how it is measured.')).toBeVisible();
    expect(screen.queryByRole('alert')).toBeNull();
  });
});

describe('D-01 cards (FR-100, FR-101, FR-102, FR-055)', () => {
  it('shows the unofficial notice once, before the first card, and one card per published metric in order', async () => {
    const { container } = render(<StatsDashboard match={match} rallyCount={14} api={api()} />);
    await screen.findByRole('heading', { name: 'Rallies won on serve' });
    expect(screen.getAllByText('unofficial scoring (rules not yet verified)')).toHaveLength(1);
    const headings = screen.getAllByRole('heading', { level: 2 }).map((h) => h.textContent);
    expect(headings).toEqual(['Rallies won on serve', 'Name of AN-03', 'Name of AN-04', 'Name of AN-05', 'Name of AN-06', 'Name of AN-07']);
    const notice = screen.getByText('unofficial scoring (rules not yet verified)');
    const firstCard = container.querySelector('section');
    expect(notice.compareDocumentPosition(firstCard as Node) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('prints each side with its names, value, k of n, n and range, your side first; low sample in words', async () => {
    await loaded();
    const card = screen.getByRole('region', { name: 'Rallies won on serve' });
    const sides = within(card).getAllByRole('heading', { level: 3 }).map((h) => h.textContent);
    expect(sides).toEqual(['Your side (Ivy and Dana)', 'Other side (Carlos and Sam)']);
    const mine = card.querySelector('[data-side="A"]') as HTMLElement;
    expect(mine).toHaveTextContent('57%');
    expect(mine).toHaveTextContent('4 of 7 rallies · n = 7 · range 25% to 84%');
    expect(within(mine).getByText('low sample')).toBeVisible();
    expect(mine).toHaveTextContent('Low sample: fewer than 20 rallies, or the range is wider than 30 points. Treat it as a rough guide.');
  });

  it('one "Show me" per side whose accessible name starts with its visible words (SC 2.5.3)', async () => {
    await loaded();
    const card = screen.getByRole('region', { name: 'Rallies won on serve' });
    const buttons = within(card).getAllByRole('button', { name: /^Show me/ });
    expect(buttons.map((b) => b.getAttribute('aria-label'))).toEqual([
      'Show me the 7 rallies, Rallies won on serve, your side',
      'Show me the 6 rallies, Rallies won on serve, other side',
    ]);
    expect(buttons[0]).toHaveTextContent('Show me the 7 rallies');
    expect(buttons[0]).toHaveAttribute('aria-expanded', 'false');
  });

  it('a side with n = 0 has no Show me, and says so in words', async () => {
    await loaded();
    const card = screen.getByRole('region', { name: 'Name of AN-07' });
    const other = card.querySelector('[data-side="B"]') as HTMLElement;
    expect(within(other).queryByRole('button', { name: /Show me/ })).toBeNull();
    expect(other).toHaveTextContent('No rallies yet · n = 0');
    expect(other).toHaveTextContent('No rallies behind this yet.');
  });

  it('AN-04 per player uses the match nicknames; AN-07 rows print every value with hidden bars', async () => {
    await loaded();
    const an04 = screen.getByRole('region', { name: 'Name of AN-04' });
    expect(an04.querySelector('[data-side="A"]')).toHaveTextContent('Ivy 1 · Dana 1');
    expect(an04.querySelector('[data-side="B"]')).toHaveTextContent('player not tagged in 1 rally');
    const an07 = screen.getByRole('region', { name: 'Name of AN-07' });
    const mine = an07.querySelector('[data-side="A"]') as HTMLElement;
    expect(mine).toHaveTextContent('Winners: 2 (33%, range 10% to 70%)');
    expect(mine).toHaveTextContent('Forced errors: 0 (0%, range 0% to 39%)');
    for (const bar of mine.querySelectorAll('.bar')) expect(bar).toHaveAttribute('aria-hidden', 'true');
  });

  it('"How is this measured?" discloses the definition, the smallest sample and the version', async () => {
    await loaded();
    const card = screen.getByRole('region', { name: 'Rallies won on serve' });
    const how = within(card).getByRole('button', { name: 'How is this measured?' });
    expect(how).toHaveAttribute('aria-expanded', 'false');
    expect(within(card).queryByText('Definition of AN-01.')).toBeNull();
    await userEvent.click(how);
    expect(how).toHaveAttribute('aria-expanded', 'true');
    expect(within(card).getByText('Definition of AN-01.')).toBeVisible();
    expect(within(card).getByText('Smallest sample we trust: 20 rallies.')).toBeVisible();
    expect(within(card).getByText('Definition version 0.1, checked by our coach.')).toBeVisible();
    const runs = screen.getByRole('region', { name: 'Name of AN-06' });
    await userEvent.click(within(runs).getByRole('button', { name: 'How is this measured?' }));
    expect(within(runs).getByText('Not flagged: this describes the match, it is not an estimate.')).toBeVisible();
  });
});

describe('E-01 "Show me" panel (ST-047; E2E-03-02, E2E-03-09)', () => {
  it('error: an alert in the panel with Try again and no rally links; Try again lists them', async () => {
    const a = await loaded(api({
      evidence: vi.fn().mockRejectedValueOnce(new ApiError(503, 'unavailable', REF)).mockResolvedValue(evidence()),
    }));
    await userEvent.click(screen.getAllByRole('button', { name: /^Show me/ })[0]!);
    expect(await screen.findByRole('alert')).toHaveTextContent(`The rallies for this stat could not be loaded. Try again. Reference: ${REF}`);
    expect(screen.queryByRole('link', { name: /Rally \d+/ })).toBeNull();
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(await screen.findByRole('link', { name: 'Rally 1 · game 1 · 0:00' })).toBeVisible();
    expect(a.evidence).toHaveBeenCalledWith(ID, 'AN-01', 'A');
  });

  it('loading: a busy region inside the panel, then the list', async () => {
    let answer: (e: Evidence) => void = () => {};
    const { container } = render(
      <StatsDashboard match={match} rallyCount={14} api={api({ evidence: vi.fn(() => new Promise<Evidence>((r) => { answer = r; })) })} />,
    );
    await screen.findByRole('heading', { name: 'Rallies won on serve' });
    await userEvent.click(screen.getAllByRole('button', { name: /^Show me/ })[0]!);
    expect(within(container.querySelector('[aria-busy="true"]') as HTMLElement).getByRole('status')).toHaveTextContent('Loading the rallies…');
    await act(async () => answer(evidence()));
    expect(await screen.findByRole('link', { name: /Rally 1/ })).toBeVisible();
    expect(container.querySelector('[aria-busy="true"]')).toBeNull();
  });

  it('lists up to 10 rallies in a list named after the stat; each opens the score sheet at that rally', async () => {
    await loaded();
    const show = screen.getAllByRole('button', { name: /^Show me/ })[0]!;
    await userEvent.click(show);
    expect(show).toHaveAttribute('aria-expanded', 'true');
    const list = await screen.findByRole('list', { name: 'Rallies behind “Rallies won on serve”, your side' });
    const links = within(list).getAllByRole('link');
    expect(links.map((l) => l.textContent)).toEqual(['Rally 1 · game 1 · 0:00', 'Rally 3 · game 1 · 0:08', 'Rally 4 · game 1 · 0:12']);
    expect(links[0]).toHaveAttribute('href', `/matches/${ID}/sheet?play=${RALLY(1)}`);
    expect(screen.queryByText(/See all/)).toBeNull();
    await userEvent.click(show);
    expect(screen.queryByRole('list', { name: /Rallies behind/ })).toBeNull();
  });

  it('more than 10: "See all 23" opens the full list page for that stat and side', async () => {
    await loaded(api({ evidence: vi.fn(async () => evidence({ total: 23 })) }));
    await userEvent.click(screen.getAllByRole('button', { name: /^Show me/ })[1]!);
    expect(await screen.findByRole('link', { name: 'See all 23' })).toHaveAttribute('href', `/matches/${ID}/stats/AN-01/evidence?side=B`);
  });

  it('no rally behind it: says so instead of an empty list', async () => {
    await loaded(api({ evidence: vi.fn(async () => evidence({ total: 0, items: [] })) }));
    await userEvent.click(screen.getAllByRole('button', { name: /^Show me/ })[0]!);
    expect(await screen.findByText('No rallies are behind this stat yet.')).toBeVisible();
    expect(screen.queryByRole('list', { name: /Rallies behind/ })).toBeNull();
  });

  it('stale: a different sheet version says the stats changed and offers to reload them', async () => {
    const a = await loaded(api({ evidence: vi.fn(async () => evidence({ sheetVersion: 16 })) }));
    await userEvent.click(screen.getAllByRole('button', { name: /^Show me/ })[0]!);
    expect(await screen.findByText('These stats changed since you opened this page. Reload the stats to see the new numbers.')).toBeVisible();
    await userEvent.click(screen.getByRole('button', { name: 'Reload the stats' }));
    expect(a.stats).toHaveBeenCalledTimes(2);
  });

  it('a stat that is gone (404): says so instead of rally links', async () => {
    await loaded(api({ evidence: vi.fn().mockRejectedValue(new ApiError(404, 'not_found')) }));
    await userEvent.click(screen.getAllByRole('button', { name: /^Show me/ })[0]!);
    expect(await screen.findByRole('alert')).toHaveTextContent('This stat is no longer available. Reload the stats.');
  });
});
