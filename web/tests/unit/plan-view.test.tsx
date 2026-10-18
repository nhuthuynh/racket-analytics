// P-01 Your training plan (ST-063a; FR-120, FR-122, FR-123; flows-sprint-04 §2). Component tests,
// negative first: a drill whose citation is missing shows an error in its row, never a blank (HAX
// G11). Then the load states (error, empty, loading, signed out), the notices, the weaknesses, the
// sessions and drill rows, "Show me" (the E-01 EvidencePanel), the not-found refetch and the nav.
import { act, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { AccountMenu } from '@/components/AccountMenu';
import { PlanView } from '@/components/plan/PlanView';
import { ApiError } from '@/lib/api/client';
import { parsePlan, type PlanRead } from '@/lib/api/plan';
import { MATCH_ID, RALLY_ID, planBody, withFirstAssignment } from './fixtures/plan';

const evidence = {
  metricId: 'AN-05', side: 'A' as const, total: 1, sheetVersion: 3, nextCursor: null,
  items: [{ number: 7, rally_id: RALLY_ID, game: 1, start_ms: 0, end_ms: 1000 }],
};

function setup(reads: PlanRead[], evidenceFn = vi.fn(async () => evidence)) {
  const getPlan = vi.fn<() => Promise<PlanRead>>();
  for (const r of reads) getPlan.mockResolvedValueOnce(r);
  const onSignedOut = vi.fn();
  const evidenceApi = { stats: vi.fn(), evidence: evidenceFn };
  render(<PlanView api={{ getPlan }} evidenceApi={evidenceApi} onSignedOut={onSignedOut} />);
  return { getPlan, onSignedOut, evidenceFn };
}

const loaded = (body: Record<string, unknown> = planBody()): PlanRead => ({ kind: 'plan', plan: parsePlan(body) });

function drillRow(name: string): HTMLElement {
  const row = screen.getByText(name).closest('li');
  if (!row) throw new Error(`no row for ${name}`);
  return row;
}

describe('P-01 a drill without a citation (negative first)', () => {
  it('citation missing -> visible error, not blank', async () => {
    setup([loaded(withFirstAssignment((a) => { a.citation = null; }))]);
    await screen.findByText('Serve to a target');
    const row = drillRow('Serve to a target');
    expect(within(row).getByText('We could not show why this drill was chosen.')).toBeVisible();
    expect(within(row).queryByText(/^Why:/)).toBeNull();
    expect(within(row).queryByRole('button', { name: /^Show me/ })).toBeNull();
    // The other rows still say why.
    expect(within(drillRow('Wall resets')).getByText('Why: Unforced errors: 2.0 over 1 game')).toBeVisible();
  });

  it('a citation without its n is the same visible error', async () => {
    setup([loaded(withFirstAssignment((a) => { delete (a.citation as Record<string, unknown>).n; }))]);
    await screen.findByText('Serve to a target');
    expect(within(drillRow('Serve to a target')).getByText('We could not show why this drill was chosen.')).toBeVisible();
  });

  it('a drill without its why text is the same visible error', async () => {
    setup([loaded(withFirstAssignment((a) => { a.why = ''; }))]);
    await screen.findByText('Serve to a target');
    expect(within(drillRow('Serve to a target')).getByText('We could not show why this drill was chosen.')).toBeVisible();
  });
});

describe('P-01 load states', () => {
  it('error: one alert with what to do and the reference, and "Try again" reloads', async () => {
    const { getPlan } = setup([{ kind: 'error', supportRef: 'ref_0123456789abcdef' }, loaded()]);
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('We could not load your plan. Try again.');
    expect(alert).toHaveTextContent('Reference: ref_0123456789abcdef');
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(await screen.findByRole('heading', { name: 'What the plan works on' })).toBeVisible();
    expect(getPlan).toHaveBeenCalledTimes(2);
  });

  it('empty, no tagged match: says how to get a plan and links to the matches', async () => {
    setup([{ kind: 'no_tagged_match' }]);
    expect(await screen.findByText('Tag a match to get a plan. The plan is built from the rallies you tag.')).toBeVisible();
    expect(screen.getByRole('link', { name: 'Your matches' })).toHaveAttribute('href', '/matches');
    expect(screen.queryByRole('link', { name: 'Make my plan' })).toBeNull();
  });

  it('empty, no plan yet: offers "Make my plan" and still says where plans come from', async () => {
    setup([{ kind: 'no_plan' }]);
    expect(await screen.findByText('You have no plan yet.')).toBeVisible();
    expect(screen.getByRole('link', { name: 'Make my plan' })).toHaveAttribute('href', '/plan/new');
    expect(screen.getByText(/The plan is built from the rallies you tag\./)).toBeVisible();
    expect(screen.getByRole('link', { name: 'Your matches' })).toHaveAttribute('href', '/matches');
  });

  it('loading: a busy region that says so politely', () => {
    const getPlan = vi.fn(() => new Promise<PlanRead>(() => {}));
    render(<PlanView api={{ getPlan }} evidenceApi={{ stats: vi.fn(), evidence: vi.fn() }} />);
    expect(screen.getByRole('status')).toHaveTextContent('Loading your plan');
    expect(screen.getByRole('status').closest('[aria-busy="true"]')).not.toBeNull();
  });

  it('signed out: goes to sign-in', async () => {
    const { onSignedOut } = setup([{ kind: 'signed_out' }]);
    await vi.waitFor(() => expect(onSignedOut).toHaveBeenCalledOnce());
  });
});

describe('P-01 header and notices', () => {
  it('says when and from how many tagged matches, and links to the setup', async () => {
    setup([loaded()]);
    expect(await screen.findByText('Made on 17 Oct 2026 from 1 tagged match.')).toBeVisible();
    expect(screen.getByRole('link', { name: 'Change my setup' })).toHaveAttribute('href', '/plan/new');
  });

  it('shows the unofficial notice once, then the human-coach notice, then the limited-data banner, before the first card', async () => {
    setup([loaded()]);
    const heading = await screen.findByRole('heading', { name: 'What the plan works on' });
    const unofficial = screen.getAllByText('unofficial scoring (rules not yet verified)');
    expect(unofficial).toHaveLength(1);
    const coach = screen.getByText('These drills have not yet been checked by a human coach. Warm up first, and stop any drill that hurts.');
    const limited = screen.getByText('Based on limited data from 14 rallies. Tag more matches for a firmer plan.');
    const order = [unofficial[0]!, coach, limited, heading];
    for (let i = 1; i < order.length; i += 1) {
      expect(order[i - 1]!.compareDocumentPosition(order[i]!) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    }
  });

  it('drops each notice when the plan no longer needs it', async () => {
    const body = { ...planBody(), unofficial: false, drills_verified: true, limited_data: null };
    setup([loaded(body)]);
    await screen.findByRole('heading', { name: 'What the plan works on' });
    expect(screen.queryByText('unofficial scoring (rules not yet verified)')).toBeNull();
    expect(screen.queryByText(/checked by a human coach/)).toBeNull();
    expect(screen.queryByText(/Based on limited data/)).toBeNull();
  });
});

describe('P-01 what the plan works on', () => {
  it('lists the weaknesses in rank order with the unit, the split and the games, and the split once as not verified', async () => {
    setup([loaded()]);
    const list = await screen.findByRole('list', { name: 'What the plan works on' });
    const items = within(list).getAllByRole('listitem');
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveTextContent('Unforced errors');
    expect(items[0]).toHaveTextContent('2 rallies lost per game');
    expect(items[0]).toHaveTextContent('On serve: 1 · On receive: 1 · Points given away: 1 per game');
    expect(items[0]).toHaveTextContent('from 1 game');
    expect(items[1]).toHaveTextContent('Serve faults');
    expect(screen.getAllByText('The split between serve and receive is not yet verified.')).toHaveLength(1);
  });

  it('says when no drill fits a weakness, with a way to change the setup', async () => {
    setup([loaded({ ...planBody(), unfitted: [{ weakness_id: 'serve_faults', reason: 'no_drill_fits' }] })]);
    const list = await screen.findByRole('list', { name: 'What the plan works on' });
    const serve = within(list).getAllByRole('listitem')[1]!;
    expect(serve).toHaveTextContent('No drill fits your setup for this one.');
    expect(within(serve).getByRole('link', { name: 'Change my setup' })).toHaveAttribute('href', '/plan/new');
  });
});

describe('P-01 your sessions and drill rows', () => {
  it('groups the sessions by week and orders each session\'s drills, warm-up first', async () => {
    setup([loaded()]);
    expect(await screen.findByRole('heading', { level: 3, name: 'Week 1' })).toBeVisible();
    expect(screen.getByText('Session 1 of 3 · 30 minutes')).toBeVisible();
    expect(screen.getByText('Session 2 of 3 · 30 minutes')).toBeVisible();
    const first = screen.getByRole('list', { name: 'Session 1 of 3 · 30 minutes' });
    const rows = within(first).getAllByRole('listitem');
    expect(rows[0]).toHaveTextContent('Wall dinks warm-up');
    expect(rows[0]).toHaveTextContent('Warm-up');
    expect(rows[1]).toHaveTextContent('Serve to a target');
  });

  it('shows name, minutes, players, equipment and why with metric, value and n', async () => {
    setup([loaded()]);
    await screen.findByText('Serve to a target');
    const serve = drillRow('Serve to a target');
    expect(within(serve).getByText('12 minutes · 1 player · Needs: a wall')).toBeVisible();
    expect(within(serve).getByText('Why: Serve faults: 29% of 7 serves')).toBeVisible();
    expect(within(serve).getByText('low sample')).toBeVisible();
    expect(within(drillRow('Wall dinks warm-up')).getByText('8 minutes · 1 player · Needs: nothing extra')).toBeVisible();
    const reset = drillRow('Wall resets');
    expect(within(reset).getByText('20 minutes · 2 players · Needs: a wall, a ball machine')).toBeVisible();
    expect(within(reset).queryByText('low sample')).toBeNull();
  });

  it('"Show me" names the metric and value, and opens the evidence panel for that metric and side', async () => {
    const { evidenceFn } = setup([loaded()]);
    await screen.findByText('Serve to a target');
    const show = within(drillRow('Serve to a target')).getByRole('button', { name: 'Show me the rallies behind Serve faults, 29%' });
    expect(show).toHaveAttribute('aria-expanded', 'false');
    await userEvent.click(show);
    expect(show).toHaveAttribute('aria-expanded', 'true');
    expect(evidenceFn).toHaveBeenCalledWith(MATCH_ID, 'AN-05', 'A');
    const panel = document.getElementById(show.getAttribute('aria-controls') ?? '');
    expect(panel).not.toBeNull();
    expect(await within(panel as HTMLElement).findByRole('link', { name: /Rally 7/ })).toHaveAttribute(
      'href', `/matches/${MATCH_ID}/sheet?play=${RALLY_ID}`,
    );
    expect(within(panel as HTMLElement).queryByText(/These stats changed/)).toBeNull();
    await userEvent.click(show);
    expect(show).toHaveAttribute('aria-expanded', 'false');
  });

  it('"Show me" works from the keyboard', async () => {
    const { evidenceFn } = setup([loaded()]);
    await screen.findByText('Serve to a target');
    const show = within(drillRow('Serve to a target')).getByRole('button', { name: /^Show me/ });
    show.focus();
    await userEvent.keyboard('{Enter}');
    expect(show).toHaveAttribute('aria-expanded', 'true');
    expect(evidenceFn).toHaveBeenCalledOnce();
  });
});

describe('P-01 not found', () => {
  it('a cited match that is gone: the plan is fetched again with a polite line', async () => {
    const gone = vi.fn(async () => { throw new ApiError(404, 'not_found'); });
    const { getPlan } = setup([loaded(), loaded()], gone);
    await screen.findByText('Serve to a target');
    await userEvent.click(within(drillRow('Serve to a target')).getByRole('button', { name: /^Show me/ }));
    await userEvent.click(await screen.findByRole('button', { name: 'Reload the stats' }));
    await act(async () => {});
    expect(getPlan).toHaveBeenCalledTimes(2);
    expect(await screen.findByText('Your plan changed on another device. Showing your current plan.')).toBeVisible();
  });
});

describe('P-01 navigation', () => {
  it('the account menu links to the training plan', async () => {
    render(<AccountMenu api={{ signOut: vi.fn() }} navigate={vi.fn()} clear={vi.fn(async () => {})} />);
    await userEvent.click(screen.getByRole('button', { name: 'Your account' }));
    expect(screen.getByRole('link', { name: 'Training plan' })).toHaveAttribute('href', '/plan');
  });
});
