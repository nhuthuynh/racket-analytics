# Sprint 4 ST-072b-part2 (FR-160; NFR-023; flows-sprint-04 §7 Q-10; interim-wording-sprint-04 §5).
# Bound in web/tests/features/storage-full-messages.test.tsx: the real U-01 (MatchUpload) with the
# API refusal of api-sprint-04 §7. Flag-on E2E: E2E-04-08 storage (storage-full.spec.ts). The
# match-limit half is ST-072b.
@M5 @story-ST-072b @matches @web
Feature: The player is told how much storage they use when a video does not fit
  With quotas on, the API refuses a video that does not fit in the player's storage. The player
  sees how much storage is used, in plain words. With quotas off, nothing new is shown.

  Rule: A video that does not fit says how much storage is used

    Scenario: A storage refusal without usage numbers still gets a safe message
      Given the API refuses the upload with "storage_quota_exceeded" and no usage
      When the upload starts
      Then the alert says "This video won't fit in your storage."
      And the alert links to "/matches"

    Scenario: A storage refusal says how much of the storage is used
      Given the API refuses the upload with "storage_quota_exceeded", 18.2 of 20 GB used
      When the upload starts
      Then the alert says "You have used 18.2 of 20 GB."
      And the alert says "Nothing from this file was saved."

  Rule: With quotas off, today's messages stay

    Scenario: Quotas off: today's unfinished-upload refusal is unchanged
      Given the API refuses the upload with "upload_quota_exceeded" and no usage
      When the upload starts
      Then the alert says "You have too many unfinished uploads."
      And the alert does not say "storage"
