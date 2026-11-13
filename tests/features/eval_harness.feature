# Sprint 6 ST-176a (story ST-176 CV readiness; NFR-006.7, SPK-1.2; ADR 0060). Owner:
# senior-ml-cv-engineer. Written before implementation.
# Steps: backend/tests/features/test_eval_harness.py (runs scripts/eval/run_eval.py as a reviewer
# would, on the committed phone-profile fixtures and fixtures/evals/dry-run-v1 inputs).
# Footage-free: the metric values are synthetic inputs; no CV story becomes Ready from this.
@story-ST-176 @nfr-006
Feature: The eval harness judges a model run against ADR 0060, row by row

  Rule: A report gives candidate, baseline, delta and pass/fail for every ADR 0060 row

    Scenario: Dry-run on the phone fixtures passes and writes a full report
      Given the dry-run candidate and baseline for gold set "dry-run-synthetic" version 1
      And the phone-profile fixture clips
      When the eval harness runs
      Then it exits with code 0
      And the report has a row for each of M1 to M11 with candidate, baseline, delta and verdict
      And the report names the gold-set version, the weights hash and licence, and the config
      And the report gives a CPU-seconds per match-minute value above zero

  Rule: Any one metric outside its tolerance fails the run

    Scenario: A planted regression fails with code 1
      Given the planted-regression candidate and the dry-run baseline
      And the phone-profile fixture clips
      When the eval harness runs
      Then it exits with code 1
      And the report marks M1 and M7 as "fail" and every other measured row as "pass"

  Rule: A candidate is never compared across gold-set versions

    Scenario: A baseline from another gold-set version is refused
      Given the dry-run candidate and a baseline for gold set "dry-run-synthetic" version 2
      And the phone-profile fixture clips
      When the eval harness runs
      Then it exits with code 2
      And no report is written

  Rule: A candidate is never compared with a baseline run under another config

    Scenario: A baseline run with another config is refused
      Given the dry-run baseline and a candidate with ball_px_threshold 20 and rally_match_window_s 5.0
      And the phone-profile fixture clips
      When the eval harness runs
      Then it exits with code 2
      And no report is written because the config differs
