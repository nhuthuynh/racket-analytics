# FIX-03-1a (G03-12, V03R1-01): a ticket PR that closes a finding writes no review-rounds row,
# so the ledger kept six open blocker/major rows after their tickets had merged into main.
# The reconciliation check names every open row that a merged ticket names and that no later
# ledger row has reconciled, so the engineering-manager writes the row before the count is read.
Feature: Open review-rounds rows that a merged ticket names are flagged for reconciliation
  As the engineering-manager
  I want a check that reads the ledger, the ticket plan and the ticket decision files
  So that a finding fixed on main is never still counted as open by G03-12

  Rule: An open row that a merged ticket names fails the check and is named

    Scenario: A commit of a merged ticket PR names an open finding
      Given a ledger with an open major row for PE-R9S9-05
      And a ticket plan where ticket PE-R9S9-07 PR #12 merged as 4f5b8f1 carries a commit "ci(PE-R9S9-05)"
      When the reconciliation check runs
      Then the check fails
      And the report names PE-R9S9-05 as due because of ticket PE-R9S9-07 (#12)

    Scenario: A ticket decision file names an open finding
      Given a ledger with an open major row for PE-R9S9-03
      And a ticket decision file "PE-R9S9-03-ITS.md"
      When the reconciliation check runs
      Then the check fails
      And the report names PE-R9S9-03 as due because of ticket PE-R9S9-03-ITS

    Scenario: A ledger without a review table is refused, never read as nothing due
      Given a ledger without a review table
      When the reconciliation check runs
      Then the check fails with a usage error

  Rule: Only a decision file already on the base branch names a merged ticket

    Scenario: A fix ticket's own decision file, added by its open PR, does not fail that PR
      Given a ledger with an open major row for PE-PR24-01
      And a base branch without a ticket decision file for PE-PR24-01
      And the ticket PR adds a ticket decision file "PE-PR24-01.md"
      When the reconciliation check runs against the base branch
      Then the check passes
      And the report says 1 open row and 0 due

    Scenario: The same decision file once merged into the base branch names the finding
      Given a ledger with an open major row for PE-PR24-01
      And a base branch with a ticket decision file "PE-PR24-01.md"
      When the reconciliation check runs against the base branch
      Then the check fails
      And the report names PE-PR24-01 as due because of ticket PE-PR24-01

  Rule: A row that already names the ticket, its PR or its merge commit is reconciled

    Scenario: The open row's section names the ticket's merge commit
      Given a ledger whose section at main 25a5af0 keeps PD-R9S9-01 open
      And a ticket plan where ticket DOCS-09 PR #64 merged as 25a5af0 carries a commit "docs(PD-R9S9-01)"
      When the reconciliation check runs
      Then the check passes
      And the report says 1 open row and 0 due

    Scenario: A later engineering-manager row records the ticket's fix
      Given a ledger with an open major row for PE-R9S9-05
      And a later row that marks PE-R9S9-05 fixed by PR #12
      And a ticket plan where ticket PE-R9S9-07 PR #12 merged as 4f5b8f1 carries a commit "ci(PE-R9S9-05)"
      When the reconciliation check runs
      Then the check passes
      And the report says 0 open rows and 0 due
