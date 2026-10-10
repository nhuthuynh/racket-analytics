# ST-052 review round 1, PE-ST052-R1-M1 (FR-150; api-sprint-03 §5.2; flows-sprint-03 §6).
# Owner: senior-frontend-engineer. The server files a hit or bounce under whichever rally holds
# its frame, and saved labels cannot be changed in Sprint 3, so L-01 keeps every mark inside the
# span of the rally being labelled. Seen red before the fix (decisions/ST-052.md).
# Unit binding: web/tests/unit/st-052-rally-span.test.ts (the rule) and
# web/tests/unit/st-052-full-tag.test.tsx (L-01 in words).
# Integration binding: web/tests/unit/st-052-full-tag-retry.test.tsx, L-01 against a stateful
# fake of the §5.2/§5.4 label routes.
@M0 @story-ST-052 @fr-150
Feature: Full Tag marks stay inside the rally being labelled

  Rule: A hit or bounce belongs to the rally being labelled only inside its span

    Scenario: A hit tagged inside a saved rally is refused
      Given rally 1 is saved from frame 0 to 30
      And the labeller has started rally 2 at frame 100
      When they tag a hit at frame 10
      Then they are told frame 10 is before the start of rally 2
      And saving rally 2 leaves rally 1 with no new event

    Scenario: A mark after the end of the rally is refused
      Given the labeller has marked a rally from frame 20 to 30
      When they tag a bounce at frame 31
      Then they are told frame 31 is after the end of the rally

  Rule: Moving the start or end never leaves a mark outside the rally

    Scenario: Rally end before the last mark is refused
      Given the labeller has a rally with a hit at frame 10
      When they move Rally end to frame 5
      Then they are told Rally end must be at or after frame 10
