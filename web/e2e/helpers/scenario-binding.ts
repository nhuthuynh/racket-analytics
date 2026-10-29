// Gherkin-to-browser binding (ST-065): a scenario of an E2E feature file is bound when it carries
// an `@E2E-nn-nn` tag and a Playwright test (not skipped, not fixme) has a title that starts with
// that id and contains the scenario's name. Read from source text, so it needs no browser.
import { readdirSync, readFileSync } from 'node:fs';
import path from 'node:path';

export interface Scenario {
  name: string;
  ids: string[];
}
export interface SpecSource {
  file: string;
  text: string;
}
export interface Unbound {
  scenario: string;
  reason: string;
}

const E2E_TAG = /@(E2E-\d\d-\d\d)\b/g;

export function scenariosOf(feature: string): Scenario[] {
  const out: Scenario[] = [];
  let tags: string[] = [];
  for (const raw of feature.split('\n')) {
    const line = raw.trim();
    if (line.startsWith('@')) tags.push(...[...line.matchAll(E2E_TAG)].map((m) => m[1] ?? ''));
    else if (/^Scenario( Outline)?:/.test(line)) {
      out.push({ name: line.replace(/^Scenario( Outline)?:\s*/, ''), ids: tags });
      tags = [];
    } else if (line !== '' && !line.startsWith('#')) tags = [];
  }
  return out;
}

/** Titles of the non-skipped `test(...)` calls whose title starts with an E2E id. */
function boundTitles(specs: SpecSource[]): string[] {
  const call = /(?<![.\w])test\(\s*(['"`])(E2E-\d\d-\d\d)(?![\d-])([^'"`]*)\1/g;
  return specs.flatMap((s) => [...s.text.matchAll(call)].map((m) => `${m[2]}${m[3]}`));
}

export function unboundScenarios(feature: string, specs: SpecSource[]): Unbound[] {
  const titles = boundTitles(specs);
  return scenariosOf(feature).flatMap((s): Unbound[] => {
    if (s.ids.length === 0) return [{ scenario: s.name, reason: 'no @E2E-nn-nn tag' }];
    return s.ids
      .filter((id) => !titles.some((t) => t.startsWith(`${id} `) && t.includes(s.name)))
      .map((id) => ({ scenario: s.name, reason: `no test titled "${id} ... ${s.name}"` }));
  });
}

/** Every *.spec.ts under `dir`, with paths relative to it. */
export function readSpecs(dir: string): SpecSource[] {
  return readdirSync(dir, { recursive: true, encoding: 'utf8' })
    .filter((f) => f.endsWith('.spec.ts'))
    .sort()
    .map((f) => ({ file: f.split(path.sep).join('/'), text: readFileSync(path.join(dir, f), 'utf8') }));
}
