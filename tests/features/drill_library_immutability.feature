# ST-053 review round 1 (PE-R1-ST053-01; FR-140 "deprecated, never deleted; edits bump the
# version"; QD-DR-02). Owner: senior-ml-cv-engineer (ST-053), next to QA's drill_library.feature.
# CLI binding: backend/tests/features/test_drill_library_immutability.py (racket-drill-lint over
# a copy of content/drills, with the library's own lock as the base branch's lock).
@M5 @story-ST-053 @fr-140
Feature: Drill library immutability against the base branch
  Scenario: A pull request deletes a drill version and its lock line
    Given the base branch locks the drill library
    And the pull request deletes "pb.fixture.drop-ladder" version 1 and its lock line
    When the library is validated against the base branch
    Then validation fails naming "pb.fixture.drop-ladder" and "deleted drill"
    And validation fails naming "pb.fixture.drop-ladder" and "lock entry removed"

  Scenario: A pull request edits a drill in place and rewrites its lock line
    Given the base branch locks the drill library
    And the pull request edits "pb.fixture.drop-ladder" version 3 in place and rewrites its lock line
    When the library is validated against the base branch
    Then validation fails naming "pb.fixture.drop-ladder" and "edited without version bump"
    And validation fails naming "pb.fixture.drop-ladder" and "lock entry changed"

  Scenario: A pull request adds a new drill version and locks it
    Given the base branch locks the drill library
    And the pull request adds "pb.fixture.drop-ladder" version 4 and locks it
    When the library is validated against the base branch
    Then validation passes
