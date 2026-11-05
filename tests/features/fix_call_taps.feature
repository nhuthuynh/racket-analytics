# Fix a call in at most 2 taps or keys (ST-080; NFR-036.4; scorecard G05-05). The call types are
# CT-1 to CT-4 in docs/domain/fix-call-types.md (COACH-5). Bound in the browser by the Playwright
# test whose title starts with the scenario's E2E id (web/e2e/sprint-05/fix-call-taps.spec.ts);
# the binding is checked by web/tests/unit/e2e-helpers-tap-counter.test.ts. Counted: each tap or
# key that acts, from the moment the control on the screen where the wrong value is visible is
# reached; moving focus (Tab, arrow keys) is not a fix (E2E-02-05, TCR 2026-10-06).
@M5 @story-ST-080
Feature: Fixing a call is quick
  A player who sees a wrong call on the score sheet, or as the last tag on Quick Tag, fixes it in
  at most 2 taps or keys, with a pointer and with the keyboard.

  @E2E-05-80
  Scenario Outline: a call is fixed in at most 2 taps or keys from where it is seen
    Given a tagged match whose score sheet shows a wrong <call type>
    When the player fixes it from <from> to <to> on the score sheet, by taps and by keys
    Then the sheet shows <to> for that rally
    And the counter reports at most 2 taps or keys for each fix

    Examples:
      | call type                | from             | to               |
      | CT-1 rally winner        | won by side B    | won by side A    |
      | CT-2 rally ending        | winner           | unforced error   |
      | CT-2 rally ending        | unforced error   | replay           |
      | CT-3 fault               | unforced error   | fault            |
      | CT-3 fault               | fault            | forced error     |
      | CT-4 responsible player  | Ivy              | Dana             |
      | CT-4 responsible player  | Dana             | not tagged       |

  @E2E-05-80
  Scenario: the wrong last tag is removed from Quick Tag in 1 key
    Given the player has just tagged a rally with the wrong winner on Quick Tag
    When she presses the undo key
    Then the wrong rally is gone from the sheet
    And the counter reports 1 key

  @E2E-05-80
  Scenario: a planted 3-step path is counted as 3 and fails the budget
    Given a wrong fault call on the score sheet
    When it is fixed through a detour of 3 taps
    Then the counter reports 3
    And the budget check reports the path as over 2
