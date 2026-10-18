# PD-4b (split from PD-4, PR #88; ADR 0037 rule 2, ADR 0047 rule 2): PE-PD4-01, PE-PD4-05, SFE-PD4-07.
Feature: The flows checker reports a design review as held only from written decider cells
  As the principal-designer chairing a design review
  I want the decider cells checked by a tool that can fail
  So that no flows gate is reported as held on paper only

  Rule: A decider cell counts only when it starts with a verdict and its date

    Scenario: A pending cell is refused even when the Opened and Due columns are dated
      Given a flows file whose security-privacy-engineer cell says "pending"
      When the checker runs with the decider security-privacy-engineer
      Then the checker exits 1 with "FAIL cell"

    Scenario: A cell that only mentions a verdict and a date is refused
      Given a flows file whose security-privacy-engineer cell says "pending: will accept or reject by 2026-10-18"
      When the checker runs with the decider security-privacy-engineer
      Then the checker exits 1 with "FAIL cell"

    Scenario: A second row for the same decider is refused
      Given a flows file with the security-privacy-engineer cells "pending" and "accept (2026-10-18)"
      When the checker runs with the decider security-privacy-engineer
      Then the checker exits 1 with "FAIL row"

    Scenario: A written, dated verdict passes
      Given a flows file whose security-privacy-engineer cell says "**reject** (2026-10-18): consent default"
      When the checker runs with the decider security-privacy-engineer
      Then the checker exits 0 with "0 problem(s)"

  Rule: The opened form proves only that the review was opened

    Scenario: The Sprint 4 flows file has its links, screen states and opened DR-04 rows
      Given the Sprint 4 flows file
      When the checker runs the opened form for DR-04 and its nine screens
      Then the checker exits 0 with "0 problem(s)"

    Scenario: A missing flows file is an error, not a pass
      Given a flows file path that does not exist
      When the checker runs with the decider security-privacy-engineer
      Then the checker exits 2 with "FAIL file"
