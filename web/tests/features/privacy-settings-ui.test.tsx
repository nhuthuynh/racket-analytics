// Binds web/tests/features/privacy_settings_ui.feature (ST-071; FR-008, FR-009). Each scenario
// below is named as in the feature file, and the first test checks that the two lists match, so a
// scenario added to the file without a binding fails here. The API is a fake at the R-01 port;
// the page's flag check runs the real page module with the public config mocked.
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { PrivacySettings } from '@/components/settings/PrivacySettings';
import type { PrivacySettingsApi } from '@/components/settings/PrivacySettingsApi';

const FEATURE = readFileSync(
  path.join(path.dirname(fileURLToPath(import.meta.url)), 'privacy_settings_ui.feature'),
  'utf8',
);
const SCENARIOS = {
  saveFails: 'Saving the video setting fails',
  shorter: 'Choosing a shorter time shows the new deletion date',
  offByDefault: 'Training use is off by default',
  turnOn: 'Turning training use on',
  flagsOff: 'Both settings turned off',
};

class NotFound extends Error {}
const features = vi.hoisted(() => ({ value: { retention: true, consent: true } }));
vi.mock('next/navigation', () => ({
  notFound: () => {
    throw new NotFound();
  },
}));
vi.mock('@/components/settings/PrivacySettingsApi', async (original) => ({
  ...(await original<object>()),
  serverFeatures: async () => features.value,
}));

const CHOICES = [30, 90, 365, null];
const DEMO = { matchId: '6647c07e-7c78-41a1-86c4-a49d73f2a69b', title: 'Demo match' };

// Background: both settings on; 90 days; "Demo match" with a video
function fakeApi(over: Partial<PrivacySettingsApi> = {}): PrivacySettingsApi {
  let days: number | null = 90;
  return {
    retention: vi.fn(async () => ({ kind: 'ok' as const, value: { days, choices: CHOICES } })),
    saveRetention: vi.fn(async (d) => {
      days = d;
      return { kind: 'ok' as const, value: { days, choices: CHOICES } };
    }),
    reviewVideos: vi.fn(async () => ({
      kind: 'ok' as const,
      value: [{ ...DEMO, deleteAt: days === 30 ? '2026-11-28T13:06:46.371Z' : '2027-01-27T13:06:46.371Z' }],
    })),
    consent: vi.fn(async () => ({ kind: 'ok' as const, value: { optIn: false } })),
    saveConsent: vi.fn(async (optIn) => ({ kind: 'ok' as const, value: { optIn } })),
    ...over,
  };
}

async function opened(api: PrivacySettingsApi) {
  render(<PrivacySettings features={{ retention: true, consent: true }} api={api} timeZone="UTC" onSignedOut={vi.fn()} />);
  await screen.findByRole('heading', { level: 2, name: 'How long we keep your videos' });
}

async function chooseAndSave(choice: string) {
  const user = userEvent.setup();
  await user.click(screen.getByRole('radio', { name: choice }));
  await user.click(screen.getByRole('button', { name: 'Save video setting' }));
}

describe('Feature: Privacy settings', () => {
  it('binds every scenario of the feature file', () => {
    const inFile = [...FEATURE.matchAll(/^\s*Scenario: (.+)$/gm)].map((m) => m[1]!.trim()).sort();
    expect(inFile).toEqual(Object.values(SCENARIOS).sort());
  });

  it(SCENARIOS.saveFails, async () => {
    await opened(fakeApi({ saveRetention: vi.fn(async () => ({ kind: 'error' as const, supportRef: null })) }));
    await chooseAndSave('30 days');
    expect(await screen.findByRole('alert')).toHaveTextContent("We couldn't save your choice. Your old setting still applies. Try again.");
    expect(screen.getByRole('radio', { name: '90 days (default)' })).toBeChecked();
  });

  it(SCENARIOS.shorter, async () => {
    await opened(fakeApi());
    await chooseAndSave('30 days');
    expect(await screen.findByText('Saved. The new deletion dates are shown below.')).toBeInTheDocument();
    expect(await screen.findByText('Video will be deleted on 28 Nov 2026')).toBeInTheDocument();
  });

  it(SCENARIOS.offByDefault, async () => {
    await opened(fakeApi());
    expect(screen.getByRole('checkbox', { name: 'Use my matches to improve the app' })).not.toBeChecked();
  });

  it(SCENARIOS.turnOn, async () => {
    await opened(fakeApi());
    const user = userEvent.setup();
    await user.click(screen.getByRole('checkbox', { name: 'Use my matches to improve the app' }));
    await user.click(screen.getByRole('button', { name: 'Save training choice' }));
    expect(await screen.findByText('Turned on. You can turn it off here at any time.')).toBeInTheDocument();
  });

  it(SCENARIOS.flagsOff, async () => {
    features.value = { retention: false, consent: false };
    const PrivacyPage = (await import('@/app/settings/privacy/page')).default;
    await expect(PrivacyPage()).rejects.toBeInstanceOf(NotFound);
    features.value = { retention: false, consent: true };
    render(await PrivacyPage());
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Privacy settings');
  });
});
