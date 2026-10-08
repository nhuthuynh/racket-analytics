# Sprint 3 §7.6 (QA-ACC-3, written for ST-052; FR-150, FR-151). Owner: senior-qa-engineer.
# API binding: backend/tests/features/test_full_tag.py. Browser binding:
# web/e2e/sprint-03/full-tag.spec.ts (E2E-03-05). Frame 1,840 is on the synthetic 60 s clip
# (3,600 frames); the plan's 18,402 is out of range there (decision-log 2026-10-06).
@M0 @story-ST-052 @fr-150
Feature: Full Tag
  Scenario: Labeller tags a hit
    Given a labeller is stepping frame by frame through a consented match
    When they tag a hit by player B1 at frame 1,840
    Then the exported label file contains that hit with its frame and player

  Scenario: Player cannot open Full Tag
    Given Ivy has a normal player account
    Then the Full Tag mode is not available to her

  Scenario: Match without consent
    Given a labeller opens a match that has no consent record
    Then they are told the match cannot be labelled
