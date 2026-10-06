# Sprint 3 §7.3 (QA-ACC-3, written for ST-047; FR-103, NFR-038). Owner: senior-qa-engineer.
# API binding: backend/tests/features/test_metric_evidence.py. Browser bindings:
# web/e2e/sprint-03/journey-v2.spec.ts (E2E-03-01) and evidence-crawl.spec.ts (E2E-03-02).
@M0 @story-ST-047 @nfr-038 @analytics @needs-verification
Feature: Evidence behind a metric
  Scenario: Show me the rallies
    Given Ivy's stats show "Rallies won on serve" with "n = 7"
    When she opens "Show me" on it
    Then she sees the 7 rallies her side served, each with a link that plays it

  Scenario: More than ten rallies
    Given a stat is based on 23 rallies
    When Ivy opens "Show me" on it
    Then she sees 10 rallies and "See all 23"

  Scenario: Every number can be checked
    When Ivy opens her stats
    Then every stat shows its sample size and a working "Show me"
