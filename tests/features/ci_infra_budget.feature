# Sprint 4, ticket CI-INFRA-BUDGET (sre-devops-engineer). Written before the fix.
# Binding: infra/tests/test_ci_infra_budget_scenarios.py (reads the real ci.yml, pyproject.toml and
# uv.lock; runs the real scripts/dev-objectstore.sh twice at once against a fake slow download).
# Incident: push CI on main 5bba847 (run 40908731812): infra-tests logged "1717 passed, 10 skipped
# in 581.90s" and was then cancelled by its 10-minute job timeout; ci-gate failed on
# "infra-tests: cancelled". The suite had crept up to its budget; nothing was failing.
@M0 @story-ST-002 @ticket-CI-INFRA-BUDGET
Feature: The infra test job finishes well inside its time budget

  Rule: The infra suite runs in parallel without dropping a test

    Scenario: The infra job runs its pytest suite on every runner core
      When the infra job's pytest command is read from the CI workflow
      Then it runs with "-n auto" and distributes whole test files with "--dist loadfile"
      And it still selects the tests marked "unit or integration"

    Scenario: pytest-xdist is a locked dev dependency of the infra suite
      Then "pytest-xdist" is a dev dependency in infra/pyproject.toml and pinned in infra/uv.lock

    Scenario: The job timeout is headroom, not the fix
      Then the infra job's timeout is between 10 and 15 minutes

  Rule: Parallel workers never share a half-written file

    Scenario: Two first starts of the dev object store download SeaweedFS one at a time
      Given an empty SeaweedFS download cache and a slow download
      When two test workers start the dev object store at the same time
      Then the two downloads never overlap
