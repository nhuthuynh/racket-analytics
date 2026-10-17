# Sprint 4 C4-LOCUST (ST-054 SRE half). Owner: sre-devops-engineer. Written before implementation.
# A new file next to ci_perf_gates.feature (accepted Sprint 3 scenarios stay unchanged; the
# test-immutability gate protects them). Steps: backend/tests/features/test_ci_perf_stats_gates.py
# runs scripts/ci/perf_verdict.py as the perf-baseline job does, on the Locust 2.46.7 stats
# fixtures in infra/tests/fixtures/perf/. The workflow wiring is checked by infra/tests.
@story-ST-054 @nfr-010 @nfr-041
Feature: CI performance gates hold the dashboard reads to their latency and availability targets

  Rule: GET stats and GET evidence are gated per route at p95 300 ms, p99 800 ms and 99.5% availability

    Scenario: A stats read over the latency threshold fails the gate
      Given the Locust stats file "stats_reads_p95_over_stats.csv"
      When the performance verdict is taken with the stats and evidence reads gated
      Then the "dashboard_p95" gate fails on the "stats" route
      And the performance verdict fails

    Scenario: Stats read latency gate
      Given the Locust stats file "stats_reads_ok_stats.csv"
      When the performance verdict is taken with the stats and evidence reads gated
      Then every dashboard read gate passes
      And the "stats" route is reported with p95 120 ms and p99 400 ms
