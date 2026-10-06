# Sprint 1 §7.2 + §14.3.3 (ST-015). Owner: senior-qa-engineer. Written before implementation.
# Binding: web/e2e/sprint-01/first-run-and-guide.spec.ts (static client content; no API).
# Wording: docs/domain/capture-guide-wording.md (coach sign-off pending, sprint-01 P9).
@M0 @story-ST-015 @nfr-033
Feature: First run and capture guide
  Rule: The app says plainly what it can and cannot do

    Scenario: New user sees capabilities and limits
      Given Ivy has just created her account
      When the app opens for the first time
      Then she sees what the app does and what it cannot do, in plain words
      And she can continue to the capture guide

  Rule: Every filming instruction is available as text

    Scenario: Read the guide without playing the video
      Given Ivy opens the capture guide
      When she reads it without playing the video
      Then every setup instruction is available as text with an illustration
      And there are no more than 6 instructions

    Scenario: Watch the guide video
      Given Ivy opens the capture guide
      When she plays the guide video
      Then captions are shown by default

  Rule: The first-run screen is honest about Release 1

    Scenario: The app does not claim to score automatically
      Given Ivy has just created her account
      When the app opens for the first time
      Then she is told that she marks who won each rally and the app keeps the score
      And she is told that scores are unofficial until the rules are verified

  Rule: The guide still works when the video does not

    Scenario: Guide video cannot load
      Given the guide video cannot be loaded
      When Ivy opens the capture guide
      Then she sees "Everything in it is in the checklist above"
      And all setup instructions are still shown
