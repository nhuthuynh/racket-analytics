# Sprint 2 §7.5 (ST-041, written first for stretch ST-035). Owner: senior-qa-engineer.
# Steps: backend/tests/features/test_side_out_singles_provisional.py (red_until ST-035).
# Rows SOS from QD §2.2 (side-out singles: two-number call, a lost serve is a side-out, the
# server's court follows the parity of the server's score). Every row stays @needs-verification
# until the coach records @rule-<number> (QD-TR-07, ADR 0009); reported separately (QD-QG-P5).
@M0 @story-ST-035 @needs-verification @scoring
Feature: Side-out singles scoring under the provisional preset
  Rows come from QD §2.2 SOS [DOM G1 R6, unverified]. Two-number call, server's score first.

  Background:
    Given the rules preset "PROVISIONAL-UNVERIFIED" for singles with target 11 and margin 2

  Rule: Only the server scores; a lost rally passes the serve

    Scenario Outline: Score after one rally
      Given a singles game called "<before>" with player <srv> serving
      When the <winner> player wins the rally
      Then the score is called "<after>" with player <next> serving
      And the game is <state>
      Examples:
        | id     | before | srv | winner    | after | next | state          |
        | SOS-01 | 0-0    | A   | serving   | 1-0   | A    | not over       |
        | SOS-02 | 0-0    | A   | receiving | 0-0   | B    | not over       |
        | SOS-03 | 10-10  | A   | serving   | 11-10 | A    | not over       |
        | SOS-04 | 11-10  | A   | serving   | 12-10 | A    | won by A 12-10 |

    Scenario: SOS-05 rally after game over
      Given a singles game that player A has won 11-8
      When any rally is applied
      Then the rally is refused with a "game already over" message

  Rule: The server's court follows the parity of the server's score

    Scenario Outline: Serving court
      Given a singles game where the server's score is <score>
      When the server serves
      Then the serve is expected from the <court> court
      Examples:
        | id     | score | court |
        | SOS-06 | 0     | right |
        | SOS-07 | 1     | left  |
        | SOS-08 | 2     | right |
        | SOS-09 | 3     | left  |
        | SOS-10 | 4     | right |
        | SOS-11 | 5     | left  |
        | SOS-12 | 6     | right |
        | SOS-13 | 7     | left  |
        | SOS-14 | 8     | right |
        | SOS-15 | 9     | left  |
        | SOS-16 | 10    | right |
        | SOS-17 | 11    | left  |
        | SOS-18 | 12    | right |
