# QA-R1S3-01 (finding raised by E2E-03-06, keyboard-and-narrow.spec.ts: "Go to your matches"
# measured 178x21 CSS px at 320 and 360 px). Owner: senior-frontend-engineer. Written before the
# browser binding was seen passing (the fix commit carried the unit test only).
# Browser binding: web/e2e/sprint-03/qa-r1s3-01-not-found-target.spec.ts (layout needs a browser).
# Unit binding: web/tests/unit/qa-r1s3-01-not-found-target.test.tsx (class and CSS rule).
@M0 @story-ST-048 @nfr-028 @nfr-051
Feature: The not-found page is usable by touch on a narrow phone
  A player who opens another player's match, a deleted match or a mistyped address gets the one
  not-found page; its way back is a link big enough to tap.

  Rule: The not-found page's way back has a touch-sized target

    Scenario Outline: The way back from a missing match at <width> px
      Given Ivy is signed in on a phone <width> CSS px wide
      When she opens a match that does not exist
      Then she sees "Page not found"
      And the "Go to your matches" link is at least 24 by 24 CSS px
      And the link is 48 CSS px tall, the size of the touch buttons
      And no visible target on the page is below 24 by 24 CSS px
      Examples:
        | width |
        | 320   |
        | 360   |
