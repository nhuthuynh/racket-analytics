# Sprint 6 §7 (ST-170a; FR-170.R1-R3; ADR 0061 Rules 1 and 3.3). Owner: senior-backend-engineer.
# CLI binding: backend/tests/features/test_reference_set.py (racket-reference-lint over a
# reference tree built in a temporary folder, with the repository's pattern catalogue and
# sources register).
@story-ST-170 @fr-170
Feature: A reference value always says where it came from
  Rule: FR-170.R1 An entry without a resolvable source is refused
    Example: complete coach-reviewed entry
      Given reference set "pb-reference" v1 with an AN-09 entry citing "SRC-0002"
      And "SRC-0002" is a row of the sources register
      When racket-reference-lint runs
      Then it exits 0

    Example: missing source
      Given reference set "pb-reference" v1 with an AN-09 entry citing "SRC-0002"
      And the entry has no "source"
      When racket-reference-lint runs
      Then it exits 1 naming the entry and "source"

    Example: unresolved citation
      Given reference set "pb-reference" v1 with an AN-09 entry citing "SRC-9999"
      When racket-reference-lint runs
      Then it exits 1 naming the entry and "unresolved citation"

    Example: citation of a register row that is not resolved
      Given reference set "pb-reference" v1 with an AN-09 entry citing "SRC-0010"
      And "SRC-0010" is a row of the sources register
      When racket-reference-lint runs
      Then it exits 1 naming the entry and "unresolved citation SRC-0010 (unresolved)"

    Example: citation of a register row that exists but was never read
      Given reference set "pb-reference" v1 with an AN-09 entry citing "SRC-0008"
      And "SRC-0008" is a row of the sources register
      When racket-reference-lint runs
      Then it exits 1 naming the entry and "unresolved citation SRC-0008 (exists-unfetched)"

    Example: better_direction differs from the catalogue
      Given reference set "pb-reference" v1 with an AN-09 entry citing "SRC-0002"
      And the entry's "better_direction" is "higher"
      When racket-reference-lint runs
      Then it exits 1 naming the entry and "better_direction"

  Rule: FR-170.R2 A published reference-set version is immutable
    Example: a new version with a changed value is locked next to the old one
      Given reference set "pb-reference" v1 with an AN-09 entry citing "SRC-0002"
      And v2 of the set changes the AN-09 band and is locked
      When racket-reference-lint runs
      Then it exits 0

    Example: v1 edited in place
      Given reference set "pb-reference" v1 with an AN-09 entry citing "SRC-0002"
      And v1 is edited in place after it was locked
      When racket-reference-lint runs
      Then it exits 1 naming "pb-reference@1" and "published version changed"

  Rule: FR-170.R3 A measured entry needs footage that permits "reference-library"
    Example: measured entry with no provenance record
      Given reference set "pb-reference" v1 with an AN-09 entry measured on footage "FTG-0001"
      When racket-reference-lint runs
      Then it exits 1 naming the entry and "FTG-0001"
