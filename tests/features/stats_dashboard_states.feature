# ST-048 (D-01 stats dashboard, E-01 "Show me"; flows-sprint-03 §2, §3; FR-100, FR-102, FR-103;
# NFR-027, NFR-028, NFR-033, NFR-039; PD-R1S3-03). Owner: senior-frontend-engineer. Added in review
# round 2 (PE-R2-ST048-02, QA-048-R2-02): one scenario per acceptance criterion of the ticket's
# states and of "Show me" opening S-01 at the rally.
# Browser binding: web/e2e/sprint-03/states.spec.ts (E2E-03-09; what is shown while a request is
# held or failed only exists in a browser, so there is no API binding, like
# not_found_touch_target.feature). The API answers behind these screens are bound in
# metric_evidence.feature and starter_stats.feature.
# Unit bindings: web/tests/unit/st-048-stats-dashboard.test.tsx ("D-01 states", "E-01 panel"),
# web/tests/unit/g03-goal-round-1-fe.test.tsx (loading), web/tests/unit/st-047-st-048-pages.test.tsx
# ("S-01 opened from Show me").
@M0 @story-ST-048 @story-ST-047 @nfr-027 @nfr-028
Feature: The stats dashboard and its evidence say what state they are in
  Ivy opens the stats of a match she tagged. Whatever the API does, the page tells her in words what
  is happening, never prints a number it does not have, and every number leads to the rallies behind
  it on the score sheet.

  Background:
    Given Ivy is signed in and her doubles match "Saturday doubles" has its video received

  Rule: A failed request is an alert with a way to try again, and no numbers

    Scenario: The dashboard numbers cannot be loaded
      Given she has tagged the coach's worked example
      And the stats request fails
      When she opens the stats of the match on a phone 360 CSS px wide
      Then she sees an alert saying the stats could not be loaded, with "Try again"
      And the alert shows no raw error
      And no "Show me" button and no number are shown
      And the page does not scroll sideways
      And axe finds no serious or critical violation and no target is below 24 by 24 CSS px
      When the stats request works again and she chooses "Try again"
      Then she sees the metric cards and no alert

    Scenario: The rallies behind a number cannot be loaded
      Given she has tagged the coach's worked example and opened its stats
      And the evidence request fails
      When she chooses "Show me" on the first metric
      Then she sees an alert saying the rallies could not be loaded, with "Try again"
      And no rally link is shown
      And axe finds no serious or critical violation and no target is below 24 by 24 CSS px
      When the evidence request works again and she chooses "Try again"
      Then she sees the rally links

  Rule: No data is said in words, not shown as an error or as zeros

    Scenario: No rally tagged yet
      Given she has tagged no rally
      When she opens the stats of the match on a phone 360 CSS px wide
      Then the page is the stats page, not the not-found page
      And she reads that no rally is tagged yet, with a "Tag rallies" link
      And no "Show me" button and no "n =" are shown
      And the page does not scroll sideways
      And axe finds no serious or critical violation and no target is below 24 by 24 CSS px

    Scenario: No stat is published yet
      Given she has tagged the coach's worked example
      And the API answers the stats request with no metric published
      When she opens the stats of the match on a phone 360 CSS px wide
      Then she reads "Each stat appears once our coach has checked how it is measured."
      And no alert is shown
      And no "Show me" button and no "n =" are shown
      And the page does not scroll sideways
      And axe finds no serious or critical violation and no target is below 24 by 24 CSS px

  Rule: While a request runs, a busy region says so, and then the numbers replace it

    Scenario: The dashboard and the rallies behind a number while they load
      Given she has tagged the coach's worked example
      And the stats request is held
      When she opens the stats of the match
      Then a busy region is shown and the browser has asked for the stats
      And no "Show me" button is shown
      And axe finds no serious or critical violation and no target is below 24 by 24 CSS px
      When the stats request is let through
      Then she sees the metric cards and nothing is busy
      Given the evidence request is held
      When she chooses "Show me" on the first metric
      Then a busy region is shown and the browser has asked for the rallies
      And axe finds no serious or critical violation and no target is below 24 by 24 CSS px
      When the evidence request is let through
      Then she sees the rally links and nothing is busy

  Rule: "Show me" opens the score sheet at the rally, playing that rally

    Scenario: A play link that names no rally of the sheet opens no video
      Given she has tagged the coach's worked example
      When she opens the score sheet with a play id that is no rally of the sheet
      Then she sees the score sheet
      And no rally video is opened

    Scenario: A rally behind a number opens S-01 with its video at its start
      Given she has tagged the coach's worked example and opened its stats
      When she chooses "Show me" on the first metric
      And she chooses the first rally, which reads "Rally <n> · game <g> · <m:ss>"
      Then the score sheet opens with "?play=" and that rally's id
      And the "Rally <n> video" region is shown, saying "Starts at <m:ss>"
      And the video can play
      And axe finds no serious or critical violation and no target is below 24 by 24 CSS px
