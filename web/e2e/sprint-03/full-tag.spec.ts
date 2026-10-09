// E2E-03-05 Full Tag (ST-052; FR-150, NFR-030; Gherkin §7.6). A player gets "not found" on the
// label tool. A labeller (role and the match's consent record set with the labeller-admin CLI of
// the stack under test, E2E_ADMIN_CMD) also gets "not found" on the player's match, even with a
// consent record: a labeller labels only matches their own account owns (api-sprint-03 §5.1,
// flows-sprint-03 L-01; SEC-S3-TM-08, PE-R2S3-01). On their own match they step frames with ','
// and '.', mark a rally, tag a hit by B1 and export; the export is a full-tag-labels/v1 document
// holding that hit.
// UI assumptions: e2e/helpers/sprint-03.ts.
import { readFileSync } from 'node:fs';
import { expect, test } from '@playwright/test';
import { expectNoBlockingA11yViolations } from '../helpers/axe';
import { signInByLink, uniqueEmail } from '../helpers/sprint-01';
import { receivedMatch } from '../helpers/sprint-02';
import { SCREEN, admin, labelPath } from '../helpers/sprint-03';

test.describe('@M0 @story-ST-052 @fr-150 Full Tag', { tag: '@red-until-ST-052' }, () => {
  test('E2E-03-05 a player, and a labeller on a match of another account, cannot open Full Tag; a labeller frame-steps their own match by keys, tags a hit and exports', async ({ page, browser }, testInfo) => {
    test.setTimeout(180_000);
    const matchId = await receivedMatch(page, 'E2E-03-05 full tag');
    admin(['consent', '--match', matchId, '--record', 'CONSENT-TEAM-SYNTHETIC-E2E']);
    const asPlayer = await page.goto(labelPath(matchId));
    expect(asPlayer?.status()).toBe(404);

    const labeller = await (await browser.newContext()).newPage();
    const email = uniqueEmail('labeller');
    await signInByLink(labeller, email);
    const me = (await (await labeller.request.get('/api/me')).json()) as { id: string };
    admin(['grant-labeller', '--account', me.id]);
    // negative first: another account's match is 404 for a labeller too, consent or not (§5.1)
    const notTheirs = await labeller.goto(labelPath(matchId));
    expect(notTheirs?.status()).toBe(404);
    await expect(labeller.getByRole('heading', { level: 1 })).not.toContainText(/Full Tag/i);

    const ownMatchId = await receivedMatch(labeller, 'E2E-03-05 full tag (labeller)', { signIn: false });
    admin(['consent', '--match', ownMatchId, '--record', 'CONSENT-TEAM-SYNTHETIC-E2E']);
    await labeller.goto(labelPath(ownMatchId));
    await expect(labeller.getByRole('heading', { level: 1 })).toContainText(/Full Tag/i);
    const frame = labeller.getByText(/Frame \d+/).first();
    const before = Number(/\d+/.exec((await frame.textContent()) ?? '')?.[0]);
    await labeller.keyboard.press('.');
    await expect(frame).toContainText(`Frame ${before + 1}`);
    await labeller.keyboard.press(',');
    await expect(frame).toContainText(`Frame ${before}`);
    await expectNoBlockingA11yViolations(labeller, testInfo, SCREEN.fullTag);

    await labeller.getByRole('button', { name: /Rally start/ }).click();
    for (let i = 0; i < 10; i += 1) await labeller.keyboard.press('.');
    await labeller.getByRole('button', { name: /Hit/ }).click();
    await labeller.getByRole('button', { name: 'Carlos', exact: true }).click();
    for (let i = 0; i < 10; i += 1) await labeller.keyboard.press('.');
    await labeller.getByRole('button', { name: /Rally end/ }).click();
    const download = labeller.waitForEvent('download');
    await labeller.getByRole('button', { name: /Export/ }).click();
    const file = await (await download).path();
    const doc = JSON.parse(readFileSync(file, 'utf8')) as {
      schema: string; rallies: { events: { type: string; frame: number; hitter?: string }[] }[];
    };
    expect(doc.schema).toBe('full-tag-labels/v1');
    const hits = doc.rallies.flatMap((r) => r.events).filter((e) => e.type === 'hit');
    expect(hits).toContainEqual(expect.objectContaining({ frame: before + 10, hitter: 'B1' }));
  });
});
