# PE-R3S3-04 (ADR 0039 amendment, PO P13): the per-ticket plan names every commit of a branch
# range exactly once, so no commit is shipped twice or left out of a ticket PR.
Feature: Every commit of the sprint branch appears exactly once in the ticket plan
  As the principal-engineer
  I want a check that reads the commit range from git and the ticket plan from the ADR
  So that a commit with no ticket row, or with two, is found before anyone relies on the plan

  Background:
    Given a repository whose sprint branch has three commits that are not on main

  Rule: The check fails closed and names each problem

    Scenario: A commit with no row in the plan fails the check and is named
      Given an ADR that names only the first two commits
      When the plan check runs over main..sprint
      Then the check fails
      And the report names the third commit as missing

    Scenario: A commit named twice in the plan fails the check and is named
      Given an ADR that names all three commits and the first one again
      When the plan check runs over main..sprint
      Then the check fails
      And the report names the first commit as named 2 times

    Scenario: A range that git cannot read fails the check instead of passing
      Given an ADR that names all three commits
      When the plan check runs over main..no-such-branch
      Then the check fails with a usage error

  Rule: A plan that names every commit once passes

    Scenario: Every commit named exactly once passes
      Given an ADR that names all three commits
      When the plan check runs over main..sprint
      Then the check passes
      And the report says 3 commits are each named once
