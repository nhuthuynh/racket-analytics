// ST-052 review round 1, PE-ST052-R1-04: the save is one POST per label (api-sprint-03 §5.2) and
// none can be safely repeated, so a retry after a failure must first read what the server holds
// (GET /label/matches/{id}) and send only what is missing. The fake below is a small stateful
// server that keeps the §5.2/§5.4 rules (overlaps_rally, no_rally, out_of_order, version + 1 per
// accepted command) and can apply a command and then lose its response, as a dropped connection
// does. Negative cases first: the blind retry would be refused or would duplicate a gold label.
import { act, fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { FullTag, type FullTagApi } from '@/components/label/FullTag';
import { ApiError } from '@/lib/api/client';
import type { Match } from '@/lib/api/types';
import type { EventLabel, LabelDocument, LabelSession, RallyLabel, SavedRally } from '@/lib/label/types';

const ID = '0b8f6c1e-3f3a-4c55-9a51-8d1f0e7d2a10';
const match: Match = {
  id: ID, title: 'Team clip 1', format: 'doubles', status: 'video_received', media: null,
  created_at: 'x', updated_at: 'x', upload: null, rejection: null,
  participants: [
    { slot: 'A1', nickname: 'Ivy', is_me: true }, { slot: 'A2', nickname: 'Dana', is_me: false },
    { slot: 'B1', nickname: 'Carlos', is_me: false }, { slot: 'B2', nickname: 'Sam', is_me: false },
  ],
};

/** A stateful stand-in for the label routes. `loseAfterApplying` lists POST call numbers (1-based)
 *  whose command is stored but whose response never arrives. */
function fakeServer(loseAfterApplying: number[] = []) {
  const rallies: SavedRally[] = [];
  let version = 0;
  let posts = 0;
  const invalid = (code: string, field: string | null = null) =>
    new ApiError(422, 'invalid_label', null, { fields: [{ field, code } as never] });
  const doc = (): LabelDocument => ({
    schema: 'full-tag-labels/v1', clip: `match:${ID}`, fps: 60, frame_count: 3600,
    players: ['A1', 'A2', 'B1', 'B2'], rallies: structuredClone(rallies),
  });
  const read = (): LabelSession => ({ matchId: ID, fps: 60, frameCount: 3600, players: ['A1', 'A2', 'B1', 'B2'], version, document: doc() });
  const labelEvent = vi.fn(async (_id: string, label: RallyLabel | EventLabel) => {
    posts += 1;
    if (label.type === 'rally') {
      if (rallies.some((r) => r.start_frame <= label.end_frame && label.start_frame <= r.end_frame)) throw invalid('overlaps_rally', 'start_frame');
      rallies.push({ id: `r${rallies.length + 1}`, start_frame: label.start_frame, end_frame: label.end_frame, outcome: label.outcome, events: [] });
    } else {
      const r = rallies.find((x) => x.start_frame <= label.frame && label.frame <= x.end_frame);
      if (!r) throw invalid('no_rally', 'frame');
      const lastFrame = r.events.at(-1)?.frame ?? -1;
      if (label.frame <= lastFrame) throw invalid('out_of_order', 'frame');
      r.events.push(structuredClone(label));
    }
    version += 1;
    if (loseAfterApplying.includes(posts)) throw new ApiError(0, 'network_error');
    return { version, rallies: rallies.length, events: rallies.reduce((n, x) => n + x.events.length, 0) };
  });
  const api: FullTagApi = {
    labelSession: vi.fn(async () => read()),
    labelEvent,
    labelExport: vi.fn(async () => doc()),
    matchMedia: vi.fn(async () => ({ url: 'https://localhost/media/a.mp4?X-Amz-Signature=1', expiresInS: 600, startMs: 0 })),
  };
  return { api, rallies, read, labelEvent };
}

const press = (key: string) =>
  act(() => {
    fireEvent.keyDown(document, { key });
  });

/** Rally 1 from frame 0 to 20 with a hit by Carlos (B1) at 10 and a bounce in view at 15. */
async function markRally(): Promise<void> {
  await userEvent.click(screen.getByRole('button', { name: /Rally start/ }));
  for (let i = 0; i < 10; i += 1) press('.');
  await userEvent.click(screen.getByRole('button', { name: /^Hit/ }));
  await userEvent.click(within(screen.getByRole('group', { name: 'Who hit it?' })).getByRole('button', { name: 'Carlos' }));
  for (let i = 0; i < 5; i += 1) press('.');
  await userEvent.click(screen.getByRole('button', { name: /^Bounce/ }));
  await userEvent.click(within(screen.getByRole('group', { name: 'Ball in view?' })).getByRole('button', { name: 'Yes' }));
  for (let i = 0; i < 5; i += 1) press('.');
  await userEvent.click(screen.getByRole('button', { name: /Rally end/ }));
}

async function choose(ending: 'Winner' | 'Replay', side: 'Your side' | null = 'Your side'): Promise<void> {
  const question = screen.getByRole('group', { name: /^How did rally \d+ end\?$/ });
  if (side) await userEvent.click(within(question).getByRole('button', { name: side }));
  await userEvent.click(within(question).getByRole('button', { name: ending }));
}

const HIT = { type: 'hit', frame: 10, hitter: 'B1', facets: {} };
const BOUNCE = { type: 'bounce', frame: 15, visible: true, court_xy_m: null };

describe('Full Tag save after a lost response (PE-ST052-R1-04)', () => {
  it('rally stored but its response lost: the retry does not send the rally again and saves the events once', async () => {
    const s = fakeServer([1]);
    render(<FullTag match={match} initial={s.read()} api={s.api} download={vi.fn()} />);
    await markRally();
    await choose('Winner');
    expect(await screen.findByText('The label was not saved because the connection dropped. Try again.')).toBeVisible();
    await choose('Winner', null);
    expect(await screen.findByText('Rally 1: frames 0 to 20, winner, 2 events')).toBeVisible();
    expect(s.labelEvent.mock.calls.filter(([, l]) => l.type === 'rally')).toHaveLength(1);
    expect(s.rallies).toEqual([expect.objectContaining({ start_frame: 0, end_frame: 20, events: [HIT, BOUNCE] })]);
  });

  it('an event stored but its response lost: the retry never duplicates it and is not refused as out of order', async () => {
    const s = fakeServer([2]);
    render(<FullTag match={match} initial={s.read()} api={s.api} download={vi.fn()} />);
    await markRally();
    await choose('Winner');
    expect(await screen.findByText('The label was not saved because the connection dropped. Try again.')).toBeVisible();
    await choose('Winner', null);
    expect(await screen.findByText('Rally 1: frames 0 to 20, winner, 2 events')).toBeVisible();
    expect(screen.queryByText(/not saved/)).toBeNull();
    expect(s.rallies[0]?.events).toEqual([HIT, BOUNCE]);
  });

  it('after the rally is saved, a different ending is not silently ignored: it says the saved one and sends nothing', async () => {
    const s = fakeServer([1]);
    render(<FullTag match={match} initial={s.read()} api={s.api} download={vi.fn()} />);
    await markRally();
    await choose('Winner');
    await screen.findByText('The label was not saved because the connection dropped. Try again.');
    const before = s.labelEvent.mock.calls.length;
    await choose('Replay', null);
    expect(
      await screen.findByText('Rally 1 is already saved as winner, and saved labels cannot be changed yet. Choose Winner to save its events.'),
    ).toBeVisible();
    expect(s.labelEvent).toHaveBeenCalledTimes(before);
    expect(s.rallies[0]?.outcome.ending).toBe('winner');
  });

  it('dropping a rally the server already holds says so, and the rally stays listed as saved', async () => {
    const s = fakeServer([1]);
    render(<FullTag match={match} initial={s.read()} api={s.api} download={vi.fn()} />);
    await markRally();
    await choose('Winner');
    await screen.findByText('The label was not saved because the connection dropped. Try again.');
    press('Escape');
    const ask = await screen.findByRole('group', { name: 'Rally 1 is already saved. Drop its 2 unsaved events?' });
    await userEvent.click(within(ask).getByRole('button', { name: 'Yes' }));
    expect(await screen.findByText('Rally 1: frames 0 to 20, winner, 0 events')).toBeVisible();
    expect(screen.queryByRole('heading', { name: /so far/ })).toBeNull();
  });

  it('the read after a lost response fails too: the retry sends nothing blindly and says the connection dropped (QA-PR14-R2-01)', async () => {
    const s = fakeServer([1]);
    const labelSession = vi.fn(async (): Promise<LabelSession> => {
      throw new ApiError(0, 'network_error');
    });
    render(<FullTag match={match} initial={s.read()} api={{ ...s.api, labelSession }} download={vi.fn()} />);
    await markRally();
    await choose('Winner');
    await screen.findByText('The label was not saved because the connection dropped. Try again.');
    const before = s.labelEvent.mock.calls.length;
    const reads = labelSession.mock.calls.length;
    await choose('Winner', null);
    await vi.waitFor(() => expect(labelSession.mock.calls.length).toBeGreaterThan(reads));
    expect(screen.getByText('The label was not saved because the connection dropped. Try again.')).toBeVisible();
    expect(s.labelEvent).toHaveBeenCalledTimes(before);
    expect(s.rallies).toHaveLength(1);
  });

  it('a rally the server holds keeps its span: Rally start and Rally end are refused in words (PE-ST052-R2-01)', async () => {
    const s = fakeServer([1]);
    render(<FullTag match={match} initial={s.read()} api={s.api} download={vi.fn()} />);
    await markRally();
    await choose('Winner');
    await screen.findByText('The label was not saved because the connection dropped. Try again.');
    const held = 'Rally 1 is already saved from frame 0 to 20, and saved labels cannot be changed yet.';
    press('.');
    await userEvent.click(screen.getByRole('button', { name: /Rally end/ }));
    expect(await screen.findByText(held)).toBeVisible();
    await userEvent.click(screen.getByRole('button', { name: /Rally start/ }));
    expect(screen.getByText(held)).toBeVisible();
    expect(screen.getByText('Rally 1: frames 0 to 20')).toBeVisible();
    await choose('Winner', null);
    expect(await screen.findByText('Rally 1: frames 0 to 20, winner, 2 events')).toBeVisible();
    expect(screen.queryByText(held)).toBeNull();
    expect(s.rallies).toEqual([expect.objectContaining({ start_frame: 0, end_frame: 20, events: [HIT, BOUNCE] })]);
  });

  it('a mark cannot be removed while its rally is being saved, so a removal is never undone and posted (PE-ST052-R1-06)', async () => {
    const s = fakeServer();
    let release: () => void = () => {};
    const gate = new Promise<void>((r) => {
      release = r;
    });
    const labelEvent = vi.fn(async (id: string, l: RallyLabel | EventLabel) => {
      if (l.type === 'rally') await gate;
      return s.labelEvent(id, l);
    });
    render(<FullTag match={match} initial={s.read()} api={{ ...s.api, labelEvent }} download={vi.fn()} />);
    await markRally();
    await choose('Winner');
    const remove = screen.getByRole('button', { name: 'Remove hit at frame 10' });
    expect(remove).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Remove bounce at frame 15' })).toBeDisabled();
    await act(async () => {
      release();
      await gate;
    });
    expect(await screen.findByText('Rally 1: frames 0 to 20, winner, 2 events')).toBeVisible();
  });

  it('a hit tagged after stepping back into a saved rally is refused, so it is never filed under that rally (PE-ST052-R1-M1)', async () => {
    const s = fakeServer();
    s.rallies.push({ id: 'r1', start_frame: 0, end_frame: 30, outcome: { ending: 'winner', winning_side: 'A', responsible_player: null, fault_kind: null }, events: [] });
    render(<FullTag match={match} initial={s.read()} api={s.api} download={vi.fn()} />);
    press('>');
    for (let i = 0; i < 40; i += 1) press('.');
    await userEvent.click(screen.getByRole('button', { name: /Rally start/ }));
    for (let i = 0; i < 90; i += 1) press(',');
    press('h');
    press('3');
    expect(screen.getByText('Frame 10 is before Rally start (frame 100). Tag hits and bounces inside the rally.')).toBeVisible();
    press('>');
    press('>');
    for (let i = 0; i < 30; i += 1) press('.');
    press('e');
    await choose('Winner');
    expect(await screen.findByText('Rally 2: frames 100 to 160, winner, 0 events')).toBeVisible();
    expect(s.labelEvent.mock.calls.map(([, l]) => l.type)).toEqual(['rally']);
    expect(s.rallies).toEqual([
      expect.objectContaining({ start_frame: 0, end_frame: 30, events: [] }),
      expect.objectContaining({ start_frame: 100, end_frame: 160, events: [] }),
    ]);
  });

  it('nothing reached the server (same version): the retry sends the rally and its events as before', async () => {
    const s = fakeServer();
    const lost = vi.fn().mockRejectedValueOnce(new ApiError(0, 'network_error'));
    const labelEvent = vi.fn(async (id: string, l: RallyLabel | EventLabel) => {
      if (lost.mock.calls.length === 0) await lost();
      return s.labelEvent(id, l);
    });
    render(<FullTag match={match} initial={s.read()} api={{ ...s.api, labelEvent }} download={vi.fn()} />);
    await markRally();
    await choose('Winner');
    await screen.findByText('The label was not saved because the connection dropped. Try again.');
    await choose('Winner', null);
    expect(await screen.findByText('Rally 1: frames 0 to 20, winner, 2 events')).toBeVisible();
    expect(s.rallies[0]?.events).toEqual([HIT, BOUNCE]);
  });
});
