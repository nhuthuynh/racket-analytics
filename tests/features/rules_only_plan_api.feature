# Sprint 4 ST-061b (FR-120..FR-123; NFR-019): the rules-only plan over HTTP, POST and GET
# /me/plan (api-sprint-04 §2), on the real database, the real drill library (content/drills) and
# matches tagged through the API. Steps: backend/tests/features/test_rules_only_plan_api.py.
# The serve/receive split follows the side-out rule, unverified until P7 (@needs-verification).
@M5 @story-ST-061b @coaching
Feature: Rules-only plan from the API
  A player who has tagged a match asks for a plan with their preferences and gets a 2-week plan
  that names their weaknesses in rallies lost per game, cites their own numbers for every drill
  and says when it rests on little data or unofficial scoring.

  Rule: No plan without a tagged match

    Scenario: No tagged match gives no plan and says why
      Given "ivy" has no tagged match
      When "ivy" asks for a plan as a solo player with a wall, 30 minutes per session, 3 sessions a week
      Then the answer is 409 "no_tagged_match" with the reason "Tag at least one match to get a plan."
      And "ivy" has no plan to read

  Rule: Preferences are checked field by field

    Scenario: Out-of-range and unknown preferences are refused with their field codes
      Given "ivy" has tagged the worked example
      When "ivy" asks for a plan with 10 minutes per session, 8 sessions a week and equipment "trampoline"
      Then the answer is 422 with the field codes "minutes_per_session:out_of_range, sessions_per_week:out_of_range, equipment:unknown_value"
      And "ivy" has no plan to read

    Scenario: No drill fits the setup
      Given "ivy" has tagged the worked example
      When "ivy" asks for a plan as an advanced solo player with no equipment, 30 minutes per session, 3 sessions a week
      Then the answer is 409 "no_plan_fits" with the reason "No plan fits these settings. Try more time or equipment."
      And "ivy" has no plan to read

  Rule: A tagged match gives a cited, honest plan

    @needs-verification
    Scenario: A plan from the worked example
      Given "ivy" has tagged the worked example
      When "ivy" asks for a plan as a solo player with a wall, 30 minutes per session, 3 sessions a week
      Then the answer is 201 with the plan
      And the weaknesses are ranked in "rallies_lost_per_game" with the side-out split marked unverified
      And the plan is marked as unofficial scoring
      And the plan has 6 sessions of at most 30 minutes, each starting with a warm-up
      And every drill cites a metric, its value, n and at most 10 rallies
      And the plan says it is based on limited data from 13 rallies
      And "ivy" reads the same plan back

    Scenario: Another player never sees the plan
      Given "ivy" has tagged the worked example
      And "ivy" has a plan as a solo player with a wall, 30 minutes per session, 3 sessions a week
      Then "carlos" has no plan to read

  Rule: A deleted match is never the basis of a plan

    Scenario: Deleting one of two cited matches rebuilds the plan from the match left
      Given "ivy" has tagged the worked example in 2 matches
      And "ivy" has a plan as a solo player with a wall, 30 minutes per session, 3 sessions a week
      When "ivy" deletes one of the 2 matches
      And "ivy" reads the plan
      Then the plan is regenerated because a source match was deleted
      And no drill cites the deleted match
      And the plan read says it is based on limited data from 13 rallies
