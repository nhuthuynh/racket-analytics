# Sprint 4 fix wave, ticket SRE-VERIFY04R3-03 (sre-devops-engineer). Written before the fix.
# Binding: infra/tests/test_coaching_quality_gates_scenarios.py (reads the real ci.yml and
# nightly-quality.yml, runs the real scripts/ci/mutation_score.py and nightly_status.py and the
# real backend unit tests). Retro action C5 / finding M7: sprint-04 §8 planned two gates that no
# ticket wired, so `coaching/plan` at 0.6753 surfaced only at VERIFY-04-r3.
@nfr-072 @nfr-073 @coaching-gates
Feature: The coaching quality gates of sprint-04 §8 run in CI and in the nightly job
  Sprint-04 §8: mutation on `coaching/plan` and `coaching/weakness` >= 0.80 (nightly and
  VERIFY-04), and the domain suite (CI's DOMAIN_TEST_PATHS, < 10 s) gains tests/unit/coaching.
  The coaching property tests keep >= 1,000 examples in CI's property step (ST-004).

  Scenario: A coaching target below 0.80 fails the nightly job and the status file says so
    Given mutation results of 0.79 for coaching/plan and 0.81 for coaching/weakness
    When each coaching mutation command from nightly-quality.yml scores its result
    And the publish step's command writes the results into a sprint status file
    Then the coaching/plan command failed and the coaching/weakness command passed
    And the status file shows coaching/plan failed and coaching/weakness passed against 0.80

  Scenario: The budgeted domain step selects the coaching unit tests
    Given CI's DOMAIN_TEST_PATHS
    When the budgeted domain step's command from ci.yml collects its tests
    Then the coaching unit tests are among them

  Scenario: The coaching property tests draw at least 1,000 examples in CI's property step
    Given the property step from ci.yml on the Hypothesis ci profile
    When it runs the coaching property tests
    Then each of them passed at least 1,000 examples
