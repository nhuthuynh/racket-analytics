# CI-E2E-MAIN-RED (main run 37905693381, job 113748522312, merge of PR #43 at bfe6f33).
# Owner: senior-frontend-engineer. Written before implementation.
# Binding: web/tests/unit/e2e-settled-read-scenarios.test.ts (Vitest, real files on disk).
# Cause: /matches/loading.tsx makes the match page stream. The server sends the "Loading…"
# fallback first; a match the player may not see (or that does not exist) ends in notFound()
# after the shell is sent, so "Page not found" replaces the fallback only once React has run in
# the browser. page.goto resolves on the load event, which can come before that, so a spec that
# reads the page text straight after goto reads "Loading…" when the browser is slow (WebKit on
# CI: object-level-authorisation.spec.ts:26, Received "Loading…").
@ticket-CI-E2E-MAIN-RED @story-ST-006 @nfr-074
Feature: An E2E spec reads a page only after the page has settled
  Rule: After a navigation, a spec waits for what it expects before it reads the page's text

    Scenario: A spec that reads the page text straight after a navigation is refused
      Given an E2E spec that opens another player's match with page.goto
      And the spec reads the text of the main region on the next line
      When the settled-read check reads the E2E specs
      Then the check names the spec and the line of the read

    Scenario: A spec that waits for the not-found heading before it reads passes
      Given an E2E spec that opens another player's match with page.goto
      And the spec waits for the heading "Page not found" with a web-first assertion
      And the spec then reads the text of the main region
      When the settled-read check reads the E2E specs
      Then the check names no spec

    Scenario: A plain assertion on a value read earlier is not a wait
      Given an E2E spec that reads the text of the main region straight after page.goto
      And an assertion on that text follows the read
      When the settled-read check reads the E2E specs
      Then the check still names the line of the read

    Scenario: Every E2E spec in the repository reads a page only after it has settled
      When the settled-read check reads the repository's E2E specs
      Then the check names no spec
