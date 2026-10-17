# CI-SIGNIN-HYDRATION (split out of QA-HARNESS-4b, review round 3; PR #105 webkit E2E run
# 39055141846). Owner: senior-frontend-engineer. Flows A-01 and A-04.
# Bindings: browser level web/e2e/sprint-01/sign-in-hydration.spec.ts (Playwright against
# `next start`, the page's JavaScript held so the pre-hydration window is deterministic);
# component level web/tests/unit/sign-in-form-hydration.test.tsx (server HTML vs mounted form).
@M0 @story-ST-013 @ticket-CI-SIGNIN-HYDRATION @nfr-074
Feature: The sign-in form only takes a request it can send

  Rule: Until the page is ready, the sign-in form takes no address and sends nothing

    Scenario: A tap before the page is ready sends nothing and keeps the address private
      Given Ivy opens the sign-in page and it is not ready yet
      When she taps "Send me a link"
      Then "Email address" and "Send me a link" are unavailable
      And the address bar never contains an email address

    Scenario: The "Send a new link" form waits the same way
      Given Ivy opens an expired sign-in link and the page is not ready yet
      Then "Email address" and "Send a new link" are unavailable

    Scenario: Once the page is ready, the same form sends the link
      Given Ivy opened the sign-in page before it was ready
      When the page becomes ready and she requests a link for her address
      Then she sees "Check your email"
      And exactly one link request with her address was sent
      And the address bar never contains an email address
