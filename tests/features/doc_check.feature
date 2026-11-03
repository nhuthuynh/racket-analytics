# CI-DOC-CHECK (PRC-05, PRC-3.1-3.4; ADR 0056): scripts/ci/check_docs.py, the ci.yml doc-check job.
Feature: The doc-check job refuses documentation that points at nothing
  As a reviewer of a tier 0 documentation PR
  I want repo paths, research citations, agent front matter and decider cells checked by a tool
  So that a docs-only change cannot merge with a dangling reference on paper only

  Background:
    Given a clone of the repository at its current commit

  Rule: Each planted break turns the check red

    Scenario: A dangling repo path in a changed Markdown file is refused
      Given a changed Markdown file that names "scripts/ci/no_such_tool.py"
      When doc-check runs on the change
      Then doc-check exits 1 with "FAIL path"

    Scenario: A citation of a source that is not Confirmed and not marked is refused
      Given a changed Markdown file that cites "[ASB/ANT-03]"
      When doc-check runs on the change
      Then doc-check exits 1 with "FAIL citation"

    Scenario: An agent file whose front matter lacks its tools line is refused
      Given the agent file "sre-devops-engineer" without its tools line
      When doc-check runs on the change
      Then doc-check exits 1 with "FAIL front-matter"

    Scenario: The current sprint's flows file with a pending decider cell is refused
      Given the current sprint's flows file with a pending decider cell
      When doc-check runs on the change
      Then doc-check exits 1 with "FAIL flows"

  Rule: A clean change on the real repository passes inside the runtime budget

    Scenario: Every agent file edited with a Confirmed citation and an existing path passes
      Given every agent file gains a line citing "[ASB/ANT-01]" and naming "scripts/ci/merge_ready.py"
      When doc-check runs on the change
      Then doc-check exits 0 with "0 problem(s)"
      And doc-check took less than 60 seconds
