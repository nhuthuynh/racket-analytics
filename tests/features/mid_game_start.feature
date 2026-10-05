# Sprint 2 §7.5 (ST-041, written first for stretch ST-034). Owner: senior-qa-engineer.
# Steps: backend/tests/features/test_mid_game_start.py. Rows SOD-13..SOD-15 from QD §2.2
# (QD-RE-06). They bind to the engine's declared state (`declare_state`, ST-020), which already
# refuses an impossible start with `IllegalState` (QD names it `IllegalStart`); ST-034 adds the
# same check behind the score sheet. @needs-verification until the coach records the rule
# numbers (ADR 0009); reported separately (QD-QG-P5).
@M0 @story-ST-034 @needs-verification @scoring
Feature: Start the score sheet mid-game
  Rows SOD-13..SOD-15 from QD §2.2 [DOM G1, unverified].

  Background:
    Given the rules preset "PROVISIONAL-UNVERIFIED"

  Scenario: Video begins part-way through a game
    Given Ivy declares the start as "4-6-2" with her side receiving
    When she tags the first rally as won by her side
    Then the score is called "6-4-1" with her side serving

  Scenario: SOD-13 a legal mid-game start
    Given Ivy declares the start as "0-0-1" with her side serving
    Then the declared start is accepted

  Scenario Outline: Impossible start refused
    Given Ivy declares the start as "<start>" with her side serving
    Then she is told why the start is impossible
    Examples:
      | id     | start  |
      | SOD-14 | 12-9-1 |
      | SOD-15 | 4-6-3  |
