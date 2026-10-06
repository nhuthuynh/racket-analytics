# Sprint 2 §14.3.2 (C-02). Owner: senior-qa-engineer. API binding:
# backend/tests/features/test_upload_quota.py; the repeated parallel cases are IT-02-11.
@M0 @story-C-02 @nfr-023
Feature: Upload quota under parallel requests
    Scenario: 14.3.2 Eight uploads started at the same moment
      Given Ivy may have 3 unfinished uploads at once
      When 8 uploads are started for her at the same moment
      Then exactly 3 are accepted
      And the other 5 are refused with a reason
