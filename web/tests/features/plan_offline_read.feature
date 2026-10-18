# Sprint 4 ST-063c-part2-part2 (FR-124; flows-sprint-04 §2 P-01 Offline). AC: "caches the plan
# page shell and the last plan JSON". Bound in web/tests/features/plan-offline-read.test.ts: the
# real public/sw.js answers the real plan read (createPlanApi) over a fake network and Cache Storage.
# The offline line on the page itself is ST-063c-part2-part2-part2's feature (PR #142).
@M5 @story-ST-063c @coaching @web
Feature: The last plan can be read offline
  The plan page and the last plan read are kept on the device, so the player can read their plan
  without a connection, and the read says when that copy was kept. Nothing else is kept.

  Rule: Offline, only a plan that was kept is shown (never a made-up one)

    Scenario: Offline with no plan kept, the plan cannot be read
      Given the player has never opened their plan online
      When the player reads their plan offline
      Then the plan read fails
      And no plan is kept on the device

    Scenario: The last plan is read offline, saying when it was kept
      Given the player read their plan online at "2026-10-18T09:30:00Z"
      When the player reads their plan offline
      Then the plan read is the kept plan
      And it was kept at "18 Oct 2026, 09:30"

  Rule: Keeping the plan never breaks reading it online (review PE-1)

    Scenario: A full device storage still shows the live plan
      Given the device storage is full
      When the player reads their plan online
      Then the plan read is the live plan

  Rule: Sign-out leaves no plan on the device (NFR-067)

    Scenario: After sign-out the plan cannot be read offline
      Given the player read their plan online at "2026-10-18T09:30:00Z"
      And the player signs out
      When the player reads their plan offline
      Then the plan read fails
