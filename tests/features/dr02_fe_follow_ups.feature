# DR-02-FE (design review DR-02 R2-2 and R2-5, flows-sprint-02 §9 PD-FL2-03 / PD-FL2-05 and §12 E-3).
# Owner: senior-frontend-engineer. Added when the ticket was ported to its own PR (PO decision
# P13): the original commits carried unit and E2E tests only. Seen red against main's S-01 and
# T-01 before the port's implementation commits were applied.
# Browser binding (live stack): web/e2e/sprint-03/focus-after-decision.spec.ts (E-3) and
# web/e2e/sprint-03/dr02-fe-wording.spec.ts (rules line, T-01 undo words).
# Unit binding: web/tests/unit/dr02-e3-focus-after-decision.test.tsx,
# web/tests/unit/score-sheet.test.tsx, web/tests/unit/quick-tag-undo.test.tsx.
@story-DR-02 @nfr-027
Feature: Score sheet and tagging follow-ups from design review DR-02
  After a decision removes a rally's controls, keyboard focus must not drop to the page; the
  rules line speaks in words, not the internal preset id; T-01 and S-01 name undo the same way.

  Rule: After a decision removes the row's controls, focus moves on, never to the page

    Scenario: A refused decision keeps focus on the control used
      Given Ivy's score sheet has rally 12 waiting for her decision
      When she presses "Remove rally 12" and the decision is refused
      Then focus stays on "Remove rally 12"

    Scenario: Removing a rally moves focus to the rally that came next
      Given Ivy's score sheet has rallies 12, 13 and 14 waiting for her decision
      When she removes rally 12 with the keyboard
      Then focus is on the first action of the rally that came after it, now numbered 12

    Scenario: Deciding the last such rally moves focus to Undo
      Given Ivy's score sheet has no rally after rally 13
      When she moves rally 13 to the next game with the keyboard
      Then focus is on "Undo last change"

  Rule: The rules line says the rules are provisional in words

    Scenario: Provisional rules
      Given Ivy's score sheet is scored with the provisional rules preset
      When she opens the score sheet
      Then she reads "Rules: provisional, not yet checked against the rulebook"
      And she does not read "PROVISIONAL-UNVERIFIED"

  Rule: Undo has the same name on T-01 and S-01

    Scenario: Undo on the tagging screen
      Given Ivy is tagging rallies on T-01
      Then the undo button is named "Undo last change"
