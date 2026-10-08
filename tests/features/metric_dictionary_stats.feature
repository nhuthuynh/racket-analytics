# Sprint 3 §7.2 (QA-ACC-3, written for ST-043; FR-102, FR-055). Owner: senior-qa-engineer.
# The dictionary as players see it in the stats response. The domain rules of the dictionary
# (published set, version bump) are tests/features/metric_dictionary.feature (ST-043, on main).
# API binding: backend/tests/features/test_metric_dictionary_stats.py. Browser binding:
# web/e2e/sprint-03/definitions.spec.ts (E2E-03-03).
@M0 @story-ST-043 @fr-102 @analytics
Feature: Metric dictionary in the stats
  Scenario: Draft metric hidden
    Given metric AN-05 has status "draft"
    When Ivy opens her stats
    Then AN-05 is not shown

  Scenario: Definition shown
    Given AN-02 is coach-reviewed
    When Ivy opens "How is this measured?" on "Rallies won when receiving"
    Then she sees its definition in plain words

  Scenario: Unofficial scoring is said on the stats too
    Given the rules preset contains an unverified rule
    When Ivy opens her stats
    Then she sees "unofficial scoring (rules not yet verified)"
