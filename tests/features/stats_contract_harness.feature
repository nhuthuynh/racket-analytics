# Sprint 3 PE-DESIGN-3 (PE-1, PE-R1S3-02; ADR 0033 rule 2): the goal harness
# (scripts/measure/statscontract.py) mirrors docs/architecture/api-sprint-03.md, so a contract
# change and the harness move in the same commit. Steps: infra/tests/test_stats_contract_harness_scenarios.py.
@story-PE-DESIGN-3
Feature: The goal harness judges the live stack by the api-sprint-03 contract

  Rule: A deletion succeeds only with 202 Accepted (api-sprint-03 §4.1, §4.2)

    Scenario: An account deletion answered 204 fails step 8, naming the status
      Given the harness built from the contract
      When DELETE /me answers 204 and signing in again gives a new, empty account
      Then the account deletion step fails, naming "DELETE /me status 204"

    Scenario: An account deletion answered 202 passes step 8
      Given the harness built from the contract
      When DELETE /me answers 202 and signing in again gives a new, empty account
      Then the account deletion step passes

  Rule: The harness names the contract's purge job and label routes (§4.4, §5.2)

    Scenario: The harness runs the contract's purge command in the contract's service
      Given the harness built from the contract
      Then the harness purge command and service are the ones api-sprint-03 §4.4 names
      And the harness label routes are exactly the ones api-sprint-03 §5.2 lists
