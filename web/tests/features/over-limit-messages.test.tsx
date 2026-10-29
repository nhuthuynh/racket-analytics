// Binds web/tests/features/over_limit_messages.feature (ST-072b; flows-sprint-04 §7 Q-10). The
// real Q-07 (MatchSetup) component; only the API client is a fake that answers with the
// api-sprint-04 §7 refusal. The first test checks that every scenario in the file is bound.
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { MatchSetup } from '@/components/MatchSetup';
import { ApiError } from '@/lib/api/client';
import { FALLBACK_UPLOAD_POLICY } from '@/lib/api/types';

const FEATURE = readFileSync(path.join(path.dirname(fileURLToPath(import.meta.url)), 'over_limit_messages.feature'), 'utf8');
const SCENARIOS = {
  noTime: 'The 11th match refused without a time still gets a safe message',
  withTime: 'The 11th match refused with a time',
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
});
