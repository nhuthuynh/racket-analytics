# Sprint 5, ticket QA-VERIFY04R5-01 (senior-backend-engineer; DEMO-1.1; IT-05-11; goal G05-09).
# Binding: infra/tests/test_seed_demo_plan.py, against the loopback fake of the public API
# (infra/tests/demo_fake_api.py) with the age gate on or off. The live flag-on run is
# infra/tests/test_demo_seed_live.py; the service the demo calls is pinned by
# backend/tests/integration/test_it_05_11_demo_age_confirmation.py.
@M5 @ticket-QA-VERIFY04R5-01
Feature: `make demo` works on a stack with the R1 feature flags on

  Rule: The age step fails loudly, before anything is seeded

    Scenario: The age-confirmation API refuses and the demo exits 1 naming the step
      Given a dev stack with the age gate on where Ivy has not confirmed her age
      And the age-confirmation API refuses the answer with "under_age"
      When the developer runs the demo
      Then the demo fails with exit code 1 naming the step "confirm the demo user's age"
      And no match or plan was requested

  Rule: The demo user's age is confirmed through the public age-confirmation API, once

    Scenario: On a flag-off stack the demo sends no age answer
      Given a dev stack where Ivy has a complete demo match
      When the developer runs the demo
      Then the demo exits 0 and prints the stack's plan page
      And no age answer was sent

    Scenario: On a flag-on stack the demo confirms Ivy's age before it reads her matches
      Given a dev stack with the age gate on where Ivy has not confirmed her age
      When the developer runs the demo
      Then the demo exits 0 and prints the stack's plan page
      And Ivy's age was confirmed once with the adult answer before any match was read

    Scenario: Running the demo again on a flag-on stack confirms nothing again
      Given a dev stack with the age gate on where Ivy has not confirmed her age
      When the developer runs the demo
      And the developer runs the demo again
      Then both runs name the same plan id
      And Ivy's age was confirmed once with the adult answer before any match was read
