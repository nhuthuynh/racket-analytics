// Self-test of the E2E-03-02 crawl (ST-054 QA; PE-R1-ST054-01, SRE-R1-01, SRE-R1-02). The crawl is
// the G03 measure for NFR-038, so it must neither fail a slow page that is right nor pass a page
// that is wrong. It runs here against a fixture stats page served by page.route (no stack): the
// cards arrive late, "Show me" works only once "hydrated", and the rallies load after the tap, as
// on D-01 and E-01 (flows-sprint-03 §2, §3). Negative cases first.
import { expect, test, type Page } from '@playwright/test';
import { crawlSide } from '../helpers/evidence-crawl';
import { decodableStandIn, rangeResponse } from '../helpers/sprint-02';
import { METRIC_NAMES, REFERENCE } from '../helpers/sprint-03';

const ORIGIN = 'https://crawl-fixture.test';
const MATCH = 'm1';
// Every dictionary metric, whatever its status: this tests the crawl, not COACH-1's publication.
const METRICS = Object.keys(METRIC_NAMES);
test.use({ baseURL: ORIGIN });
test.skip(({ browserName }) => browserName !== 'chromium', 'tests the crawl logic, not a browser: run once');

interface Fixture { withoutN?: string[]; deadLinks?: boolean; emptyFillsLate?: string }

/** What each side block prints (flows-sprint-03 §2 table), from the worked-example reference. */
function sampleLine(id: string, s: Record<string, unknown>): string {
  if (id === 'AN-03') return `${s.points} points in ${s.turns} service turns · n = ${s.turns}`;
  if (id === 'AN-04') return `${s.count} unforced errors in ${s.games} game${s.games === 1 ? '' : 's'}`;
  if (id === 'AN-06') return `n = ${s.n} runs`;
  if (id === 'AN-07') return `n = ${s.n} rallies`;
  return `${s.k} of ${s.n} rallies · n = ${s.n}`;
}

function statsHtml(f: Fixture): string {
  const cards = METRICS.map((id) => ({
    id,
    name: METRIC_NAMES[id] ?? id,
    sides: (['A', 'B'] as const).map((side) => {
      const ref = REFERENCE[id]![side];
      return {
        side,
        line: f.withoutN?.includes(`${id} ${side}`) ? '' : sampleLine(id, ref as unknown as Record<string, unknown>),
        rallies: ref.rallies,
        fillsLate: f.emptyFillsLate === `${id} ${side}`,
      };
    }),
  }));
  const play = f.deadLinks ? 'gone' : 'ok';
  return `<!doctype html><html lang="en"><head><title>Stats: fixture</title></head><body><main><h1>Stats</h1></main>
<script>
const cards = ${JSON.stringify(cards)};
const later = (ms, fn) => setTimeout(fn, ms);
later(200, () => {
  const main = document.querySelector('main');
  for (const c of cards) {
    const section = document.createElement('section');
    section.innerHTML = '<h2>' + c.name + '</h2>';
    for (const s of c.sides) {
      const words = s.side === 'A' ? 'your side' : 'other side';
      const block = document.createElement('div');
      block.dataset.side = s.side;
      block.innerHTML = '<h3>' + (s.side === 'A' ? 'Your side (Ivy, Dana)' : 'Other side (Carlos, Sam)') + '</h3><p>' + s.line
        + '</p><p><button type="button" aria-expanded="false" aria-label="Show me the rallies, ' + c.name + ', ' + words
        + '">Show me the rallies</button></p>';
      const button = block.querySelector('button');
      later(600, () => button.addEventListener('click', () => {   // "hydrated" 600 ms after it shows
        const open = button.getAttribute('aria-expanded') !== 'true';
        button.setAttribute('aria-expanded', String(open));
        block.querySelector('.panel')?.remove();
        if (!open) return;
        const panel = document.createElement('div');
        panel.className = 'panel';
        panel.innerHTML = '<p role="status">Loading the rallies…</p>';
        block.append(panel);
        const title = 'Rallies behind “' + c.name + '”, ' + words;
        const list = (ids) => '<ul aria-label="' + title + '">' + ids.slice(0, 10).map((n) =>
          '<li><a href="/matches/${MATCH}/sheet?play=${play}-' + n + '">Rally ' + n + '</a></li>').join('') + '</ul>';
        later(500, () => {                                         // the evidence request answers
          if (s.fillsLate) {
            panel.innerHTML = '';
            later(500, () => { panel.innerHTML = list([1, 2]); });
          } else {
            panel.innerHTML = s.rallies.length ? list(s.rallies) : '<p>No rallies are behind this stat yet.</p>';
          }
        });
      }));
      section.append(block);
    }
    main.append(section);
  }
});
</script></body></html>`;
}

async function serve(page: Page, f: Fixture): Promise<void> {
  const clip = await decodableStandIn();
  await page.route(`${ORIGIN}/**`, async (route) => {
    const url = new URL(route.request().url());
    const html = (body: string): Promise<void> => route.fulfill({ contentType: 'text/html', body });
    if (url.pathname === `/matches/${MATCH}/stats`) return html(statsHtml(f));
    if (url.pathname === `/matches/${MATCH}/sheet`) {
      const src = url.searchParams.get('play')?.startsWith('gone') ? '/media/gone.webm' : '/media/clip.webm';
      return html(`<!doctype html><html lang="en"><head><title>Sheet</title></head><body><main><h1>Score sheet</h1>
<video src="${src}" muted autoplay playsinline></video></main></body></html>`);
    }
    if (url.pathname === '/media/clip.webm') return route.fulfill(rangeResponse(route.request().headers()['range'], clip));
    return route.fulfill({ status: 404, body: 'not found' });
  });
}

test.describe('@M0 @story-ST-054 Evidence crawl harness', () => {
  test('reports a first rally whose link opens no playable video', async ({ page }) => {
    await serve(page, { deadLinks: true });
    expect(await crawlSide(page, MATCH, 'AN-01', 'A')).toEqual([expect.stringMatching(/^AN-01 A: .*playable video/)]);
  });

  test('reports a side that prints no sample size, AN-06 included', async ({ page }) => {
    await serve(page, { withoutN: ['AN-01 B', 'AN-06 B'] });
    expect(await crawlSide(page, MATCH, 'AN-01', 'B')).toEqual([expect.stringMatching(/^AN-01 B: .*sample size/)]);
    expect(await crawlSide(page, MATCH, 'AN-06', 'B')).toEqual([expect.stringMatching(/^AN-06 B: .*sample size/)]);
  });

  test('reports a side with no rallies whose "Show me" lists rallies after a while', async ({ page }) => {
    expect(REFERENCE['AN-05']?.B.rallies, 'the worked example has a side with n > 0 and no rally behind it').toEqual([]);
    await serve(page, { emptyFillsLate: 'AN-05 B' });
    expect(await crawlSide(page, MATCH, 'AN-05', 'B')).toEqual([expect.stringMatching(/^AN-05 B: /)]);
  });

  test('passes a page that is right but slow: late cards, late hydration, late rallies', async ({ page }) => {
    test.setTimeout(180_000);
    await serve(page, {});
    const problems: string[] = [];
    for (const id of METRICS) {
      for (const side of ['A', 'B'] as const) problems.push(...(await crawlSide(page, MATCH, id, side)));
    }
    expect(METRICS).toHaveLength(7);
    expect(problems).toEqual([]);
  });
});
