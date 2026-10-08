// Upload helpers for the "close the tab mid-upload" journeys (QA-owned; CI-FLAKE-RESUMABLE).
import { expect, type BrowserContext } from '@playwright/test';

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
