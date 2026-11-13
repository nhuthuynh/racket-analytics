# QA-WIP-GATE (story PRC-06; atomic item PRC-12.1; goal metric G06-10; ADR 0056 decision 3;
# working-agreement §3 "Flow and WIP limits"). Owner: senior-qa-engineer. Written before
# implementation. Binding: infra/tests/test_wip_gate_scenarios.py runs
# scripts/measure/wip_gate.py over HTTP against the local GitHub REST stub
# (infra/tests/wip_stub.py).
@ticket-QA-WIP-GATE
Feature: A ticket start is refused while a stage is full
  Rule: the stage counts come from the GitHub REST API; a start must not push "in progress"
        over 4, and no ticket starts while in review (3), awaiting QA (2) or awaiting merge (1)
        is full

    Scenario: A fourth start is refused while three PRs are in review
      Given 3 ticket PRs are in review
      When the orchestrator asks to start a ticket
      Then the start is refused, naming "in review"

    Scenario: A start is allowed while every stage has room
      Given 2 ticket PRs are in review
      And 1 ticket PR is in progress
      When the orchestrator asks to start a ticket
      Then the start is allowed
      And the stage counts read "In progress 1 · in review 2 · awaiting QA 0 · awaiting merge 0"

    Scenario: GitHub cannot be read
      Given the GitHub API fails
      When the orchestrator asks to start a ticket
      Then the start is refused as unknown
