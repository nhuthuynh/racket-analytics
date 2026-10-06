# Sprint 2 §14.3.3 (C-03). Owner: senior-qa-engineer. Browser binding only:
# web/e2e/sprint-02/upload-recovery.spec.ts.
@M0 @story-C-03
Feature: Recover from an upload server error
    Scenario: 14.3.3 The server fails during the upload
      Given Ivy's upload is at 40%
      When the server answers with an error
      Then she sees "Try again" and a support reference
      And she does not see "No video yet"
      And trying again continues from 40%
