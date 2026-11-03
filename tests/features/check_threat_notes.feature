# SEC-5 (sprint-05 §3; NFR-050.9, P19; kickoff item SEC-3): "Accepted residual" stays open until a human ADR covers it.
Feature: The threat-notes checker accepts a residual risk only when an Accepted ADR covers it
  As the security-privacy-engineer writing threat notes
  I want every "Accepted residual" row checked against an Accepted ADR
  So that no residual risk is reported as accepted without a human decider on record

  Rule: An "Accepted residual" row must name an Accepted ADR

    Scenario: A planted residual row without an ADR id is refused
      Given a threat-notes file with the row "| T5-UT-9 | I | threat | control | judgment | ST-083 | test | Accepted residual |"
      When the threat-notes checker runs on it
      Then the threat-notes checker exits 1 with "FAIL residual: T5-UT-9"

    Scenario: A residual row naming a Proposed ADR is refused
      Given a threat-notes file with the row "| T5-UT-9 | I | threat | control | ADR 0018 | ST-083 | test | Accepted residual |"
      When the threat-notes checker runs on it
      Then the threat-notes checker exits 1 with "not an Accepted ADR"

    Scenario: A residual row naming an Accepted ADR passes
      Given a threat-notes file with the row "| T5-UT-9 | I | threat | control | ADR 0023 | ST-083 | test | Accepted residual |"
      When the threat-notes checker runs on it
      Then the threat-notes checker exits 0 with "0 problem(s)"

  Rule: The Sprint 5 threat notes pass their own gate

    Scenario: The Sprint 5 notes cover the S5 topics, have a disclaimer and no unaccepted residual
      Given the Sprint 5 threat notes
      When the threat-notes checker runs with the Sprint 5 topics and the disclaimer
      Then the threat-notes checker exits 0 with "0 problem(s)"
