// QA-VERIFY04R3-06 (NFR-028, WCAG 2.2 SC 2.5.8; G04-08 (b)): on R-01 at 320 px the "Use my
// matches to improve the app" checkbox measured 19x24 CSS px (E2E-04-07, flag-on project,
// targets-R-01-320.json: `input "" 19x24`). A `.choice` row is a flex row and its long label
// wraps at 320 px, so the input shrank below its 1.5rem size. jsdom has no layout, so the rule
// itself is checked in the CSS (as qa-r1s3-01-not-found-target.test.tsx does). Negative first.
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';

const css = readFileSync(path.resolve(process.cwd(), 'src/app/globals.css'), 'utf8');

function ruleOf(selector: string): string {
  const at = css.indexOf(`\n${selector} {`);
  if (at < 0) return '';
  return css.slice(at, css.indexOf('}', at));
}

describe('.choice input keeps its 24 px target in a narrow row (QA-VERIFY04R3-06)', () => {
  it('may not shrink when its label wraps (flex-shrink 0 or flex none)', () => {
    expect(ruleOf('.choice input')).toMatch(/flex(-shrink)?:\s*(0|none)\b/);
  });

  it('keeps its 1.5rem (24 px) size in both directions', () => {
    const rule = ruleOf('.choice input');
    expect(rule).toMatch(/inline-size:\s*1\.5rem/);
    expect(rule).toMatch(/block-size:\s*1\.5rem/);
  });
});
