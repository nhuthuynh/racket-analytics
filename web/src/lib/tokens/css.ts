// Design tokens (docs/design/tokens.json, principal-designer) → CSS custom properties.
// Naming per docs/design/tokens.md: --color-<name> for the active theme, plus --space-*,
// --size-*, --font-*. Pure function; `pnpm tokens` writes src/app/tokens.css from it.

type TokenLeaf = { value: string | number };
type TokenGroup = Record<string, TokenLeaf | unknown>;

const HEX_COLOR = /^#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?$/;
// Allowed characters for non-colour values: lengths, numbers, font stacks, calc().
const SAFE_VALUE = /^[A-Za-z0-9 .,'%()+\-*/]+$/;

function leaves(group: unknown, path: string): Array<[string, string]> {
  if (typeof group !== 'object' || group === null) {
    throw new Error(`tokens: ${path} is missing`);
  }
  const out: Array<[string, string]> = [];
  for (const [name, token] of Object.entries(group as TokenGroup)) {
    if (typeof token !== 'object' || token === null || !('value' in token)) continue;
    const value = (token as TokenLeaf).value;
    if (typeof value !== 'string' && typeof value !== 'number') continue;
    out.push([name, String(value)]);
  }
  return out;
}

function colorBlock(tokens: Record<string, unknown>, theme: 'light' | 'dark'): string[] {
  const color = tokens.color as Record<string, unknown> | undefined;
  if (!color || typeof color[theme] !== 'object' || color[theme] === null) {
    throw new Error(`tokens: color.${theme} is missing (both light and dark themes are required)`);
  }
  return leaves(color[theme], `color.${theme}`).map(([name, value]) => {
    if (!HEX_COLOR.test(value)) throw new Error(`tokens: color.${theme}.${name} is not a hex colour`);
    return `  --color-${name}: ${value};`;
  });
}

function scalarBlock(
  tokens: Record<string, unknown>,
  path: string[],
  prefix: string,
  skip: readonly string[] = [],
): string[] {
  let node: unknown = tokens;
  for (const key of path) node = (node as Record<string, unknown> | undefined)?.[key];
  return leaves(node, path.join('.'))
    .filter(([name]) => !skip.includes(name))
    .map(([name, value]) => {
      if (!SAFE_VALUE.test(value)) throw new Error(`tokens: ${path.join('.')}.${name} has unsafe characters`);
      return `  --${prefix}-${name}: ${value};`;
    });
}

export function tokensToCss(input: unknown): string {
  if (typeof input !== 'object' || input === null) throw new Error('tokens: not an object');
  const tokens = input as Record<string, unknown>;
  // Validate both themes before producing anything.
  const light = colorBlock(tokens, 'light');
  const dark = colorBlock(tokens, 'dark');

  const typography = tokens.typography as Record<string, unknown> | undefined;
  const fonts = [
    `  --font-family: ${String((typography?.['font-family'] as TokenLeaf | undefined)?.value ?? 'system-ui, sans-serif')};`,
    `  --font-family-mono: ${String((typography?.['font-family-mono'] as TokenLeaf | undefined)?.value ?? 'monospace')};`,
  ];

  const root = [
    ...light,
    ...fonts,
    ...scalarBlock(tokens, ['typography', 'size'], 'font-size'),
    ...scalarBlock(tokens, ['typography', 'line-height'], 'line-height'),
    ...scalarBlock(tokens, ['typography', 'weight'], 'font-weight'),
    ...scalarBlock(tokens, ['space'], 'space'),
    ...scalarBlock(tokens, ['size'], 'size'),
    ...scalarBlock(tokens, ['border'], 'border'),
    // focus.style and focus.scroll-padding are recipes, applied in globals.css.
    ...scalarBlock(tokens, ['focus'], 'focus', ['style', 'scroll-padding']),
    ...scalarBlock(tokens, ['motion'], 'motion'),
    ...scalarBlock(tokens, ['layer'], 'layer'),
  ];

  return [
    '/* GENERATED from docs/design/tokens.json by `pnpm tokens`. Do not edit by hand. */',
    ':root {',
    '  color-scheme: light dark;',
    ...root,
    '}',
    '',
    '@media (prefers-color-scheme: dark) {',
    '  :root {',
    ...dark.map((line) => `  ${line}`),
    '  }',
    '}',
    '',
  ].join('\n');
}
