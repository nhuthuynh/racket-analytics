// Footage quality report, R1 facts (ST-019 stretch; FR-025; flows U-02/M-02; HAX G16).
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { QualityReport } from '@/components/QualityReport';
import { qualityFindings } from '@/lib/quality';

const media = { duration_ms: 60_000, fps: 60, width: 1920, height: 1080, has_audio: true, vfr: false, container: 'mp4', video_codec: 'h264' };

describe('qualityFindings', () => {
  it('finds nothing to report for 1080p at 60 fps', () => {
    expect(qualityFindings(media)).toEqual([]);
  });

  it('states a low frame rate as its consequence, and what is unaffected', () => {
    expect(qualityFindings({ ...media, fps: 30 })).toEqual([
      'Recorded at 30 fps: some later results, such as shot types, may be less accurate. Your score and rally stats are unaffected.',
    ]);
  });

  it('states a low resolution and a variable frame rate as facts with consequences', () => {
    const lines = qualityFindings({ ...media, width: 1280, height: 720, vfr: true });
    expect(lines).toContain('Recorded at 1280×720: some later results may be less accurate. Your score and rally stats are unaffected.');
    expect(lines).toContain('Variable frame rate: timings in later results may be slightly less precise. Your score and rally stats are unaffected.');
  });
});

describe('QualityReport', () => {
  it('never blocks: it says the match can still be tagged', () => {
    render(<QualityReport media={{ ...media, fps: 30 }} />);
    expect(screen.getByRole('heading', { name: 'Footage quality' })).toBeVisible();
    expect(screen.getByText(/Recorded at 30 fps/)).toBeVisible();
    expect(screen.getByText('You can still tag this match.')).toBeVisible();
  });

  it('says the footage is good when nothing is found', () => {
    render(<QualityReport media={media} />);
    expect(screen.getByText('Good: 1080p or better at 50 fps or more.')).toBeVisible();
  });
});
