# Sprint 5, ticket CI-RECON-ON-PR (sre-devops-engineer; story PRC-05; PRC-4.1, PRC-4.2).
# Retro 4 M3/L13 (an author-found gap had no route into the ledger), M8/D3 and M13/E3 (a
# finding named only in a decisions file was invisible to open_defects.py and reconcile_due.py).
# Binding: infra/tests/test_reconcile_on_pr_scenarios.py (the real pr-policy steps of
# .github/workflows/ci.yml on a real git checkout of the PR merge ref). Written before the code.
@story-PRC-05 @ticket-CI-RECON-ON-PR
Feature: A ticket PR cannot leave a finding in its decisions file outside the ledger
  As the engineering-manager
  I want pr-policy to join the findings a ticket's decisions file names to the review ledger
  So that every blocker or major is counted, and no author-found gap is lost in prose

  Background:
    Given a pull request opened against main with a Sprint 5 ledger

  Rule: A blocker or major id named in a changed decisions file needs a ledger row

    Scenario: A planted decisions file naming a major with no ledger row fails pr-policy
      Given the pull request adds a decisions file naming "AF-PLANT05-01 (major)"
      When the PR policy checks run on the merge ref
      Then the reconcile step fails
      And it names AF-PLANT05-01 as a major with no ledger row

    Scenario: The same major passes once the pull request writes its ledger row
      Given the pull request adds a decisions file naming "AF-PLANT05-01 (major)"
      And the pull request writes a ledger row for AF-PLANT05-01
      When the PR policy checks run on the merge ref
      Then the reconcile step passes

    Scenario: A minor needs no ledger row
      Given the pull request adds a decisions file naming "AF-PLANT05-02 (minor)"
      When the PR policy checks run on the merge ref
      Then the reconcile step passes

  Rule: A gap phrase in a decisions file must carry a finding id

    Scenario: A "can only" line without a finding id fails pr-policy
      Given the pull request adds a decisions file line "the solo-wall plan can only show no_alternative"
      When the PR policy checks run on the merge ref
      Then the reconcile step fails
      And it names the "can only" line as having no finding id

    Scenario: The same gap with a declared finding id passes
      Given the pull request adds a decisions file line "AF-PLANT05-03 (minor): the solo-wall plan can only show no_alternative"
      When the PR policy checks run on the merge ref
      Then the reconcile step passes

  Rule: Only the pull request's own decisions lines are judged

    Scenario: A PR that changes no decisions file passes
      Given the pull request changes only documentation
      When the PR policy checks run on the merge ref
      Then the reconcile step passes
