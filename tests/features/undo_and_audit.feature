# Sprint 2 §7.4 (QA-ACC, written for ST-031). Owner: senior-qa-engineer.
# API binding: backend/tests/features/test_undo_and_audit.py. Browser binding:
# web/e2e/sprint-02/undo-history.spec.ts (E2E-02-06).
@M0 @story-ST-031
Feature: Undo and correction history
  Rule: Every change can be undone and is remembered

    Scenario: Undo a correction
      Given Ivy changed rally 5's winner
      When she undoes the change
      Then the score sheet is identical to the one before her change
      And her correction history lists both the change and the undo

    Scenario: Correction history shows what changed
      Given Ivy changed rally 5's ending from "winner" to "forced error"
      When she opens the correction history
      Then it shows rally 5, the field "ending", the old value "winner" and the new value "forced error"
