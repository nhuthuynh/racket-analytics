# Sprint 3 rule L11 (QA-FUZZ-3; testing-strategy §L11, NFR-023, NFR-058). Owner: senior-qa-engineer.
# API binding: backend/tests/features/test_json_fuzz_sprint_03.py. The full fuzz (every new
# string field, Hypothesis, any JSON value, the Full Tag label bodies) is IT-03-12.
@M0 @story-ST-050 @nfr-023 @nfr-058
Feature: Hidden characters and races on the Sprint 3 delete routes
  Rule: A confirmation with a hidden character is not a confirmation

    Scenario Outline: A delete confirmation with a hidden character is refused
      Given Ivy has a match with a received video
      When she deletes it typing "delete" with <character> inside
      Then she is told the deletion is not confirmed
      And her match is unchanged

      Examples:
        | character          |
        | a NUL              |
        | a lone surrogate   |
        | a line separator   |

  Rule: A delete racing a tag ends in one consistent outcome

    Scenario: A delete and a tag at the same moment
      Given Ivy has a match ready to tag
      When she tags a rally and deletes the match at the same moment
      Then the delete succeeds
      And nothing of the match can be read any more
