# QA-VERIFY04R3-01 (FR-124 "Not for me", FR-141; QD-DR-05; G04-01 step 9). Owner: pickleball-domain-coach.
# CLI binding: backend/tests/features/test_drill_coverage_solo_wall.py (racket-drill-coverage over a
# copy of content/drills and over content/drills). Negative scenario first.
@needs-verification @story-QA-VERIFY04R3-01 @fr-124 @fr-141
Feature: Drill coverage for a player alone with a wall
  A player alone with a wall must always have a second drill to swap to.

  Scenario: Only one solo wall drill for a metric
    Given a drill library where pb.drive.wall-margin is the only solo wall drill for AN-04
    When the coverage check runs
    Then it fails and names the cell "AN-04 × intermediate × solo+wall: drills: 1"

  Scenario: Starter library for a solo wall player
    Given the starter drill library
    When the coverage check runs
    Then every target has at least 2 solo wall drills at intermediate
