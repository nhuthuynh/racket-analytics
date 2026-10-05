# Sprint 1 §7.3 + §14.3.4 (ST-016). Owner: senior-qa-engineer. Written before implementation.
# Bindings: API level backend/tests/features/test_match_setup.py ("Wrong participants for the
# format" and "Rally scoring is not yet available" through POST /matches; IT-01-05);
# browser level web/e2e/sprint-01/match-setup.spec.ts (all scenarios; E2E-01-03).
@M0 @story-ST-016 @nfr-037
Feature: Match setup
  Rule: One question per page, with errors summarised at the top

    Scenario: Missing answer
      Given Ivy is on the "format" question
      When she continues without choosing a format
      Then she sees "There is a problem" at the top with a link to the format question
      And the page title starts with "Error:"

    Scenario: Review before upload
      Given Ivy has answered every setup question
      When she reaches "Check your answers"
      Then each answer is listed with a "Change" link

  Rule: Participants are nicknames assigned by the user

    Scenario: Doubles match setup
      Given Ivy is setting up a doubles match
      When she enters four nicknames, two per side, and marks herself as "me"
      Then the match shows two sides of two players with her marked as "me"

    Scenario Outline: Wrong participants for the format
      Given Ivy is setting up a <format> match
      When she enters <entered>
      Then she sees an error summary saying "<message>"
      Examples:
        | format  | entered                             | message                            |
        | doubles | three nicknames                     | Each side needs two players        |
        | singles | three nicknames                     | Each side needs one player         |
        | doubles | four nicknames with two marked "me" | Choose one player as "me"          |

  Rule: Only verified scoring systems can be chosen

    Scenario: Rally scoring is not yet available
      Given Ivy is on the "scoring system" question
      Then she can choose side-out scoring
      And rally scoring is shown as provisional and cannot be chosen
      And she is told it becomes available once the rules are verified

  Rule: Answers can be changed from the check page

    Scenario: Change one answer
      Given Ivy is on "Check your answers"
      When she changes the format from doubles to singles
      Then she returns to "Check your answers"
      And she is asked to enter one player per side

  Rule: Contact details are discouraged, not stored silently

    Scenario: A nickname that looks like an email address
      Given Ivy is entering players
      When she enters "carlos@example.com" as a nickname
      Then she sees "This looks like contact details. Use a nickname instead."
      And she can still continue

  Rule: Dates cannot be in the future

    Scenario: Future match date
      Given Ivy is on the "date" question
      When she enters tomorrow's date
      Then she sees an error summary saying "The date must be today or in the past"
