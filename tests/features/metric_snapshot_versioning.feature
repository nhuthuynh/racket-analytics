# Sprint 3 ST-046a (FR-100, FR-101, NFR-075, ADR 0040, ADR 0041): the MetricSnapshot aggregate and its repository.
# Steps: backend/tests/features/test_metric_snapshot_versioning.py. The QA-ACC-3 acceptance
# scenarios over the stats route are stats_snapshot.feature (senior-qa-engineer).
# Scoring is PROVISIONAL-UNVERIFIED (ADR 0009, ADR 0023).
@M4 @story-ST-046 @fr-100 @nfr-075 @analytics @needs-verification
Feature: A match's starter stats are kept as one snapshot per dictionary and rules version
  A snapshot is a recomputable read model of the score sheet. It is keyed by the match, the
  metric dictionary version and the rules version, and only a newer sheet version replaces it.

  Rule: Only a newer sheet version replaces a stored snapshot

    Scenario: A late event with an older sheet version leaves the stored snapshot unchanged
      Given the snapshot of the worked-example game at sheet version 15 is stored
      When a snapshot of the same match at sheet version 14 is written
      Then nothing is written
      And the stored snapshot is at sheet version 15 with the stats of the worked-example game

    Scenario: The same sheet version written twice is written once
      Given the snapshot of the worked-example game at sheet version 15 is stored
      When a snapshot of the same match at sheet version 15 is written
      Then nothing is written
      And the stored snapshot is at sheet version 15 with the stats of the worked-example game

    Scenario: A newer sheet version replaces the stored snapshot
      Given the snapshot of the first 3 rallies at sheet version 3 is stored
      When the snapshot of the worked-example game at sheet version 15 is written
      Then the write is accepted
      And the stored snapshot is at sheet version 15 with the stats of the worked-example game

  Rule: A snapshot is versioned by the metric dictionary and the rules version

    Scenario: A dictionary without the interval-width rule builds no snapshot
      Given a metric dictionary without the low-sample interval-width rule
      When the snapshot of the worked-example game is computed
      Then the computation is refused naming "low_sample"

    Scenario: Each metric's flag uses that metric's own minimum sample
      Given a metric dictionary where AN-05 needs 30 rallies and the other proportions need 20
      When the snapshot of a match where side A serves and wins 25 rallies is stored
      Then the stored AN-05 of side A has n 25 and is low sample
      And the stored AN-01 of side A has n 25 and is not low sample
      And the published card of AN-05 shows a minimum sample of 30 rallies

    Scenario: A snapshot under another dictionary version is kept beside the first
      Given the snapshot of the worked-example game at sheet version 15 is stored
      When a snapshot of the same match under dictionary version "9.9.9" at sheet version 1 is written
      Then the write is accepted
      And the match has 2 stored snapshots
      And the snapshot keyed by the shipped dictionary and "PROVISIONAL-UNVERIFIED" is at sheet version 15
