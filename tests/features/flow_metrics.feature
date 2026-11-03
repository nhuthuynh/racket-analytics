# QA-FLOW-METRICS (story PRC-05; atomic items PRC-5.1-5.5; goal metric G05-11; ADR 0056
# decisions 1 and 3). Owner: senior-qa-engineer. Written before implementation. Binding:
# infra/tests/test_flow_metrics_scenarios.py runs scripts/measure/flow_metrics.py over HTTP
# against the local GitHub REST stub (infra/tests/flow_stub.py).
@ticket-QA-FLOW-METRICS
Feature: Flow and cost per PR are measured from the REST API and the decisions files
  Rule: the values are reported, never targets; the run is complete only when every merged
        ticket's decisions file carries a cost-per-PR table

    Scenario: A pull request closed without a merge is not throughput
      Given a ticket PR merged into main with a cost table in its decisions file
      And a ticket PR closed without a merge
      When the flow metrics are measured
      Then throughput is 1
      And the measurement is complete

    Scenario: A merged ticket without a cost table makes the measurement incomplete
      Given a ticket PR merged into main whose decisions file has no cost table
      When the flow metrics are measured
      Then the measurement is incomplete, naming "T-1"

    Scenario: A stage count above its WIP limit is a breach
      Given a ticket PR merged into main with a cost table in its decisions file
      And a decisions file records "In progress 5 · in review 0 · awaiting QA 0 · awaiting merge 0"
      When the flow metrics are measured
      Then 1 WIP breach is reported for "in progress"

    Scenario: GitHub cannot be read
      Given the GitHub API fails
      When the flow metrics are measured
      Then the measurement is unknown
