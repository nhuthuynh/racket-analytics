# Sprint 4, ticket ST-064 (sre-devops-engineer; QD §7; goal G04-06).
# Binding: IT-04-11 infra/tests/test_seed_demo_plan.py, against a loopback fake of the public API
# (infra/tests/demo_fake_api.py) in which Ivy has a complete demo match. A new file beside
# demo_seed.feature, which is protected (decisions ST-064 row 1).
@M4 @ticket-ST-064
Feature: `make demo` also gives the demo user a 2-week plan

  Rule: The plan step fails loudly, and only after the match is seeded

    Scenario: The plan step fails and the demo exits 1 naming the step
      Given a dev stack where Ivy has a complete demo match
      And the plan API refuses to generate a plan with "no_plan_fits"
      When the developer runs the demo
      Then the demo fails with exit code 1 naming the step "generate the plan"
      And the demo prints no plan page

  Rule: Ivy gets one plan with the fixed demo preferences, and running the demo again adds nothing

    Scenario: The demo generates Ivy's plan with the demo preferences
      Given a dev stack where Ivy has a complete demo match
      When the developer runs the demo
      Then the demo exits 0 and prints the stack's plan page
      And the plan was generated once with solo, 30 min, 3 sessions a week, no ball machine, intermediate

    Scenario: Running the demo again keeps the same plan id
      Given a dev stack where Ivy has a complete demo match
      When the developer runs the demo
      And the developer runs the demo again
      Then both runs name the same plan id
      And the plan was generated once with solo, 30 min, 3 sessions a week, no ball machine, intermediate
