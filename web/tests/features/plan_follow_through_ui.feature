# Sprint 4 ST-063c (FR-124; flows-sprint-04 §4 P-03; HAX G8, G15): the UI half of
# tests/features/plan_follow_through.feature (ST-062, API). "Mark done" works offline through an
# IndexedDB outbox that syncs on "online" and on page load ("Not for me": plan_not_for_me_ui.feature). Bound by
# Vitest + Testing Library in web/tests/features/plan-follow-through-ui.test.tsx (fake-indexeddb;
# the contract test web/tests/contract/plan-follow-through.test.ts covers the wire).
@M5 @story-ST-063c @coaching @web
Feature: Following the plan through, on the plan page
  A player marks sessions done even when the phone is offline.

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

    Scenario: Mark done when the browser blocks IndexedDB
      Given this browser blocks IndexedDB
      When the player marks "Session 1 of 3" done
      Then the server got one "done"
      And the session says "Done"

    Scenario: Undo of a done session fails
      Given "Session 1 of 3" is done
      When the player presses "Undo" and the server cannot undo it
      Then the session says "We could not undo 'done'. Try again."
      And the session still says "Done"
