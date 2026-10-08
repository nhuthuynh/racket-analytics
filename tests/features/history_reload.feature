# C3-10 / PD-R3S2-02 (Sprint 2 review round 3 minor, carried to Sprint 3). Owner: senior-frontend-engineer.
# Added when the ticket was ported to its own PR (PO decision P13): the fix commit carried the
# unit and E2E tests only. Seen red against main's S-01 before the port's implementation commit.
# Browser binding: web/e2e/sprint-03/fe-minors.spec.ts ("PD-R3S2-02 ...", live stack; the
# corrections request is answered 503 or held by page.route, service workers blocked).
# Unit binding: web/tests/unit/pd-r3s2-02-history-reload.test.tsx.
@story-C3-10 @nfr-027
Feature: Reloading the correction history gives feedback
  H-01 "Reload the history" that failed again left the same text on screen, so the press looked
  ignored. The reload now says it is working, and a reload that fails again says so.

  Rule: H-01 says when a history reload failed again and shows that it is reloading

    Scenario: The history reload fails again
      Given Ivy's score sheet could not load the correction history
      When she presses "Reload the history" and the history still cannot be loaded
      Then an alert says "The history still could not be loaded (tried 2 times). Check your connection, then reload it again."

    Scenario: The history is reloading
      Given Ivy's score sheet could not load the correction history
      When she presses "Reload the history" and the history has not arrived yet
      Then the button says "Reloading the history…" and is marked busy

    Scenario: The history reload works
      Given Ivy has seen that the history reload failed again
      When she presses "Reload the history" and the history loads
      Then the correction history is shown with no alert and no reload button
