// Match status and probe facts (ST-010 with ST-009). The status label wording comes from
// the QA contract's STATUS_LABELS; facts are hidden until the probe has run.
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { MatchFacts } from '@/components/MatchFacts';
import type { Match } from '@/lib/api/types';

const base: Match = {
  id: '0b8f6c1e-3f3a-4c55-9a51-8d1f0e7d2a10',
  title: 'Skeleton test',
  format: 'doubles',
  status: 'awaiting_upload',
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

describe('MatchFacts', () => {
  it('shows no media facts while uploading', () => {
    render(<MatchFacts match={{ ...base, status: 'uploading' }} />);
    expect(screen.getByText('Uploading')).toBeVisible();
    expect(screen.queryByText(/^Duration/)).toBeNull();
  });

  it('says the video is being read when received but not yet probed', () => {
    render(<MatchFacts match={{ ...base, status: 'video_received' }} />);
    expect(screen.getByText('Video received')).toBeVisible();
    expect(screen.getByRole('status')).toHaveTextContent(/reading the video/i);
    expect(screen.queryByText(/^Duration/)).toBeNull();
  });

  it('explains a failed probe in words', () => {
    render(<MatchFacts match={{ ...base, status: 'probe_failed' }} />);
    expect(screen.getByText('We could not read this video')).toBeVisible();
  });

  it('shows the media facts once probed', () => {
    render(<MatchFacts match={{ ...base, status: 'video_received', media }} />);
    expect(screen.getByText('Duration 1:00 · 60 fps · 1920×1080')).toBeVisible();
    expect(screen.getByText('h264')).toBeVisible();
    expect(screen.getByText('Constant')).toBeVisible();
    expect(screen.queryByRole('status')).toBeNull();
  });

  it('shows the format and each status label exactly once', () => {
    render(<MatchFacts match={{ ...base, status: 'video_received', media }} />);
    expect(screen.getAllByText('Video received')).toHaveLength(1);
    expect(screen.getByText('Doubles')).toBeVisible();
  });
});
