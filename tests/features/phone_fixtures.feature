# Sprint 1 §14.3.9 (ST-025). Owner: senior-qa-engineer. Written before the fixture set exists.
# Binding: backend/tests/features/test_phone_fixtures.py (RED until ST-025 adds
# fixtures/clips/phones-v1/manifest.json; uses racket-manifest-check from ST-011).
@M0 @story-ST-025 @nfr-025
Feature: Phone-file fixtures cover what players upload

  Rule: The fixture set is broad enough and documented

    Scenario: Coverage of the set
      Given the phone fixture set version 1
      Then it has files from at least 5 phone models
      And at least one file has a variable frame rate
      And every file is listed in its manifest with model, frame rate and consent status

  Rule: Footage with people needs recorded consent

    Scenario: File with people and no consent record
      Given a fixture file shows people
      And its manifest has no consent record
      When the integrity check runs
      Then the check fails and names the file

  Rule: Every phone file is readable by the probe

    Scenario: Probe every fixture
      Given the phone fixture set version 1
      When each file is probed
      Then every file reports container, codec, frame rate and duration
