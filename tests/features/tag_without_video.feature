# MVP-02 (MVP goal, PO 2026-10-15; FR-050). Owner: senior-frontend-engineer.
# Live finding on main 6c666b9: in a browser that cannot play the match video, T-01 offers to tag
# without it, but only rally 1 was saved; every later "Rally start" was refused.
# Browser binding: web/e2e/sprint-03/mvp-02-tag-without-video.spec.ts (live stack; the video is
# made unplayable in every browser: media request aborted, decode error, time stuck at 0).
# Unit bindings: web/tests/unit/mvp-02-tag-without-video.test.tsx (T-01 with the reducer) and
# web/tests/unit/mvp-02-rally-clock.test.ts (the rally clock).
@story-MVP-02 @fr-050
Feature: Tagging without a playable video
  When the browser cannot play the match video, the rally times come from the page clock,
  carried on from the end of the last tagged rally, so every rally can be tagged.

  Rule: Every rally tagged without the video is recorded

    Scenario: A later rally start is not refused
      Given Ivy's browser cannot play her match video
      And she has tagged rally 1 without the video
      When she marks the start of rally 2
      Then she is not told that the rally starts before the end of rally 1

    Scenario: Three rallies tagged without the video
      Given Ivy's browser cannot play her match video
      And she is told "If you tag without it, the rally times will not match the video."
      When she tags 3 rallies without the video
      Then the score sheet shows 3 rallies
      And each rally starts after the one before it ends

    Scenario: A video that plays still gives the rally times
      Given Ivy's browser plays her match video
      When she marks a rally from 12 s to 16.5 s of the video
      Then the rally is saved from 12000 ms to 16500 ms
