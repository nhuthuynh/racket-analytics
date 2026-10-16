# Sprint 3, ticket MVP-03 (senior-backend-engineer; PO MVP goal 2026-10-15).
# Binding: infra/tests/test_demo_seed_scenarios.py. The refusal scenarios run everywhere (a stub
# API on loopback); the seeding scenarios run against a live Compose stack (`make up`) named by
# RA_DEMO_BASE_URL, as the CI web-checks job does after its Playwright journeys.
# The demo is a client of the public HTTP API only: it changes no product behaviour.
@M3 @ticket-MVP-03
Feature: A new developer sees a ready-to-explore match after `make demo`

  Rule: The demo seeds only a dev-profile stack

    Scenario: The demo refuses a production profile and sends nothing
      Given a stack whose profile is "prod"
      When the developer runs the demo
      Then the demo is refused with "only against the dev profile"
      And the stack received no request

    Scenario: The demo refuses a stack whose dev sign-in is disabled
      Given a stack whose profile is "dev" but whose dev sign-in is disabled
      When the developer runs the demo
      Then the demo is refused with "dev sign-in is disabled"
      And no match was created

  Rule: One demo match with stats is ready to explore, and running the demo again adds nothing

    Scenario: A fresh stack shows stats for the demo match
      Given a running dev stack
      When the developer runs the demo
      Then the demo prints the match's stats page and "Sign in as Ivy"
      And the demo match has 12 tagged rallies
      And its stats show published metrics for both sides
      And "Show me" lists the rallies behind a metric

    Scenario: Running the demo again reuses the demo match
      Given a running dev stack
      When the developer runs the demo
      And the developer runs the demo again
      Then both runs name the same demo match
      And the demo match has 12 tagged rallies
