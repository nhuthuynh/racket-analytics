# Sprint 5 CI-NIGHTLY-PERF (story "CI first"; NFR-010 dashboard, NFR-013; analytics-snapshots.md
# §4.2): reading the stats or the evidence of a match again while its scorebook did not change
# reuses the projected sheet; a correction shows in the next read. Root cause of the nightly
# 50 RPS miss of run 43007950254. Steps: backend/tests/features/test_stats_read_cost.py.
@M5 @story-CI-NIGHTLY-PERF @analytics
Feature: Reading the dashboard again is cheap and never out of date
  A player keeps her match dashboard open while she corrects rallies. While the match did not
  change, the stats and the "Show me" evidence are read without replaying its scorebook; a
  correction shows in the next read.

  Rule: A change of the match is read live

    Scenario: A correction after a read shows in the next stats read
      Given "ivy" has tagged the worked example
      And "ivy" has read the stats of the match
      When "ivy" corrects rally 3 of the match
      And "ivy" reads the stats of the match
      Then the stats read are the corrected worked example

  Rule: An unchanged match is not replayed

    Scenario: Reading the stats and the evidence again replays no scorebook
      Given "ivy" has tagged the worked example
      And "ivy" has read the stats of the match
      When "ivy" reads the stats and the evidence of the match
      Then the reads replayed no scorebook and wrote nothing
