# Sprint 6 ST-173b (FR-173.R3; FR-173.R1). Owner: senior-backend-engineer; drills that close the
# cells: ST-173c (pickleball-domain-coach). CLI binding: backend/tests/features/
# test_drill_coverage_patterns.py (racket-drill-coverage --patterns over copies of content/drills).
# Negative scenario first.
@M5 @story-ST-173 @fr-173
Feature: Drill coverage for the rankable reference patterns
  Every ranked weakness needs a drill the plan can assign for the player's level, players and
  equipment, or the plan says "no exercise yet for this gap".

  Scenario: No solo wall drill for dink rally tolerance
    Given a drill library with no drill for AN-13 that 1 player can do at a wall
    When the pattern coverage check runs
    Then it fails and names the cell "AN-13 × intermediate × 1 player × wall: no fitting drill"

  Scenario: Every pattern cell has a fitting drill
    Given a drill library with a solo wall drill and a solo court drill for AN-09 and AN-13
    When the pattern coverage check runs
    Then it passes with a fitting drill in all 54 pattern cells
