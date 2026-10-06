# Sprint 1 §14.3.7 (ST-022). Owner: senior-qa-engineer. Written before ST-020 (tests first).
# Steps: backend/tests/features/test_property_and_oracle.py. Hypothesis versions of P1-P8:
# backend/tests/unit/sports/pickleball/test_rules_properties.py. Oracle: backend/tests/oracle/.
# The 100,000-sequence scenario is @nightly @slow (ST-024 runs it nightly; NFR-002b).
@M0 @story-ST-022 @nfr-002 @scoring
Feature: The scoring engine keeps its invariants under any valid configuration
  Invariants P1-P8 come from QD §2.3. They make no rulebook claim (ADR 0009 part a).

  Rule: Invariants hold for random rally sequences

    Scenario Outline: Random sequences under a configuration
      Given 1,000 random rally sequences
      And a game configured with target <target> and margin <margin>
      When every sequence is scored
      Then no invariant from P1 to P8 is broken
      Examples:
        | target | margin |
        | 11     | 2      |
        | 15     | 2      |
        | 21     | 2      |
        | 11     | 1      |

  Rule: An independent engine agrees with the production engine

    @nightly @slow
    Scenario: Nightly differential check
      Given 100,000 random rally sequences
      When both engines score every sequence
      Then they agree on every sequence

    Scenario: A disagreement is reported usefully
      Given the two engines disagree on a sequence
      When the nightly check finishes
      Then the run is marked failed
      And the report shows the shortest sequence that disagrees
