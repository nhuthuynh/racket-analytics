// Upload helpers for the "close the tab mid-upload" journeys (QA-owned; CI-FLAKE-RESUMABLE).
import { expect, type BrowserContext, type Page } from '@playwright/test';

const DIGITS = /^\d+$/;

/**
 * Whether the E2E holds back the tus PATCH that starts at `uploadOffset`: the first chunk that
 * starts at or after `atPercent` of the file. Anything without a usable offset, or at the end,
 * goes through, so the hold can never stop a request it does not understand.
 */
export function holdsAt(uploadOffset: string | undefined, fileSize: number, atPercent: number): boolean {
  if (!(atPercent >= 1 && atPercent <= 99)) throw new Error(`atPercent must be between 1 and 99, got ${atPercent}`);
  if (!uploadOffset || !DIGITS.test(uploadOffset) || !(fileSize > 0)) return false;
  const offset = Number(uploadOffset);
  return offset < fileSize && offset * 100 >= atPercent * fileSize;
}

export interface HeldChunk {
  /** The upload URL (tus) the chunk was for. */
  url: string;
  /** Its Upload-Offset: the server has every byte before it and none after. */
  offset: number;
}

/**
 * Routes the page's tus PATCH requests: chunks before `atPercent` go through, the first one at
 * or after it is never answered, so the page can close with the upload unfinished by
 * construction (CI-FLAKE-RESUMABLE). `chunk` resolves when that PATCH has been sent, i.e. every
 * earlier chunk was accepted (tus sends one PATCH at a time).
 */
export async function holdUploadAt(page: Page, fileSize: number, atPercent: number): Promise<{ chunk: Promise<HeldChunk> }> {
  let hold: (chunk: HeldChunk) => void = () => undefined;
  const held = new Promise<HeldChunk>((resolve) => {
    hold = resolve;
  });
  await page.route('**/uploads/**', async (route) => {
    const request = route.request();
    const offset = request.headers()['upload-offset'];
    if (request.method() === 'PATCH' && holdsAt(offset, fileSize, atPercent)) {
      hold({ url: request.url(), offset: Number(offset) });
      return; // never answered: the tab closes with this chunk unsent
    }
    await route.fallback();
  });
  return { chunk: held };
}

/** The server's tus offset for an upload URL (HEAD, api-sprint-00 §6). */
export async function serverOffset(context: BrowserContext, uploadUrl: string): Promise<number> {
  const head = await context.request.head(uploadUrl, { headers: { 'Tus-Resumable': '1.0.0' } });
  expect(head.status()).toBe(200);
  return Number(head.headers()['upload-offset']);
}

/**
 * The server offset once it has stopped changing for a full interval. A PATCH still in flight
 * when the tab closes can land afterwards and move it (QA-V1-02).
 */
export async function settledServerOffset(context: BrowserContext, uploadUrl: string): Promise<number> {
  expect(uploadUrl, 'no PATCH was seen, so there is no upload URL').not.toBe('');
  let settled = -1;
  await expect
    .poll(
      async () => {
        const now = await serverOffset(context, uploadUrl);
        const stable = now === settled;
        settled = now;
        return stable;
      },
      { intervals: [1_000], timeout: 30_000 },
    )
    .toBe(true);
  return settled;
}
