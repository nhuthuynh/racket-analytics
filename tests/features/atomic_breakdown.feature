# QA-DOR-CHECK (PRC-05, PRC-7.1; ADR 0056): scripts/ci/check_atomic_breakdown.py in the doc-check job.
Feature: The doc-check job refuses a requirements breakdown that is not atomic
  As the senior-qa-engineer who turns atomic items into tests
  I want the Definition of Ready "atomic breakdown" rules checked by a tool
  So that an NFR without a measurable method or an FR rule without a negative case cannot be pulled

  Background:
    Given a copy of the current sprint's requirements breakdown

  Rule: Each planted break turns the check red

    Scenario Outline: An NFR row with an empty attribute cell is refused
      Given the NFR row "NFR-041.3" with an empty "<column>" cell
      When the atomic-breakdown check runs on the copy
      Then the check exits 1 naming "NFR-041.3" and "<attribute>"

      Examples:
        | column          | attribute  |
        | Metric and unit | metric     |
        | Method          | method     |
        | Target          | target     |
        | Test level      | test level |

    Scenario: An FR rule whose Examples are all happy is refused
      Given the FR rule "FR-124.R1" without its negative Example
      When the atomic-breakdown check runs on the copy
      Then the check exits 1 naming "FR-124.R1" and "negative"

    Scenario: An item id that the finding-id parser cannot read is refused
      Given the item id "PRC-7.1" rewritten as "PRC7.1"
      When the atomic-breakdown check runs on the copy
      Then the check exits 1 naming "PRC7.1" and "id"

  Rule: The real breakdown passes, as the doc-check job runs it

    Scenario: The current sprint's breakdown passes unchanged
      When the atomic-breakdown check runs on the copy
      Then the check exits 0 with "0 problem(s)"
