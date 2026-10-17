# Sprint 4 §3.7 ST-059 (FR-141; QD-DR-05; drill-review-checklist §3). Owner: senior-qa-engineer.
# CLI binding: backend/tests/features/test_drill_coverage.py (racket-drill-coverage over
# backend/tests/fixtures/drills-coverage-gap/ and content/drills). Negative scenario first.
@needs-verification @M5 @story-ST-059 @fr-141
Feature: Drill coverage
  Scenario: Missing coverage cell
    Given no reviewed drill targets AN-05 for beginners with 2 or fewer players
    When the coverage check runs
    Then it fails and names the empty cell

  Scenario: Starter library
    Given the starter drill library
    When the coverage check runs
    Then it passes and prints the matrix
