# Sprint 5 ST-085 (story "Offline and focus behaviour is tested", P2). FR-124.R3/.R4 and
# NFR-034.1-.3 as BA-5 broke them down (docs/sprints/05/requirements-breakdown.md §1 NFR-034 (a),
# §2 FR-124 offline part; flows-sprint-04 §2 P-01 Offline, §4 and §9 P-03 "focus trapped, returned").
# Bound in web/tests/features/st085-offline-and-focus.test.tsx: the real public/sw.js answers the
# real plan and follow-through clients that the real plan page uses; only the network and Cache
# Storage are fakes. Tests behaviour that already exists, so the red step was a planted defect
# (assumption A9, accepted by the senior-qa-engineer in PR #197 review 5759915501).
@M5 @story-ST-085 @coaching @web
Feature: The plan page offline, and focus after the "Not for me" dialog
  The plan can be read without a connection and says when it was kept; a session marked done
  offline reaches the API once; and the keyboard user is put back where they were after the
  "Not for me" dialog closes.

  Rule: FR-124.R3 While the device is offline and a plan is cached, the plan page shows the cached plan with the line "This is your plan as of <time>"

    Scenario: A plan kept at 18:05 is shown offline with its "as of" line
      Given the player read their plan online at 18:05
      When the player opens the plan page offline
      Then the page says "You are offline. This is your plan as of" the time 18:05
      And the kept sessions are shown

    Scenario: No plan kept on this device, offline
      Given the player has never opened their plan online on this device
      When the player opens the plan page offline
      Then the page says "You are offline and this plan is not saved on this device yet."
      And no sessions are shown

  Rule: FR-124.R4 A session marked done while offline is sent to the API exactly once after the connection returns

    Scenario: One session marked done offline is sent once when the connection returns
      Given the player opened their plan online
      And the connection drops
      When the player marks "Session 1" done
      And the connection returns
      Then the API got one "done" request for "Session 1"
      And "Session 1" stays done

    Scenario: The connection drops and returns twice before the queue drains
      Given the player opened their plan online
      And the connection drops
      And the player marks "Session 1" done
      When the connection returns, drops and returns again before the first send is answered
      Then the API got one "done" request for "Session 1"
      And "Session 1" stays done

  Rule: NFR-034.1-.3 Focus returns to the row's "Not for me" on every close path of the dialog

    Scenario: Close, after "no other drill fits" (NFR-034.1)
      Given the "Not for me" dialog for "Serve to a target" is open
      And no other drill fits
      When the player presses "Close"
      Then the dialog is gone and the focus is on "Not for me" for "Serve to a target"

    Scenario: Cancel (NFR-034.2)
      Given the "Not for me" dialog for "Serve to a target" is open
      When the player presses "Cancel"
      Then the dialog is gone and the focus is on "Not for me" for "Serve to a target"

    Scenario: Esc (NFR-034.3)
      Given the "Not for me" dialog for "Serve to a target" is open
      When the player presses Esc
      Then the dialog is gone and the focus is on "Not for me" for "Serve to a target"
      And the focus is not left on the page body
