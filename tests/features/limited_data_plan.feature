# Sprint 4 ST-057 (FR-123; QD-PL-06): a plan built on a low-sample top weakness says so.
# Pure domain; the low-sample flag comes from the metric dictionary rule (ADR 0041, ADR 0005)
# through the Analytics ACL. Steps: backend/tests/features/test_drill_rationale.py.
@M5 @story-ST-057 @coaching
Feature: A plan from little data says so
  When the metric of the player's top weakness is low-sample, the plan carries the number of
  rallies it is based on and says "based on limited data from N rallies".

  Background:
    Given the reviewed test library with warm-ups, wall, ball-machine and 4-player drills
    And the top weaknesses are "unforced errors" on "AN-04", "serve faults" on "AN-05" and "errors under pressure" on "AN-07:forced-error"
    And a solo player with a wall and no ball machine, 30 minutes per session, 3 sessions a week

  Scenario: A missing citation is refused
    Given one short match of 13 rallies with no citation for "AN-04"
    When the plan is assembled and cited
    Then the plan is refused under "QD-PL-04"

  Scenario: One short match
    Given one short match of 13 rallies where "AN-04" is low-sample
    When the plan is assembled and cited
    Then the plan carries limited data from 13 rallies
    And the plan says "based on limited data from 13 rallies"

  Scenario: Enough data for the top weakness, no limited-data notice
    Given one short match of 13 rallies where only "AN-05" is low-sample
    When the plan is assembled and cited
    Then the plan carries no limited-data notice
