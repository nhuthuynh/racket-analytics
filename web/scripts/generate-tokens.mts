// Writes src/app/tokens.css from docs/design/tokens.json (`pnpm tokens`).
// Node >= 22.18 runs this TypeScript file directly (type stripping).
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { tokensToCss } from '../src/lib/tokens/css.ts';

const at = (p: string) => fileURLToPath(new URL(p, import.meta.url));
const tokens = JSON.parse(readFileSync(at('../../docs/design/tokens.json'), 'utf8'));
writeFileSync(at('../src/app/tokens.css'), tokensToCss(tokens));
console.log('wrote src/app/tokens.css');
