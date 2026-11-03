# Sprint 5, ticket CI-TIERS-a (sre-devops-engineer; review tier 2, ADR 0056). Story PRC-05 "The
# process rules are enforced by checks", atomic items PRC-2.1, PRC-2.2, PRC-2.3.
# The tier matrix below is the ticket's acceptance matrix (docs/sprints/sprint-05.md §3.7,
# CI-TIERS-a), copied case by case before any implementation; the senior-qa-engineer reviews it
# against the plan (writer/reviewer split).
# Binding: infra/tests/test_review_tiers_scenarios.py. It commits the planted files to a throwaway
# git repository and runs `scripts/ci/review_tiers.py --base <base> --head <head>` on it, so the
# executable bit, the shebang line and the role-file front matter come from real git objects.
@story-PRC-05 @ticket-CI-TIERS-a @prc-2.1 @prc-2.2 @prc-2.3
Feature: The review tier of a pull request is computed from its changed paths

  Rule: A file gets the highest tier of every rule it matches, the PR the highest over its files,
        and a path no rule matches is tier 2 (fail closed)

    Scenario Outline: A pull request changing <paths> is tier <tier>
      Given a repository on main
      And a pull request that changes "<paths>"
      When the tier classifier runs on the pull request
      Then the computed tier is <tier>

      Examples: executable floor (an executable file is at least tier 1 wherever it lives)
        | paths                                                                       | tier |
        | docs/security/tools/check_threat_notes.py                                   | 1    |
        | docs/security/tools/asvs_status.py                                          | 1    |
        | docs/sprints/05/close-checks/retro05_check.py                               | 1    |
        | docs/tools/run-check (shebang)                                              | 1    |
        | docs/notes/helper (executable bit)                                          | 1    |
        | README.md, docs/x.md, docs/design/tools/check_flows.py                      | 1    |

      Examples: tier 2 wins over tier 0 and fails closed
        | paths                                                                       | tier |
        | docs/architecture/api-matches.md                                            | 2    |
        | docs/x.md, docs/architecture/api-x.md                                       | 2    |
        | docs/x.md, docs/unknown/thing.bin                                           | 2    |
        | backend/src/racket/migrations/versions/0001_identity_and_matches.py         | 2    |
        | backend/src/racket/migrations/env.py                                        | 2    |
        | docs/sprints/05/ticket-owners.json                                          | 2    |
        | scripts/ci/merge_ready.py                                                   | 2    |
        | scripts/ci/review_tiers.py                                                  | 2    |
        | backend/src/racket/video_ingest/service.py                                  | 2    |
        | .claude/hooks/pre_tool_use.py                                               | 2    |

      Examples: tier 0, docs and process text only
        | paths                                                                       | tier |
        | docs/sprints/05/status.json                                                 | 0    |
        | docs/sprints/sprint-05.md                                                   | 0    |
        | README.md, docs/x.md                                                        | 0    |

      Examples: ordinary code
        | paths                                                                       | tier |
        | docs/x.md, backend/src/racket/analytics/service.py                          | 1    |

  Rule: A role file is tier 0 unless the text between its first two --- lines changes, which is
        tier 2; an added or deleted role file, or one without a closed front matter block, is tier 2

    Scenario: A body-only edit of a role file is tier 0
      Given a repository on main
      And a pull request that edits only the body of ".claude/agents/sre-devops-engineer.md"
      When the tier classifier runs on the pull request
      Then the computed tier is 0

    Scenario: A changed tools: line in a role file is tier 2
      Given a repository on main
      And a pull request that changes the tools: line of ".claude/agents/sre-devops-engineer.md"
      When the tier classifier runs on the pull request
      Then the computed tier is 2

    Scenario Outline: A role file front matter edit "<edit>" is tier <tier>
      Given a repository on main
      And a pull request that makes the front matter edit "<edit>" to ".claude/agents/sre-devops-engineer.md"
      When the tier classifier runs on the pull request
      Then the computed tier is <tier>

      Examples: any front matter change can widen or narrow the role's powers
        | edit                                           | tier |
        | description reworded                           | 2    |
        | block-list tool item under an unchanged tools: | 2    |
        | continuation line under an unchanged tools:    | 2    |
        | permissionMode bypassPermissions added         | 2    |
        | hooks added                                    | 2    |
        | mcpServers added                               | 2    |
        | disallowedTools removed                        | 2    |
        | front matter no longer parses                  | 2    |
        | closing --- removed                            | 2    |

    Scenario: An added role file is tier 2
      Given a repository on main
      And a pull request that adds the role file ".claude/agents/new-role.md"
      When the tier classifier runs on the pull request
      Then the computed tier is 2

    Scenario: A deleted role file is tier 2
      Given a repository on main
      And a pull request that deletes ".claude/agents/sre-devops-engineer.md"
      When the tier classifier runs on the pull request
      Then the computed tier is 2

  Rule: Specialist reviewers are flagged by the paths they own

    Scenario Outline: A pull request changing <path> flags <role>
      Given a repository on main
      And a pull request that changes "<path>"
      When the tier classifier runs on the pull request
      Then the flagged specialists include "<role>"

      Examples:
        | path                                                   | role                     |
        | web/src/components/stats/messages.ts                   | principal-designer       |
        | backend/src/racket/coaching/drills/rules.py            | pickleball-domain-coach  |
        | backend/src/racket/worker/stages.py                    | senior-ml-cv-engineer    |
        | backend/src/racket/dataset/labels.py                   | senior-ml-cv-engineer    |
        | backend/src/racket/coaching/evals/runner.py            | senior-ml-cv-engineer    |
        | web/src/lib/security/csp.ts                            | senior-frontend-engineer |
