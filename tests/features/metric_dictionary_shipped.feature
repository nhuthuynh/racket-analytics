# Sprint 3, GS-AN-1-V2 (ST-043 review round 2: PD-R2S3-01, PE-R2S3-05; FR-102; ADR 0044).
# Written by senior-backend-engineer in the ticket PR; owner: senior-qa-engineer.
# Steps: backend/tests/features/test_metric_dictionary_shipped.py (domain binding over the shipped
# metrics.json and the coach's status rows in docs/domain/metric-dictionary.md).
# Integration: backend/tests/integration/test_gs_an_1_v2_shipped_statuses_packaged.py (built wheel).
# Unit: backend/tests/unit/sports/pickleball/test_metric_dictionary_status_sync.py
@M0 @story-ST-043 @fr-102
Feature: The shipped metric dictionary follows the coach's record
  Only the pickleball-domain-coach moves a metric's status, in the metric dictionary document.
  The dictionary the product ships mirrors it, so players see exactly the metrics the coach has
  reviewed, no more and no fewer.

  Rule: A status moved on one side only is reported

    Scenario: The coach reviewed a metric the product still ships as draft
      Given the coach records "AN-01" as "coach-reviewed"
      And the shipped dictionary has "AN-01" as "draft"
      When the shipped statuses are compared with the coach's record
      Then the difference "AN-01: shipped 'draft', recorded 'coach-reviewed'" is reported

    Scenario: The product publishes a metric the coach has not reviewed
      Given the coach records "AN-05" as "draft"
      And the shipped dictionary has "AN-05" as "coach-reviewed"
      When the shipped statuses are compared with the coach's record
      Then the difference "AN-05: shipped 'coach-reviewed', recorded 'draft'" is reported

  Rule: The shipped dictionary equals the coach's record since COACH-1

    Scenario: AN-01 to AN-07 are coach-reviewed and published
      Given the coach's status rows in the metric dictionary document
      And the shipped dictionary
      When the shipped statuses are compared with the coach's record
      Then no difference is reported
      And the published metrics are "AN-01, AN-02, AN-03, AN-04, AN-05, AN-06, AN-07"
