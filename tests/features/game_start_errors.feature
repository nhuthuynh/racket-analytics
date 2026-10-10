# C3-10 / PD-R3S2-01 (Sprint 2 review round 3 minor, carried to Sprint 3). Owner: senior-frontend-engineer.
# Added when the ticket was ported to its own PR (PO decision P13): the fix commit carried the
# unit and E2E tests only. Seen red against main's T-02 before the port's implementation commit.
# Browser binding: web/e2e/sprint-03/fe-minors.spec.ts ("PD-R3S2-01 ...", live stack).
# Unit binding: web/tests/unit/pd-r3s2-01-t02-error-summary.test.tsx (server failure, focus repeat).
@story-C3-10 @nfr-027
Feature: Starting a game explains what is missing
  T-02 "Who serves first in game n?" reports its errors the way every other form does: the shared
  error summary [DPA/DESIGN-13], with a link to the question and the message next to it.

  Rule: T-02 errors use the shared error summary with a link to the question

    Scenario: Ivy starts a game without choosing who serves first
      Given Ivy is tagging her match and game 1 has not started
      When she presses "Start game 1" without choosing who serves first
      Then the error summary "There is a problem" has focus
      And the question "Who serves first in game 1?" shows "Choose who serves first in game 1."
      And the summary's link "Choose who serves first in game 1." moves focus to the question's first answer

    Scenario: Ivy answers the question after the error
      Given Ivy has seen the error summary for game 1
      When she chooses her side and presses "Start game 1"
      Then she can tag the first rally

    Scenario: The server cannot start the game
      Given Ivy has chosen who serves first in game 1
      When the server cannot start the game
      Then the error summary "There is a problem" has focus and gives the reason with its reference
      And the summary has no link to a question
