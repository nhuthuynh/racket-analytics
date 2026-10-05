# Sprint 1 §7.5 + §14.3.6 (ST-018). Owner: senior-qa-engineer. Written before implementation.
# Bindings: API level backend/tests/features/test_upload_validation.py (every scenario, against
# the match read model: rejection codes map to the U-03 copy); browser level
# web/e2e/sprint-01/upload-validation.spec.ts (the copy on U-03). IT-01-09 is the regression form.
@M0 @story-ST-018 @nfr-053
Feature: Upload validation
  Rule: Only real video files within the caps are accepted

    Scenario Outline: Reject invalid files
      Given Ivy selects <file>
      When she starts the upload
      Then she sees "There is a problem" with "<message>"
      And no match video is stored from that file
      Examples:
        | file                                  | message                                      |
        | a PDF renamed to match.mp4            | This file is not a video we can read         |
        | a program renamed to match.mov        | This file is not a video we can read         |
        | a 12 GB video                         | Videos must be 10 GB or smaller              |
        | a 4-hour video                        | Videos must be 2 hours 30 minutes or shorter |

    Scenario: A valid phone video is accepted
      Given Ivy selects a 1080p 60 fps MP4 recorded on a phone
      When the upload completes
      Then the match shows the status "Video received"

  Rule: Oversized files are refused before any data is stored

    Scenario: Declared size above the cap
      Given Ivy starts an upload that declares 12 GB
      When the server receives the upload request
      Then the upload is refused with "Videos must be 10 GB or smaller"
      And no bytes of that file are stored

  Rule: A refused file starts no work

    Scenario: No video check for a refused file
      Given Ivy's file was refused as "This file is not a video we can read"
      When she opens the match
      Then the match shows "No video yet"
      And no video check was started for that file
