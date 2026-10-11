# FIX-03-1b (sprint-03 §9.1, S3-DoD-P6; NFR-027 b; PO P12 option b): the manual screen-reader
# pass is a human item. Its status is counted from the result cells of
# docs/sprints/03/a11y-manual.md §3, never written by hand, so no report can call it met
# before a human has recorded a result for every row on both screen readers.
Feature: The S3-DoD-P6 status is counted from the screen-reader manual
  As the product-manager reporting the sprint-DoD rows
  I want the manual's result cells tallied by a script
  So that "met" is only ever reported when a human tester has run every row on VoiceOver and TalkBack

  Rule: The tally fails closed

    Scenario: A manual without a result table is refused
      Given a manual with no result table
      When the manual is tallied
      Then the tally is refused as malformed

    Scenario: A manual with a gap in its row numbers is refused
      Given a manual with rows 1 to 3 and 5
      When the manual is tallied
      Then the tally is refused as malformed

    Scenario: A cell outside "pass", "fail: <words heard>" and "not run" is refused
      Given a manual of 38 rows whose row 2 on VoiceOver says "passive"
      When the manual is tallied
      Then the tally is refused as malformed

    Scenario: A "fail:" cell with only a count and no words heard is refused
      Given a manual whose rows 1-24 say "fail: (3 of 24)" and rows 25 to 38 say "pass" on both screen readers
      When the manual is tallied
      Then the tally is refused as malformed

    Scenario: A count inside the words heard is refused
      Given a manual whose rows 1-24 say "fail: label not read (3 of 24)." and rows 25 to 38 say "pass" on both screen readers
      When the manual is tallied
      Then the tally is refused as malformed

    Scenario: A reversed range row is refused
      Given a manual whose rows 1 to 36 say "pass" and whose last row is "38-37" with "not run"
      When the manual is tallied
      Then the tally is refused as malformed

    Scenario: A row id that cannot be read is refused
      Given a manual with rows 1 to 37 and a last row numbered "**38**"
      When the manual is tallied
      Then the tally is refused as malformed

    Scenario: A manual with fewer rows than expected is refused
      Given a manual of 37 rows with every result recorded on both screen readers
      When the manual is tallied expecting 38 rows
      Then the tally is refused as malformed

  Rule: The status is "met" only when every row has a result on both screen readers

    Scenario: No row run is not met, waiting on P6
      Given a manual of 38 rows with no result recorded
      When the manual is tallied
      Then the status is "not met: waiting on P6 (0 of 38 rows run)"

    Scenario: One row missing on TalkBack is not met
      Given a manual of 38 rows with every VoiceOver result recorded and 37 TalkBack results
      When the manual is tallied
      Then the status is "not met: waiting on P6 (37 of 38 rows run)"

    Scenario: Every row run on both screen readers is met
      Given a manual of 38 rows with every result recorded on both screen readers
      When the manual is tallied
      Then the status is "met (38 of 38 rows run)"

    Scenario: A range row with a partial count counts only the rows proven run on both
      Given a manual whose rows 1-24 say "pass (3 of 24)" and rows 25 to 38 say "pass" on both screen readers
      When the manual is tallied
      Then the status is "not met: waiting on P6 (14 of 38 rows run)"

  Rule: The sprint-DoD row says what the manual says

    Scenario: A sprint-DoD row that claims more than the manual is refused
      Given a manual of 38 rows with no result recorded
      And a sprint plan whose S3-DoD-P6 row says "met (38 of 38 rows run)"
      When the manual is tallied against the sprint plan
      Then the tally reports that the sprint-DoD row disagrees with the manual
