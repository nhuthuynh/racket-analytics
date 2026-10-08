# Sprint 3 ST-044 (FR-100, FR-101, NFR-004): the analytics domain over the projected sheet.
# Steps: backend/tests/features/test_starter_stats_domain.py. The API view of the same stats is
# starter_stats.feature (QA-ACC-3, ST-046). Scoring is PROVISIONAL-UNVERIFIED (ADR 0009, ADR 0023).
@M4 @story-ST-044 @nfr-004 @analytics @needs-verification
Feature: Starter stats over the projected score sheet
  Every proportion carries n and a 95% Wilson interval; small samples are flagged (ADR 0005).

  Rule: Nothing is invented from an empty sheet

    Scenario: A match with no rally has no values and every proportion is flagged
      Given a projected sheet with no game
      When the starter stats are computed
      Then "AN-01" for side A has no value with "n = 0"
      And "AN-01" for side A is flagged as a low sample

  Rule: The stats equal the coach's hand count of the worked example (metric-dictionary §2)

    Scenario: Rallies won on serve and when receiving
      Given the worked-example game of the metric dictionary is projected
      When the starter stats are computed
      Then "AN-01" for side A is 4 of 7 with the interval 0.2505 to 0.8418
      And "AN-02" for side A is 2 of 6 with the interval 0.0968 to 0.7
      And no stat counts rally 8, which was a replay

    Scenario: The longest run is reported per side per game (AN-06)
      Given the worked-example game of the metric dictionary is projected
      When the starter stats are computed
      Then the longest run of side A per game is "3"
      And the longest run of side B per game is "2"

  Rule: Small samples are flagged (FR-101)

    Scenario: How rallies ended is flagged when a share's interval is too wide, not only when n is small
      Given a game where side A ends 24 rallies, 12 with a winner and 12 with an unforced error
      When the starter stats are computed
      Then "AN-07" for side A ends 24 rallies
      And "AN-07" for side A is flagged as a low sample

    Scenario Outline: The low-sample flag follows n and the interval width
      Given a proportion of <k> out of <n>
      Then its Wilson interval is <low> to <high>
      And it is <flag>
      Examples:
        | k  | n  | low   | high  | flag        |
        | 4  | 8  | 0.215 | 0.785 | flagged     |
        | 10 | 20 | 0.299 | 0.701 | flagged     |
        | 22 | 40 | 0.398 | 0.693 | not flagged |
