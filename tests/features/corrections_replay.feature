# Sprint 2 §7.4 (ST-041, written first for ST-032; QD §2.2 rows C-01..C-04, QD-RE-10).
# Owner: senior-qa-engineer. Steps: backend/tests/features/test_corrections_replay.py, on the
# pure scorebook (`racket.matches.scorebook.domain`, match-aggregate §4-§5); the same commands
# through the API are IT-02-01 / IT-02-02 and G02-01 steps 7-9.
# C-01 and C-04 are mechanics (ADR 0009 part a). C-02 and C-03 depend on where a game ends under
# the unverified preset, so they stay @needs-verification. C-02's game is the harness conflict
# game (`taglib.CONFLICT_TAGS`): the plan's "12-10 after 24 rallies" cannot happen under the
# provisional preset (22 points need at least 25 rallies with side-outs), decision-log 2026-10-05.
@M0 @story-ST-032 @nfr-013 @scoring
Feature: Corrections re-score later rallies
  Rule: A correction re-scores every later rally in one step

    Scenario: C-01 correction in the middle of a game
      Given a tagged game with 30 rallies
      When Ivy changes the winner of rally 5
      Then rallies 5 to 30 show scores recomputed from the corrected outcomes
      And the score sheet matches one built from scratch with the corrected outcomes

    Scenario: C-04 undo restores the exact sheet
      Given Ivy changed the winner of rally 5 of 30
      When she undoes that change
      Then the score sheet is identical to the one before the change

  Rule: Rallies are never deleted when a correction changes where a game ends

    @needs-verification
    Scenario: C-02 correction ends the game earlier
      Given a tagged game that side A won 11-0 after 14 rallies
      When Ivy changes rally 11 to "won by side A"
      Then the game shows as won by side A at rally 11
      And rallies 12 to 14 are listed as needing her decision, not deleted

    @needs-verification
    Scenario: C-03 correction un-ends a game
      Given game 1 was won by side A at rally 22 and game 2 has 5 tagged rallies
      When Ivy changes rally 22 to "won by side B"
      Then game 1 is no longer over
      And the rallies of game 2 are listed as needing her decision, not deleted

  # Sprint 3 §7.7 (C3-03, PE-S2-R3-01). API binding: the server's rule (the move the client may
  # offer); browser binding: web/e2e/sprint-03/move-offer.spec.ts (E2E-03-07).
  Rule: Only moves the server accepts are offered

    @needs-verification
    Scenario: Move offered only on the latest kept rally
      Given rallies 12 to 14 need Ivy's decision
      When she opens the options of rally 12
      Then "Move to the next game" is not offered
      And she is told only the latest kept rally can be moved first
