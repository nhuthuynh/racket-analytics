# Sprint 4 ST-057 (FR-122; QD-PL-04): every drill assignment cites the metric, its value, n and
# the evidence rallies. Pure domain (no API, no database); IT-04-02b checks the same citations
# against GET stats and GET evidence in Postgres. Steps: backend/tests/features/plan_citation_steps.py.
@M5 @story-ST-057 @coaching
Feature: Every drill says why
  Each assignment in a plan cites the player's own numbers: the metric, its value, n and up to
  10 rallies, with a "see all n" link to the evidence list.

  Background:
    Given the reviewed test library with warm-ups, wall, ball-machine and 4-player drills
    And the top weaknesses are "unforced errors" on "AN-04", "serve faults" on "AN-05" and "errors under pressure" on "AN-07:forced-error"
    And a solo player with a wall and no ball machine, 30 minutes per session, 3 sessions a week
    And the player's citations for every plan target

  Rule: No assignment without a reason (QD-PL-04)

    Scenario: A drill cannot be assigned without a reason
      Given the player has no citation for "AN-05"
      When the plan is assembled and cited
      Then the plan is refused under "QD-PL-04"
      And the refusal names the drill "pb.test.serve-target@1"

  Rule: The reason is the player's own numbers (FR-122)

    Scenario: Why this drill
      Given the player's "AN-05" is 2 of 7 serves
      When the plan is assembled and cited
      Then every assignment cites a metric it targets, a value, n and at most 10 rallies
      And the drill for "serve faults" says why "Serve faults: 29% of 7 serves"

    Scenario: At most 10 rallies, then "see all"
      Given the player's "AN-04" is 14 unforced errors over 2 games in 2 matches
      When the plan is assembled and cited
      Then the drill for "unforced errors" cites 10 rallies and links to all 14 in 2 matches
