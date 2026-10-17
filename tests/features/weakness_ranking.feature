# Sprint 4 ST-055 (FR-120; ADR 0003; OQ-08): weakness ranking by rallies lost per game, split
# serve/receive, points conceded shown apart, unit provisional. Catalogue: COACH-4
# docs/domain/weakness-catalogue.md. Design: docs/architecture/coaching-plan.md §3.
# Steps: backend/tests/features/test_weakness_ranking.py (pure domain, no API, no database).
# Integration: backend/tests/integration/test_it_04_01_weakness_from_stats.py.
# The serve/receive split rests on the side-out rule (DOM G1 R2), UNVERIFIED until P7.
@M5 @story-ST-055 @fr-120 @coaching @needs-verification
Feature: Weakness ranking by rallies lost per game
  The player's weaknesses are ranked by the rallies they lost per game, each split into
  lost on serve and lost on receive, with the points conceded shown apart and never ranked on.

  Rule: No tagged match gives no ranking, and says why

    Scenario: No tagged match
      Given player "Ivy" has no tagged match
      When Ivy's weaknesses are ranked
      Then the ranking is empty with the reason "no_tagged_match"
      And the ranking covers 0 games

  Rule: Weaknesses are ranked by rallies lost per game, ties in catalogue order

    Scenario: Unforced errors outrank serve faults (FR-120)
      Given over 1 game Ivy lost 10 rallies on serve to "unforced_error"
      And over the same game Ivy lost 4 rallies on receive to a "serve" fault
      When Ivy's weaknesses are ranked
      Then the weaknesses in order are "Unforced errors, Serve faults"
      And "Unforced errors" shows 10.0 rallies lost per game, 10 on serve and 0 on receive
      And "Serve faults" shows 4.0 rallies lost per game, 0 on serve and 4 on receive

    Scenario: Equal counts keep the catalogue order
      Given side A of the metric dictionary's worked example is Ivy's side
      When Ivy's weaknesses are ranked
      Then the weaknesses in order are "Opponent winners against you, Unforced errors, Serve faults"

  Rule: Lost on serve and lost on receive are shown, points conceded apart

    Scenario: Serve and receive are shown for each weakness
      Given side A of the metric dictionary's worked example is Ivy's side
      When Ivy's weaknesses are ranked
      Then "Opponent winners against you" shows 3.0 rallies lost per game, 0 on serve and 3 on receive
      And "Unforced errors" shows 2.0 rallies lost per game, 1 on serve and 1 on receive
      And "Serve faults" shows 2.0 rallies lost per game, 2 on serve and 0 on receive
      And "Serve faults" shows 0 points conceded
      And "Unforced errors" shows 1 point conceded
      And every rally Ivy lost is counted once, on serve or on receive

  Rule: The unit is provisional while the side-out rule is unverified

    Scenario: Unit provisional
      Given side A of the metric dictionary's worked example is Ivy's side
      When Ivy's weaknesses are ranked
      Then the ranking's unit is "rallies_lost_per_game"
      And the ranking is marked provisional, side-out rule not verified
