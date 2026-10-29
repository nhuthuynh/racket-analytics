// Binds web/tests/features/storage_full_messages.feature (ST-072b-part2; flows-sprint-04 §7 Q-10).
// The real U-01 (MatchUpload) component; only the tus transfer is a fake that answers with the
// api-sprint-04 §7 refusal. The first test checks that every scenario in the file is bound.
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { act, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { MatchUpload } from '@/components/MatchUpload';
import { FALLBACK_UPLOAD_POLICY, type Match } from '@/lib/api/types';
import type { UploadErrorDetail } from '@/lib/upload/tus-policy';
import type { TransferCallbacks } from '@/lib/upload/transfer';

const FEATURE = readFileSync(path.join(path.dirname(fileURLToPath(import.meta.url)), 'storage_full_messages.feature'), 'utf8');
const SCENARIOS = {
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

describe('storage_full_messages.feature', () => {
  it('binds every scenario in the feature file', () => {
    for (const name of Object.values(SCENARIOS)) expect(FEATURE).toContain(`Scenario: ${name}`);
    expect(FEATURE.match(/^\s*Scenario:/gm)).toHaveLength(Object.keys(SCENARIOS).length);
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
