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

  Rule: With the flags off nothing the flags add is served and no limit applies (G04-09 a, G04-10 c)

    Scenario: A privacy route still served with the flags off is found
      Given a flags-off stack that still serves "/me/quota"
      When the steps "flags-off" run
      Then the step fails, naming "flag route answered 200"

    Scenario: A match that cannot be created with the flags off is found, not skipped
      Given a flags-off stack that refuses new matches
      When the steps "flags-off" run
      Then the step fails, naming "match creation failed"

    Scenario: An over-quota upload that errors with the flags off is found
      Given a flags-off stack that answers the over-quota upload with 500
      When the steps "quota" run
      Then the step fails, naming "status 500"

    Scenario: Flags off with every limit lifted passes
      Given a flags-off stack
      When the steps "flags-off burst quota" run
      Then every step passes

  Rule: The verdict is every step at once (exit 0 only when all pass, else 1)

    Scenario: One failing flags-off step makes the harness exit 1
      Given a flags-off stack that still serves "/me/quota"
      When the harness runs against the stack with "--flags off --runs 1 --quotas"
      Then it exits 1 with "flags_off" failing

    Scenario: A clean flags-off stack makes the harness exit 0
      Given a flags-off stack
      When the harness runs against the stack with "--flags off --runs 2 --quotas"
      Then it exits 0 with every step passing

    Scenario: A flags-on run whose match cannot be prepared exits 1
      Given a stack that refuses under-18 answers without writing a row
      When the harness runs against the stack with "--flags on --runs 1"
      Then it exits 1 with "prepare" failing

    Scenario: A wrong count of billing alert rules fails the quota steps
      Given a stack that accepts 10 matches an hour and refuses uploads past the quota
      And an alert rules file with 5 rules
      When the quota steps run with the alert test
      Then the "alerts" step fails, naming "5 billing alert rules, want 6"

    Scenario: Exact limits and a passing alert test pass the quota steps
      Given a stack that accepts 10 matches an hour and refuses uploads past the quota
      And an alert rules file with 6 rules
      When the quota steps run with the alert test
      Then every quota step passes

  Rule: Without its instruments the harness refuses to judge (exit 2)

    Scenario Outline: A missing instrument refuses to start
      When the harness starts with "<args>"
      Then it exits 2, naming "<option>"

      Examples:
        | args                                                         | option             |
        | --flags on --runs 1                                          | --psql             |
        | --flags on --psql p --purge-cmd p --label-set-cmd p --quotas | --stored-bytes-cmd |
