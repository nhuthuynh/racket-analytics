# Sprint 3, ST-043 (FR-102, NFR-075). Written by senior-backend-engineer in the ticket PR (review
# PE-ST043-02 / SQA-1); owner: senior-qa-engineer. Steps: backend/tests/features/test_metric_dictionary.py
# (domain binding: MetricDictionary.published() and version_bump_violations()). The API binding
# (IT-03-03, a draft metric is absent from the stats response) comes with ST-046.
# Unit tests: backend/tests/unit/sports/pickleball/test_metric_dictionary.py
@M0 @story-ST-043 @nfr-075
Feature: Pickleball metric dictionary
  Only metrics the coach has reviewed reach players, and a metric never changes meaning silently.

  Rule: Only coach-reviewed and verified metrics are published

    Scenario: Draft metric hidden
      Given the metric dictionary has "AN-01" as "draft"
      When the published metrics are listed
      Then "AN-01" is not among them

    Scenario: Deprecated metric hidden
      Given the metric dictionary has "AN-01" as "deprecated"
      When the published metrics are listed
      Then "AN-01" is not among them

    Scenario: Coach-reviewed metric published
      Given the metric dictionary has "AN-01" as "coach-reviewed"
      When the published metrics are listed
      Then "AN-01" is among them

  Rule: A definition change needs a version bump

    Scenario: Definition changed and the lock rewritten without a bump
      Given the locked metric dictionary on main
      When the formula of "AN-01" changes and its locked digest is rewritten in place
      Then the version check fails and names "AN-01"

    Scenario: Definition changed with a version bump
      Given the locked metric dictionary on main
      When the formula of "AN-01" changes with a version bump recorded in the lock
      Then the version check passes
