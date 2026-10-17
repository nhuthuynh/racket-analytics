// A-01 before hydration (CI-SIGNIN-HYDRATION, found on PR #105's webkit E2E run 39055141846).
// The server renders the form before React has attached onSubmit. A tap on "Send me a link"
// in that window was a native GET submit: the page reloaded as /?email=<address> (the address
// in the URL, against AQS/SEC-05) and no link was sent. Until hydration, the field and the
// button are disabled, so nothing can be typed or sent that React would not see.
import { render, screen } from '@testing-library/react';
import { renderToString } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import { SignInForm } from '@/components/SignInForm';

const api = () => ({ requestLink: vi.fn(async () => undefined) });

function serverMarkup(variant?: 'sign-in' | 'expired'): Document {
  const html = renderToString(<SignInForm api={api()} variant={variant} />);
  return new DOMParser().parseFromString(`<body>${html}</body>`, 'text/html');
}

describe('SignInForm before hydration (CI-SIGNIN-HYDRATION)', () => {
  it('server HTML: the button cannot submit the form natively before hydration', () => {
    const doc = serverMarkup();
    const button = doc.querySelector('button[type="submit"]');
    expect(button?.textContent).toBe('Send me a link');
    expect(button?.hasAttribute('disabled')).toBe(true);
  });

  it('server HTML: the field takes no typing that React would not see', () => {
    const doc = serverMarkup();
    expect(doc.querySelector('input#email')?.hasAttribute('disabled')).toBe(true);
  });

  it('server HTML of A-04 ("Send a new link") is disabled the same way', () => {
    const doc = serverMarkup('expired');
    expect(doc.querySelector('button[type="submit"]')?.hasAttribute('disabled')).toBe(true);
    expect(doc.querySelector('input#email')?.hasAttribute('disabled')).toBe(true);
  });

  it('once mounted in the browser, the field and the button are enabled', () => {
    render(<SignInForm api={api()} />);
    expect(screen.getByLabelText('Email address')).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Send me a link' })).toBeEnabled();
  });
});
