# Sprint 1 §7.9 (ST-023). Owner: senior-qa-engineer. Written before ST-020 (tests first).
# Steps: backend/tests/features/test_faults_provisional.py (shared: scoring_steps.py).
# Rows F-01..F-06 from QD §2.2; @needs-verification until the coach records @rule-<number>.
@M0 @story-ST-023 @needs-verification @scoring
Feature: Faults end the rally against the faulting side (provisional preset)
  Rows come from QD §2.2 F-01..F-06 [DOM G1 R4-R6, unverified].

  Background:
    Given the rules preset "PROVISIONAL-UNVERIFIED"

  Rule: A fault is scored as the faulting side losing the rally

    Scenario Outline: Fault outcome
      Given a doubles game called "<before>" with side A serving
      When the <side> side commits a <fault> fault
      Then the score is called "<after>" with side <next> serving
      Examples:
        | id   | before | side      | fault               | after | next |
        | F-01 | 4-2-1  | serving   | serve               | 4-2-2 | A    |
        | F-02 | 4-2-2  | serving   | foot fault on serve | 2-4-1 | B    |
        | F-03 | 4-2-1  | receiving | two-bounce          | 5-2-1 | A    |
        | F-04 | 4-2-1  | serving   | two-bounce          | 4-2-2 | A    |
        | F-05 | 4-2-1  | receiving | NVZ                 | 5-2-1 | A    |

  Rule: The fault subtype never changes the score

    Scenario Outline: F-06 same outcome for every fault subtype
      Given a doubles game called "4-2-1" with side A serving
      When the receiving side commits a <fault> fault
      Then the score is called "5-2-1" with side A serving
      Examples:
        | id   | fault      |
        | F-06 | two-bounce |
        | F-06 | NVZ        |
        | F-06 | other      |
