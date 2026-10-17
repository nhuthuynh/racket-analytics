# C4-RECON (retro 3 B3, VM-R3-02 / verifier id V03R3-02): reconcile_due.py saw a merged ticket only
# when it named an open row, so FIX-03-2b/2c showed "0 due" while the evidence to close two open
# rows was already on main. A merged ticket PR whose diff changes a file that the open row's
# evidence cites, with no ledger row written after that merge, is now due too.
# A new file next to reconcile_due.feature: an addition, so no accepted scenario is changed.
Feature: A merged ticket that changes an open row's evidence is flagged for reconciliation
  As the engineering-manager
  I want the reconciliation check to see merges that change what an open row's evidence reads
  So that a finding whose closing evidence is on main is reconciled, not left open by G03-12

  Background:
    Given a ledger with an open major row for PE-R9S9-05 whose evidence cites "docs/design/flows.md"

  Rule: A merge that changes a cited file after the row was written makes the row due

    Scenario: Evidence changed, no reconciliation row: the row is due
      Given ticket FIX-09 is merged as PR #7 and changes "docs/design/flows.md"
      When the reconciliation check runs against main
      Then the check fails
      And the report names PE-R9S9-05 as due because of ticket FIX-09 (#7)

    Scenario: The same due row is reported, not failed, in report-only mode
      Given ticket FIX-09 is merged as PR #7 and changes "docs/design/flows.md"
      When the reconciliation check runs against main in report-only mode
      Then the check passes
      And the report names PE-R9S9-05 as due because of ticket FIX-09 (#7)

    Scenario: A merge whose PR title names the open finding is due
      Given ticket FIX-10 is merged as PR #8 with the title "Meet goal metric G99-12-PE-R9S9-05"
      When the reconciliation check runs against main
      Then the check fails
      And the report names PE-R9S9-05 as due because the title of ticket FIX-10 (#8) names it

  Rule: A merge that leaves the evidence alone, or a row written after it, is not due

    Scenario: A merge that changes only files the evidence does not cite is not due
      Given ticket FIX-09 is merged as PR #7 and changes "docs/other.md"
      When the reconciliation check runs against main
      Then the check passes
      And the report says 1 open row and 0 due

    Scenario: A reconciliation row written after the merge clears it
      Given ticket FIX-09 is merged as PR #7 and changes "docs/design/flows.md"
      And the engineering-manager then writes a later row that keeps PE-R9S9-05 open
      When the reconciliation check runs against main
      Then the check passes
      And the report says 1 open row and 0 due

    Scenario: A verifier-format id in the open row is read, never a usage error
      Given a verifier row V04R1-01 that is open and major
      When the reconciliation check runs against main
      Then the check passes
      And the report says 2 open rows and 0 due
