// ST-085 (NFR-034.1-.3; P-03 "focus trapped, returned", flows-sprint-04 §9; QA-ST065-01): one test
// per close path of the "Not for me" dialog, so a failure names its path. After Close, Cancel or
// Esc the focus is on that row's "Not for me", and it was moved there only once no dialog was on
// the page (Chromium refuses focus behind an open modal <dialog>; jsdom does not model that).
// Negative first: a dialog removed without restoring focus, or focus left on <body>, fails.
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { PlanView } from '@/components/plan/PlanView';
import { parsePlan } from '@/lib/api/plan';
import { planBody } from './fixtures/plan';

const OPENER = 'Not for me, Serve to a target';
let focusedWhileDialogOpen: boolean[];

beforeEach(() => {
  focusedWhileDialogOpen = [];
  vi.spyOn(navigator, 'onLine', 'get').mockReturnValue(true);
  const focus = HTMLElement.prototype.focus;
  vi.spyOn(HTMLElement.prototype, 'focus').mockImplementation(function (this: HTMLElement, options) {
    if (this.getAttribute('aria-label') === OPENER) focusedWhileDialogOpen.push(document.querySelector('dialog') !== null);
    focus.call(this, options);
  });
});

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
  expect(screen.getByRole('dialog')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Cancel' })).toHaveFocus();
  return user;
}

async function expectFocusReturned() {
  expect(screen.queryByRole('dialog')).toBeNull();
  await waitFor(() => expect(screen.getByRole('button', { name: OPENER })).toHaveFocus());
  expect(document.activeElement).not.toBe(document.body);
  expect(focusedWhileDialogOpen.length).toBeGreaterThan(0);
  expect(focusedWhileDialogOpen).not.toContain(true);
}

describe('NFR-034 focus returns to "Not for me", one test per close path (negative first)', () => {
  it('NFR-034.3 Esc: focus is on "Not for me", not left on <body>', async () => {
    const user = await openDialog();
    await user.keyboard('{Escape}');
    // jsdom runs no close request on Esc; a browser fires this cancelable event at the dialog.
    const open = document.querySelector('dialog');
    if (open) fireEvent(open, new Event('cancel', { cancelable: true }));
    await expectFocusReturned();
  });

  it('NFR-034.2 Cancel: focus is on "Not for me"', async () => {
    const user = await openDialog();
    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    await expectFocusReturned();
  });

  it('NFR-034.1 Close (no other drill fits): focus is on "Not for me"', async () => {
    const user = await openDialog();
    await user.click(screen.getByRole('button', { name: 'Swap drill' }));
    await user.click(await screen.findByRole('button', { name: 'Close' }));
    await expectFocusReturned();
  });
});
