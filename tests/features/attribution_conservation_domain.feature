# Sprint 3 ST-045 (FR-109, ADR 0003): attribution conservation in the analytics domain, per game
# and per side, on serve and on receive. Steps: backend/tests/features/test_attribution_conservation_domain.py.
# The QA-ACC-3 acceptance scenario is attribution_conservation.feature (senior-qa-engineer).
# Scoring is PROVISIONAL-UNVERIFIED (ADR 0009, ADR 0023).
@M4 @story-ST-045 @fr-109 @analytics @needs-verification
Feature: Attribution conservation per game and serve/receive
  Every rally a side lost is attributed exactly once, to a category or to "unattributed",
  and the check runs on every stats computation.

  Rule: A broken attribution never publishes numbers

    Scenario: A rally attributed twice stops the stats computation
      Given the worked-example game of the metric dictionary is projected
      And the attribution counts rally 10 twice
      When the starter stats are computed
      Then the computation is refused with "A game 1 serve"

    Scenario: A lost rally left out stops the stats computation
      Given the worked-example game of the metric dictionary is projected
      And the attribution leaves out what side B lost on receive
      When the starter stats are computed
      Then the computation is refused with "B game 1 receive"

    Scenario: A lost rally swapped for one the side did not lose stops the stats computation
      Given the worked-example game of the metric dictionary is projected
      And the attribution puts rally 1 in place of rally 3 that side A lost on receive
      When the starter stats are computed
      Then the computation is refused with "A game 1 receive: lost [3, 4, 13, 14]"

  Rule: Attributed plus unattributed equals rallies lost, per game, side and phase

    Scenario: The worked example conserves every lost rally
      Given the worked-example game of the metric dictionary is projected
      When the starter stats are computed
      Then side A lost rallies "2,10,12" on serve and "3,4,13,14" on receive in game 1
      And side B lost rallies "5,6" on serve and "1,7,9,11" on receive in game 1
      And for each side, game and phase the attributed and unattributed rallies equal the lost ones

    Scenario: A rally lost to the opponent's winner is unattributed
      Given the worked-example game of the metric dictionary is projected
      When the lost rallies are attributed
      Then side A's unattributed rallies on receive in game 1 are "3,13,14"
      And side B's unattributed rallies on receive in game 1 are "1,7"

    Scenario: Games are kept apart
      Given a match of two games where side A wins game 1 and game 2 starts with side B serving
      When the starter stats are computed
      Then side B lost rallies "" on serve and "1,2,3,4,5,6,7,8,9,10,11" on receive in game 1
      And side B lost rallies "12" on serve and "" on receive in game 2
      And for each side, game and phase the attributed and unattributed rallies equal the lost ones
