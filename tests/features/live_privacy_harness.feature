# QA-HARNESS-4b (G04-09, G04-10; FR-003, FR-008, FR-009, FR-160, NFR-023, NFR-022). Owner: senior-qa-engineer.
# Binding: infra/tests/test_live_privacy_harness_scenarios.py (a local HTTP stub of the Sprint 4
# routes of api-sprint-04 §4-§7, a real Postgres from scripts/dev-postgres.sh read through real
# psql, and stub commands for the purge job, the label-set build and the stored-bytes count).
# The harness never reads as a pass when it cannot see (fail closed, ADR 0014).
@ticket-QA-HARNESS-4b
Feature: The privacy and quota harness measures G04-09 and G04-10 honestly

  Rule: An under-18 answer creates no account row (G04-09 b)

    Scenario: An account row written for an under-18 answer is found
      Given a stack that writes an account row when the answer is under 18
      When the age step runs
      Then the step fails, naming "1 new account rows"

    Scenario: The age step fails closed when the database cannot be read
      Given a stack that refuses under-18 answers without writing a row
      And a psql command that cannot reach the database
      When the age step runs
      Then the step fails, naming "psql rc="

    Scenario: A refused under-18 answer and a usable adult account pass
      Given a stack that refuses under-18 answers without writing a row
      When the age step runs
      Then the step passes

  Rule: Consent and retention are judged on the account's own match (G04-09 c, d)

    Scenario: A match still in the label set after revoking is found
      Given a label-set build that lists the match whatever the consent
      When the consent step runs
      Then the step fails, naming "in the label set after revoke"

    Scenario: A review video still served after the purge is found
      Given a purge job that leaves the review video
      When the retention step runs
      Then the step fails, naming "review video status 206 after purge"

    Scenario: A label set that follows consent and a purged video pass
      Given a label-set build that lists the match only while consent is on
      And a purge job that deletes the review video
      When the consent step runs and the retention step runs
      Then both steps pass

  Rule: Limits hold exactly over a burst (G04-10 a, b)

    Scenario: An 11th match accepted within the hour is found
      Given a stack that accepts 11 matches an hour
      When the burst step runs
      Then the step fails, naming "11 accepted"

    Scenario: Bytes stored by a refused over-quota upload are found
      Given a stack that refuses the over-quota upload but stores its bytes
      When the quota step runs
      Then the step fails, naming "stored bytes changed"

    Scenario: Exact limits pass
      Given a stack that accepts 10 matches an hour and refuses uploads past the quota
      When the burst step runs and the quota step runs
      Then both steps pass

  Rule: Without its instruments the harness refuses to judge (exit 2)

    Scenario Outline: A missing instrument refuses to start
      When the harness starts with "<args>"
      Then it exits 2, naming "<option>"

      Examples:
        | args                                                         | option             |
        | --flags on --runs 1                                          | --psql             |
        | --flags on --psql p --purge-cmd p --label-set-cmd p --quotas | --stored-bytes-cmd |
