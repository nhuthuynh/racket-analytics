# ST-078a (sprint-05 §3; NFR-050.1, NFR-050.4, NFR-050.5; scorecard G05-07): the ASVS L2 release review fails closed.
Feature: The ASVS status tool counts the checklist per chapter and fails on unreviewed rows
  As the security-privacy-engineer running the R1 ASVS L2 release review
  I want every applicable row assessed, every Fail owned and every Pass backed by evidence
  So that the release review cannot report a pass the checklist does not show

  Rule: An applicable row must be assessed

    Scenario: A planted "Not assessed" row is refused
      Given an ASVS checklist with the V1 row "| 1.1.1 | 2 | decode once | Yes | Not assessed | security | — |"
      When the ASVS status tool runs on it with the G05-07 rules
      Then the ASVS status tool exits 1 with "FAIL not-assessed: 1.1.1"

    Scenario: A planted legacy "S0 planned" row counts as not assessed
      Given an ASVS checklist with the V1 row "| 1.2.4 | 1 | parameterised queries | Yes | S0 planned | BE ST-005 | code review |"
      When the ASVS status tool runs on it with the G05-07 rules
      Then the ASVS status tool exits 1 with "FAIL not-assessed: 1.2.4"

  Rule: A Fail row needs an owner and a Pass row needs evidence

    Scenario: A planted Fail row without a fix ticket or a residual-risk owner is refused
      Given an ASVS checklist with the V5 row "| 5.4.3 | 2 | antivirus | Yes | Fail | security | no scanner |"
      When the ASVS status tool runs on it with the G05-07 rules
      Then the ASVS status tool exits 1 with "FAIL fail-without-owner: 5.4.3"

    Scenario: A planted Pass row without an evidence command or test id is refused
      Given an ASVS checklist with the V3 row "| 3.3.4 | 2 | HttpOnly | Yes | Pass | security | code review |"
      When the ASVS status tool runs on it with the G05-07 rules
      Then the ASVS status tool exits 1 with "FAIL pass-without-evidence: 3.3.4"

    Scenario: An owned Fail row and an evidenced Pass row pass
      Given an ASVS checklist with the V3 row "| 3.3.4 | 2 | HttpOnly | Yes | Pass | security | `test_outside_test_the_cookie_meets_the_host_prefix_rules` |"
      And the V5 row "| 5.4.3 | 2 | antivirus | Yes | Fail | P19 (residual) | no scanner |"
      When the ASVS status tool runs on it with the G05-07 rules
      Then the ASVS status tool exits 0 with "0 problem(s)"

  Rule: The real checklist passes its own gate for the chapters ST-078a assessed

    Scenario: Chapters V1-V5 of the real checklist have no unassessed, unowned or unevidenced row
      Given the real ASVS L2 checklist
      When the ASVS status tool runs on it with the G05-07 rules for chapters V1-V5
      Then the ASVS status tool exits 0 with "0 problem(s)"
