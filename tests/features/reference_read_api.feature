# Sprint 6 §7 (ST-170b; FR-170.R4, NFR-050.10; SEC-6 T6-PL-3, T6-PL-4, T6-PL-6; ADR 0061 "ACL read
# side"). Owner: senior-backend-engineer. API binding: backend/tests/features/
# test_reference_read_api.py (the real app on Postgres, reference tree built in a temporary folder
# and linted with the repository's pattern catalogue and sources register).
@story-ST-170 @fr-170
Feature: Players read only coach-reviewed or verified reference entries
  Rule: FR-170.R4 The reference read API returns only entries with status coach-reviewed or verified, each with its source_type, citation and version
    Example: set with 3 coach-reviewed and 1 draft entry
      Given reference set "pb-reference" v1 with 3 coach-reviewed entries and 1 draft entry
      When "ivy" reads the current reference set
      Then the answer is 200 with 3 entries
      And every entry has its source_type, citation, version and provenance label
      And no entry is a draft

    Example: a draft entry is never returned, also not by id
      Given reference set "pb-reference" v1 with 3 coach-reviewed entries and 1 draft entry
      When "carlos" reads the draft entry by id
      Then the answer is 404 with the same body as an unknown entry id

  Rule: NFR-050.10 Reference answers are for signed-in users only, never cached, and read-only
    Example: an anonymous caller is refused
      Given reference set "pb-reference" v1 with 3 coach-reviewed entries and 1 draft entry
      When "anonymous" reads the current reference set
      Then the answer is 401
      And the answer says "Cache-Control: no-store"

    Example: no write route
      Given reference set "pb-reference" v1 with 3 coach-reviewed entries and 1 draft entry
      When "ivy" sends POST, PUT, PATCH and DELETE to a reviewed entry
      Then every answer is 405
