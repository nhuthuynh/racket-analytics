# MVP-04 (Sprint 3 MVP goal, PO 2026-10-15; ST-050, FR-006; flows D-2 default title, X-01).
# A live run on main 6c666b9 showed "Doubles · 11 Oct 2026 · 11 Oct 2026" in "Delete this match?":
# the default title already carries the date played. Owner: senior-frontend-engineer.
# Browser binding: web/e2e/sprint-03/mvp-04-delete-match-summary.spec.ts (real stack).
# Component bindings: web/tests/unit/mvp-04-delete-match-summary.test.tsx.
@M0 @story-ST-050 @ticket-MVP-04
Feature: The delete confirmation names the match once
  Rule: The match line in "Delete this match?" shows the date played exactly once

    Scenario: A match with its default title
      Given Ivy has a doubles match played on 5 Sep 2026 with the default title "Doubles · 5 Sep 2026"
      When she starts deleting the match
      Then the confirmation names it "Doubles · 5 Sep 2026"
      And the date played appears once in the confirmation

    Scenario: A match with a title of her own
      Given Ivy has a match titled "Saturday doubles" played on 3 Oct 2026
      When she starts deleting the match
      Then the confirmation names it "Saturday doubles · 3 Oct 2026"
