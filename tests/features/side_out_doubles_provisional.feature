# Sprint 1 §7.8 (ST-023). Owner: senior-qa-engineer. Written before ST-020 (tests first).
# Steps: backend/tests/features/test_side_out_doubles_provisional.py (shared: scoring_steps.py).
# Rows SOD-01..SOD-12 and SOD-16 from QD §2.2. SOD-13..SOD-15 (declared starts) run in Sprint 2.
# Every row stays @needs-verification until the coach records @rule-<number> (QD-TR-07,
# ADR 0009). The test report lists these rows separately (QD-QG-P5).
@M0 @story-ST-023 @needs-verification @scoring
Feature: Side-out doubles scoring under the provisional preset
  Rows come from QD §2.2 and rest on unverified rules [DOM G1 R2, R6].
  They do not count toward FR-041's Definition of Done until each row carries @rule-<number>.

  Background:
    Given the rules preset "PROVISIONAL-UNVERIFIED" with target 11, margin 2 and the first-service exception

  Rule: Only the serving side scores; a lost serve passes to the partner, then to the other side

    Scenario Outline: Score after one rally
      Given a doubles game called "<before>" with side <srv> serving
      When the <winner> side wins the rally
      Then the score is called "<after>" with side <next> serving
      Examples:
        | id     | before  | srv | winner    | after   | next |
        | SOD-01 | 0-0-2   | A   | serving   | 1-0-2   | A    |
        | SOD-02 | 0-0-2   | A   | receiving | 0-0-1   | B    |
        | SOD-03 | 3-5-1   | A   | receiving | 3-5-2   | A    |
        | SOD-04 | 3-5-2   | A   | receiving | 5-3-1   | B    |
        | SOD-05 | 7-4-1   | A   | serving   | 8-4-1   | A    |
        | SOD-08 | 10-10-1 | A   | serving   | 11-10-1 | A    |
        | SOD-10 | 10-9-2  | A   | receiving | 9-10-1  | B    |
        | SOD-16 | 5-5-1   | A   | replay    | 5-5-1   | A    |

  Rule: A game is won at the target score by the margin

    Scenario Outline: Game end
      Given a doubles game called "<before>" with side A serving
      When the <winner> side wins the rally
      Then the game is <state>
      Examples:
        | id     | before  | winner    | state          |
        | SOD-07 | 10-8-1  | serving   | won by A 11-8  |
        | SOD-09 | 11-10-2 | serving   | won by A 12-10 |
        | SOD-11 | 21-20-1 | serving   | won by A 22-20 |

  Rule: Serving positions follow the score

    Scenario: SOD-06 server changes court after scoring
      Given a doubles game called "7-4-1" with side A serving
      When the serving side wins the rally
      Then the same server serves again from the other court
      And the receiving players keep their positions

  Rule: A finished game refuses rallies

    Scenario: SOD-12 rally after game over
      Given a doubles game that side A has won 11-8
      When any rally is applied
      Then the rally is refused with a "game already over" message
