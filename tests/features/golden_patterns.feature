# Sprint 6 §3.3 QA-REF-GOLD (story ST-170; FR-171.R2-R4, FR-172.R1; ADR 0061 Rule 6; NFR-078).
# Owner: senior-qa-engineer. Binding: backend/tests/features/test_golden_patterns.py (the
# integrity check over a copy of the frozen files in a temporary folder).
# The product goldens (backend/tests/regression/golden_patterns/test_golden_*.py) are
# red_until ST-171b, ST-171c, ST-171d and ST-172a; these scenarios guard the frozen values.
@story-ST-170 @fr-171 @fr-172
Feature: Frozen golden pattern values change only with an ADR
  Rule: A frozen vector, reference or input fixture is protected by its hash and an ADR

    Example: the frozen files as committed
      Given the frozen golden pattern files and their lock
      When the golden integrity check runs
      Then it reports no problem

    Example: a vector edited without a new lock row
      Given the frozen golden pattern files and their lock
      And the AN-09 value of gp1-doubles side A is edited in the measures vector
      When the golden integrity check runs
      Then it names the measures vector as "edited without an ADR"

    Example: the GS-PAT-1 input fixture edited
      Given the frozen golden pattern files and their lock
      And a rally of gp2-singles is edited in the GS-PAT-1 fixture
      When the golden integrity check runs
      Then it names the GS-PAT-1 fixture as "edited without an ADR"

    Example: a lock row naming an ADR that does not exist
      Given the frozen golden pattern files and their lock
      And the measures vector is edited and locked by a row naming "docs/decisions/0999-no-such-adr.md"
      When the golden integrity check runs
      Then it reports "docs/decisions/0999-no-such-adr.md" as "does not exist"

    Example: a lock row reusing the ADR of the first freeze
      Given the frozen golden pattern files and their lock
      And the measures vector is edited and locked by a row naming the first row's ADR
      When the golden integrity check runs
      Then it reports the problem "already authorised change 1"
