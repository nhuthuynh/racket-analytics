# Sprint 3 ST-052a (FR-150, FR-151): the Full Tag domain (racket.dataset.full_tag), with no API
# and no database. Steps: backend/tests/features/test_full_tag_domain.py. The API and browser
# view of the same rules is full_tag.feature (QA-ACC-3; red until the label routes, ST-052c).
@M0 @story-ST-052 @fr-150
Feature: Full Tag access, consent and label session
  Only a labeller can open Full Tag, only on a match with a team-held consent record, and every
  label the session accepts keeps the full-tag-labels/v1 export valid.

  Rule: Full Tag is not available to a player, and needs a consent record

    Scenario: A player is never offered Full Tag, even on a consented match
      Given match "m-1" has a team-held consent record
      When a player who is not a labeller asks for Full Tag on match "m-1"
      Then the answer is "not available"

    Scenario: A labeller on a match without a consent record is told why
      Given match "m-2" has a team-held consent record
      When a labeller asks for Full Tag on match "m-1"
      Then the answer is "no consent"

    Scenario: A consent reference that could hold a name is refused
      When a consent record for match "m-1" is made with the reference "Ivy Smith, 4 Elm Road"
      Then the consent record is refused because it must be a code

    Scenario: A labeller on a consented match may label it
      Given match "m-1" has a team-held consent record
      When a labeller asks for Full Tag on match "m-1"
      Then the answer is "allowed"

  Rule: Every accepted command keeps the export valid

    Scenario: A hit by a player who is not in the match is refused and the export stays valid
      Given a labeller has marked a rally from frame 1,800 to 1,900 on a 3,600-frame clip
      When they tag a hit by player "Z9" at frame 1,840
      Then the label is refused naming "Z9"
      And the export is valid against full-tag-labels/v1 with no hit

    Scenario: A hit outside the clip is refused
      Given a labeller has marked a rally from frame 1,800 to 1,900 on a 3,600-frame clip
      When they tag a hit by player "B1" at frame 3,600
      Then the label is refused naming "outside the clip"

    Scenario: A hit outside every marked rally is refused
      Given a labeller has marked a rally from frame 1,800 to 1,900 on a 3,600-frame clip
      When they tag a hit by player "B1" at frame 100
      Then the label is refused naming "mark the rally first"

    Scenario: Labeller tags a hit and the export carries its frame and player
      Given a labeller has marked a rally from frame 1,800 to 1,900 on a 3,600-frame clip
      When they tag a hit by player "B1" at frame 1,840
      Then the export is valid against full-tag-labels/v1 and holds a hit by "B1" at frame 1840
