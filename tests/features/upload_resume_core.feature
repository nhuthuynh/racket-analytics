# Sprint 0 §7. Owner: senior-qa-engineer. Written before implementation (ST-012).
# Steps: backend/tests/features/test_upload_resume_core.py
# Regression suite: backend/tests/regression/test_upload_resume.py (IT-00-07).
@M0 @story-ST-008 @nfr-026
Feature: Resumable upload protocol core
  Uploads follow tus 1.0.0 so that a client can always find where to resume.

  Rule: The server reports the stored offset and refuses mismatched chunks

    Scenario: Resume from the server's offset
      Given Ivy has started an upload and the server has stored 40% of it
      When her client asks the server for the current offset
      Then the server reports the offset at 40%
      And sending the rest from that offset completes the upload

    Scenario: Chunk sent from the wrong offset
      Given the server has stored 40% of Ivy's upload
      When her client sends a chunk that starts at 30%
      Then the chunk is refused as a conflict
      And the stored upload is still at 40%

    Scenario: Stored names never come from the user's file name
      Given Ivy uploads a file named "../../etc/passwd.mp4"
      When the upload completes
      Then the stored object name contains none of the original file name
