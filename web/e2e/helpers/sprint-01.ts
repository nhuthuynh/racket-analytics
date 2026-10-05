// Sprint 1 helpers (QA-owned). Selectors are role/label/text based and use the exact copy from
// docs/design/flows-sprint-01.md, so they double as the copy and accessibility contract with
// the front end. Changing one is a test change (docs/sprints/01/test-change-requests.md).
import { expect, type Page } from '@playwright/test';
import { randomUUID } from 'node:crypto';
import path from 'node:path';

export const FIXTURE_CLIP = path.resolve(__dirname, '../../../fixtures/clips/synthetic-60s/clip.mp4');
export const LONG_CLIP = path.resolve(__dirname, '../../../fixtures/clips/long-4h/clip.mp4');

const MAILPIT = process.env.MAILPIT_API_URL ?? 'http://localhost:8025';
const TOKEN_LINK = /(https?:\/\/[^\s"<>]+\/auth\/callback#token=[A-Za-z0-9_-]{43})/;

// A fresh address per test: rate-limit windows and accounts never leak between specs
// (testing-strategy rule 10).
export function uniqueEmail(name = 'ivy'): string {
  return `${name}+${randomUUID().slice(0, 12)}@example.com`;
}

export async function latestSignInLink(email: string, count = 1, timeoutMs = 15_000): Promise<string> {
  const deadline = Date.now() + timeoutMs;
  for (;;) {
    const search = await fetch(`${MAILPIT}/api/v1/search?query=${encodeURIComponent(`to:"${email}"`)}`);
    const found = ((await search.json()) as { messages?: { ID: string }[] }).messages ?? [];
    const newest = found[0];
    if (found.length >= count && newest) {
      const message = await fetch(`${MAILPIT}/api/v1/message/${newest.ID}`);
      const body = (await message.json()) as { Text?: string; HTML?: string };
      const match = TOKEN_LINK.exec(`${body.Text ?? ''}\n${body.HTML ?? ''}`);
      const link = match?.[1];
      if (!link) throw new Error('sign-in email has no link with a 43-character token');
      return link;
    }
    if (Date.now() > deadline) throw new Error(`no sign-in email for ${email}`);
    await new Promise((r) => setTimeout(r, 250));
  }
}

// A-01 -> A-02 (sprint-01 §7.1). Returns once "Check your email" is shown.
export async function requestLink(page: Page, email: string): Promise<void> {
  await page.goto('/');
  await page.getByLabel('Email address').fill(email);
  await page.getByRole('button', { name: 'Send me a link' }).click();
  await expect(page.getByRole('heading', { level: 1, name: 'Check your email' })).toBeVisible();
}

// Full magic-link sign-in. The link's origin is the configured PUBLIC_WEB_ORIGIN, so only the
// path and fragment are reused against the test base URL.
export async function signInByLink(page: Page, email = uniqueEmail()): Promise<string> {
  await requestLink(page, email);
  const link = new URL(await latestSignInLink(email));
  await page.goto(`${link.pathname}${link.hash}`);
  await expect(page).not.toHaveURL(/token=/);
  return email;
}

// Q-01..Q-07 with the given answers; stops on "Check your answers".
export async function answerSetup(
  page: Page,
  answers: { format: 'Doubles' | 'Singles'; players: string[]; me: string; file?: string },
): Promise<void> {
  await page.getByRole('link', { name: 'Record your first match' }).or(
    page.getByRole('link', { name: /new match/i }),
  ).first().click();
  await page.getByRole('radio', { name: answers.format }).check();
  await page.getByRole('button', { name: 'Continue' }).click();
  await page.getByRole('radio', { name: 'Side-out scoring (traditional)' }).check();
  await page.getByRole('button', { name: 'Continue' }).click();
  const boxes = page.getByRole('textbox');
  for (const [i, name] of answers.players.entries()) await boxes.nth(i).fill(name);
  await page.getByRole('button', { name: 'Continue' }).click();
  await page.getByRole('radio', { name: new RegExp(`^${answers.me} \\(Side [AB]\\)$`) }).check();
  await page.getByRole('button', { name: 'Continue' }).click();
  await page.getByRole('button', { name: 'Continue' }).click(); // date: today by default
  await page.getByLabel('Choose video').setInputFiles(answers.file ?? FIXTURE_CLIP);
  await page.getByRole('button', { name: 'Continue' }).click();
  await expect(page.getByRole('heading', { level: 1, name: 'Check your answers' })).toBeVisible();
}

export async function expectErrorSummary(page: Page, message: string | RegExp): Promise<void> {
  const summary = page.getByRole('alert').filter({ hasText: 'There is a problem' });
  await expect(summary).toBeVisible();
  await expect(summary.getByRole('link', { name: message })).toBeVisible();
  await expect(page).toHaveTitle(/^Error: /);
}

// The synthetic clip followed by an ISO-BMFF 'free' box of ``extraMb`` MiB: still a valid MP4
// (players and ffprobe skip 'free'), but large enough to be sent in several chunks, so a
// connection cut or a tab close can happen mid-upload. Written to the test's output dir.
export async function paddedClip(dir: string, extraMb: number, name = 'Sat doubles.mp4'): Promise<string> {
  const fs = await import('node:fs/promises');
  const clip = await fs.readFile(FIXTURE_CLIP);
  const size = extraMb * 1024 * 1024;
  const header = Buffer.alloc(8);
  header.writeUInt32BE(size + 8, 0);
  header.write('free', 4, 'ascii');
  const file = path.join(dir, name);
  await fs.mkdir(dir, { recursive: true });
  await fs.writeFile(file, Buffer.concat([clip, header, Buffer.alloc(size)]));
  return file;
}

export async function writeBytes(dir: string, name: string, bytes: Buffer): Promise<string> {
  const fs = await import('node:fs/promises');
  await fs.mkdir(dir, { recursive: true });
  const file = path.join(dir, name);
  await fs.writeFile(file, bytes);
  return file;
}

export const PDF_BYTES = Buffer.from('%PDF-1.7\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<< /Type /Catalog >>\nendobj\n'.repeat(800), 'latin1');
export const ELF_BYTES = Buffer.concat([Buffer.from([0x7f, 0x45, 0x4c, 0x46, 2, 1, 1, 0]), Buffer.alloc(64 * 1024, 0x90)]);

// Q-07 -> U-01: create the match and start the upload; returns once the upload panel shows.
export async function createAndUpload(page: Page): Promise<void> {
  await page.getByRole('button', { name: 'Create match and upload' }).click();
  await expect(page.getByRole('heading', { name: 'Video upload' })).toBeVisible();
}

export async function uploadPercent(page: Page): Promise<number> {
  const text = await page.getByRole('progressbar').evaluate((el) => el.parentElement?.textContent ?? '');
  const m = /(\d{1,3})%/.exec(text);
  return m ? Number(m[1]) : -1;
}
