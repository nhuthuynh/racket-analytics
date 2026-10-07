// QA-R1S3-01 (NFR-028, WCAG 2.2 SC 2.5.8): the one not-found page, which a player sees for another
// player's stats, a deleted match's stats or a wrong id (NFR-051), measured "Go to your matches"
// at 178x21 CSS px at 320/360 px (E2E-03-06, keyboard-and-narrow.spec.ts). The link stands alone
// in its paragraph, so the inline exception does not apply: it must carry a class whose rule gives
// it a target of at least 24 px (jsdom has no layout, so the rule itself is checked in the CSS).
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

vi.mock('next/headers', () => ({ headers: async () => new Headers() }));

const NotFound = (await import('@/app/not-found')).default;
const css = readFileSync(path.resolve(process.cwd(), 'src/app/globals.css'), 'utf8');

function ruleOf(selector: string): string {
  const at = css.indexOf(`\n${selector} {`);
  if (at < 0) return '';
  return css.slice(at, css.indexOf('}', at));
}

describe('not-found page targets (QA-R1S3-01)', () => {
  it('"Go to your matches" is a standalone link with a touch-sized target class, not a bare 21 px link', async () => {
    render(await NotFound());
    const link = screen.getByRole('link', { name: 'Go to your matches' });
    expect(link).toHaveAttribute('href', '/matches');
    expect(link).toHaveClass('touch-link');
  });

  it('the touch-link rule gives the target a block size of at least 24 px (48 px touch token)', () => {
    const rule = ruleOf('.touch-link');
    expect(rule).toMatch(/display:\s*inline-flex/);
    expect(rule).toMatch(/min-block-size:\s*var\(--size-target-touch\)/);
  });
});
