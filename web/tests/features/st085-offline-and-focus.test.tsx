// Binds web/tests/features/st085_offline_and_focus.feature (ST-085; FR-124.R3/.R4, NFR-034.1-.3).
// Integration over the page's own parts: the real service worker (public/sw.js, run in node:vm by
// fixtures/sw.ts) answers the real plan and follow-through clients used by the real PlanView and
// outbox. Only the network and Cache Storage are fakes (fixtures/device.ts). The first test checks
// that every scenario in the feature file is bound.
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { PlanView } from '@/components/plan/PlanView';
import { createOutbox, memoryOutboxStore } from '@/lib/plan-outbox';
import { device } from '../unit/fixtures/device';

const FEATURE = readFileSync(
  path.join(path.dirname(fileURLToPath(import.meta.url)), 'st085_offline_and_focus.feature'),
  'utf8',
);
const SCENARIOS = {
  asOf: 'A plan kept at 18:05 is shown offline with its "as of" line',
  nothingKept: 'No plan kept on this device, offline',
  syncOnce: 'One session marked done offline is sent once when the connection returns',
  flapping: 'The connection drops and returns twice before the queue drains',
  close: 'Close, after "no other drill fits" (NFR-034.1)',
  cancel: 'Cancel (NFR-034.2)',
  esc: 'Esc (NFR-034.3)',
};
const OPENER = 'Not for me, Serve to a target';
const SESSION_1_DONE = '/api/me/plan/sessions/00000000-0000-4000-8000-000000000010/done';

let online: boolean;
let d: ReturnType<typeof device>;

beforeEach(() => {
  online = true;
  vi.spyOn(navigator, 'onLine', 'get').mockImplementation(() => online);
  d = device();
});
afterEach(() => vi.useRealTimers());

/** The device's connection: the network and `navigator.onLine` change, then the browser's event. */
function connection(up: boolean) {
  online = up;
  d.net.up = up;
  act(() => {
    window.dispatchEvent(new Event(up ? 'online' : 'offline'));
  });
}

function openPlanPage() {
  render(
    <PlanView
      api={d.planApi}
      followApi={d.followApi}
      outbox={createOutbox(memoryOutboxStore())}
      onSignedOut={vi.fn()}
      evidenceApi={{ stats: vi.fn(), evidence: vi.fn() }}
    />,
  );
}

const sessionRegions = () => screen.queryAllByRole('region', { name: /^Session \d+ of / });
const session1 = () => screen.getByRole('region', { name: /^Session 1 of 3/ });

async function markSession1DoneOffline() {
  openPlanPage();
  await screen.findByText('Serve to a target');
  connection(false);
  await userEvent.setup().click(within(session1()).getByRole('button', { name: 'Mark done' }));
  expect(await within(session1()).findByText('Saved on this device, will sync')).toBeVisible();
}

async function openDialog() {
  openPlanPage();
  const user = userEvent.setup();
  await user.click(await screen.findByRole('button', { name: OPENER }));
  expect(screen.getByRole('dialog')).toBeInTheDocument();
  return user;
}

/**
 * Esc on an open modal dialog. jsdom runs no close request on Esc, so after the key this fires
 * the cancelable `cancel` event a browser fires at the dialog (HTML "close request" steps).
 */
async function pressEsc(user: ReturnType<typeof userEvent.setup>) {
  await user.keyboard('{Escape}');
  const open = document.querySelector('dialog');
  if (open) fireEvent(open, new Event('cancel', { cancelable: true }));
}

async function expectFocusBackOnOpener() {
  expect(screen.queryByRole('dialog')).toBeNull();
  await waitFor(() => expect(screen.getByRole('button', { name: OPENER })).toHaveFocus());
  expect(document.activeElement).not.toBe(document.body);
}

describe('Feature: The plan page offline, and focus after the "Not for me" dialog', () => {
  it('binds every scenario of the feature file', () => {
    const inFile = [...FEATURE.matchAll(/^\s*Scenario: (.+)$/gm)].map((m) => m[1]!.trim()).sort();
    expect(inFile).toEqual(Object.values(SCENARIOS).sort());
  });

  describe('Rule: FR-124.R3 offline plan read with its "as of" line', () => {
    it(`Scenario: ${SCENARIOS.asOf}`, async () => {
      vi.useFakeTimers({ toFake: ['Date'] });
      vi.setSystemTime(new Date(2026, 9, 18, 18, 5)); // 18:05 on the device's clock
      expect(await d.planApi.getPlan()).toMatchObject({ kind: 'plan' });
      vi.useRealTimers();
      connection(false);
      openPlanPage();
      expect(
        await screen.findByText(/^You are offline\. This is your plan as of 18 Oct 2026, 18:05\.$/),
      ).toBeVisible();
      expect(sessionRegions()).toHaveLength(2);
      expect(within(session1()).getByText('Serve to a target')).toBeVisible();
    });

    it(`Scenario: ${SCENARIOS.nothingKept}`, async () => {
      connection(false);
      openPlanPage();
      expect(await screen.findByText('You are offline and this plan is not saved on this device yet.')).toBeVisible();
      expect(sessionRegions()).toHaveLength(0);
    });
  });

  describe('Rule: FR-124.R4 a "done" marked offline is sent exactly once', () => {
    it(`Scenario: ${SCENARIOS.syncOnce}`, async () => {
      await markSession1DoneOffline();
      expect(d.doneRequests).toEqual([]);
      connection(true);
      expect(await within(session1()).findByText('Done')).toBeVisible();
      expect(d.doneRequests).toEqual([SESSION_1_DONE]);
    });

    it(`Scenario: ${SCENARIOS.flapping}`, async () => {
      await markSession1DoneOffline();
      d.net.hold = true;
      connection(true);
      await waitFor(() => expect(d.doneRequests).toHaveLength(1)); // the first send is in flight
      connection(false);
      connection(true);
      d.net.hold = false;
      await act(async () => d.releaseHeld());
      expect(await within(session1()).findByText('Done')).toBeVisible();
      await act(async () => d.releaseHeld()); // a second send, if one was made, is answered too
      expect(d.doneRequests).toEqual([SESSION_1_DONE]);
      expect(within(session1()).getByText('Done')).toBeVisible();
    });
  });

  describe('Rule: NFR-034.1-.3 focus returns to "Not for me" on every close path', () => {
    it(`Scenario: ${SCENARIOS.close}`, async () => {
      const user = await openDialog();
      await user.click(screen.getByRole('button', { name: 'Swap drill' }));
      expect(await screen.findByText('No other drill fits your setup for this. Your plan is unchanged.')).toBeVisible();
      await user.click(screen.getByRole('button', { name: 'Close' }));
      await expectFocusBackOnOpener();
    });

    it(`Scenario: ${SCENARIOS.cancel}`, async () => {
      const user = await openDialog();
      await user.click(screen.getByRole('button', { name: 'Cancel' }));
      await expectFocusBackOnOpener();
    });

    it(`Scenario: ${SCENARIOS.esc}`, async () => {
      const user = await openDialog();
      await pressEsc(user);
      await expectFocusBackOnOpener();
    });
  });
});
