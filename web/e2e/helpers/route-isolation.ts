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

export interface UnisolatedRoute {
  /** Spec path relative to the scanned directory, with "/" separators. */
  file: string;
  /** 1-based line of the route call. */
  line: number;
}

const ROUTE_CALL = /\.route(?:FromHAR)?\s*\(/;
const BLOCKS_SERVICE_WORKERS = /serviceWorkers\s*:\s*(['"])block\1/;

/** Blanks out comments, keeping line breaks so line numbers stay as in the file. */
function withoutComments(source: string): string {
  return source
    .replace(/\/\*[\s\S]*?\*\//g, (block) => block.replace(/[^\n]/g, ' '))
    .replace(/(^|\s)\/\/.*$/gm, '$1');
}

/** Lines of the route calls in a spec that does not block service workers; [] when it is fine. */
export function unisolatedRoutes(source: string): number[] {
  const code = withoutComments(source);
  if (BLOCKS_SERVICE_WORKERS.test(code)) return [];
  return code.split('\n').flatMap((text, i) => (ROUTE_CALL.test(text) ? [i + 1] : []));
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
