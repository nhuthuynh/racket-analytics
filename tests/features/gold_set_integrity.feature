# Sprint 0 §7. Owner: senior-qa-engineer.
# Steps: backend/tests/features/test_gold_set_integrity.py
# Unit tests: backend/tests/unit/dataset/test_manifest_check.py
@M0 @story-ST-011 @nfr-078
Feature: Fixture and gold-set integrity
  Nobody edits a gold set or fixture to make a test pass.

  Rule: Every frozen file matches its manifest

    Scenario: A fixture file changes without a new version
      Given the synthetic fixture set version 1 is frozen
      When one of its files changes and the version stays the same
      Then the integrity check fails and names the changed file

    Scenario: An unlisted file is added
      Given the synthetic fixture set version 1 is frozen
      When a file that is not in its manifest is added to the set
      Then the integrity check fails and names the unlisted file
