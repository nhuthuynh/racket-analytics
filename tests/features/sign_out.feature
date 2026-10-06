# Sprint 1 §7.1 + §14.3.2 (ST-014). Owner: senior-qa-engineer. Written before implementation.
# Binding: web/e2e/sprint-01/sign-out.spec.ts (browser storage and caches are client-side).
# API-level support: IT-01-04 (Cache-Control: no-store) and Clear-Site-Data on sign-out.
@M0 @story-ST-014 @nfr-067
Feature: Signing out leaves nothing behind
  Scenario: Shared device
    Given Ivy viewed her match on a shared tablet
    When she signs out and the next person opens the app offline
    Then none of Ivy's matches, facts or videos can be seen

  Rule: Signing out during an upload is a deliberate choice

    Scenario: Upload in progress
      Given Ivy's upload of "Sat doubles" is 64% done
      When she chooses to sign out
      Then she is told "Your upload will stop"
      And she can choose to keep uploading

  Rule: Match video is never stored by the app on the device

    Scenario: Video watched, then signed out
      Given Ivy has watched her match video in the app
      When she signs out
      Then no part of the video remains in the app's storage on the device
