// Binds web/tests/features/over_limit_messages.feature (ST-072b; flows-sprint-04 §7 Q-10). The
// real Q-07 (MatchSetup) and U-01 (MatchUpload) components; only the API client and the tus
// transfer are fakes that answer with the api-sprint-04 §7 refusals. The first test checks that
// every scenario in the file is bound.
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { act, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { MatchSetup } from '@/components/MatchSetup';
import { MatchUpload } from '@/components/MatchUpload';
import { ApiError } from '@/lib/api/client';
import { FALLBACK_UPLOAD_POLICY, type Match } from '@/lib/api/types';
import type { UploadErrorDetail } from '@/lib/upload/tus-policy';
import type { TransferCallbacks } from '@/lib/upload/transfer';

const FEATURE = readFileSync(path.join(path.dirname(fileURLToPath(import.meta.url)), 'over_limit_messages.feature'), 'utf8');
const SCENARIOS = {
  noTime: 'The 11th match refused without a time still gets a safe message',
  withTime: 'The 11th match refused with a time',
  noUsage: 'A storage refusal without usage numbers still gets a safe message',
  usage: 'A storage refusal says how much of the storage is used',
  flagOff: "Quotas off: today's unfinished-upload refusal is unchanged",
};
const GIB = 2 ** 30;
const ID = '0b8f6c1e-3f3a-4c55-9a51-8d1f0e7d2a10';
const match: Match = {
  id: ID, title: 'Singles · 29 Oct 2026', format: 'singles', status: 'awaiting_upload', media: null,
  created_at: 'x', updated_at: 'x', participants: [], upload: null, rejection: null,
};

/** Q-07: answer every question, then "Create match and upload" meets the API's refusal. */
async function createRefused(error: ApiError): Promise<HTMLElement> {
  const createMatch = vi.fn(async () => Promise.reject(error));
  render(<MatchSetup api={{ createMatch }} today={{ year: 2026, month: 10, day: 29 }} policy={FALLBACK_UPLOAD_POLICY} navigate={vi.fn()} />);
  const cont = () => userEvent.click(screen.getByRole('button', { name: 'Continue' }));
  await userEvent.click(screen.getByRole('radio', { name: 'Singles' }));
  await cont();
  await userEvent.click(screen.getByRole('radio', { name: 'Side-out scoring (traditional)' }));
  await cont();
  await userEvent.type(screen.getByLabelText('Side A player'), 'Ivy');
  await userEvent.type(screen.getByLabelText('Side B player'), 'Carlos');
  await cont();
  await userEvent.click(screen.getByRole('radio', { name: 'Ivy (Side A)' }));
  await cont();
  await cont();
  await userEvent.upload(screen.getByLabelText('Choose video'), new File(['x'], 'Sat.mp4', { type: 'video/mp4' }));
  await cont();
  await userEvent.click(screen.getByRole('button', { name: 'Create match and upload' }));
  await waitFor(() => expect(createMatch).toHaveBeenCalledOnce());
  return screen.findByRole('alert');
}

/** U-01: the upload handed over from setup starts and the API refuses its creation. */
function uploadRefused(detail: Partial<UploadErrorDetail>): HTMLElement {
  let callbacks: TransferCallbacks | null = null;
  const start = vi.fn((o: { callbacks: TransferCallbacks }) => ((callbacks = o.callbacks), { pause: vi.fn(), resume: vi.fn(), abort: vi.fn() }));
  render(
    <MatchUpload match={match} policy={FALLBACK_UPLOAD_POLICY} startTransfer={start as never} onUploaded={vi.fn()} onProblem={vi.fn()}
      initialFile={new File([new Uint8Array(10)], 'Sat.mp4', { type: 'video/mp4' })} />,
  );
  act(() => callbacks!.onError(429, { code: null, retryAt: null, supportRef: null, ...detail }));
  return screen.getByRole('alert');
}

describe('over_limit_messages.feature', () => {
  it('binds every scenario in the feature file', () => {
    for (const name of Object.values(SCENARIOS)) expect(FEATURE).toContain(`Scenario: ${name}`);
    expect(FEATURE.match(/^\s*Scenario:/gm)).toHaveLength(Object.keys(SCENARIOS).length);
  });

  it(SCENARIOS.noTime, async () => {
    const alert = await createRefused(new ApiError(429, 'rate_limited'));
    expect(alert).toHaveTextContent('You can start a new match within the hour.');
    expect(alert).toHaveTextContent('Your answers are kept.');
    expect(alert.textContent).not.toMatch(/rate_limited|429/);
  });

  it(SCENARIOS.withTime, async () => {
    const at = '2026-10-29T14:05:00Z';
    const local = new Date(at).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', hourCycle: 'h23' });
    const alert = await createRefused(new ApiError(429, 'rate_limited', null, { retryAt: at }));
    expect(alert.textContent).toMatch(new RegExp(`You can start a new match (tomorrow )?at ${local}\\.`));
  });

  it(SCENARIOS.noUsage, () => {
    const alert = uploadRefused({ code: 'storage_quota_exceeded' });
    expect(alert).toHaveTextContent("This video won't fit in your storage.");
    expect(within(alert).getByRole('link', { name: /won't fit/ })).toHaveAttribute('href', '/matches');
  });

  it(SCENARIOS.usage, () => {
    const quota = { usedBytes: Math.round(18.2 * GIB), limitBytes: 20 * GIB, requestedBytes: 3 * GIB };
    const alert = uploadRefused({ code: 'storage_quota_exceeded', quota });
    expect(alert).toHaveTextContent('You have used 18.2 of 20 GB.');
    expect(alert).toHaveTextContent('Nothing from this file was saved.');
  });

  it(SCENARIOS.flagOff, () => {
    const alert = uploadRefused({ code: 'upload_quota_exceeded' });
    expect(alert).toHaveTextContent('You have too many unfinished uploads.');
    expect(alert.textContent).not.toMatch(/storage/);
  });
});
