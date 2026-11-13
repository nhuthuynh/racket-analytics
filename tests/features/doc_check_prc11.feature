# CI-DOC-CHECK-06 (PRC-06, PRC-11.1-11.3; ADR 0056 required ticket b, extended):
# scripts/ci/check_docs.py (doc-check job) and scripts/ci/check_cost_table.py (pr-policy job).
Feature: Reference citations, threat notes and cost tables are checked by a tool
  As a reviewer of a Sprint 6 ticket PR
  I want reference citations, the newest threat notes and the cost-per-PR table checked in CI
  So that an unresolved source, a broken threat row or a missing cost record cannot merge

  Background:
    Given a clone of the repository at its current commit

  Rule: doc-check refuses a reference entry whose citation id is not a sources register row

    Scenario: A reference entry citing an unknown source id is refused
      Given a reference set file whose entry cites "SRC-9999"
      When doc-check runs on the change
      Then doc-check exits 1 with "FAIL reference"

    Scenario: A reference entry citing a sources register row passes
      Given a reference set file whose entry cites "SRC-0001"
      When doc-check runs on the change
      Then doc-check exits 0 with "0 problem(s)"

  Rule: doc-check runs the threat-notes checker on the newest threat notes

    Scenario: The newest threat notes with a threat row lacking its status are refused
      Given the newest threat notes gain a threat row with an empty status cell
      When doc-check runs on the change
      Then doc-check exits 1 with "FAIL threat-notes"

    Scenario: The repository's newest threat notes pass as they are
      Given a changed Markdown file with no references
      When doc-check runs on the change
      Then doc-check exits 0 with "threat-notes: docs/security/threat-notes-sprint-"

  Rule: pr-policy refuses a ready ticket PR whose decisions file has no cost per PR table

    Scenario: A ticket whose decisions file has no cost table is refused
      Given the decisions file of ticket "PLANTED-1" without a cost per PR table
      When the cost-table check runs for the PR title "[PLANTED-1] planted ticket"
      Then the cost-table check exits 1 with "FAIL cost-table"

    Scenario: A ticket whose decisions file has a cost row passes
      Given the decisions file of ticket "PLANTED-2" with a cost per PR row
      When the cost-table check runs for the PR title "[PLANTED-2] planted ticket"
      Then the cost-table check exits 0 with "1 row(s)"
