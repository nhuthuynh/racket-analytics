# ST-052b (FR-150, NFR-078; api-sprint-03 §5.5). Owner: senior-ml-cv-engineer, QA to accept.
# API binding: backend/tests/features/test_labeller_admin.py. The operator runs
# `python -m racket.dataset.admin` in the api container; the label routes are ST-052c
# (full_tag.feature).
@M0 @story-ST-052 @fr-150
Feature: Labeller role and team-held consent record
  Rule: Only an operator makes a labeller or records consent, and only with a reference code

    Scenario: Consent written as a person's name is refused and nothing is stored
      Given Dana has a received match
      When the operator records consent for it as "Ivy Example <ivy@example.com>"
      Then the operator is told the input was refused
      And the match has no consent record

    Scenario: Consent for a deleted match is refused and nothing is stored
      Given Dana has deleted a received match
      When the operator records consent for it as "CONSENT-TEAM-001"
      Then the operator is told the input was refused
      And the match has no consent record

    Scenario: The operator records the team's consent reference for a match
      Given Dana has a received match
      When the operator records consent for it as "CONSENT-TEAM-001"
      And the operator records consent for it again as "CONSENT-TEAM-002"
      Then the match has one consent record with reference "CONSENT-TEAM-002"

    Scenario: A deleted account cannot be made a labeller
      Given Ivy has deleted her account
      When the operator grants Ivy the labeller role
      Then the operator is told the input was refused
      And Ivy holds no role

    Scenario: Revoking the role of an unknown account is refused
      Given an account id that belongs to no account
      When the operator revokes the labeller role of that account
      Then the operator is told the input was refused

    Scenario: The operator grants and revokes the labeller role
      Given Dana has a normal player account
      When the operator grants Dana the labeller role
      Then Dana is a labeller
      When the operator revokes Dana's labeller role
      Then Dana is not a labeller

    Scenario: Purging a deleted match removes its consent record and label session
      Given Dana has a received match with a consent record and a label session
      When Dana deletes the match and the clean-up runs
      Then no consent record or label session of the match is left
