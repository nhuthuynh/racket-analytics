// Route isolation check (CI-WEBKIT-PD-R3S2-02; tests/features/e2e_route_isolation.feature).
// A spec that fakes a response with page.route / context.route / routeFromHAR must also say
// test.use({ serviceWorkers: 'block' }). public/sw.js has a fetch handler and claims open pages,
// so in WebKit a controlled page's fetches go through the worker and Playwright's route never
// sees them, while Chromium still routes them: the spec passes in one browser and fails in the
// other (fe-minors.spec.ts:24 on PR #4). Read by web/tests/unit/e2e-route-isolation*.test.ts,
// which run in the web-checks CI job, so a new spec cannot reach the E2E job without it.
// Scope: *.spec.ts files only; a helper that routes says in its doc comment what its callers
// need (helpers/sprint-02.ts playableVideo). The rule is per file (judgment: no spec mixes both).
import { readdirSync, readFileSync } from 'node:fs';
import path from 'node:path';
import ts from 'typescript';

export interface UnisolatedRoute {
  /** Spec path relative to the scanned directory, with "/" separators. */
  file: string;
  /** 1-based line of the route call. */
  line: number;
}

const ROUTE_METHODS = new Set(['route', 'routeFromHAR']);

/** True for `serviceWorkers: 'block'` (or "block") as an object property. */
function blocksServiceWorkers(node: ts.Node): boolean {
  return (
    ts.isPropertyAssignment(node) &&
    (ts.isIdentifier(node.name) || ts.isStringLiteral(node.name)) &&
    node.name.text === 'serviceWorkers' &&
    ts.isStringLiteralLike(node.initializer) &&
    node.initializer.text === 'block'
  );
}

/**
 * Lines of the route calls in a spec that does not block service workers; [] when it is fine.
 * Parsed with the TypeScript compiler, so comments are skipped and strings, template literals
 * and regex literals stay code. A glob such as the uploads glob holds the two block-comment
 * markers, which a comment-stripping regex took for a comment (review round 1, PE-R1-01 / F1).
 */
export function unisolatedRoutes(source: string): number[] {
  const file = ts.createSourceFile('spec.ts', source, ts.ScriptTarget.Latest, false, ts.ScriptKind.TS);
  const routeLines: number[] = [];
  let blocked = false;
  const visit = (node: ts.Node): void => {
    if (blocksServiceWorkers(node)) blocked = true;
    if (
      ts.isCallExpression(node) &&
      ts.isPropertyAccessExpression(node.expression) &&
      ROUTE_METHODS.has(node.expression.name.text)
    ) {
      routeLines.push(file.getLineAndCharacterOfPosition(node.expression.name.getStart(file)).line + 1);
    }
    ts.forEachChild(node, visit);
  };
  visit(file);
  return blocked ? [] : [...new Set(routeLines)].sort((a, b) => a - b);
}

/** Every route call under `dir` (recursively, *.spec.ts only) whose spec allows service workers. */
export function checkSpecs(dir: string): UnisolatedRoute[] {
  return readdirSync(dir, { recursive: true, encoding: 'utf8' })
    .filter((name) => name.endsWith('.spec.ts'))
    .sort()
    .flatMap((name) =>
      unisolatedRoutes(readFileSync(path.join(dir, name), 'utf8')).map((line) => ({
        file: name.split(path.sep).join('/'),
        line,
      })),
    );
}
