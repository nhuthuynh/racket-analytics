// QA-ST065-01 (ST-065; flows-sprint-04 §9 P-03 "focus trapped, returned"; WCAG 2.4.3): after the
// "Not for me" dialog closes by Cancel, Esc or Close, focus goes back to the row's "Not for me".
// Chromium refuses focus while a modal <dialog> is still open (the page behind it is inert), and
// jsdom does not model that, so the test also checks that no dialog is on the page when the
// opener is focused. Negative first: before the fix the opener was focused with the dialog open.
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { PlanView } from '@/components/plan/PlanView';
import { parsePlan } from '@/lib/api/plan';
import { planBody } from './fixtures/plan';

const OPENER = 'Not for me, Serve to a target';
let dialogOpenWhenOpenerFocused: boolean[];

beforeEach(() => {
  dialogOpenWhenOpenerFocused = [];
  vi.spyOn(navigator, 'onLine', 'get').mockReturnValue(true);
  const focus = HTMLElement.prototype.focus;
  vi.spyOn(HTMLElement.prototype, 'focus').mockImplementation(function (this: HTMLElement, options) {
    if (this.getAttribute('aria-label') === OPENER || this.textContent === 'Not for me') {
      dialogOpenWhenOpenerFocused.push(document.querySelector('dialog') !== null);
    }
    focus.call(this, options);
  });
});
afterEach(() => vi.restoreAllMocks());

async function openDialog() {
  render(
    <PlanView
      api={{ getPlan: vi.fn(async () => ({ kind: 'plan' as const, plan: parsePlan(planBody()) })) }}
      followApi={{ markDone: vi.fn(), undoDone: vi.fn(), swap: vi.fn(async () => ({ kind: 'no_alternative' as const })) }}
      onSignedOut={vi.fn()}
      evidenceApi={{ stats: vi.fn(), evidence: vi.fn() }}
    />,
  );
  const user = userEvent.setup();
  await user.click(await screen.findByRole('button', { name: OPENER }));
  return user;
}

describe('focus returns to "Not for me" once the dialog is gone (negative first)', () => {
  it.each([
    ['Cancel', async (user: ReturnType<typeof userEvent.setup>) => user.click(screen.getByRole('button', { name: 'Cancel' }))],
    ['Close', async (user: ReturnType<typeof userEvent.setup>) => {
      await user.click(screen.getByRole('button', { name: 'Swap drill' }));
      await user.click(await screen.findByRole('button', { name: 'Close' }));
    }],
  ])('after %s the opener is focused, and only after the dialog left the page', async (_, close) => {
    const user = await openDialog();
    await close(user);
    expect(screen.queryByRole('dialog')).toBeNull();
    await waitFor(() => expect(screen.getByRole('button', { name: OPENER })).toHaveFocus());
    expect(dialogOpenWhenOpenerFocused).not.toContain(true);
  });
});
