# Sprint 4, ST-070 (FR-009; OQ-06 accepted, ADR 0023; api-sprint-04 §6; context map R9;
# SEC-4 T4-CS-1..T4-CS-4). Steps: backend/tests/features/test_training_consent.py.
# Negative case first: a player who has not opted in is never in a built label set.
@story-ST-070
Feature: Training-data consent decides whose matches enter a label set

  Scenario: User has not opted in
    Given the training consent setting is on
    And Ivy has a tagged match
    And Ivy has not opted in to training use
    When the next label set is built
    Then none of Ivy's matches or corrections are in it

  Scenario: User revokes consent
    Given the training consent setting is on
    And Ivy has a tagged match
    And Ivy opted in to training use
    And the label set built then holds Ivy's match
    When Ivy revokes training use
    And the next label set is built
    Then none of Ivy's matches are in it
    And the label set built before the revoke is unchanged

  Scenario: Another player's opt-in does not include my match
    Given the training consent setting is on
    And Ivy has a tagged match
    And Carlos has a tagged match
    And Carlos opted in to training use
    When the next label set is built
    Then Carlos's match is in it
    And none of Ivy's matches or corrections are in it

  Scenario: Flag off keeps the team-held consent rule
    Given the training consent setting is off
    And Ivy has a tagged match
    And Carlos has a tagged match with a team-held consent record
    When the next label set is built
    Then Carlos's match is in it
    And none of Ivy's matches or corrections are in it
    And the training consent setting is not found
