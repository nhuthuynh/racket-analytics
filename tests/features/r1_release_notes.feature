# ST-082 (REL-1.1, FR-055.R1, T5-RB-3; ADR 0058 rule 7): scripts/ci/check_release_notes.py in the doc-check job.
Feature: The R1 release notes say what ships, what is switched off and what is not true yet
  As the product owner who signs off the R1 release candidate (P18)
  I want the release notes checked by a tool against the requirement register and the flags
  So that a release never ships notes that hide the unofficial scoring, a flag or a limitation

  Background:
    Given a copy of the R1 release notes

  Rule: FR-055.R1 While the scoring preset is PROVISIONAL-UNVERIFIED, the R1 release notes show the "unofficial scoring" notice

    Scenario: The real R1 release notes pass unchanged
      When the release-notes check runs on the copy
      Then the check exits 0 with "0 problem(s)"

    Scenario: Release notes without the "unofficial scoring" notice are refused
      Given the "unofficial scoring" notice removed from the copy
      When the release-notes check runs on the copy
      Then the check exits 1 naming "unofficial scoring"

  Rule: REL-1.1 The notes list every R1 FR, every flag with its default, and every limitation with its P-n

    Scenario: A release note that leaves out an R1 FR is refused
      Given the feature row "FR-055" removed from the copy
      When the release-notes check runs on the copy
      Then the check exits 1 naming "FR-055"

    Scenario: A flag listed with the wrong default is refused
      Given the flag "FEATURE_QUOTAS" listed with default "true"
      When the release-notes check runs on the copy
      Then the check exits 1 naming "FEATURE_QUOTAS"

    Scenario: A known limitation that names no P-n is refused
      Given the limitation "L-1" with its P-n removed
      When the release-notes check runs on the copy
      Then the check exits 1 naming "L-1"

  Rule: T5-RB-3 The release candidate never runs with development settings

    Scenario: Release notes that leave development sign-in on are refused
      Given the runtime setting "DEV_IDENTITY_ENABLED" listed as "true"
      When the release-notes check runs on the copy
      Then the check exits 1 naming "DEV_IDENTITY_ENABLED"

    Scenario: Release notes with no development sign-in line are refused
      Given the runtime setting row "DEV_IDENTITY_ENABLED" removed from the copy
      When the release-notes check runs on the copy
      Then the check exits 1 naming "DEV_IDENTITY_ENABLED"

    Scenario: Release notes that run the candidate as APP_ENV dev are refused
      Given the runtime setting "APP_ENV" listed as "dev"
      When the release-notes check runs on the copy
      Then the check exits 1 naming "APP_ENV"

    Scenario: A privacy flag listed on by default is refused
      Given the flag "FEATURE_AGE_GATE" listed with default "true"
      When the release-notes check runs on the copy
      Then the check exits 1 naming "privacy"
