# CI-WEBKIT-PD-R3S2-02 (blockers.md 2026-10-08; PR #4 runs 37643676432, 37715576115,
# 37718386760, 37719909230). Owner: senior-frontend-engineer. Written before implementation.
# Binding: web/tests/unit/e2e-route-isolation-scenarios.test.ts (Vitest, real files on disk).
# Cause: public/sw.js has a fetch handler and claims open pages, so in WebKit the page's fetches
# go through the service worker and Playwright's page.route never sees them (Chromium does).
@ticket-CI-WEBKIT-PD-R3S2-02 @nfr-024 @nfr-074
Feature: An E2E spec that fakes a response sees it in every browser
  Rule: A spec that routes a request blocks service workers, so the route applies in WebKit too

    Scenario: A spec that routes a request without blocking service workers is refused
      Given an E2E spec that fakes "/api/matches/{id}/corrections" with page.route
      And the spec does not block service workers
      When the route isolation check reads the E2E specs
      Then the check names the spec and the line of the route

    Scenario: A spec that routes a request and blocks service workers passes
      Given an E2E spec that fakes "/api/matches/{id}/corrections" with page.route
      And the spec blocks service workers
      When the route isolation check reads the E2E specs
      Then the check names no spec

    Scenario: A spec that routes nothing needs no service worker setting
      Given an E2E spec that routes no request
      When the route isolation check reads the E2E specs
      Then the check names no spec

    Scenario: Every E2E spec in the repository routes only with service workers blocked
      When the route isolation check reads the repository's E2E specs
      Then the check names no spec

    # Review round 1 (PE-R1-01, F1): globs such as '**/api/**' hold "/*" and "*/", so a reader
    # that strips comments without knowing strings hid route calls and the block between globs.
    Scenario: Globs that look like comment markers do not hide a route or a block
      Given an E2E spec whose glob strings contain "/*" and "*/" around its route calls
      And the spec does not block service workers
      When the route isolation check reads the E2E specs
      Then the check names the line of every route
      And a spec that blocks service workers between two such globs is not named
