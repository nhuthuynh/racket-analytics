// A-01 Sign in, A-02 Check your email, A-04 This link has expired (ST-013; flows §2).
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { SignInForm } from '@/components/SignInForm';
import { ApiError } from '@/lib/api/client';

const api = (impl?: () => Promise<void>) => ({ requestLink: vi.fn(impl ?? (async () => undefined)) });

describe('SignInForm (A-01)', () => {
  it('refuses a malformed address with an error summary and does not call the API', async () => {
    const fake = api();
    render(<SignInForm api={fake} />);
    await userEvent.type(screen.getByLabelText('Email address'), 'ivy@example');
    await userEvent.click(screen.getByRole('button', { name: 'Send me a link' }));
    const summary = screen.getByRole('alert');
    expect(summary).toHaveTextContent('There is a problem');
    expect(summary).toHaveFocus();
    const link = screen.getByRole('link', {
      name: 'Enter an email address in the correct format, like name@example.com',
    });
    await userEvent.click(link);
    expect(screen.getByLabelText('Email address')).toHaveFocus();
    expect(screen.getByLabelText('Email address')).toHaveAttribute('aria-invalid', 'true');
    expect(fake.requestLink).not.toHaveBeenCalled();
    expect(document.title).toMatch(/^Error: /);
  });

  it('PD-R2-01: after the error, typing into the field keeps focus and every character', async () => {
    render(<SignInForm api={api()} />);
    await userEvent.type(screen.getByLabelText('Email address'), 'not-an-email');
    await userEvent.click(screen.getByRole('button', { name: 'Send me a link' }));
    expect(screen.getByRole('alert')).toHaveFocus();
    await userEvent.click(screen.getByRole('link', { name: /Enter an email address/ }));
    await userEvent.keyboard('@x');
    expect(screen.getByLabelText('Email address')).toHaveFocus();
    expect(screen.getByLabelText('Email address')).toHaveValue('not-an-email@x');
  });

  it('tells a rate-limited user when to try again', async () => {
    const fake = api(async () => {
      throw new ApiError(429, 'rate_limited', null, { retryAt: '2026-10-05T14:32:00Z' });
    });
    render(<SignInForm api={fake} />);
    await userEvent.type(screen.getByLabelText('Email address'), 'ivy@example.com');
    await userEvent.click(screen.getByRole('button', { name: 'Send me a link' }));
    expect(await screen.findByRole('link', { name: /You can ask for a new link at \d{2}:\d{2}\./ })).toBeVisible();
  });

  it('has one field: an email input that allows paste and autofill', () => {
    render(<SignInForm api={api()} />);
    expect(screen.getAllByRole('textbox')).toHaveLength(1);
    const field = screen.getByLabelText('Email address');
    expect(field).toHaveAttribute('type', 'email');
    expect(field).toHaveAttribute('autocomplete', 'email');
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Sign in or create an account');
  });

  it('shows "Check your email" with the trimmed address after a 202', async () => {
    const fake = api();
    render(<SignInForm api={fake} />);
    await userEvent.type(screen.getByLabelText('Email address'), '  ivy@example.com ');
    await userEvent.click(screen.getByRole('button', { name: 'Send me a link' }));
    const heading = await screen.findByRole('heading', { level: 1, name: 'Check your email' });
    await waitFor(() => expect(heading).toHaveFocus());
    expect(fake.requestLink).toHaveBeenCalledWith('ivy@example.com');
    expect(screen.getByText('ivy@example.com')).toBeVisible();
    expect(screen.getByText(/It works once and expires in 15 minutes\./)).toBeVisible();
  });

  it('blocks a double submit while sending', async () => {
    let release!: () => void;
    const fake = api(() => new Promise<void>((r) => (release = r)));
    render(<SignInForm api={fake} />);
    await userEvent.type(screen.getByLabelText('Email address'), 'ivy@example.com');
    const button = screen.getByRole('button', { name: 'Send me a link' });
    await userEvent.click(button);
    expect(screen.getByRole('button', { name: 'Sending…' })).toHaveAttribute('aria-busy', 'true');
    await userEvent.click(screen.getByRole('button', { name: 'Sending…' }));
    expect(fake.requestLink).toHaveBeenCalledTimes(1);
    release();
    await screen.findByRole('heading', { name: 'Check your email' });
  });

  it('"send a new link" returns with the address filled in; "different address" empties it', async () => {
    render(<SignInForm api={api()} />);
    await userEvent.type(screen.getByLabelText('Email address'), 'ivy@example.com');
    await userEvent.click(screen.getByRole('button', { name: 'Send me a link' }));
    await userEvent.click(await screen.findByRole('button', { name: 'send a new link' }));
    expect(screen.getByLabelText('Email address')).toHaveValue('ivy@example.com');
    await userEvent.click(screen.getByRole('button', { name: 'Send me a link' }));
    await userEvent.click(await screen.findByRole('button', { name: 'Use a different email address' }));
    expect(screen.getByLabelText('Email address')).toHaveValue('');
  });
});

describe('SignInForm (A-04 variant)', () => {
  it('says the link expired, offers a new one and never pre-fills the address', () => {
    render(<SignInForm api={api()} variant="expired" />);
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('This link has expired');
    expect(screen.getByText('Sign-in links work once and only for 15 minutes.')).toBeVisible();
    expect(screen.getByLabelText('Email address')).toHaveValue('');
    expect(screen.getByRole('button', { name: 'Send a new link' })).toBeVisible();
  });
});
