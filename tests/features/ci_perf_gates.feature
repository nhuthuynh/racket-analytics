# Sprint 3 CI-PERF-GATES. Owner: sre-devops-engineer. Written before implementation.
# Steps: backend/tests/features/test_ci_perf_gates.py (runs scripts/ci/perf_verdict.py and
# scripts/ci/run_with_budget.py as CI does; the workflow wiring is checked by infra/tests).
@story-ST-039 @nfr-041 @nfr-013 @nfr-073
Feature: CI performance gates measure the product, not the runner

  Rule: The load-test rate is measured after warm-up, over at least 60 seconds

    Scenario: A slow start-up does not fail the rate gate
      Given a load test that starts up for 14 seconds with no load
      And then holds 51 requests per second for 76 seconds with all 51 users
      When the performance verdict is taken for 50 requests per second
      Then the achieved rate is 51 requests per second over a 76 second window
      And the rate gate passes

    Scenario: A slow steady state still fails the rate gate
      Given a load test that starts up for 2 seconds with no load
      And then holds 47 requests per second for 70 seconds with all 51 users
      When the performance verdict is taken for 50 requests per second
      Then the rate gate fails

    Scenario: A steady window shorter than 60 seconds fails
      Given a load test that starts up for 40 seconds with no load
      And then holds 51 requests per second for 50 seconds with all 51 users
      When the performance verdict is taken for 50 requests per second
      Then the measurement window gate fails

  Rule: The integration budget times the suite and records it

    Scenario: A suite that runs past its budget is stopped
      Given a suite that takes 5 seconds
      When it runs under a budget of 1 second
      Then it is stopped with exit code 124
      And the budget record says it was over budget

    Scenario: A suite within its budget records its wall time
      Given a suite that takes 0.2 seconds
      When it runs under a budget of 10 seconds
      Then it finishes with exit code 0
      And the budget record says it was within budget
