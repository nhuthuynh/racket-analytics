# Sprint 0 §7. Owner: senior-qa-engineer. Written before implementation (ST-012).
# Steps: backend/tests/features/test_object_level_authorisation.py
# Regression suite: backend/tests/regression/test_bola_matrix.py (IT-00-02).
@M0 @story-ST-006 @nfr-051 @nfr-064
Feature: Object-level authorisation for matches
  Every resource ID is checked against its owner.

  Rule: Another user cannot see or change my match

    Scenario Outline: Carlos tries to use Ivy's match
      Given Ivy owns a match
      When Carlos tries to <action> that match by its ID
      Then Carlos gets the same "not found" result as for a match that does not exist
      And the attempt appears in the security log without Ivy's details
      Examples:
        | action       |
        | open         |
        | upload to    |
        | see facts of |

    Scenario: My match list shows only my matches
      Given Ivy owns 2 matches and Carlos owns 1 match
      When Carlos opens his matches list
      Then he sees exactly 1 match

  Rule: Every route that takes an ID is covered by the BOLA matrix

    Scenario: A new route without BOLA coverage
      Given a route that takes a match ID is added without a BOLA matrix entry
      When the regression suite runs
      Then the suite fails and names the uncovered route
