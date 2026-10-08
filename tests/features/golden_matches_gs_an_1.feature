# Sprint 3 ST-049 (NFR-004, FR-151, QD-GD-03): the golden matches GS-AN-1 v1 guard the starter
# stats. Steps: backend/tests/features/test_golden_matches_gs_an_1.py. The full gate (3 matches x
# AN-01..AN-07 x 2 sides) is backend/tests/regression/test_golden_an.py (`pytest -m golden_an`).
# Scoring is PROVISIONAL-UNVERIFIED (ADR 0009, ADR 0023).
@M4 @story-ST-049 @nfr-004 @analytics @golden_an @needs-verification
Feature: Golden matches GS-AN-1 v1 guard the starter stats
  Three frozen tag scripts and their expected values; the product must equal them exactly,
  and any difference names the match, the metric and the side.

  Rule: The frozen set cannot change silently (FR-151, NFR-078)

    Scenario: An expected value edited without a version bump is refused
      Given a copy of the golden set GS-AN-1
      And side A's AN-04 count of "gm1-two-games" is changed in the copy
      When the manifest check runs on the copy
      Then the check fails naming "expected/gm1-two-games.json"

    Scenario: The committed golden set passes the manifest check
      Given the committed golden set GS-AN-1
      When the manifest check runs on it
      Then the check passes as "GS-AN-1 v1, 6 files"

  Rule: A difference names the match, the metric and the side (NFR-004)

    Scenario: A re-tagged rally is reported with its match, metric and side
      Given golden match "gm3-corrections-needs-decision" with its first winner re-tagged as an unforced error
      When its starter stats are compared with GS-AN-1
      Then a difference names "GS-AN-1 gm3-corrections-needs-decision AN-" and a side

  Rule: Corrections and "needs your decision" rallies count as the frozen values say

    Scenario: The match with corrections equals its frozen values
      Given golden match "gm3-corrections-needs-decision" as scripted, with its corrections
      When its starter stats are compared with GS-AN-1
      Then there is no difference
      And no stat counts rallies 20 to 23, which need a decision
