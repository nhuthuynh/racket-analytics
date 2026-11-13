# Sprint 6, ticket CI-TIERS-06 (sre-devops-engineer; review tier 2, ADR 0056). Story PRC-06, atomic
# items PRC-10.1 and PRC-10.2 (docs/sprints/06/requirements-breakdown.md).
# The path matrix below is the ticket's acceptance matrix (docs/sprints/sprint-06.md §3,
# CI-TIERS-06, and the red-first table), written case by case before any implementation; the
# senior-qa-engineer reviews it against the plan (writer/reviewer split). A new file, so the
# accepted tests/features/review_tiers.feature (CI-TIERS-a) stays unchanged.
# Binding: infra/tests/test_review_tiers_sprint_06_scenarios.py, which reuses the CI-TIERS-a steps:
# planted files committed to a throwaway git repository, then `scripts/ci/review_tiers.py --json`.
@story-PRC-06 @ticket-CI-TIERS-06 @prc-10.1 @prc-10.2
Feature: Sprint 6 footage, consent, pose, pattern-snapshot and model paths get their review tier

  Rule: Footage provenance, consent, pose data, the pattern-measure snapshot and model weights are
        tier 2 by a named rule; near misses stay tier 1

    Scenario Outline: A pull request changing <paths> is tier <tier>
      Given a repository on main
      And a pull request that changes "<paths>"
      When the tier classifier runs on the pull request
      Then the computed tier is <tier>

      Examples: personal data and licences are tier 2 (PRC-10.1)
        | paths                                                       | tier |
        | backend/src/racket/dataset/provenance.py                    | 2    |
        | backend/src/racket/analysis_jobs/footage_permit.py          | 2    |
        | backend/src/racket/dataset/consent.py                       | 2    |
        | backend/src/racket/worker/pose/keypoints.py                 | 2    |
        | backend/src/racket/analytics/patterns/snapshot.py           | 2    |
        | models/manifest.json                                        | 2    |
        | docs/x.md, models/weights/pose-small.onnx                   | 2    |

      Examples: near misses stay tier 1 (PRC-10.1 negatives)
        | paths                                                       | tier |
        | backend/src/racket/analytics/patterns/measures.py           | 1    |
        | backend/src/racket/analytics/snapshot.py                    | 1    |
        | backend/src/racket/dataset/models.py                        | 1    |
        | backend/src/racket/worker/composer.py                       | 1    |
        | content/references/pickleball/v1.json                       | 1    |

  Rule: A reference pattern set flags the pickleball-domain-coach

    Scenario Outline: A pull request changing <path> flags <role>
      Given a repository on main
      And a pull request that changes "<path>"
      When the tier classifier runs on the pull request
      Then the flagged specialists include "<role>"

      Examples:
        | path                                         | role                    |
        | content/references/pickleball/v1.json        | pickleball-domain-coach |
        | content/references/references.lock          | pickleball-domain-coach |
