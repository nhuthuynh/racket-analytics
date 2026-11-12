@nfr-073 @ci-domain-budget
Feature: Domain workers keep start-up and collection objects out of the cyclic garbage collector
  Main run 43281846173 (1c3b648) stopped the domain unit suite at its 10 s budget (exit 124) with
  no domain test changed; the previous main run passed in 9.9 s. In each xdist worker the cyclic
  garbage collector spent 0.8-1.0 s of CPU re-scanning the ~220,000 objects that start-up and
  collection create and that live until the worker exits, five of those full scans at exit while
  the controller waits for the slowest worker. The backend's root conftest freezes those objects
  once collection ends. Budget, selection, Hypothesis profile and examples are unchanged
  (infra/tests/test_ci_domain_budget.py); objects a test creates are collected as before.

  Scenario: Each worker runs its tests with the start-up and collection objects frozen
    Given the backend unit suite on CI's DOMAIN_TEST_PATHS
    When the budgeted domain step's command from ci.yml runs with a garbage-collector probe
    Then every worker ran its tests with the collector on and its collected test modules frozen
    And no garbage that start-up or collection left behind is among the frozen objects
    And no test failed or errored in that run
