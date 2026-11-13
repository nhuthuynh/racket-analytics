# Sprint 6 ST-171a (FR-171.R1, R5, R6; ADR 0061 Rule 1): player pattern measures from Quick Tag.
# Steps: backend/tests/features/test_pattern_measures_quick_tag.py. Pure domain: the sheet is
# built by the real projection, the measures by racket.analytics.patterns over starter_stats.
# Scoring is PROVISIONAL-UNVERIFIED, so AN-01 reads the provisional sequence (ADR 0009, ADR 0023).
@story-ST-171 @analytics @needs-verification
Feature: Player pattern measures from Quick Tag data
  A pattern measure reuses the starter stat it comes from, says when its data source is
  missing, and is ranked only when its sample is large enough.

  Rule: FR-171.R1 A Quick Tag pattern measure equals its starter stat

    Scenario: AN-01 of the worked example equals the coach's hand count
      Given the worked-example game of the metric dictionary is projected
      When the pattern measures of the match are taken from Quick Tag
      Then "AN-01" for side A is 0.5714 with n 7 and the Wilson interval 0.2505 to 0.8418
      And every Quick Tag measure equals its starter stat

  Rule: FR-171.R5 A pattern whose data source the match lacks is unavailable, never zero

    Scenario: AN-09 on a Quick Tag-only match is unavailable
      Given the worked-example game of the metric dictionary is projected
      When the pattern measures of the match are taken from Quick Tag with "AN-09" from "FT"
      Then "AN-09" for side A is unavailable with the reason "no_shot_facets" and no value

  Rule: FR-171.R6 Below the pattern's min_n the measure is flagged and not rankable

    Scenario: AN-01 with n 7 is a low sample and not rankable
      Given the worked-example game of the metric dictionary is projected
      When the pattern measures of the match are taken from Quick Tag
      Then "AN-01" for side A is flagged as a low sample and is not rankable

    Scenario: AN-01 with n 25 and a narrow interval is rankable
      Given side A serves and wins 25 rallies
      When the pattern measures of the match are taken from Quick Tag
      Then "AN-01" for side A is rankable
