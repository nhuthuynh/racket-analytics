# Sprint 3 §7.1 (QA-ACC-3, written for ST-044/ST-046). Owner: senior-qa-engineer.
# API binding: backend/tests/features/test_starter_stats.py. Browser binding: web/e2e/sprint-03/
# journey-v2.spec.ts (E2E-03-01). Scoring is PROVISIONAL-UNVERIFIED, so every scenario that reads
# the score sequence is @needs-verification (ADR 0009, ADR 0023; QD-QG-P5).
@M4 @story-ST-044 @nfr-004 @analytics @needs-verification
Feature: Starter stats
  The definitions are the coach's (metric-dictionary v0.1); scoring is provisional.

  Background:
    Given Ivy has tagged the worked-example game of the metric dictionary

  Rule: Every stat equals the coach's hand count

    Scenario: Rallies won on serve
      When she opens her stats
      Then "Rallies won on serve" shows 57% for her side with "n = 7"

    Scenario: Replays are not counted
      When she opens her stats
      Then no stat counts rally 8, which was a replay

    Scenario: Errors are charged to the side that made them
      When she opens her stats
      Then her side shows 2 unforced errors in the game
      And the other side shows 1 with "player not tagged in 1 rally"

  Rule: Stats follow corrections

    Scenario: A correction changes the stats
      Given her stats show "Rallies won when receiving" as 33% with "n = 6"
      When she changes rally 3 to won by her side
      Then "Rallies won when receiving" shows 40% with "n = 5"
