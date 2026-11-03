# Sprint 5, ticket CI-TIERS-b (sre-devops-engineer; review tier 2, ADR 0056). Story PRC-05 "The
# process rules are enforced by checks", atomic items PRC-2.4, PRC-2.5, PRC-2.6, PRC-2.7.
# The first two rules are docs/sprints/sprint-05.md §7 (merge_tiers.feature) word for word; the
# others are the card's acceptance (§3.7 CI-TIERS-b). Written before the implementation.
# Binding: infra/tests/test_merge_tiers_scenarios.py runs scripts/ci/merge_ready.py over HTTP
# against the local GitHub API stub (infra/tests/github_stub.py), which also serves the PR's
# files and docs/sprints/<nn>/ticket-owners.json on main.
@story-PRC-05 @ticket-CI-TIERS-b @prc-2.4 @prc-2.5 @prc-2.6 @prc-2.7
Feature: The merge gate requires the verdicts of the PR's risk tier

  Rule: PRC-2.5 Tier 1 needs the principal-engineer and the senior-qa-engineer on the head

    Example: both approve the head SHA
      Given a PR that changes only "backend/src/racket/analytics/x.py"
      And APPROVE verdicts from principal-engineer and senior-qa-engineer on the head
      When merge_ready.py runs
      Then it exits 0

    Example: a senior-backend verdict does not replace QA
      Given a PR that changes only "backend/src/racket/analytics/x.py"
      And APPROVE verdicts from principal-engineer and senior-backend-engineer on the head
      When merge_ready.py runs
      Then it exits non-zero naming "senior-qa-engineer"

  Rule: PRC-2.1 An unclassified path is tier 2

    Example: a new top-level directory
      Given a PR that adds "newdir/tool.py"
      When the tier is computed
      Then the tier is 2

  Rule: PRC-2.4 Tier 0 needs one APPROVE from a role other than the author's and a green doc-check

    Example: a docs PR with a fresh-context approval passes
      Given a PR that changes only "docs/process/x.md"
      And the doc-check succeeded on the head
      And APPROVE verdicts from principal-designer on the head
      When merge_ready.py runs
      Then it exits 0

    Example: a docs PR without the doc-check fails
      Given a PR that changes only "docs/process/x.md"
      And APPROVE verdicts from principal-designer on the head
      When merge_ready.py runs
      Then it exits non-zero naming "Doc checks"

    Example: a planted APPROVE from the author's own role does not count
      Given a PR that changes only "docs/process/x.md"
      And the doc-check succeeded on the head
      And APPROVE verdicts from sre-devops-engineer on the head
      When merge_ready.py runs
      Then it exits non-zero naming "sre-devops-engineer"

    Example: a hidden code file makes a docs PR tier 1
      Given a PR that changes only "docs/process/x.md"
      And the PR also adds an extensionless file "docs/process/run" with a shebang line
      And the doc-check succeeded on the head
      And APPROVE verdicts from principal-designer on the head
      When merge_ready.py runs
      Then it exits non-zero naming "principal-engineer"

  Rule: PRC-2.6 Every tier 2 PR also needs the security-privacy-engineer

    Example: a migration-only PR with PE and QA but no security fails
      Given a PR that changes only "backend/src/racket/migrations/versions/0009_x.py"
      And APPROVE verdicts from principal-engineer and senior-qa-engineer on the head
      When merge_ready.py runs
      Then it exits non-zero naming "security-privacy-engineer"

    Example: the same PR with the security verdict passes
      Given a PR that changes only "backend/src/racket/migrations/versions/0009_x.py"
      And APPROVE verdicts from principal-engineer, senior-qa-engineer and security-privacy-engineer on the head
      When merge_ready.py runs
      Then it exits 0

  Rule: PRC-2.7 The author role comes from ticket-owners.json on main, never from the PR

    Example: the PR body claims another role
      Given a PR that changes only "docs/process/x.md"
      And the PR body says "Author role: principal-engineer"
      And the doc-check succeeded on the head
      And APPROVE verdicts from sre-devops-engineer on the head
      When merge_ready.py runs
      Then it exits non-zero naming "sre-devops-engineer"

    Example: a head branch with no row fails closed
      Given a PR from the head branch "s05/new-ticket" that changes only "backend/src/racket/analytics/x.py"
      And APPROVE verdicts from principal-engineer and senior-qa-engineer on the head
      When merge_ready.py runs
      Then it exits non-zero naming "s05/owners-<slug>"

    Example: a sprint without an owner file fails closed naming the bootstrap step
      Given a PR from the head branch "s06/st-090" that changes only "backend/src/racket/analytics/x.py"
      And APPROVE verdicts from principal-engineer and senior-qa-engineer on the head
      When merge_ready.py runs
      Then it exits non-zero naming "merge s06/plan first"

    Example: the plan PR of a new sprint passes through the bootstrap rule
      Given a PR from the head branch "s06/plan" that changes only "docs/sprints/06/ticket-owners.json"
      And APPROVE verdicts from principal-engineer, senior-qa-engineer and security-privacy-engineer on the head
      When merge_ready.py runs
      Then it exits 0
