# Sprint 3, ticket SIZE-WAIVERS-03 (engineering-manager). Written before the decisions file.
# Binding: infra/tests/test_size_waivers_scenarios.py (the real decisions file, real git, the
# `PR size` step of .github/workflows/ci.yml run on the PR merge ref).
# Incident: PR #4, CI run 37719909230 (a ticket PR over 400 lines, no size decision, red).
@M0 @nfr-077 @ticket-SIZE-WAIVERS-03
Feature: Every Sprint 3 ticket PR over 400 changed lines has its size decided before it opens

  Rule: The size-waiver label goes only on a waived PR within its recorded number

    Scenario: A waived ticket PR above its recorded number gets no label and fails PR size
      Given the size decision for "HARNESS-03" PR 1
      And that PR changes 1503 lines
      When the size decision is applied and the PR policy checks run on the merge ref
      Then the decision asks for a new decision row
      And no size-waiver label is applied
      And the PR size check fails and counts 1503 changed lines

    Scenario: A stacked part over 400 lines gets no label and fails PR size
      Given the size decision for "ST-049" PR 1
      And that PR changes 401 lines
      When the size decision is applied and the PR policy checks run on the merge ref
      Then the decision asks for a new decision row
      And no size-waiver label is applied
      And the PR size check fails and counts 401 changed lines

    Scenario: A waived ticket PR within its recorded number passes PR size with the label
      Given the size decision for "HARNESS-03" PR 1
      And that PR changes 1502 lines
      When the size decision is applied and the PR policy checks run on the merge ref
      Then the size-waiver label is applied
      And the PR size check passes and counts 1502 changed lines

    Scenario: A stacked part within 400 lines passes PR size without a label
      Given the size decision for "ST-049" PR 1
      And that PR changes 355 lines
      When the size decision is applied and the PR policy checks run on the merge ref
      Then no size-waiver label is applied
      And the PR size check passes and counts 355 changed lines

  Rule: The decisions file covers every Sprint 3 ticket PR over 400 changed lines

    Scenario: Every ticket in scope has a waiver or a stacked split
      Given the Sprint 3 ticket PRs measured over 400 changed lines
      When the SIZE-WAIVERS-03 decisions file is checked against them
      Then every ticket has a size decision
      And no stacked part without a waiver is over 400 changed lines
      And every ticket's PRs leave room for its own decisions file
