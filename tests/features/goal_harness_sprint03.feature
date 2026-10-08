# HARNESS-03 (G03-01 step 8, G03-03; NFR-066 b, FR-006, FR-007; BE-GR1-01). Owner: senior-qa-engineer.
# Binding: infra/tests/test_goal_harness_sprint03_scenarios.py (real Postgres from
# scripts/dev-postgres.sh and real psql for the purge check; local HTTP stand-ins for the object
# store link and for Mailpit). The harness never reads as a pass when it cannot see (fail closed).
@ticket-HARNESS-03 @nfr-066
Feature: The Sprint 3 goal harness measures purge and sign-in honestly

  Rule: The purge check finds every row and object a deleted match or account left behind

    Scenario: A row and a video the purge left behind are found and named
      Given a database holding a deleted match, a deleted account and a kept match
      And a rally video link of the deleted match taken before deletion
      And a purge job that leaves 1 "metric_snapshots" row of the deleted match and the video
      When the purge check runs
      Then the purge check fails
      And it names "metric_snapshots.match_id: 1 rows left"
      And it names "media object still served after purge: status 206"

    Scenario: The purge check fails closed when the database cannot be read
      Given a database holding a deleted match, a deleted account and a kept match
      And a rally video link of the deleted match taken before deletion
      And a purge job that removes every row and object of the deleted match and account
      And a psql command that cannot reach the database
      When the purge check runs
      Then the purge check fails
      And it names "psql rc="

    Scenario: A complete purge leaves nothing, and rows of a kept match are not counted
      Given a database holding a deleted match, a deleted account and a kept match
      And a rally video link of the deleted match taken before deletion
      And a purge job that removes every row and object of the deleted match and account
      When the purge check runs
      Then the purge check passes
      And every inventoried column counts 0 rows, "matches.id" and "accounts.id" among them
      And the video link answered 404

  Rule: Signing in again never reuses a spent sign-in link (G03-01 step 8, BE-GR1-01)

    Scenario: No new sign-in mail means no link
      Given a mailbox whose only sign-in link the harness already used
      When the harness asks for a sign-in link and no new mail arrives
      Then it gets no link

    Scenario: The second sign-in waits for the new mail
      Given a mailbox whose only sign-in link the harness already used
      When a new sign-in mail arrives while the harness waits
      Then it gets the new link, not the spent one
