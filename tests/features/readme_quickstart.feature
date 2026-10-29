# Sprint 4, ticket ST-066 (sre-devops-engineer; QD §7; goal G04-06).
# Binding: infra/tests/test_readme_quickstart_walkthrough_scenarios.py, running the real
# scripts/ci/check_readme_quickstart.py. A new file beside readme_quick_start.feature (MVP-01),
# which is protected (decisions ST-066 row 1).
@M4 @ticket-ST-066
Feature: The README walks a player through the prototype, and the checker holds it to that

  Scenario: A missing walkthrough step fails the checker
    Given a README whose "Try the prototype" walkthrough leaves out "Not for me"
    When the quick-start check runs on it
    Then it fails naming "Not for me"

  Scenario: A quick start without the walkthrough fails the checker
    Given a README whose "Run it locally" section has no "Try the prototype" walkthrough
    When the quick-start check runs on it
    Then it fails naming "Try the prototype"

  Scenario: The repository README walks through the whole prototype
    Given the repository README
    When the quick-start check runs on it
    Then it passes
    And the walkthrough names, in order, "make up", "make demo", "/stats", "/plan", "Why", "Show me", "Mark done", "Not for me" and "make down"
