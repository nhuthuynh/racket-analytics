// Esc on an open modal <dialog> (ST-085, NFR-034.3). jsdom runs no close request on Esc, so after
// the key this fires the cancelable `cancel` event a browser fires at the open dialog (HTML
// "close request" steps); the real browser path is covered by E2E-04-04.
import { fireEvent } from '@testing-library/react';
import type userEvent from '@testing-library/user-event';

export async function pressEsc(user: ReturnType<typeof userEvent.setup>) {
  await user.keyboard('{Escape}');
  const open = document.querySelector('dialog');
  if (open) fireEvent(open, new Event('cancel', { cancelable: true }));
}
