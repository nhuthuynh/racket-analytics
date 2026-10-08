# C3-10 / SEC-RV3-03, QA-RV3-06 (Sprint 2 review round 3 minors, carried to Sprint 3).
# Owner: senior-qa-engineer (IT-02-05); scenario added by the senior-frontend-engineer when the
# ticket was ported to its own PR (PO decision P13).
# Steps: backend/tests/features/test_rally_ownership_mixed_ids.py (API on Postgres + object store).
# Integration: backend/tests/integration/test_it_02_05_bola_sprint_02_routes.py (IT-02-05).
@story-C3-10 @nfr-051
Feature: A rally is reached only through the match that holds it
  Every rally route names a match and a rally. Owning the match is not enough: the rally must
  belong to that match, or the answer is the same "not found" as for a rally that does not exist.

  Rule: A rally named under another player's match is not found

    Scenario Outline: Carlos names Ivy's rally under his own match
      Given Ivy and Carlos each own a tagged match
      When Carlos tries to <action> Ivy's rally under his own match, with his current version
      Then Carlos gets the same "not found" result as for a rally that does not exist
      And Ivy's score sheet is unchanged
      Examples:
        | action     |
        | correct    |
        | decide on  |
        | watch      |
