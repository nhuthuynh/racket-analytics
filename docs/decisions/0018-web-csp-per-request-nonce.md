# 0018. Web CSP: per-request nonce in middleware, no inline-script allowance

- **Status:** Proposed
- **Date:** 2026-10-03
- **Deciders:** senior-frontend-engineer
- **Consulted:** security-privacy-engineer (review at the ST-010 PR), principal-engineer
- **Related:** ST-010, NFR-061, NFR-067, IT-00-14 (HTML part, `web/e2e/security-headers.spec.ts`), [AQS/STACK-04], ADR 0008

## Context and problem statement
ST-010 requires a Content-Security-Policy on HTML responses. IT-00-14 checks for `default-src 'self'` and `frame-ancestors 'none'`. The Next.js App Router puts inline `<script>` blocks into every page (the RSC flight data), so `script-src 'self'` on its own breaks the app. We have to choose how those inline scripts are allowed.

## Decision drivers
- XSS defence in depth for a page that renders user text (match titles) [AQS/STACK-04]; the API contract says titles are rendered as text only (api-sprint-00 §8).
- No `unsafe-inline` and no `unsafe-eval` for scripts in production (judgment: these two keywords remove most of the protection a CSP gives).
- The `/api` rewrite must keep working for tus uploads (see ADR 0019).
- The first-route JavaScript budget is ≤ 200 KB gzipped (NFR-015).

## Considered options
1. **Per-request nonce set in `src/middleware.ts`** (`script-src 'self' 'nonce-…' 'strict-dynamic'`). Next.js reads the nonce from the request CSP header and adds it to its own scripts.
2. **Static CSP in `next.config` headers with `script-src 'self' 'unsafe-inline'`.**
3. **Hash-based CSP.** This cannot work: the inline flight-data scripts differ on every response.

## Decision outcome
Chosen option: **1, a per-request nonce**. It is the only option that keeps inline scripts blocked unless the server issued them. The cost is that every page renders dynamically. Every page reads the session cookie anyway, so this costs nothing extra in practice.

## Pros and cons of the options
### Option 1: nonce
- Good: an injected `<script>` without the nonce does not run. `object-src 'none'`, `base-uri 'self'`, `form-action 'self'` and `frame-ancestors 'none'` are included.
- Bad: no static HTML caching of pages, and the middleware runs on every page request. The root `not-found` page had to become dynamic (`await headers()`), because a static page carries no nonce.
### Option 2: `unsafe-inline`
- Good: simple, and static pages stay possible.
- Bad: reflected or stored script injection would run.
### Option 3: hashes
- Bad: not feasible with streamed RSC payloads.

## Consequences
- Good: production pages ship `script-src 'self' 'nonce-…' 'strict-dynamic'` and `style-src 'self' 'nonce-…'`, with no inline allowance. Dev mode adds only `'unsafe-eval'` and `'unsafe-inline'` for styles, which the Next dev server needs.
- Trade-off accepted: inline `style="…"` attributes in server HTML would be blocked. Components set dynamic styles only on the client (the progress-bar width is a CSSOM update, which CSP allows).
- The middleware matcher skips `/api/`, `/_next/static`, `/sw.js`, icons and the manifest.
- Follow-up: the security-privacy-engineer reviews the directive list at the ST-010 PR. Add `upgrade-insecure-requests` once dev and CI no longer serve plain `http://localhost` (judgment).

## Evidence
| Claim | Evidence | Type |
|---|---|---|
| The CSP is on `/`, `/matches` and the 404 page, with `default-src 'self'` and `frame-ancestors 'none'` | `BASE_URL=http://localhost:3000 PW_PROJECTS=chromium pnpm exec playwright test` → `security-headers.spec.ts` 3/3 route tests passed (real API, 2026-10-03) | test result |
| Production `script-src` has no `unsafe-inline` or `unsafe-eval` | `tests/unit/csp.test.ts` (4 tests) passed; `curl -sI http://localhost:3000/` → `script-src 'self' 'nonce-…' 'strict-dynamic'; style-src 'self' 'nonce-…'` | test result |
| The app hydrates with no CSP violation | A Playwright probe listened for `securitypolicyviolation` across sign-in, matches, new match, error summary, 404 and back. The only console error was the expected 404 resource load | test result |
| The root not-found page was static, so it had no nonce | `next build` route table: `○ /_not-found` before the change, `ƒ /_not-found` after | test result |
| First route stays in budget | `check_first_route_js.py --route /page --budget-kb 200` → 103.1 KB, exit 0 | test result |
| Inline-script allowances weaken CSP | (judgment) | judgment |

## Confirmation
`web/e2e/security-headers.spec.ts` (CI e2e job), `tests/unit/csp.test.ts` (web-checks job).

## Notes
