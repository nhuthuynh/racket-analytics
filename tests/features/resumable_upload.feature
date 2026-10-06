# Sprint 1 §7.4 + §14.3.5 (ST-017). Owner: senior-qa-engineer. Written before implementation.
# Bindings: API level backend/tests/features/test_resumable_upload.py ("A damaged chunk is not
# kept", "The unfinished upload has expired", "Carlos tries to send data to Ivy's upload",
# "A different file is chosen to resume"; IT-01-06..08); browser level
# web/e2e/sprint-01/resumable-upload.spec.ts (all scenarios; E2E-01-02).
@M0 @story-ST-017 @nfr-026
Feature: Resumable upload
  Rule: An interrupted upload continues from where the server stopped

    Scenario: Connection drops mid-upload
      Given Ivy is uploading a 3 GB video and 40% has been sent
      When her connection drops for 2 minutes and returns
      Then the upload continues from at least 40%
      And she sees the state change from "Paused: waiting for connection" to "Uploading"

    Scenario: Return after closing the tab
      Given Ivy closed the tab when her upload was 64% done
      When she opens the app again within 24 hours
      Then she is offered to resume from 64%

    Scenario: A damaged chunk is not kept
      Given Ivy's upload is at 40%
      When a chunk arrives that does not match its checksum
      Then the chunk is refused
      And the upload is still at 40%

  Rule: Progress is honest

    Scenario: Time estimate appears only after measuring
      Given Ivy has just started an upload
      When less than 10 seconds of transfer have been measured
      Then she sees the percentage and megabytes sent but no time estimate

  Rule: Resuming needs the same video

    Scenario: A different file is chosen to resume
      Given Ivy's upload of "Sat doubles.mp4" stopped at 64%
      When she chooses a different video to resume it
      Then she sees "This is not the same video"
      And the upload is still at 64%

    Scenario: The unfinished upload has expired
      Given Ivy's unfinished upload has passed its expiry time
      When she tries to resume it
      Then she is told the upload expired and must be started again

  Rule: Nobody else can continue my upload

    Scenario: Carlos tries to send data to Ivy's upload
      Given Ivy has an unfinished upload
      When Carlos sends a chunk to it
      Then Carlos gets the same "not found" result as for an upload that does not exist
      And Ivy's upload is unchanged

  Rule: The app never promises a background upload

    Scenario: Upload page wording
      Given Ivy is uploading a video
      Then the page does not say the upload continues after the tab is closed
