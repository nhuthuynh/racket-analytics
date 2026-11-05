# Sprint 5, ST-078d (NFR-067.1; G05-06; story ST-078). Owner: senior-backend-engineer.
# Written before the binding ran. Binding: backend/tests/features/test_no_store.py. The route
# list is the app's own GET inventory; IT-05-06 (backend/tests/integration/test_it_05_no_store.py)
# carries the same check with the error answers and the anonymous controls. Negative case first.
@ticket-ST-078d @nfr-067
Feature: A shared cache never keeps a player's data
  Rule: Every authenticated GET answer says "Cache-Control: no-store"

    Scenario: A route that asks to be cached
      Given a route answers Ivy with "Cache-Control: public, max-age=3600"
      When Ivy opens it through the API edge
      Then the answer says only "no-store"

    Scenario: Every page of Ivy's own data
      Given Ivy has a tagged match and a training plan
      When Ivy opens every authenticated GET route of the API
      Then every answer says only "no-store"
