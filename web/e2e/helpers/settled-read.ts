// Settled-read check (CI-E2E-MAIN-RED; tests/features/e2e_settled_read.feature).
// After a navigation (goto, reload, goBack, goForward) a spec must wait for what it expects, with
// an awaited web-first assertion or an explicit waitFor*, before it reads page text
// (innerText, textContent, allInnerTexts, allTextContents, innerHTML). Why: the match page
// streams (/matches/loading.tsx), so "Page not found" replaces the "Loading…" fallback only after
// React runs in the browser, and page.goto resolves on the load event, which can come first.
// object-level-authorisation.spec.ts:26 read "Loading…" in WebKit on main run 37905693381.
// Read by web/tests/unit/e2e-settled-read*.test.ts in the web-checks CI job.
// Scope (judgment): *.spec.ts files only, and statements of one function body in source order;
// a navigation inside a helper call (signInAs, createMatch) is the helper's to settle.
import { readdirSync, readFileSync } from 'node:fs';
import path from 'node:path';
import ts from 'typescript';

export interface UnsettledRead {
  /** Spec path relative to the scanned directory, with "/" separators. */
  file: string;
  /** 1-based line of the text read. */
  line: number;
}

const NAVIGATIONS = new Set(['goto', 'reload', 'goBack', 'goForward']);
const TEXT_READS = new Set(['innerText', 'textContent', 'allInnerTexts', 'allTextContents', 'innerHTML']);
// waitForLoadState and waitForTimeout are left out on purpose: neither waits for the content.
const WAITS = new Set(['waitFor', 'waitForURL', 'waitForResponse', 'waitForSelector', 'waitForFunction']);

type Step = { kind: 'navigate' } | { kind: 'wait' } | { kind: 'read'; line: number };

function calledName(call: ts.CallExpression): string | undefined {
  return ts.isPropertyAccessExpression(call.expression) ? call.expression.name.text : undefined;
}

/** True when the chain (expect(x).not.toHaveText(...)) starts with a call to expect. */
function isExpectChain(node: ts.Expression): boolean {
  let current: ts.Expression = node;
  while (ts.isCallExpression(current) || ts.isPropertyAccessExpression(current)) {
    if (ts.isCallExpression(current) && ts.isIdentifier(current.expression)) {
      return current.expression.text === 'expect';
    }
    current = current.expression;
  }
  return false;
}

/** True for an object literal argument with a `name` or `hasText` property ({ name: 'Page not found' }). */
function namesText(arg: ts.Expression): boolean {
  return (
    ts.isObjectLiteralExpression(arg) &&
    arg.properties.some(
      (p) => p.name !== undefined && ts.isIdentifier(p.name) && (p.name.text === 'name' || p.name.text === 'hasText'),
    )
  );
}

/**
 * True when the locator a read is called on names the text it expects (getByText, getByLabel,
 * or a { name } / { hasText } option anywhere in the chain): the read then waits for that text
 * to exist. getByRole('main') does not, since the Loading fallback already has a main region.
 */
function locatorNamesText(receiver: ts.Expression): boolean {
  let current: ts.Expression = receiver;
  while (ts.isCallExpression(current) || ts.isPropertyAccessExpression(current) || ts.isParenthesizedExpression(current)) {
    if (ts.isCallExpression(current)) {
      const name = calledName(current);
      if (name === 'getByText' || name === 'getByLabel' || current.arguments.some(namesText)) return true;
    }
    current = current.expression;
  }
  return false;
}

/**
 * The navigations, waits and reads of one statement, in evaluation order. Nested functions are
 * skipped: they are scanned as bodies of their own. A web-first assertion is an awaited expect
 * chain (`await expect(locator).toHaveText(...)`); a plain `expect(value)` does not wait.
 */
function stepsOf(statement: ts.Node, file: ts.SourceFile): Step[] {
  const steps: Step[] = [];
  const visit = (node: ts.Node): void => {
    if (ts.isFunctionLike(node)) return;
    ts.forEachChild(node, visit);
    if (ts.isAwaitExpression(node) && isExpectChain(node.expression)) {
      steps.push({ kind: 'wait' });
      return;
    }
    if (!ts.isCallExpression(node)) return;
    const name = calledName(node);
    if (name === undefined) return;
    if (NAVIGATIONS.has(name)) steps.push({ kind: 'navigate' });
    else if (WAITS.has(name)) steps.push({ kind: 'wait' });
    else if (TEXT_READS.has(name)) {
      const access = node.expression as ts.PropertyAccessExpression;
      if (locatorNamesText(access.expression)) {
        steps.push({ kind: 'wait' });
        return;
      }
      const at = access.name.getStart(file);
      steps.push({ kind: 'read', line: file.getLineAndCharacterOfPosition(at).line + 1 });
    }
  };
  visit(statement);
  return steps;
}

/** Lines of the text reads that follow a navigation with no wait in between; [] when fine. */
export function unsettledReads(source: string): number[] {
  const file = ts.createSourceFile('spec.ts', source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
  const lines = new Set<number>();
  const scanBody = (statements: readonly ts.Node[]): void => {
    let navigated = false;
    for (const step of statements.flatMap((s) => stepsOf(s, file))) {
      if (step.kind === 'navigate') navigated = true;
      else if (step.kind === 'wait') navigated = false;
      else if (navigated) lines.add(step.line);
    }
  };
  const visit = (node: ts.Node): void => {
    if (ts.isSourceFile(node)) scanBody(node.statements);
    else if (ts.isFunctionLike(node)) {
      const body = (node as ts.FunctionLikeDeclarationBase).body;
      if (body && ts.isBlock(body)) scanBody(body.statements);
      else if (body) scanBody([body]);
    }
    ts.forEachChild(node, visit);
  };
  visit(file);
  return [...lines].sort((a, b) => a - b);
}

/** Every unsettled read under `dir` (recursively, *.spec.ts only). */
export function checkSpecs(dir: string): UnsettledRead[] {
  return readdirSync(dir, { recursive: true, encoding: 'utf8' })
    .filter((name) => name.endsWith('.spec.ts'))
    .sort()
    .flatMap((name) =>
      unsettledReads(readFileSync(path.join(dir, name), 'utf8')).map((line) => ({
        file: name.split(path.sep).join('/'),
        line,
      })),
    );
}
