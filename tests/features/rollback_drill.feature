# ST-082 (REL-1.2; ADR 0058 rule 7): scripts/ops/rollback_drill.py. The scenarios run the drill as a
# process against a recording stand-in for `docker`, so the order and the fallback are checked
# without a stack; the live drill on a Compose project is the G05-09 method.
Feature: A release can be rolled back to the previous image tag set
  As the sre-devops-engineer on call for a bad release
  I want one drill that backs up, downgrades with the current image, then redeploys the previous tag
  So that a rollback follows ADR 0058 rule 7 and never runs an older image on a newer schema

  Background:
    Given a Compose project "racket-drill" whose previous release is "r1-rehearsal-0020" at revision "0020"
    And its current release is "r1-rc1"

  Rule: REL-1.2 The previous image tag set redeploys and the API is healthy

    Scenario: The drill backs up, downgrades, then redeploys the previous tag
      When the rollback drill runs to the previous tag
      Then the drill exits 0
      And the steps ran in the order "backup, downgrade, redeploy, health"
      And the downgrade ran with the current image to revision "0020"
      And the redeploy started tag "r1-rehearsal-0020" without building

    Scenario: A failed downgrade restores the backup and redeploys the current release
      Given the downgrade fails
      When the rollback drill runs to the previous tag
      Then the drill exits 1
      And the steps ran in the order "backup, downgrade, restore, redeploy, health"
      And the redeploy started tag "r1-rc1" without building

    Scenario: Missing previous images stop the drill before anything changes
      Given the images of tag "r1-rehearsal-0020" are missing
      When the rollback drill runs to the previous tag
      Then the drill exits 2
      And no downgrade ran
