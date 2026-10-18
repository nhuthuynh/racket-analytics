# Sprint 4 ST-063c (FR-124; flows-sprint-04 §4 P-03; HAX G8, G15): the UI half of
# tests/features/plan_follow_through.feature (ST-062, API). "Mark done" works offline through an
# IndexedDB outbox that syncs on "online" and on page load; "Not for me" swaps a drill. Bound by
# Vitest + Testing Library in web/tests/features/plan-follow-through-ui.test.tsx (fake-indexeddb;
# the contract test web/tests/contract/plan-follow-through.test.ts covers the wire).
@M5 @story-ST-063c @coaching @web
Feature: Following the plan through, on the plan page
  A player marks sessions done even when the phone is offline, and swaps a drill that is not
  for them for another that works on the same thing.

  Background:
    Given a plan whose first session is "Session 1 of 3" with the drill "Serve to a target"

  Rule: "Mark done" is never lost (FR-124)

    Scenario: Mark done offline, and the sync fails
      Given the phone is offline
      When the player marks "Session 1 of 3" done
      And the phone is back online but the server cannot be reached
      Then the session says "We could not save 'done'. It stays on this device and will sync."
      And the op is still on this device

    Scenario: Mark done offline twice
      Given the phone is offline
      When the player marks "Session 1 of 3" done twice
      Then the session says "Saved on this device, will sync"
      And one op is on this device
      When the phone is back online
      Then the server got one "done" with that op id
      And the page says "Session 1 synced."
      And no op is left on this device

  Rule: "Not for me" swaps for a drill that works on the same thing (FR-124)

    Scenario: No other drill fits
      Given no other drill fits "Serve to a target"
      When the player says "Not for me" to "Serve to a target" with the reason "too hard"
      Then the dialog says "No other drill fits your setup for this. Your plan is unchanged."
      And the plan still has "Serve to a target"

    Scenario: Swap a drill
      When the player says "Not for me" to "Serve to a target"
      Then "Deep serves" replaces it and has the focus
      And the page says "Swapped for Deep serves."
