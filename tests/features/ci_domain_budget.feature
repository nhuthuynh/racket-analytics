@nfr-073 @ci-domain-budget
Feature: The domain unit suite runs inside its 10 s budget with margin, on the same selection
  NFR-073 gives the "rules + domain" unit suite (CI's DOMAIN_TEST_PATHS) 10 s of wall time,
  measured by run_with_budget.py from interpreter start to exit. Main runs 37882972340 and
  37918385248 were stopped at 10 s (exit 124) although every test passed: about 80% of the
  suite's time is Hypothesis example generation in some 30 property tests on the default
  profile, in one process. The suite runs in parallel test workers instead. The budget, the
  test selection and the Hypothesis profile stay as they are (ci.yml guards:
  infra/tests/test_ci_domain_budget.py).

  Scenario: The domain step runs in parallel workers on the same tests with the same results
    Given the backend unit suite on CI's DOMAIN_TEST_PATHS
    When the budgeted domain step's command from ci.yml runs
    And the same selection runs in one process
    Then the step ran on more than one worker
    And both runs executed the same test ids with the same outcomes and none failed

  Scenario: A fresh checkout's Hypothesis cache is filled before the budget starts
    Given an empty Hypothesis storage directory, as on a fresh CI checkout
    When the Hypothesis cache warm-up step's command from ci.yml runs
    And the budgeted domain step's command from ci.yml runs
    Then the warm-up wrote at least 90% of the constants cache entries the domain run reads
