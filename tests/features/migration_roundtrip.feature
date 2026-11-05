# ST-082 (REL-1.3; ADR 0058 rule 7 "Every migration is reversible"); IT-05-10 is the integration form.
Feature: Every database migration can be stepped down and up again
  As the sre-devops-engineer who rolls a release back with `alembic downgrade`
  I want each migration to round-trip on a seeded database
  So that the rollback in ADR 0058 rule 7 step 2 never meets a one-way migration

  Rule: REL-1.3 Every Alembic migration since the R1 baseline downgrades one step and upgrades again on a seeded copy

    Scenario: The real migrations each round-trip on a seeded database
      Given a scratch database at the head revision with seed rows
      When every migration is stepped down one revision and up again from the head
      Then every step returned to its revision with the same schema
      And no seed row in a table that outlived the downgrade was lost

    Scenario: A migration without a downgrade is refused
      Given a migration directory where "0002" has no downgrade
      When the migrations are checked for a downgrade
      Then the check names "0002"
