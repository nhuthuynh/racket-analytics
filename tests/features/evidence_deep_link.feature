# Sprint 2 §7.6 and §14.3.6 (QA-ACC, written for ST-037). Owner: senior-qa-engineer.
# API binding: backend/tests/features/test_evidence_deep_link.py (the link's start, expiry and
# signature). Browser binding: web/e2e/sprint-02/rally-video.spec.ts (E2E-02-04, the video
# playing from the rally). The plan's "14:32" is moved to 0:56: the fixture video is 60 s long (QA-S2-API-02).
@M0 @story-ST-037 @nfr-014 @nfr-055
Feature: Jump to the video moment
  Rule: Every rally row opens the video at that rally

    Scenario: Open a rally from the score sheet
      Given Ivy's score sheet lists rally 12 starting at 0:56
      When she opens rally 12's video link
      Then the video plays from 0:56

    Scenario: An old video link stops working
      Given Ivy copied a video link from her score sheet 20 minutes ago
      When the link is opened
      Then the video does not play
      And reopening rally 12 from the score sheet still works

    Scenario: 14.3.6 A changed video link is refused
      Given Ivy has a video link for rally 3
      When the link is changed by hand
      Then the video does not play
