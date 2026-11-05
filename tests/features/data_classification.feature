# Sprint 5, ST-077 (NFR-063.1-.2; IT-05-05; ADR 0058 rule 5.3; SEC-5 T5-BK-1; AQS/SEC-05
# 14.1.1, 14.1.2). Steps: backend/tests/integration/test_it_05_data_classification.py.
# Negative cases first: a planted unclassified column, a planted unclassified backup
# artefact, and a walk that finds zero backup artefacts all fail the check.
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

  Scenario: Every table, column, bucket prefix and backup artefact of the live stack is classified
    Given the data-classification map
    And a migrated database, a demo upload and an on-demand backup
    When every store is walked
    Then no table, column, bucket prefix or backup artefact is unclassified
    And every class and every row has an encryption, a retention and an access rule
