# Sprint 0 §7. Owner: senior-qa-engineer. Written before implementation (ST-012).
# Steps: backend/tests/features/test_job_resilience.py
# Regression suites: backend/tests/regression/test_worker_crash.py (IT-00-04),
#                    backend/tests/regression/test_fail_closed.py (IT-00-05).
@M0 @story-ST-007 @nfr-046 @nfr-047
Feature: Analysis jobs survive worker failure without leaving partial results
  Workers are disposable; jobs are idempotent and fail closed.

  Rule: A job interrupted by a worker shutdown is retried exactly once more

    Scenario: Worker stops in the middle of probing
      Given a probe job is running for Ivy's match
      When the worker is told to shut down
      Then the job is back in the queue within 10 seconds
      And after it runs again the match has exactly one set of media facts

  Rule: A failing stage leaves nothing behind

    Scenario: Probe stage fails after writing part of its result
      Given the probe stage will fail after writing part of its result
      When the job runs
      Then the job is marked failed
      And the match shows no media facts
      And the match shows "We could not read this video"
