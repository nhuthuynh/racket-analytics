# Sprint 5, ST-077 (NFR-063.1-.2; IT-05-05; ADR 0058 rule 5.3; SEC-5 T5-BK-1; AQS/SEC-05
# 14.1.1, 14.1.2). Steps: backend/tests/integration/test_it_05_data_classification.py.
# Negative cases first: a planted unclassified column, a planted unclassified backup
# artefact, and a walk that finds zero backup artefacts all fail the check; a column the
# API returns, or a sum or time it computes from it, is never marked server-side only
# (SPE-ST077-01, SPE-ST077-R2-01); nor is an object key the owner gets inside a presigned
# video link or an id copied from one the owner reads (SPE-ST077-R3-01).
@story-ST-077 @nfr-063
Feature: Every stored datum has a class with encryption, retention and access rules

  Scenario: A planted unclassified column is reported
    Given the data-classification map
    And a live table with a column the map does not name
    When the database schema is walked
    Then the planted column is reported as unclassified

  Scenario: A planted unclassified backup artefact is reported
    Given the data-classification map
    And an on-demand backup set holding a file the map does not name
    When the backup artefacts are walked
    Then the planted file is reported as unclassified

  Scenario: A walk that finds zero backup artefacts fails
    Given the data-classification map
    And an empty backup directory
    When the backup artefacts are walked
    Then the check fails because no backup artefact was found

  Scenario: No upload-session column the API returns to its owner is marked server-side only
    Given the data-classification map
    And an unfinished upload of a demo video
    When the owner reads the match and the upload offset
    Then no column of that upload session the API returned is marked server-side only

  Scenario: No stored-video size or rate-limit time the quota read returns is marked server-side only
    Given the data-classification map
    And a stored demo video and match creations at the hourly limit
    When the owner reads the quota and is refused one more match
    Then no stored-video or rate-limit column the API returned is marked server-side only

  Scenario: No object key or id copy the owner reads through the video link or /me is marked server-side only
    Given the data-classification map
    And a stored and probed demo video
    When the owner reads the account, the match and the video link
    Then no media, upload, job or account column the API returned is marked server-side only

  Scenario: Every table, column, bucket prefix and backup artefact of the live stack is classified
    Given the data-classification map
    And a migrated database, a demo upload and an on-demand backup
    When every store is walked
    Then no table, column, bucket prefix or backup artefact is unclassified
    And every class and every row has an encryption, a retention and an access rule
