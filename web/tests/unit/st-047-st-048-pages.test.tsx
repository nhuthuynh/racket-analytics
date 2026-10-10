// ST-048 D-01 and ST-047 E-02 server pages, the S-01 `?play=` reader and the entry links
// (flows-sprint-03 §1-§3; ADR 0043). Negative cases first: another player's or a deleted match,
// a wrong metric id or side, and a signed-out visitor get the one not-found page or sign-in
// (NFR-051); an unknown rally in `?play=` opens nothing.
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ScoreSheetView, type SheetApi } from '@/components/score-sheet/ScoreSheetView';
import { EvidenceAll } from '@/components/stats/EvidenceAll';
import { ApiError } from '@/lib/api/client';
import type { Match } from '@/lib/api/types';
import { parseStats } from '@/lib/stats/parse';
import type { Evidence } from '@/lib/stats/types';
import { WORKED_BODY } from './fixtures/stats';
import type { ScoreSheet, SheetRow } from '@/lib/tagging/types';

const ID = '0b8f6c1e-3f3a-4c55-9a51-8d1f0e7d2a10';
const rid = (n: number) => `7d0c6c1e-3f3a-4c55-9a51-8d1f0e7d2a${String(n).padStart(2, '0')}`;
const match: Match = {
  id: ID, title: 'Saturday doubles', format: 'doubles', status: 'video_received', media: null,
  created_at: 'x', updated_at: 'x', upload: null, rejection: null,
  participants: [
    { slot: 'A1', nickname: 'Ivy', is_me: true }, { slot: 'A2', nickname: 'Dana', is_me: false },
    { slot: 'B1', nickname: 'Carlos', is_me: false }, { slot: 'B2', nickname: 'Sam', is_me: false },
  ],
};
const row = (n: number): SheetRow => ({
  rally_id: rid(n), number: n, game: 1, start_ms: (n - 1) * 4000, end_ms: (n - 1) * 4000 + 3000, serving_side: 'A',
  score_before: '0-0-2', score_after: '1-0-2', winning_side: 'A', ending: 'winner', responsible_player: null,
  fault_kind: null, marker: null, corrected_by_user: false,
});
const sheet = (rows: SheetRow[]): ScoreSheet => ({
  rules_version: 'PROVISIONAL-UNVERIFIED', unofficial: true, label: 'unofficial scoring (rules not yet verified)',
  rows, games: [{ number: 1, first_serving_side: 'A', winner: null }], match_winner: null,
});

const api = { getMatch: vi.fn(), getScoreSheet: vi.fn(), stats: vi.fn() };
vi.mock('@/lib/api/server', () => ({
  serverApi: async () => api,
  getMatchForRequest: (id: string) => api.getMatch(id),
}));
class Redirect extends Error {
  constructor(readonly to: string) {
    super(`redirect ${to}`);
  }
}
class NotFound extends Error {}
vi.mock('next/navigation', () => ({
  redirect: (to: string) => {
    throw new Redirect(to);
  },
  notFound: () => {
    throw new NotFound();
  },
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}));

const StatsPage = (await import('@/app/matches/[matchId]/stats/page')).default;
const EvidencePage = (await import('@/app/matches/[matchId]/stats/[metricId]/evidence/page')).default;
const MatchDetail = (await import('@/components/MatchDetail')).MatchDetail;

beforeEach(() => {
  api.getMatch.mockReset();
  api.getScoreSheet.mockReset();
  api.stats.mockReset();
});

