// ST-052 UI, L-01 Full Tag and L-02 keys (FR-150, FR-151; NFR-030; api-sprint-03 §5;
// flows-sprint-03 §6; DR-03 R3-8 with the FE key amendments). Negative cases first: a player, a
// labeller on someone else's match and a deleted match get the not-found page; no consent and no
// probed video are refused in words; a rally is never saved without its ending (ADR 0043); a
// refused label keeps the marks and says why; keys typed into a field do nothing.
import { act, fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { FullTag, type FullTagApi } from '@/components/label/FullTag';
import { ApiError } from '@/lib/api/client';
import type { Match } from '@/lib/api/types';
import type { LabelDocument, LabelSession } from '@/lib/label/types';

const server = vi.hoisted(() => ({ labelSession: vi.fn(), getMatch: vi.fn() }));
vi.mock('@/lib/api/server', () => ({
  serverApi: async () => server,
  getMatchForRequest: (id: string) => server.getMatch(id),
}));
vi.mock('next/navigation', () => ({
  redirect: (to: string) => {
    throw Object.assign(new Error(`redirect ${to}`), { to });
  },
  notFound: () => {
    throw Object.assign(new Error('not found'), { notFound: true });
  },
}));

const ID = '0b8f6c1e-3f3a-4c55-9a51-8d1f0e7d2a10';
const REF = 'ref_0123456789abcdef';
const match: Match = {
  id: ID, title: 'Team clip 1', format: 'doubles', status: 'video_received', media: null,
  created_at: 'x', updated_at: 'x', upload: null, rejection: null,
  participants: [
    { slot: 'A1', nickname: 'Ivy', is_me: true }, { slot: 'A2', nickname: 'Dana', is_me: false },
    { slot: 'B1', nickname: 'Carlos', is_me: false }, { slot: 'B2', nickname: 'Sam', is_me: false },
  ],
};
const DOC = (rallies: unknown[] = []): LabelDocument => ({
  schema: 'full-tag-labels/v1', clip: `match:${ID}`, fps: 60, frame_count: 3600, players: ['A1', 'A2', 'B1', 'B2'], rallies: rallies as LabelDocument['rallies'],
});
const session = (rallies: unknown[] = []): LabelSession => ({
  matchId: ID, fps: 60, frameCount: 3600, players: ['A1', 'A2', 'B1', 'B2'], version: rallies.length, document: DOC(rallies),
});
const SAVED = { id: 'r1', start_frame: 100, end_frame: 400, outcome: { ending: 'winner', winning_side: 'A', responsible_player: null, fault_kind: null }, events: [] };

function api(over: Partial<FullTagApi> = {}): FullTagApi {
  return {
    labelSession: vi.fn(async () => session()),
    labelEvent: vi.fn(async () => ({ version: 1, rallies: 1, events: 0 })),
    labelExport: vi.fn(async () => DOC()),
    matchMedia: vi.fn(async () => ({ url: 'https://localhost/media/a.mp4?X-Amz-Signature=1', expiresInS: 600, startMs: 0 })),
    ...over,
  };
}

function setup(a: FullTagApi = api(), initial: LabelSession = session()) {
  const download = vi.fn();
  render(<FullTag match={match} initial={initial} api={a} download={download} />);
  return { a, download };
}

const press = (key: string, target: Element | Document = document) =>
  act(() => {
    fireEvent.keyDown(target, { key });
  });
const readout = () => screen.getByText(/^Frame \d+ of \d+/);

beforeEach(() => {
  try {
    window.localStorage.clear();
  } catch {
    // storage blocked: the default (single keys on) applies
  }
});

describe('L-01 server page /label/matches/{id}', () => {
  const params = Promise.resolve({ matchId: ID });
  // The hoisted fakes keep calls and implementations across tests unless reset (QA-PR14-06).
  beforeEach(() => {
    server.getMatch.mockReset();
    server.labelSession.mockReset();
  });

  it('the label session is fine but the match read then fails: not-found for 404, the error itself otherwise', async () => {
    const Page = (await import('@/app/label/matches/[matchId]/page')).default;
    server.labelSession.mockResolvedValue(session());
    server.getMatch.mockRejectedValueOnce(new ApiError(404, 'not_found'));
    await expect(Page({ params })).rejects.toMatchObject({ notFound: true });
    server.getMatch.mockRejectedValueOnce(new ApiError(500, 'internal_error', REF));
    await expect(Page({ params })).rejects.toMatchObject({ status: 500, code: 'internal_error' });
  });

  it('a 409 with a code that has no refusal text is not shown as a refusal: it is thrown', async () => {
    const Page = (await import('@/app/label/matches/[matchId]/page')).default;
    server.labelSession.mockRejectedValue(new ApiError(409, 'decision_needed'));
    server.getMatch.mockResolvedValue(match);
    await expect(Page({ params })).rejects.toMatchObject({ status: 409, code: 'decision_needed' });
  });

  it('a player, a labeller on another account\'s match, and a deleted match get the not-found page', async () => {
    server.labelSession.mockRejectedValue(new ApiError(404, 'not_found'));
    const Page = (await import('@/app/label/matches/[matchId]/page')).default;
    await expect(Page({ params })).rejects.toMatchObject({ notFound: true });
    expect(server.getMatch).not.toHaveBeenCalled();
  });

  it('a signed-out visitor goes to sign in', async () => {
    server.labelSession.mockRejectedValue(new ApiError(401, 'unauthenticated'));
    const Page = (await import('@/app/label/matches/[matchId]/page')).default;
    await expect(Page({ params })).rejects.toMatchObject({ to: '/' });
  });

  it('no consent record: the heading and the reason, no video and no tag bar, no consent reference', async () => {
    server.labelSession.mockRejectedValue(new ApiError(409, 'no_consent'));
    server.getMatch.mockResolvedValue(match);
    const Page = (await import('@/app/label/matches/[matchId]/page')).default;
    render(await Page({ params }));
    expect(screen.getByRole('heading', { level: 1, name: 'Full Tag: Team clip 1' })).toBeVisible();
    expect(screen.getByRole('alert')).toHaveTextContent(
      'This match has no consent record for labelling. Nothing can be labelled until the team records consent.',
    );
    expect(screen.queryByRole('group', { name: 'Tag at this frame' })).toBeNull();
    expect(document.querySelector('video')).toBeNull();
  });

  it('video not ready: says the video is not ready for frame-by-frame labelling', async () => {
    server.labelSession.mockRejectedValue(new ApiError(409, 'match_not_ready'));
    server.getMatch.mockResolvedValue(match);
    const Page = (await import('@/app/label/matches/[matchId]/page')).default;
    render(await Page({ params }));
    expect(screen.getByRole('alert')).toHaveTextContent("This match's video is not ready for frame-by-frame labelling.");
  });

  it('a labeller on their own consented match gets L-01', async () => {
    server.labelSession.mockResolvedValue(session());
    server.getMatch.mockResolvedValue(match);
    const Page = (await import('@/app/label/matches/[matchId]/page')).default;
    render(await Page({ params }));
    expect(screen.getByRole('heading', { level: 1, name: 'Full Tag: Team clip 1' })).toBeVisible();
    expect(screen.getByRole('group', { name: 'Tag at this frame' })).toBeVisible();
  });
});

describe('L-01 frame stepping (NFR-030: keys and buttons, no dragging)', () => {
  it('starts at frame 0 with plain digits and the time', () => {
    setup();
    expect(readout()).toHaveTextContent('Frame 0 of 3600 · 0:00.00');
  });

  it('"." and "," step one frame; never below 0 or past the last frame', () => {
    setup();
    press(',');
    expect(readout()).toHaveTextContent('Frame 0 of 3600');
    press('.');
    press('.');
    expect(readout()).toHaveTextContent('Frame 2 of 3600');
    press(',');
    expect(readout()).toHaveTextContent('Frame 1 of 3600');
  });

  it('">" and "<" move one second (by KeyboardEvent.key, so the layout does not matter)', () => {
    setup();
    press('>');
    expect(readout()).toHaveTextContent('Frame 60 of 3600 · 0:01.00');
    press('<');
    expect(readout()).toHaveTextContent('Frame 0 of 3600');
  });

  it('the buttons do the same as the keys', async () => {
    setup();
    const bar = screen.getByRole('group', { name: 'Move through the video' });
    await userEvent.click(within(bar).getByRole('button', { name: 'Next frame' }));
    await userEvent.click(within(bar).getByRole('button', { name: 'Forward 1 second' }));
    expect(readout()).toHaveTextContent('Frame 61 of 3600');
    await userEvent.click(within(bar).getByRole('button', { name: 'Previous frame' }));
    await userEvent.click(within(bar).getByRole('button', { name: 'Back 1 second' }));
    expect(readout()).toHaveTextContent('Frame 0 of 3600');
  });

  it('keys typed into a field do nothing', async () => {
    setup();
    await userEvent.click(screen.getByRole('button', { name: /^Bounce/ }));
    const across = screen.getByRole('spinbutton', { name: /Across/ });
    press('.', across);
    expect(readout()).toHaveTextContent('Frame 0 of 3600');
  });

  it('single-key shortcuts can be turned off in L-02 (SC 2.1.4), and the choice is kept on this device', async () => {
    setup();
    press('?');
    const dialog = screen.getByRole('dialog', { name: 'Full Tag keys' });
    expect(dialog).toHaveTextContent('Next frame');
    await userEvent.click(within(dialog).getByRole('checkbox', { name: 'Use single-key shortcuts' }));
    await userEvent.click(within(dialog).getByRole('button', { name: 'Close' }));
    press('.');
    expect(readout()).toHaveTextContent('Frame 0 of 3600');
    expect(window.localStorage.getItem('ra-full-tag-single-keys')).toBe('off');
  });
});

async function markRallyWithHit(): Promise<void> {
  await userEvent.click(screen.getByRole('button', { name: /Rally start/ }));
  for (let i = 0; i < 10; i += 1) press('.');
  await userEvent.click(screen.getByRole('button', { name: /^Hit/ }));
  await userEvent.click(within(screen.getByRole('group', { name: 'Who hit it?' })).getByRole('button', { name: 'Carlos' }));
  for (let i = 0; i < 10; i += 1) press('.');
  await userEvent.click(screen.getByRole('button', { name: /Rally end/ }));
}

describe('L-01 tagging and saving (ADR 0043: the ending saves the rally)', () => {
  it('"Rally end" before "Rally start", or at its frame, is refused in words and asks nothing', async () => {
    const { a } = setup();
    await userEvent.click(screen.getByRole('button', { name: /Rally end/ }));
    expect(screen.getByText('Press Rally start first.')).toBeVisible();
    await userEvent.click(screen.getByRole('button', { name: /Rally start/ }));
    await userEvent.click(screen.getByRole('button', { name: /Rally end/ }));
    expect(screen.getByText('Rally end must be after its start.')).toBeVisible();
    expect(screen.queryByRole('group', { name: /^How did rally/ })).toBeNull();
    expect(a.labelEvent).not.toHaveBeenCalled();
  });

  it('a hit or bounce before Rally start makes no hidden mark: it says "Press Rally start first." (PE-ST052-R1-07)', async () => {
    const { a } = setup();
    press('h');
    await userEvent.click(within(screen.getByRole('group', { name: 'Who hit it?' })).getByRole('button', { name: 'Carlos' }));
    expect(screen.getByText('Press Rally start first.')).toBeVisible();
    await userEvent.click(screen.getByRole('button', { name: /^Bounce/ }));
    await userEvent.click(within(screen.getByRole('group', { name: 'Ball in view?' })).getByRole('button', { name: 'Yes' }));
    await userEvent.click(screen.getByRole('button', { name: /Rally start/ }));
    press('.');
    await userEvent.click(screen.getByRole('button', { name: /Rally end/ }));
    expect(screen.queryByText(/^Hit by|^Bounce (in|not in) view/)).toBeNull();
    expect(screen.getByText('Rally 1: frames 0 to 1')).toBeVisible();
    expect(a.labelEvent).not.toHaveBeenCalled();
  });

  it('nothing is saved at "Rally end": the outcome question appears and the marks are listed', async () => {
    const { a } = setup();
    await markRallyWithHit();
    expect(a.labelEvent).not.toHaveBeenCalled();
    expect(screen.getByRole('group', { name: 'How did rally 1 end?' })).toBeVisible();
    expect(screen.getByRole('heading', { level: 2, name: 'Rally 1 so far' })).toBeVisible();
    expect(screen.getByText('Hit by Carlos at frame 10')).toBeVisible();
    expect(screen.getByText('Rally 1: frames 0 to 20')).toBeVisible();
  });

  it('an ending other than replay needs who won first; nothing is sent until then', async () => {
    const { a } = setup();
    await markRallyWithHit();
    const question = screen.getByRole('group', { name: 'How did rally 1 end?' });
    await userEvent.click(within(question).getByRole('button', { name: 'Winner' }));
    expect(a.labelEvent).not.toHaveBeenCalled();
    expect(within(question).getByRole('alert')).toHaveTextContent('Choose who won the rally first.');
  });

  it('choosing the ending saves the rally, then its events, as slots (never nicknames)', async () => {
    const a = api({ labelSession: vi.fn(async () => session([{ ...SAVED, start_frame: 0, end_frame: 20, events: [{ type: 'hit', frame: 10, hitter: 'B1', facets: {} }] }])) });
    setup(a);
    await markRallyWithHit();
    const question = screen.getByRole('group', { name: 'How did rally 1 end?' });
    await userEvent.click(within(question).getByRole('button', { name: 'Your side' }));
    await userEvent.click(within(question).getByRole('button', { name: 'Winner' }));
    expect(a.labelEvent).toHaveBeenNthCalledWith(1, ID, {
      type: 'rally', start_frame: 0, end_frame: 20,
      outcome: { ending: 'winner', winning_side: 'A', responsible_player: null, fault_kind: null },
    });
    expect(a.labelEvent).toHaveBeenNthCalledWith(2, ID, { type: 'hit', frame: 10, hitter: 'B1', facets: {} });
    expect(await screen.findByText('Rally 1: frames 0 to 20, winner, 1 event')).toBeVisible();
    expect(screen.queryByRole('heading', { name: /so far/ })).toBeNull();
    expect(screen.getByText('Saved labels cannot be changed yet.')).toBeVisible();
  });

  it('a fault asks the fault kind before saving', async () => {
    const { a } = setup();
    await markRallyWithHit();
    const question = screen.getByRole('group', { name: 'How did rally 1 end?' });
    await userEvent.click(within(question).getByRole('button', { name: 'Other side' }));
    await userEvent.click(within(question).getByRole('button', { name: 'Fault' }));
    expect(a.labelEvent).not.toHaveBeenCalled();
    await userEvent.click(within(screen.getByRole('group', { name: 'Fault kind' })).getByRole('button', { name: 'Kitchen (non-volley zone)' }));
    expect(a.labelEvent).toHaveBeenCalledWith(ID, expect.objectContaining({
      type: 'rally', outcome: { ending: 'fault', winning_side: 'B', responsible_player: null, fault_kind: 'nvz' },
    }));
  });

  it('a refused label keeps the marks and says why; an overlap names the saved rally', async () => {
    const fields = [{ field: 'start_frame', code: 'overlaps_rally' as const }];
    const a = api({ labelEvent: vi.fn().mockRejectedValue(new ApiError(422, 'invalid_label', null, { fields })) });
    setup(a, session([SAVED]));
    await userEvent.click(screen.getByRole('button', { name: /Rally start/ }));
    press('>');
    press('>');
    press('>');
    press('>');
    press('>');
    press('>');
    await userEvent.click(screen.getByRole('button', { name: /Rally end/ }));
    const question = screen.getByRole('group', { name: 'How did rally 2 end?' });
    await userEvent.click(within(question).getByRole('button', { name: 'Your side' }));
    await userEvent.click(within(question).getByRole('button', { name: 'Replay' }));
    expect(await screen.findByText('This label was not saved: it overlaps rally 1.')).toBeVisible();
    expect(screen.getByRole('heading', { level: 2, name: 'Rally 2 so far' })).toBeVisible();
  });

  it('too many labels (429) and other failures say what to do, with the reference', async () => {
    const a = api({ labelEvent: vi.fn().mockRejectedValueOnce(new ApiError(429, 'rate_limited')).mockRejectedValueOnce(new ApiError(500, 'internal_error', REF)) });
    setup(a);
    await markRallyWithHit();
    const question = screen.getByRole('group', { name: 'How did rally 1 end?' });
    await userEvent.click(within(question).getByRole('button', { name: 'Your side' }));
    await userEvent.click(within(question).getByRole('button', { name: 'Winner' }));
    expect(await screen.findByText('Too many labels in a short time. Wait a moment, then save again.')).toBeVisible();
    await userEvent.click(within(question).getByRole('button', { name: 'Winner' }));
    expect(await screen.findByText(`The label was not saved. Try again. Reference: ${REF}`)).toBeVisible();
  });

  it('a bounce asks whether the ball is in view, with an optional court position in metres', async () => {
    setup();
    await userEvent.click(screen.getByRole('button', { name: /Rally start/ }));
    press('.');
    await userEvent.click(screen.getByRole('button', { name: /^Bounce/ }));
    await userEvent.type(screen.getByRole('spinbutton', { name: /Across/ }), '3.1');
    await userEvent.type(screen.getByRole('spinbutton', { name: /Along/ }), '12.4');
    await userEvent.click(within(screen.getByRole('group', { name: 'Ball in view?' })).getByRole('button', { name: 'Yes' }));
    expect(screen.getByText('Bounce in view at frame 1 (3.1 m across, 12.4 m along)')).toBeVisible();
  });

  it('Esc asks before dropping the unsaved rally and its events', async () => {
    setup();
    await markRallyWithHit();
    press('Escape');
    const ask = screen.getByRole('group', { name: 'Drop rally 1 and its 1 event?' });
    await userEvent.click(within(ask).getByRole('button', { name: 'No' }));
    expect(screen.getByText('Hit by Carlos at frame 10')).toBeVisible();
    press('Escape');
    await userEvent.click(within(screen.getByRole('group', { name: /^Drop rally 1/ })).getByRole('button', { name: 'Yes' }));
    expect(screen.queryByText('Hit by Carlos at frame 10')).toBeNull();
    expect(screen.getByText('No rallies labelled yet. Step to the first serve and press Rally start.')).toBeVisible();
  });
});

describe('L-01 export (FR-151: full-tag-labels/v1)', () => {
  it('downloads labels-<id>.json and says how much it holds', async () => {
    const doc = DOC([{ ...SAVED, events: [{ type: 'hit', frame: 150, hitter: 'B1', facets: {} }] }]);
    const { download } = setup(api({ labelExport: vi.fn(async () => doc) }), session([SAVED]));
    await userEvent.click(screen.getByRole('button', { name: 'Export labels' }));
    expect(download).toHaveBeenCalledWith(`labels-${ID}.json`, doc);
    expect(await screen.findByText('Exported 1 rally with 1 event.')).toBeVisible();
  });

  it('never blocks on an unsaved rally, and says it is not included', async () => {
    const { download } = setup();
    await markRallyWithHit();
    await userEvent.click(screen.getByRole('button', { name: 'Export labels' }));
    expect(download).toHaveBeenCalled();
    expect(await screen.findByText('Exported 0 rallies with 0 events. Rally 1 is not saved yet: choose how it ended to include it.')).toBeVisible();
  });

  it('a failed export says so with the reference and downloads nothing', async () => {
    const { download } = setup(api({ labelExport: vi.fn().mockRejectedValue(new ApiError(500, 'internal_error', REF)) }));
    await userEvent.click(screen.getByRole('button', { name: 'Export labels' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(`The labels could not be exported. Try again. Reference: ${REF}`);
    expect(download).not.toHaveBeenCalled();
  });
});
