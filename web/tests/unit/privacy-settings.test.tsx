// R-01 Privacy settings (ST-071; FR-008, FR-009; flows-sprint-04 §6; PM-4 W-R01..W-R11,
// W-C01..W-C07). Unit level: the component against a fake API port, and the pure model.
// Negative first (sprint-04 §3.7 ST-071): a save error keeps the old value.
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { PrivacySettings } from '@/components/settings/PrivacySettings';
import type { PrivacySettingsApi } from '@/components/settings/PrivacySettingsApi';
import { privacyPageExists, retentionChoiceLabel, reviewVideoLine } from '@/components/settings/PrivacySettingsModel';

const CHOICES = [30, 90, 365, null];
const DEMO = { matchId: '6647c07e-7c78-41a1-86c4-a49d73f2a69b', title: 'Demo match', deleteAt: '2027-01-27T13:06:46.371Z' };
const BOTH = { retention: true, consent: true };
let online: boolean;

beforeEach(() => {
  online = true;
  vi.spyOn(navigator, 'onLine', 'get').mockImplementation(() => online);
});

function fakeApi(over: Partial<PrivacySettingsApi> = {}): PrivacySettingsApi {
  return {
    retention: vi.fn(async () => ({ kind: 'ok' as const, value: { days: 90, choices: CHOICES } })),
    saveRetention: vi.fn(async (days) => ({ kind: 'ok' as const, value: { days, choices: CHOICES } })),
    reviewVideos: vi.fn(async () => ({ kind: 'ok' as const, value: [DEMO] })),
    consent: vi.fn(async () => ({ kind: 'ok' as const, value: { optIn: false } })),
    saveConsent: vi.fn(async (optIn) => ({ kind: 'ok' as const, value: { optIn } })),
    ...over,
  };
}

async function shown(api: PrivacySettingsApi, features = BOTH) {
  render(<PrivacySettings features={features} api={api} timeZone="UTC" onSignedOut={vi.fn()} />);
  await screen.findByRole('heading', { level: 2, name: features.retention ? 'How long we keep your videos' : 'Help improve the app' });
}