describe('D-01 server page /matches/{id}/stats', () => {
  const params = Promise.resolve({ matchId: ID });

  it('another player\'s, a deleted or a missing match is the one not-found page', async () => {
    api.getMatch.mockRejectedValue(new ApiError(404, 'not_found'));
    await expect(StatsPage({ params })).rejects.toBeInstanceOf(NotFound);
  });

  it('a signed-out visitor goes to sign in; other failures reach the error page', async () => {
    api.getMatch.mockRejectedValue(new ApiError(401, 'unauthenticated'));
    await expect(StatsPage({ params })).rejects.toMatchObject({ to: '/' });
    api.getMatch.mockRejectedValue(new ApiError(500, 'internal_error'));
    await expect(StatsPage({ params })).rejects.toBeInstanceOf(ApiError);
  });

  it('a match without its video yet does not ask for the score sheet', async () => {
    api.getMatch.mockResolvedValue({ ...match, status: 'awaiting_upload' });
    render(await StatsPage({ params }));
    expect(api.getScoreSheet).not.toHaveBeenCalled();
    expect(screen.getByText("You can see stats once this match's video is received and rallies are tagged.")).toBeVisible();
  });

  it('has the h1 "Stats", the match title, the HAX sentence with a score-sheet link, and the empty state', async () => {
    api.getMatch.mockResolvedValue(match);
    api.getScoreSheet.mockResolvedValue({ version: 1, sheet: sheet([]) });
    render(await StatsPage({ params }));
    expect(screen.getByRole('heading', { level: 1, name: 'Stats' })).toBeVisible();
    expect(screen.getByText('Saturday doubles')).toBeVisible();
    expect(screen.getByRole('link', { name: 'Back to the match' })).toHaveAttribute('href', `/matches/${ID}`);
    expect(screen.getByRole('link', { name: 'score sheet' })).toHaveAttribute('href', `/matches/${ID}/sheet`);
    expect(screen.getByText('No rallies are tagged yet, so there are no stats to show.')).toBeVisible();
    expect(document.title === '' || document.querySelector('title')?.textContent).toBeTruthy();
  });
});

describe('E-02 server page /matches/{id}/stats/{metric}/evidence', () => {
  it('a wrong metric id or side is the not-found page, without asking the API', async () => {
    for (const [metricId, side] of [['AN-1', 'A'], ['AN-01', 'C'], ['AN-01', undefined]] as const) {
      await expect(
        EvidencePage({ params: Promise.resolve({ matchId: ID, metricId }), searchParams: Promise.resolve({ side }) }),
      ).rejects.toBeInstanceOf(NotFound);
    }
    expect(api.getMatch).not.toHaveBeenCalled();
  });

  it('a metric that is not published (draft, deprecated or unknown) is the not-found page (FR-102)', async () => {
    api.getMatch.mockResolvedValue(match);
    api.stats.mockResolvedValue(parseStats(structuredClone(WORKED_BODY)));
    await expect(
      EvidencePage({ params: Promise.resolve({ matchId: ID, metricId: 'AN-02' }), searchParams: Promise.resolve({ side: 'A' }) }),
    ).rejects.toBeInstanceOf(NotFound);
  });

  it('names the stat and the side, with "low sample" when the side is flagged', async () => {
    api.getMatch.mockResolvedValue(match);
    api.stats.mockResolvedValue(parseStats(structuredClone(WORKED_BODY)));
    render(await EvidencePage({ params: Promise.resolve({ matchId: ID, metricId: 'AN-01' }), searchParams: Promise.resolve({ side: 'A' }) }));
    expect(screen.getByRole('heading', { level: 1, name: 'Rallies behind “Rallies won on serve”' })).toBeVisible();
    expect(screen.getByText(/low sample/)).toBeVisible();
  });

  it('a match that is not yours is the not-found page', async () => {
    api.getMatch.mockRejectedValue(new ApiError(404, 'not_found'));
    await expect(
      EvidencePage({ params: Promise.resolve({ matchId: ID, metricId: 'AN-01' }), searchParams: Promise.resolve({ side: 'A' }) }),
    ).rejects.toBeInstanceOf(NotFound);
  });
});

