# Sprint 3 PE-DESIGN-3 (PE-1, PE-R2S3-04; ADR 0033 rule 2): the api-sprint-03 §2.1 per-side
# field table is the contract the FE and the goal harness build against; it must name exactly
# what the analytics domain serves. Steps: backend/tests/features/test_stats_contract_doc.py.
@story-PE-DESIGN-3 @analytics
Feature: The stats contract table equals the starter stats output
  A field the domain serves without a contract row has no consumer and no automated comparison,
  and a documented field the domain does not serve is a promise nobody keeps.

  Rule: A difference in either direction fails, naming the metric

    Scenario: A contract table that leaves out a served field fails, naming the metric
      Given the api-sprint-03 per-side table with "longest_by_game" removed from "AN-06"
      When the table is compared with the starter stats of the worked example
      Then the comparison fails, naming "AN-06"

    Scenario: A contract table that documents a field the domain does not serve fails
      Given the api-sprint-03 per-side table with "median" added to "AN-05"
      When the table is compared with the starter stats of the worked example
      Then the comparison fails, naming "AN-05"

    Scenario: A table without a row for every metric is refused
      Given a per-side table with rows for "AN-01, AN-02" only
      When the table is read
      Then it is refused, naming "AN-07"

  Rule: The shipped contract names exactly what the domain serves

    Scenario: The shipped api-sprint-03 table equals the starter stats fields
      Given the shipped api-sprint-03 per-side table
      When the table is compared with the starter stats of the worked example
      Then the comparison passes for every metric and side
      And "AN-06" documents "longest_by_game"
