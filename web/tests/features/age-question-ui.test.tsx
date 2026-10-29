// Binds web/tests/features/age_question_ui.feature (ST-068b; FR-003). Each scenario is named as in
// the feature file and the first test checks the two lists match. The API answers with the bodies
// captured from the real backend on Postgres (web/tests/contract/live-age.json), through the real
// client (server pages and browser alike); only `fetch` is a fake.
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { cloneElement, type ReactElement } from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

type Live = Record<string, { status: number; body: unknown }>;
const wire = vi.hoisted(() => ({ gate: 'config_off', me: 'me_pending', answer: 'under_age' }));
const HERE = path.dirname(fileURLToPath(import.meta.url));
const LIVE = JSON.parse(readFileSync(path.join(HERE, '../contract/live-age.json'), 'utf8')) as Live;

const fakeFetch = vi.hoisted(() => vi.fn());
vi.mock('@/lib/api/server', async () => {
  const { createApiClient } = await import('@/lib/api/client');
  return { serverApi: async () => createApiClient({ baseUrl: 'http://api.test', fetch: fakeFetch }) };
});
vi.mock('@/lib/api/browser', async () => {
  const { createApiClient } = await import('@/lib/api/client');
  return { browserApi: createApiClient({ baseUrl: '/api', fetch: fakeFetch }) };
});
class NotFound extends Error {}
vi.mock('next/navigation', () => ({
  redirect: (to: string) => {
    throw new Error(`redirect ${to}`);
  },
  notFound: () => {
    throw new NotFound();
  },
  useRouter: () => ({ push: vi.fn() }),
}));

const { AgeQuestion } = await import('@/components/age/AgeQuestion');
const AgeQuestionPage = (await import('@/app/welcome/age/page')).default;
const NewMatchPage = (await import('@/app/matches/(list)/new/page')).default;

const FEATURE = readFileSync(path.join(HERE, 'age_question_ui.feature'), 'utf8');
const SCENARIOS = { under: 'Under-age applicant', adult: 'Adult confirms', off: 'Flag off, no question' };
const NOTICE = "Don't upload matches with anyone under 18. Film only people who agree to be filmed.";

beforeEach(() => {
  fakeFetch.mockImplementation(async (url: string, init: RequestInit) => {
    const path = new URL(url, 'http://web.test').pathname.replace(/^\/api/, '');
    const key =
      path === '/config/public' ? wire.gate
      : path === '/me' ? wire.me
      : path === '/me/age-confirmation' && init.method === 'POST' ? wire.answer
      : 'route_off';
    const live = LIVE[key]!;
    return new Response(JSON.stringify(live.body), { status: live.status });
  });
});

/** Given the age gate is on/off; And a new address has signed in with a link (a pending sign-in). */
function givenGate(on: boolean) {
  wire.gate = on ? 'config_on' : 'config_off';
  wire.me = on ? 'me_pending' : 'adult';
}

async function answers(label: string) {
  const user = userEvent.setup();
  await user.click(screen.getByRole('radio', { name: label }));
  await user.click(screen.getByRole('button', { name: 'Continue' }));
}

/** The upload page Q-01..Q-06, answered up to "Choose video". */
async function openUploadPage() {
  render((await NewMatchPage()) as ReactElement);
  const user = userEvent.setup();
  const cont = () => user.click(screen.getByRole('button', { name: 'Continue' }));
  await user.click(await screen.findByRole('radio', { name: 'Singles' }));
  await cont();
  await user.click(screen.getByRole('radio', { name: 'Side-out scoring (traditional)' }));
  await cont();
  await user.type(screen.getByLabelText('Side A player'), 'Ivy');
  await user.type(screen.getByLabelText('Side B player'), 'Carlos');
  await cont();
  await user.click(screen.getByRole('radio', { name: 'Ivy (Side A)' }));
  await cont();
  await cont();
  expect(screen.getByLabelText('Choose video')).toBeVisible();
}

describe('Feature: The age question after sign-in', () => {
  it('binds every scenario of the feature file', () => {
    const inFile = [...FEATURE.matchAll(/^\s*Scenario: (.+)$/gm)].map((m) => m[1]!.trim()).sort();
    expect(inFile).toEqual(Object.values(SCENARIOS).sort());
  });

  it(`Scenario: ${SCENARIOS.under}`, async () => {
    givenGate(true);
    wire.answer = 'under_age';
    render((await AgeQuestionPage()) as ReactElement);
    await answers('No, I am under 18');
    expect(await screen.findByRole('heading', { level: 1, name: "You can't have an account yet" })).toBeVisible();
    expect(
      screen.getByText('You need to be 18 or over to use this app. We did not make an account for you.'),
    ).toBeVisible();
    expect(screen.getByText('You are welcome to come back when you turn 18.')).toBeVisible();
  });

  it(`Scenario: ${SCENARIOS.adult}`, async () => {
    givenGate(true);
    wire.answer = 'adult';
    const page = (await AgeQuestionPage()) as ReactElement;
    expect(page.type).toBe(AgeQuestion);
    const navigate = vi.fn();
    const { unmount } = render(cloneElement(page as ReactElement<{ navigate?: unknown }>, { navigate }));
    await answers('Yes, I am 18 or over');
    await waitFor(() => expect(navigate).toHaveBeenCalledWith('/welcome'));
    unmount();
    wire.me = 'adult';
    await openUploadPage();
    expect(screen.getByRole('heading', { level: 2, name: 'Before you upload' })).toBeVisible();
    expect(screen.getByText(NOTICE)).toBeVisible();
  });

  it(`Scenario: ${SCENARIOS.off}`, async () => {
    givenGate(false);
    await expect(AgeQuestionPage()).rejects.toBeInstanceOf(NotFound);
    await openUploadPage();
    expect(screen.queryByText(NOTICE)).toBeNull();
    expect(screen.queryByRole('heading', { name: 'Before you upload' })).toBeNull();
  });
});