describe('E-02 all rallies behind a stat (EvidenceAll)', () => {
  const page = (from: number, to: number, next: string | null): Evidence => ({
    metricId: 'AN-01', side: 'A', total: 23, sheetVersion: 15, nextCursor: next,
    items: Array.from({ length: to - from + 1 }, (_, i) => {
      const n = from + i;
      return { number: n, rally_id: rid(n), game: 1, start_ms: (n - 1) * 4000, end_ms: (n - 1) * 4000 + 3000 };
    }),
  });

  it('error: an alert with Try again and no links', async () => {
    const evidence = vi.fn().mockRejectedValueOnce(new ApiError(503, 'unavailable')).mockResolvedValue(page(1, 10, 'c2'));
    render(<EvidenceAll match={match} metricId="AN-01" metricName="Rallies won on serve" lowSample side="A" api={{ evidence }} />);
    expect(await screen.findByRole('alert')).toHaveTextContent('The rallies for this stat could not be loaded. Try again.');
    expect(screen.queryByRole('link', { name: /Rally \d+/ })).toBeNull();
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(await screen.findByRole('link', { name: 'Rally 1 · game 1 · 0:00' })).toBeVisible();
  });

  it('pages through 10 at a time with the position in words, forward and back', async () => {
    const evidence = vi.fn(async (_m: string, _id: string, _s: string, cursor: string | null) =>
      cursor === null ? page(1, 10, 'c2') : cursor === 'c2' ? page(11, 20, 'c3') : page(21, 23, null));
    render(<EvidenceAll match={match} metricId="AN-01" metricName="Rallies won on serve" lowSample side="A" api={{ evidence }} />);
    expect(await screen.findByText('Rallies 1 to 10 of 23')).toBeVisible();
    expect(screen.getByText('Your side (Ivy and Dana) · 23 rallies')).toBeVisible();
    expect(screen.queryByRole('button', { name: 'Previous 10 rallies' })).toBeNull();
    await userEvent.click(screen.getByRole('button', { name: 'Next 10 rallies' }));
    expect(await screen.findByText('Rallies 11 to 20 of 23')).toBeVisible();
    expect(evidence).toHaveBeenLastCalledWith(ID, 'AN-01', 'A', 'c2');
    await userEvent.click(screen.getByRole('button', { name: 'Next 10 rallies' }));
    expect(await screen.findByText('Rallies 21 to 23 of 23')).toBeVisible();
    expect(screen.queryByRole('button', { name: 'Next 10 rallies' })).toBeNull();
    await userEvent.click(screen.getByRole('button', { name: 'Previous 10 rallies' }));
    expect(await screen.findByText('Rallies 11 to 20 of 23')).toBeVisible();
    const list = screen.getByRole('list', { name: /Rallies behind/ });
    expect(within(list).getAllByRole('link')[0]).toHaveAttribute('href', `/matches/${ID}/sheet?play=${rid(11)}`);
  });

  it('nothing behind the stat: says so and links back to the stats', async () => {
    const evidence = vi.fn(async () => ({ ...page(1, 1, null), total: 0, items: [] }));
    render(<EvidenceAll match={match} metricId="AN-01" metricName="Rallies won on serve" lowSample side="A" api={{ evidence }} />);
    expect(await screen.findByText('No rallies are behind this stat yet.')).toBeVisible();
    expect(screen.getByRole('link', { name: 'Back to the stats' })).toHaveAttribute('href', `/matches/${ID}/stats`);
  });
});

describe('S-01 opened from "Show me" (?play=<rally_id>, ADR 0043)', () => {
  const URL1 = 'https://localhost:3000/media/racket-media/a.mp4?X-Amz-Signature=1';
  function view(initialPlay: string | undefined) {
    const sheetApi = {
      undo: vi.fn(), corrections: vi.fn().mockResolvedValue([]), correctRally: vi.fn(), getScoreSheet: vi.fn(),
      rallyMedia: vi.fn<SheetApi['rallyMedia']>().mockResolvedValue({ url: URL1, expiresInS: 600, startMs: 8000 }),
    };
    render(
      <ScoreSheetView match={match} initialSheet={sheet([row(1), row(3)])} initialVersion={1} api={sheetApi as unknown as SheetApi} initialPlay={initialPlay} />,
    );
    return sheetApi;
  }

  it('an id that is not a rally of this sheet opens nothing', async () => {
    const sheetApi = view(rid(9));
    await Promise.resolve();
    expect(sheetApi.rallyMedia).not.toHaveBeenCalled();
    expect(screen.queryByRole('region', { name: /video/ })).toBeNull();
  });

  it('opens V-01 for that rally from a fresh link', async () => {
    const sheetApi = view(rid(3));
    expect(await screen.findByRole('region', { name: 'Rally 3 video' })).toBeVisible();
    expect(sheetApi.rallyMedia).toHaveBeenCalledWith(ID, rid(3));
  });
});

describe('entry links (flows-sprint-03 §2 "Entry")', () => {
  it('M-02 offers "Stats" next to "Tag rallies" and "Score sheet" once the video is received', () => {
    const media = { duration_ms: 60_000, fps: 60, width: 1920, height: 1080, has_audio: true, vfr: false, container: 'mp4', video_codec: 'h264' };
    render(<MatchDetail initialMatch={{ ...match, media }} api={{ getMatch: vi.fn() }} initialFile={null} />);
    expect(screen.getByRole('link', { name: 'Stats' })).toHaveAttribute('href', `/matches/${ID}/stats`);
  });

  it('M-02 has no "Stats" link before the video is received', () => {
    render(<MatchDetail initialMatch={{ ...match, status: 'awaiting_upload' }} api={{ getMatch: vi.fn() }} initialFile={null} />);
    expect(screen.queryByRole('link', { name: 'Stats' })).toBeNull();
  });
});
