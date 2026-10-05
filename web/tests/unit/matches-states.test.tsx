// C-30 (PD-R1-09 / PD-R2R-07) and C-21 (PD-R2R-06): M-01 states per flows-sprint-01 §5 M-01.
// Error: "Sorry, we could not load your matches. Try again. Reference: {support_ref}" with a
// "Try again" button; offline: "You're offline. ..."; loading: skeleton rows with reserved
// height; the card date in the viewer's time zone; the unfinished-upload status in flows words.
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import MatchesError from '@/app/matches/error';
import MatchesLoading from '@/app/matches/loading';
import { LocalDateLine } from '@/components/LocalDate';
import { matchStatusLine } from '@/lib/format';

const path = vi.hoisted(() => ({ value: '/matches' }));
vi.mock('next/navigation', () => ({ usePathname: () => path.value }));

afterEach(() => {
  path.value = '/matches';
  vi.unstubAllGlobals();
});

describe('M-01 error state (C-30)', () => {
  it('a reference that is not a support reference is not shown as one', () => {
    render(<MatchesError error={Object.assign(new Error('x'), { digest: '<b>1</b>' })} reset={vi.fn()} />);
    expect(screen.getByText('Sorry, we could not load your matches. Try again.')).toBeVisible();
    expect(screen.queryByText(/Reference/)).toBeNull();
  });

  it('shows the API support reference and "Try again" calls reset', async () => {
    const reset = vi.fn();
    render(<MatchesError error={Object.assign(new Error('x'), { digest: 'ref_0123456789abcdef' })} reset={reset} />);
    expect(screen.getByText('Sorry, we could not load your matches. Try again. Reference: ref_0123456789abcdef')).toBeVisible();
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(reset).toHaveBeenCalledOnce();
  });

  it('offline says so instead', () => {
    vi.stubGlobal('navigator', { ...navigator, onLine: false });
    render(<MatchesError error={new Error('x')} reset={vi.fn()} />);
    expect(screen.getByText("You're offline. Your matches will appear when you reconnect.")).toBeVisible();
  });

  it('below M-01 (a match, its sheet) the copy names the page, not the list', () => {
    path.value = '/matches/0b8f6c1e-3f3a-4c55-9a51-8d1f0e7d2a10/sheet';
    render(<MatchesError error={Object.assign(new Error('x'), { digest: 'ref_0123456789abcdef' })} reset={vi.fn()} />);
    expect(screen.getByText('Sorry, we could not load this page. Try again. Reference: ref_0123456789abcdef')).toBeVisible();
  });
});

describe('M-01 loading state (C-30)', () => {
  it('says it is loading and reserves the rows', () => {
    const { container } = render(<MatchesLoading />);
    expect(screen.getByRole('status')).toHaveTextContent('Loading your matches…');
    expect(container.querySelectorAll('.skeleton-row')).toHaveLength(3);
  });
});

describe('M-01 dates and status (C-21)', () => {
  it('formats the date in the given time zone, not UTC', () => {
    render(<LocalDateLine prefix="Created " iso="2026-10-05T23:30:00Z" timeZone="Australia/Sydney" />);
    expect(screen.getByText('Created 6 Oct 2026')).toBeVisible();
  });

  it('an unfinished upload reads "Upload stopped at 64%" (flows M-01)', () => {
    expect(matchStatusLine({ status: 'uploading', upload: { state: 'receiving', offset: 64, length: 100 } })).toBe('Upload stopped at 64%');
    expect(matchStatusLine({ status: 'video_received', upload: null })).toBe('Video received');
  });
});
