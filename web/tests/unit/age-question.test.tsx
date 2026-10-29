// A-10 Are you 18 or over? / A-11 under-18 outcome and the footage notice (ST-068b; FR-003;
// flows-sprint-04 §5; PM-4 W-A01..W-A09). Negative first: the under-18 path.
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { AgeQuestion } from '@/components/age/AgeQuestion';
import { FootageNotice } from '@/components/age/FootageNotice';
import { AuthCallback } from '@/components/AuthCallback';
import { ApiError } from '@/lib/api/client';
import type { AgeOutcome } from '@/lib/identity/age';

let online = true;
vi.spyOn(navigator, 'onLine', 'get').mockImplementation(() => online);
afterEach(() => {
  online = true;
});

function setup(confirmAge: (isAdult: boolean) => Promise<AgeOutcome>) {
  const api = { confirmAge: vi.fn(confirmAge), requestLink: vi.fn() };
  const navigate = vi.fn();
  render(<AgeQuestion api={api} navigate={navigate} />);
  return { api, navigate, user: userEvent.setup() };
}

const choose = (user: ReturnType<typeof userEvent.setup>, name: string) => user.click(screen.getByRole('radio', { name }));
const submit = (user: ReturnType<typeof userEvent.setup>) => user.click(screen.getByRole('button', { name: 'Continue' }));

describe('A-10 / A-11 the age question', () => {
  it('under 18 on a pending sign-in: says why and what to do instead, no way to change the answer', async () => {
    const { api, user } = setup(async () => 'under_age');
    await choose(user, 'No, I am under 18');
    await submit(user);
    expect(await screen.findByRole('heading', { level: 1, name: "You can't have an account yet" })).toBeVisible();
    expect(api.confirmAge).toHaveBeenCalledWith(false);
    expect(screen.getByText(/We did not make an account for you\./)).toBeVisible();
    expect(screen.getByRole('link', { name: 'Close and return to the start' })).toHaveAttribute('href', '/');
    expect(screen.queryByRole('radio')).toBeNull();
    expect(document.title).toBe("You can't have an account yet – Racket Analytics");
  });

  it('under 18 on an existing account (422): no claim that no account was made, nothing deleted', async () => {
    const { user } = setup(async () => 'confirmation_required');
    await choose(user, 'No, I am under 18');
    await submit(user);
    expect(await screen.findByRole('heading', { level: 1, name: "You can't have an account yet" })).toBeVisible();
    expect(screen.getByText('You need to be 18 or over to use this app.')).toBeVisible();
    expect(screen.queryByText(/We did not make an account/)).toBeNull();
    expect(screen.queryByRole('alert')).toBeNull(); // a step, not an error
  });

  it('Continue with nothing chosen: error summary linked to the first radio, no request', async () => {
    const { api, user } = setup(async () => 'adult');
    await submit(user);
    const summary = await screen.findByRole('alert');
    expect(summary).toHaveFocus();
    expect(screen.getByRole('link', { name: 'Choose yes or no' })).toHaveAttribute('href', '#age-yes');
    expect(document.title).toMatch(/^Error: Are you 18 or over\?/);
    expect(api.confirmAge).not.toHaveBeenCalled();
  });

  it('a failed save keeps the choice and shows the reference', async () => {
    const { user } = setup(async () => {
      throw new ApiError(500, 'internal_error', 'ref_0123456789abcdef');
    });
    await choose(user, 'Yes, I am 18 or over');
    await submit(user);
    expect(await screen.findByText('We could not save your answer. Try again. Reference: ref_0123456789abcdef')).toBeVisible();
    expect(screen.getByRole('radio', { name: 'Yes, I am 18 or over' })).toBeChecked();
  });

  it('a sign-in that expired (401) shows A-04 "This link has expired"', async () => {
    const { user } = setup(async () => {
      throw new ApiError(401, 'unauthenticated');
    });
    await choose(user, 'Yes, I am 18 or over');
    await submit(user);
    expect(await screen.findByRole('heading', { level: 1, name: 'This link has expired' })).toBeVisible();
  });

  it('offline: Continue is disabled with the reason and the choice is kept', async () => {
    online = false;
    const { api, user } = setup(async () => 'adult');
    await choose(user, 'Yes, I am 18 or over');
    expect(screen.getByText('You are offline. Connect to continue.')).toBeVisible();
    expect(screen.getByRole('button', { name: 'Continue' })).toBeDisabled();
    expect(api.confirmAge).not.toHaveBeenCalled();
  });

  it('while saving: "Checking…" and Continue disabled; then 18 or over goes to the first-run page', async () => {
    let finish: (v: AgeOutcome) => void = () => {};
    const { navigate, user } = setup(() => new Promise((resolve) => (finish = resolve)));
    expect(screen.getByRole('heading', { level: 1, name: 'Are you 18 or over?' })).toBeVisible();
    expect(screen.getByText(/We do not store your birth date\./)).toBeVisible();
    await choose(user, 'Yes, I am 18 or over');
    await submit(user);
    expect(screen.getByRole('button', { name: 'Checking…' })).toBeDisabled();
    finish('adult');
    await waitFor(() => expect(navigate).toHaveBeenCalledWith('/welcome'));
  });
});

describe('Footage notice', () => {
  it('flag off: nothing at all', () => {
    const { container } = render(<FootageNotice show={false} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('flag on: "Before you upload" with the PM-4 text, information, not a checkbox', () => {
    render(<FootageNotice show />);
    expect(screen.getByRole('heading', { level: 2, name: 'Before you upload' })).toBeVisible();
    expect(screen.getByText("Don't upload matches with anyone under 18. Film only people who agree to be filmed.")).toBeVisible();
    expect(screen.queryByRole('checkbox')).toBeNull();
  });
});

describe('A-03 after the link', () => {
  const TOKEN = 'Abc_-0123456789abcdefghijklmnopqrstuvwxyzAB';

  it('a sign-in that needs the age answer goes to the age question, not to the first-run page', async () => {
    window.history.replaceState(null, '', `/auth/callback#token=${TOKEN}`);
    const navigate = vi.fn();
    const api = {
      exchangeLink: vi.fn(async () => ({ newAccount: true })),
      requestLink: vi.fn(),
      me: vi.fn(async () => {
        throw new ApiError(403, 'age_confirmation_required');
      }),
    };
    render(<AuthCallback api={api} navigate={navigate} />);
    await waitFor(() => expect(navigate).toHaveBeenCalledWith('/welcome/age'));
    expect(navigate).toHaveBeenCalledTimes(1);
  });

  it('flag off: GET /me answers and the destination is unchanged', async () => {
    window.history.replaceState(null, '', `/auth/callback#token=${TOKEN}`);
    const navigate = vi.fn();
    const api = {
      exchangeLink: vi.fn(async () => ({ newAccount: false })),
      requestLink: vi.fn(),
      me: vi.fn(async () => ({ id: 'x', display_name: null })),
    };
    render(<AuthCallback api={api} navigate={navigate} />);
    await waitFor(() => expect(navigate).toHaveBeenCalledWith('/matches'));
  });
});
