# Sprint 4 ST-071 (FR-008, FR-009; flows-sprint-04 §6 R-01; PM-4 W-R*, W-C*): the UI half of
# tests/features/video_retention.feature (ST-069) and training_consent.feature (ST-070). Bound by
# Vitest + Testing Library in web/tests/features/privacy-settings-ui.test.tsx (the contract test
# web/tests/contract/privacy-settings.test.ts covers the wire). Flag-on E2E: E2E-04-07.
@M5 @story-ST-071 @privacy @web
Feature: Privacy settings
  A player chooses how long their match videos are kept and whether their matches may be used
  to train the app, and sees when each video will be deleted.

  Background:
    Given the video setting and the training choice are turned on
    And the player keeps videos for 90 days and has the match "Demo match" with a video

  Rule: A failed save never changes the setting (FR-008, FR-009)

    Scenario: Saving the video setting fails
      Given saving the video setting will fail
      When the player chooses "30 days" and saves the video setting
      Then the page says "We couldn't save your choice. Your old setting still applies. Try again."
      And "90 days (default)" is still chosen

  Rule: The player sees and changes how long videos are kept (FR-008)

    Scenario: Choosing a shorter time shows the new deletion date
      When the player chooses "30 days" and saves the video setting
      Then the page says "Saved. The new deletion dates are shown below."
      And "Demo match" says "Video will be deleted on 28 Nov 2026"

  Rule: Training use is off unless the player turns it on (FR-009)

    Scenario: Training use is off by default
      Then "Use my matches to improve the app" is not ticked

    Scenario: Turning training use on
      When the player ticks "Use my matches to improve the app" and saves the training choice
      Then the page says "Turned on. You can turn it off here at any time."

  Rule: The page exists only when a privacy setting is turned on

    Scenario: Both settings turned off
      Given the video setting and the training choice are turned off
      When the player opens the privacy settings
      Then the app's not-found page is shown
