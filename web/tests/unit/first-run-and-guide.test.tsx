// F-01 What this app does and G-01 How to film your match (ST-015; flows §3, §4; FR-004,
// FR-020; NFR-033, NFR-035; wording: docs/domain/capture-guide-wording.md).
import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { CAPTURE_GUIDE_ITEMS } from '@/lib/content/capture-guide';
import { GuideVideo } from '@/components/GuideVideo';

const WelcomePage = (await import('@/app/welcome/page')).default;
const GuidePage = (await import('@/app/guide/page')).default;

describe('capture guide content', () => {
  it('has at most 6 items, each an imperative of at most 12 words with a why line', () => {
    expect(CAPTURE_GUIDE_ITEMS.length).toBeGreaterThan(0);
    expect(CAPTURE_GUIDE_ITEMS.length).toBeLessThanOrEqual(6);
    for (const item of CAPTURE_GUIDE_ITEMS) {
      expect(item.instruction.split(/\s+/).length).toBeLessThanOrEqual(12);
      expect(item.why.length).toBeGreaterThan(10);
    }
  });

  it('gives every illustration a unique purpose description (NFR-035)', () => {
    const alts = CAPTURE_GUIDE_ITEMS.map((i) => i.alt.trim());
    expect(alts.every((a) => a.length > 10)).toBe(true);
    expect(new Set(alts).size).toBe(alts.length);
  });
});

describe('G-01 page', () => {
  it('lists every instruction as text with a described illustration', () => {
    render(<GuidePage />);
    expect(screen.getByRole('heading', { level: 1, name: 'How to film your match' })).toBeVisible();
    const items = within(screen.getByRole('list', { name: 'Checklist' })).getAllByRole('listitem');
    expect(items).toHaveLength(CAPTURE_GUIDE_ITEMS.length);
    items.forEach((li, i) => {
      expect(li).toHaveTextContent(CAPTURE_GUIDE_ITEMS[i]!.instruction);
      expect(within(li).getByRole('img')).toHaveAccessibleName(CAPTURE_GUIDE_ITEMS[i]!.alt);
    });
  });

  it('shows the safety line and only the generic 60 fps help (device steps unverified)', () => {
    render(<GuidePage />);
    expect(screen.getByText(/Keep the tripod and its legs off the court and out of walkways\./)).toBeVisible();
    expect(screen.getByText('How to record at 60 fps on my phone')).toBeVisible();
    expect(screen.queryByText(/Settings > Camera/)).toBeNull();
  });

  it('starts setup and links back to the matches', () => {
    render(<GuidePage />);
    expect(screen.getByRole('link', { name: 'Record your first match' })).toHaveAttribute('href', '/matches/new');
    expect(screen.getByRole('link', { name: 'Back to your matches' })).toHaveAttribute('href', '/matches');
  });
});

describe('GuideVideo', () => {
  it('has captions on by default, native controls and no autoplay', () => {
    const { container } = render(<GuideVideo />);
    const video = container.querySelector('video')!;
    expect(video).toHaveAttribute('controls');
    expect(video).not.toHaveAttribute('autoplay');
    const track = video.querySelector('track')!;
    expect(track).toHaveAttribute('kind', 'captions');
    expect(track).toHaveAttribute('default');
    expect(track).toHaveAttribute('srclang', 'en');
    expect(screen.getByText('Everything in the video is in the checklist above.')).toBeVisible();
  });

  it('says the checklist has everything when the video cannot load', () => {
    const { container } = render(<GuideVideo />);
    const sources = container.querySelectorAll('source');
    fireEvent.error(sources[sources.length - 1]!);
    expect(
      screen.getByText("The video can't play right now. Everything in it is in the checklist above."),
    ).toBeVisible();
  });
});

describe('F-01 page', () => {
  it('says what the player does, what the app does and what it cannot do', () => {
    render(<WelcomePage />);
    expect(screen.getByRole('heading', { level: 1, name: 'What Racket Analytics does' })).toBeVisible();
    const main = document.body;
    expect(main).toHaveTextContent('mark who won each rally');
    expect(main).toHaveTextContent('keep the score');
    expect(main).toHaveTextContent("We can't make line calls or referee your match from one phone.");
    expect(main).toHaveTextContent('not yet checked against the official rulebook');
    expect(main).toHaveTextContent("unofficial");
    expect(main).toHaveTextContent('Only you can see your videos.');
  });

  it('continues to the guide, or straight to setup', () => {
    render(<WelcomePage />);
    expect(screen.getByRole('link', { name: 'Show me how to film' })).toHaveAttribute('href', '/guide');
    expect(screen.getByRole('link', { name: 'Record your first match' })).toHaveAttribute('href', '/matches/new');
  });
});
