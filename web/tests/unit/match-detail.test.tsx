// Match detail: refreshes the match from the API until the probe has a result.
import { act, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { MatchDetail } from '@/components/MatchDetail';
import { ApiError } from '@/lib/api/client';
import type { Match } from '@/lib/api/types';

const base: Match = {
  id: '0b8f6c1e-3f3a-4c55-9a51-8d1f0e7d2a10',
  title: 'Skeleton test',
  format: 'doubles',
  status: 'video_received',
  media: null,
  created_at: '2026-10-05T09:12:44.123Z',
  updated_at: '2026-10-05T09:12:44.123Z',
};
const media = {
  duration_ms: 60_000,
  fps: 60,
  width: 1920,
  height: 1080,
  has_audio: true,
  vfr: false,
  container: 'mov,mp4,m4a,3gp,3g2,mj2',
  video_codec: 'h264',
};

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

const tick = async (ms: number) => {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
};

describe('MatchDetail', () => {
  it('does not poll a match that is waiting for an upload', async () => {
    const api = { getMatch: vi.fn() };
    render(<MatchDetail initialMatch={{ ...base, status: 'awaiting_upload' }} api={api} />);
    await tick(10_000);
    expect(api.getMatch).not.toHaveBeenCalled();
    expect(screen.getByLabelText(/match video/i)).toBeInTheDocument();
  });

  it('keeps showing the last known state when a refresh fails', async () => {
    const api = { getMatch: vi.fn().mockRejectedValue(new ApiError(503, 'unavailable')) };
    render(<MatchDetail initialMatch={base} api={api} pollMs={1_000} />);
    await tick(1_000);
    expect(api.getMatch).toHaveBeenCalled();
    expect(screen.getByText('Video received')).toBeVisible();
  });

  it('polls until the facts arrive, then stops', async () => {
    const api = {
      getMatch: vi
        .fn()
        .mockResolvedValueOnce(base)
        .mockResolvedValueOnce({ ...base, media })
        .mockResolvedValue({ ...base, media }),
    };
    render(<MatchDetail initialMatch={base} api={api} pollMs={1_000} />);
    await tick(1_000);
    expect(screen.queryByText(/^Duration/)).toBeNull();
    await tick(1_000);
    expect(screen.getByText('Duration 1:00 · 60 fps · 1920×1080')).toBeVisible();
    const calls = api.getMatch.mock.calls.length;
    await tick(10_000);
    expect(api.getMatch.mock.calls.length).toBe(calls);
  });

  it('stops polling when the probe failed', async () => {
    const api = { getMatch: vi.fn().mockResolvedValue({ ...base, status: 'probe_failed' }) };
    render(<MatchDetail initialMatch={base} api={api} pollMs={1_000} />);
    await tick(1_000);
    expect(screen.getByText('We could not read this video')).toBeVisible();
    await tick(10_000);
    expect(api.getMatch).toHaveBeenCalledTimes(1);
  });

  it('shows the title as a heading, as text only', () => {
    render(
      <MatchDetail
        initialMatch={{ ...base, title: '<img src=x onerror=alert(1)>' }}
        api={{ getMatch: vi.fn().mockResolvedValue(base) }}
      />,
    );
    expect(
      screen.getByRole('heading', { level: 1, name: '<img src=x onerror=alert(1)>' }),
    ).toBeVisible();
    expect(document.querySelector('img')).toBeNull();
  });
});
