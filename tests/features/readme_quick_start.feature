# Sprint 3, ticket MVP-01 (sre-devops-engineer; PO MVP goal 2026-10-15).
# Binding: infra/tests/test_readme_quick_start_scenarios.py. Checker: scripts/ci/check_readme_quickstart.py.
# The README's "Run it locally" section must only name commands and settings the repo really has.
@M3 @ticket-MVP-01
Feature: A new developer can run the app locally from the README alone

  Scenario: A quick start naming a make target the Makefile lacks is rejected
    Given a README whose "Run it locally" section says "make launch"
    When the quick-start check runs
    Then it fails naming "make launch"

  Scenario: A quick start without its own section is rejected
    Given a README with no "Run it locally" section
    When the quick-start check runs
    Then it fails naming "Run it locally"

  Scenario: The repository README's quick start names only real commands and settings
    Given the repository README
    When the quick-start check runs
    Then it passes
    And the section names the commands "make up", "make demo", "make ps", "make logs" and "make down"
    And the section names the addresses "https://localhost:3000" and "http://localhost:8025"
    And the section names the mirror setting "DOCKERHUB_REGISTRY=mirror.gcr.io"
