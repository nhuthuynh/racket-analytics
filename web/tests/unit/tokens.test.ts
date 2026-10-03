// docs/design/tokens.md §5: the CSS variables generated from tokens.json equal the JSON values.
// The committed src/app/tokens.css must be exactly what the generator produces from the
// designer's source of truth, so a token change cannot drift silently.
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { tokensToCss } from '@/lib/tokens/css';

const here = (p: string) => fileURLToPath(new URL(p, import.meta.url));
const tokens = JSON.parse(readFileSync(here('../../../docs/design/tokens.json'), 'utf8'));
const committedCss = readFileSync(here('../../src/app/tokens.css'), 'utf8');

describe('tokensToCss', () => {
  it('rejects a token file without both themes', () => {
    expect(() => tokensToCss({ color: { light: {} } })).toThrow(/dark/);
  });

  it('rejects a colour that is not a hex value', () => {
    const bad = structuredClone(tokens);
    bad.color.light.text.value = 'red; background: url(x)';
    expect(() => tokensToCss(bad)).toThrow(/color.light.text/);
  });

  it('maps every light and dark colour to --color-<name>', () => {
    const css = tokensToCss(tokens);
    for (const theme of ['light', 'dark'] as const) {
      for (const [name, token] of Object.entries<{ value: string }>(tokens.color[theme])) {
        expect(css).toContain(`--color-${name}: ${token.value};`);
      }
    }
  });

  it('puts the dark theme behind prefers-color-scheme', () => {
    const css = tokensToCss(tokens);
    const dark = css.slice(css.indexOf('@media (prefers-color-scheme: dark)'));
    expect(dark).toContain(`--color-bg: ${tokens.color.dark.bg.value};`);
  });

  it('maps type, space, size, border and focus tokens', () => {
    const css = tokensToCss(tokens);
    expect(css).toContain(`--font-size-md: ${tokens.typography.size.md.value};`);
    expect(css).toContain(`--space-4: ${tokens.space['4'].value};`);
    expect(css).toContain(`--size-target-touch: ${tokens.size['target-touch'].value};`);
    expect(css).toContain(`--border-control-width: ${tokens.border['control-width'].value};`);
    expect(css).toContain(`--focus-ring-width: ${tokens.focus['ring-width'].value};`);
  });

  it('the committed tokens.css equals the generator output (run pnpm tokens to refresh)', () => {
    expect(committedCss).toBe(tokensToCss(tokens));
  });
});