describe('R-01 save errors (negative first)', () => {
  it('a retention save error keeps the old value and says so', async () => {
    const api = fakeApi({ saveRetention: vi.fn(async () => ({ kind: 'error' as const, supportRef: 'ref_0123456789abcdef' })) });
    await shown(api);
    const user = userEvent.setup();
    await user.click(screen.getByRole('radio', { name: '30 days' }));
    await user.click(screen.getByRole('button', { name: 'Save video setting' }));
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent("We couldn't save your choice. Your old setting still applies. Try again.");
    expect(alert).toHaveTextContent('Reference: ref_0123456789abcdef');
    expect(screen.getByRole('radio', { name: '90 days (default)' })).toBeChecked();
    expect(screen.getByRole('radio', { name: '30 days' })).not.toBeChecked();
  });

  it('a consent save error keeps the old value (off) and says so', async () => {
    const api = fakeApi({ saveConsent: vi.fn(async () => ({ kind: 'error' as const, supportRef: null })) });
    await shown(api);
    const user = userEvent.setup();
    await user.click(screen.getByRole('checkbox', { name: 'Use my matches to improve the app' }));
    await user.click(screen.getByRole('button', { name: 'Save training choice' }));
    expect(await screen.findByRole('alert')).toHaveTextContent("We couldn't save your choice. Your old setting still applies. Try again.");
    expect(screen.getByRole('checkbox', { name: 'Use my matches to improve the app' })).not.toBeChecked();
  });

  it('a saved retention whose new dates cannot be read says so and shows no old date (PE-ST071-01)', async () => {
    const reviewVideos = vi.fn()
      .mockResolvedValueOnce({ kind: 'ok', value: [DEMO] })
      .mockResolvedValue({ kind: 'error', supportRef: 'ref_00000000000000bb' });
    const api = fakeApi({ reviewVideos });
    await shown(api);
    const user = userEvent.setup();
    await user.click(screen.getByRole('radio', { name: '30 days' }));
    await user.click(screen.getByRole('button', { name: 'Save video setting' }));
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Your video setting is saved, but we could not load the new deletion dates. Reload the page to see them.');
    expect(alert).toHaveTextContent('Reference: ref_00000000000000bb');
    expect(screen.queryByText('Saved. The new deletion dates are shown below.')).toBeNull();
    expect(screen.queryByText('Video will be deleted on 27 Jan 2027')).toBeNull();
    expect(screen.queryByRole('list', { name: 'When each video is deleted' })).toBeNull();
    expect(screen.getByRole('radio', { name: '30 days' })).toBeChecked();
  });

  it('a load error shows "Try again" and the reference, and no controls', async () => {
    const api = fakeApi({ retention: vi.fn(async () => ({ kind: 'error' as const, supportRef: 'ref_00000000000000aa' })) });
    render(<PrivacySettings features={BOTH} api={api} onSignedOut={vi.fn()} />);
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('We could not load your privacy settings. Try again.');
    expect(alert).toHaveTextContent('Reference: ref_00000000000000aa');
    expect(screen.queryByRole('radio')).toBeNull();
    expect(screen.queryByRole('checkbox')).toBeNull();
    await userEvent.setup().click(screen.getByRole('button', { name: 'Try again' }));
    expect(api.retention).toHaveBeenCalledTimes(2);
  });

  it('signed out on load goes to sign in', async () => {
    const onSignedOut = vi.fn();
    render(<PrivacySettings features={BOTH} api={fakeApi({ consent: vi.fn(async () => ({ kind: 'signed_out' as const })) })} onSignedOut={onSignedOut} />);
    await waitFor(() => expect(onSignedOut).toHaveBeenCalled());
  });

  it('offline: values read-only, both saves disabled with the reason', async () => {
    online = false;
    await shown(fakeApi());
    expect(screen.getByText('You are offline. Connect to change these settings.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Save video setting' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Save training choice' })).toBeDisabled();
  });
});

describe('R-01 loaded and saved', () => {
  it('while loading, no control shows a value that is not the stored one', () => {
    render(<PrivacySettings features={BOTH} api={fakeApi({ retention: () => new Promise(() => {}) })} onSignedOut={vi.fn()} />);
    expect(screen.getByRole('status')).toHaveTextContent('Loading your privacy settings…');
    expect(screen.queryByRole('radio')).toBeNull();
  });

  it('shows the stored retention choice, the system rule and each video deletion date', async () => {
    await shown(fakeApi());
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Privacy settings');
    expect(screen.getByRole('radio', { name: '90 days (default)' })).toBeChecked();
    expect(screen.getAllByRole('radio').map((r) => (r as HTMLInputElement).labels?.[0]?.textContent))
      .toEqual(['30 days', '90 days (default)', '365 days', 'Until I delete it']);
    expect(screen.getByText(/We delete the file you uploaded 30 days after it is ready/)).toBeInTheDocument();
    const list = screen.getByRole('list', { name: 'When each video is deleted' });
    expect(within(list).getByText('Demo match')).toBeInTheDocument();
    expect(within(list).getByText('Video will be deleted on 27 Jan 2027')).toBeInTheDocument();
  });

  it('consent is off by default and carries the explanation', async () => {
    await shown(fakeApi());
    expect(screen.getByRole('checkbox', { name: 'Use my matches to improve the app' })).not.toBeChecked();
    expect(screen.getByText(/It stays off unless you turn it on\./)).toBeInTheDocument();
    expect(screen.getByText(/You can turn it off at any time\./)).toBeInTheDocument();
  });

  it('saving retention confirms and re-reads the deletion dates', async () => {
    const later = { ...DEMO, deleteAt: '2026-11-28T13:06:46.371Z' };
    const reviewVideos = vi.fn().mockResolvedValueOnce({ kind: 'ok', value: [DEMO] }).mockResolvedValue({ kind: 'ok', value: [later] });
    const api = fakeApi({ reviewVideos });
    await shown(api);
    const user = userEvent.setup();
    await user.click(screen.getByRole('radio', { name: '30 days' }));
    await user.click(screen.getByRole('button', { name: 'Save video setting' }));
    expect(api.saveRetention).toHaveBeenCalledWith(30);
    expect(await screen.findByText('Saved. The new deletion dates are shown below.')).toBeInTheDocument();
    expect(await screen.findByText('Video will be deleted on 28 Nov 2026')).toBeInTheDocument();
    expect(api.saveConsent).not.toHaveBeenCalled();
  });

  it('saving consent on, then off, confirms each', async () => {
    const api = fakeApi();
    await shown(api);
    const user = userEvent.setup();
    await user.click(screen.getByRole('checkbox', { name: 'Use my matches to improve the app' }));
    await user.click(screen.getByRole('button', { name: 'Save training choice' }));
    expect(await screen.findByText('Turned on. You can turn it off here at any time.')).toBeInTheDocument();
    await user.click(screen.getByRole('checkbox', { name: 'Use my matches to improve the app' }));
    await user.click(screen.getByRole('button', { name: 'Save training choice' }));
    expect(await screen.findByText('Turned off. Your matches will not be in any new training set.')).toBeInTheDocument();
    expect(api.saveConsent).toHaveBeenNthCalledWith(1, true);
    expect(api.saveConsent).toHaveBeenNthCalledWith(2, false);
    expect(api.saveRetention).not.toHaveBeenCalled();
  });

  it('no match video yet: the list says so and the setting still saves', async () => {
    await shown(fakeApi({ reviewVideos: vi.fn(async () => ({ kind: 'ok' as const, value: [] })) }));
    expect(screen.getByText('You have no match videos yet.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Save video setting' })).toBeEnabled();
  });

  it('each section appears only with its own flag', async () => {
    const api = fakeApi();
    await shown(api, { retention: false, consent: true });
    expect(screen.queryByRole('radio')).toBeNull();
    expect(api.retention).not.toHaveBeenCalled();
    expect(api.reviewVideos).not.toHaveBeenCalled();
  });

  it('works by keyboard alone: choose with arrows, save with Enter', async () => {
    const api = fakeApi();
    await shown(api);
    const user = userEvent.setup();
    screen.getByRole('radio', { name: '90 days (default)' }).focus();
    await user.keyboard('{ArrowUp}');
    expect(screen.getByRole('radio', { name: '30 days' })).toBeChecked();
    await user.tab();
    expect(screen.getByRole('button', { name: 'Save video setting' })).toHaveFocus();
    await user.keyboard('{Enter}');
    expect(api.saveRetention).toHaveBeenCalledWith(30);
  });
});

describe('R-01 model', () => {
  it('the page exists only when either flag is on', () => {
    expect(privacyPageExists({ retention: false, consent: false })).toBe(false);
    expect(privacyPageExists({ retention: true, consent: false })).toBe(true);
    expect(privacyPageExists({ retention: false, consent: true })).toBe(true);
  });

  it('names each retention choice with PM-4 words', () => {
    expect([30, 90, 365, null].map(retentionChoiceLabel)).toEqual(['30 days', '90 days (default)', '365 days', 'Until I delete it']);
  });

  it('a video with no deletion date is kept until the player deletes it', () => {
    expect(reviewVideoLine({ ...DEMO, deleteAt: null })).toEqual({ text: 'Video kept until you delete it' });
    expect(reviewVideoLine(DEMO)).toEqual({ prefix: 'Video will be deleted on ', iso: DEMO.deleteAt });
  });
});
