# Sprint 4, ST-069 (FR-008; OQ-07 accepted, ADR 0023; ADR 0006, ADR 0042; api-sprint-04 §5;
# SEC-4 T4-RT-1..T4-RT-4). Steps: backend/tests/features/test_video_retention.py.
# Negative case first: with the flag off this rule deletes nothing.
@story-ST-069
Feature: The review video is kept for the time the player chose, then deleted; stats stay

  Scenario: Flag off keeps the video
    Given the retention setting is off
    And Ivy has a tagged match whose video was analysed
    When the purge runs 400 days later
    Then Ivy's review video is still stored
    And the match shows no deletion date
    And the retention setting is not found

  Scenario: Retention period passes
    Given the retention setting is on
    And Ivy has a tagged match whose video was analysed
    And Ivy keeps review video for 30 days
    Then the match shows the deletion date 30 days after the analysis
    When the purge runs 31 days later
    Then Ivy's review video is gone
    And the stats and the score sheet of the match are still there

  Scenario: Another player's choice does not shorten mine
    Given the retention setting is on
    And Ivy has a tagged match whose video was analysed
    And Carlos has a tagged match whose video was analysed
    And Ivy keeps review video for 30 days
    And Carlos keeps review video for 365 days
    When the purge runs 31 days later
    Then Ivy's review video is gone
    And Carlos's review video is still stored
