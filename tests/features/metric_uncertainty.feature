# Sprint 3 §7.1 (QA-ACC-3, written for ST-044/ST-046; FR-101, ADR 0005). Owner: senior-qa-engineer.
# API binding: backend/tests/features/test_metric_uncertainty.py. Thresholds are configuration
# (n < 20, interval wider than 30 points, count metrics with fewer than 2 games); an amendment of
# ADR 0005 changes the Examples with a test-change-request row.
@M4 @story-ST-044 @fr-101 @analytics @needs-verification
Feature: Metrics show their uncertainty
  Rule: Small samples are flagged, never hidden

    Scenario Outline: Low-sample flag
      Given Ivy received serve in <n> rallies and won <won>
      When she opens her stats
      Then "Rallies won when receiving" shows <pct> with "n = <n>" and the low-sample flag "<flag>"
      Examples:
        | n  | won | pct | flag |
        | 8  | 4   | 50% | yes  |
        | 20 | 10  | 50% | yes  |
        | 40 | 22  | 55% | no   |

    Scenario: The interval is shown
      Given Ivy received serve in 40 rallies and won 22
      When she opens her stats
      Then she sees the range 40% to 69% next to 55%

    Scenario: One game is too few for a per-game count
      Given Ivy has tagged one game
      When she opens her stats
      Then "Unforced errors per game" is shown and flagged "low sample"
