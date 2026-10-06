# Sprint 1 §7.10 (ST-021; the M rows are part of ST-023's golden tables). Owner: senior-qa-engineer.
# Written before ST-021 (tests first). Steps: backend/tests/features/test_match_structure.py.
# M-01..M-08 state the match format, first server and end switch as explicit inputs and make no
# rulebook claim (ADR 0009 part a), so they are Ready and NOT @needs-verification.
@M0 @story-ST-021 @scoring
Feature: Match structure
  Rows M-01..M-08 from QD §2.2 (enumerated in review-log RL-04). They state the match format,
  first server and end switch as explicit inputs and make no rulebook claim (ADR 0009 part a).

  Rule: A match ends when one side has won the majority of its games

    Scenario Outline: Match result
      Given a best-of-<n> match in which the games were won by <games>
      Then the match is <result>
      Examples:
        | id   | n | games   | result                |
        | M-01 | 1 | B       | won by side B, 1-0    |
        | M-02 | 3 | A, A    | won by side A, 2-0    |
        | M-03 | 3 | A, B    | not over; game 3 open |
        | M-04 | 3 | A, B, B | won by side B, 2-1    |

    Scenario Outline: Rallies after the match is decided are refused
      Given a best-of-<n> match in which the games were won by <games>
      When a rally is recorded for game <game>
      Then the rally is refused with a "match is over" message
      Examples:
        | id   | n | games | game |
        | M-05 | 3 | A, A  | 3    |
        | M-08 | 1 | B     | 2    |

  Rule: Who serves first and whether ends switched are recorded, never guessed

    Scenario: M-06 and M-07 second game set-up
      Given game 1 of Ivy's match has ended
      When she starts game 2 and states that side B serves first and ends were switched
      Then game 2 starts with side B serving
      And game 2 is recorded as played from switched ends
