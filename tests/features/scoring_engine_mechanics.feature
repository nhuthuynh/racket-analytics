# Sprint 1 §7.7 (ST-020). Owner: senior-qa-engineer. Written before ST-020 (tests first).
# Steps: backend/tests/features/test_scoring_engine_mechanics.py (shared: scoring_steps.py).
# Ready (ADR 0009 part a): every scenario names the configuration values it assumes.
@M0 @story-ST-020 @nfr-079 @scoring
Feature: Configurable scoring engine
  The engine applies only the values in its configuration; no rule value is hard-coded.

  Rule: A game ends at the first rally that reaches the configured target with the configured margin

    Scenario Outline: Game end follows the configuration
      Given a game configured with target <target> and margin <margin> where only the serving side scores
      And side A is serving with the score <a> to <b>
      When side A wins the rally
      Then the game is <state>
      Examples:
        | target | margin | a  | b  | state             |
        | 11     | 2      | 10 | 8  | won by side A     |
        | 11     | 2      | 10 | 10 | not over          |
        | 15     | 2      | 14 | 12 | won by side A     |
        | 11     | 1      | 10 | 10 | won by side A     |

  Rule: A finished game accepts no more rallies

    Scenario: Rally after the game is over
      Given a game has ended
      When another rally is applied to that game
      Then the rally is refused with a "game already over" message

  Rule: Invalid configurations are refused

    Scenario Outline: Configuration out of range
      Given a game configuration with <field> set to <value>
      When the configuration is loaded
      Then it is refused with a message naming <field>
      Examples:
        | field  | value |
        | target | 0     |
        | margin | 0     |

  Rule: Scores are reproducible from the recorded rallies

    Scenario: Replaying the same rallies gives the same score sheet
      Given a game with 30 recorded rally outcomes
      When the score sheet is rebuilt from those outcomes
      Then it is identical to the score sheet computed rally by rally

    Scenario: A replayed rally changes nothing
      Given a game at 5-5 with side A serving at server 1
      When a rally is recorded as a replay
      Then the score is still 5-5 with side A serving at server 1

  Rule: A match keeps the rules version it was scored under

    Scenario: A newer rules preset ships
      Given Ivy's match was scored under preset "PROVISIONAL-UNVERIFIED"
      When a newer rules preset becomes available
      Then her match still uses "PROVISIONAL-UNVERIFIED" and shows the same scores
