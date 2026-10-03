# Sprint 0 §7. Owner: senior-qa-engineer. Written before implementation (ST-012).
# Steps: backend/tests/features/test_walking_skeleton.py (API level).
# UI level: web/e2e/walking-skeleton.spec.ts (E2E-00-01).
@M0 @story-ST-008 @story-ST-009 @story-ST-010
Feature: Walking skeleton from upload to media facts
  A signed-in player can upload a match video and see what the system learned about the file.

  Background:
    Given Ivy is signed in

  Rule: A completed upload is probed and its facts are shown on the match

    Scenario: Upload the fixture clip and see its facts
      Given Ivy has created a match called "Skeleton test"
      When she uploads the 60-second synthetic fixture clip to that match
      Then the match shows the status "Video received"
      And the match shows duration "1:00", frame rate "60 fps" and resolution "1920×1080"

    Scenario: No probing before the upload is complete
      Given Ivy's upload to match "Skeleton test" is 50% done
      When she opens the match
      Then the match shows the status "Uploading"
      And no media facts are shown
