# Sprint 5 ST-074 (story ST-074 "R1 reads stay fast under load", P1). Owner: senior-backend-engineer.
# Written before implementation (sprint-05 §7). Steps: infra/tests/test_r1_read_latency_scenarios.py
# runs scripts/ci/perf_verdict.py as the nightly perf-r1 job does (--per-endpoint
# match,score-sheet,dashboard,plan) on Locust 2.46.7 stats files of the R1 run.
@story-ST-074 @nfr-010
Feature: R1 reads meet latency at 50 RPS

  Rule: NFR-010.7 GET /me/plan p95 ≤ 300 ms

    Example: verdict passes on a run within target
      Given an R1 run in which every read has p95 120 ms and p99 400 ms
      When the R1 verdict is taken per endpoint
      Then the R1 verdict passes for match, score-sheet, dashboard and plan

    Example: verdict fails naming "plan" when p95 is 301 ms
      Given an R1 run in which the "plan" read has p95 301 ms
      When the R1 verdict is taken per endpoint
      Then the R1 verdict fails
      And the failure names the "plan" endpoint and no other

  Rule: NFR-010.9 errors under the same load ≤ 0.5 %

    Example: 15 failed requests of 3,000 (0.5 %) pass
      Given an R1 run in which the "match" read has 15 failed requests of 3000
      When the R1 verdict is taken per endpoint
      Then the R1 verdict passes for match, score-sheet, dashboard and plan

    Example: 16 failed requests of 3,000 (0.53 %) fail
      Given an R1 run in which the "match" read has 16 failed requests of 3000
      When the R1 verdict is taken per endpoint
      Then the R1 verdict fails
      And the failure names the "match" endpoint and no other

  Rule: the warm-up is excluded and the run must reach 49.5 RPS, else it is not a pass

    Example: a run whose statistics were never reset after the warm-up fails
      Given an R1 run in which every read has p95 120 ms and p99 400 ms
      And the run's statistics were never reset after the warm-up
      When the R1 verdict is taken per endpoint
      Then the R1 verdict fails on the "warmup_excluded" check

    Example: a run at 49 RPS fails
      Given an R1 run in which every read has p95 120 ms and p99 400 ms
      And the measured window ran at 49 RPS
      When the R1 verdict is taken per endpoint
      Then the R1 verdict fails on the "achieved_rps" check
