# ST-076c (NFR-045.1-.4; ADR 0058 rule 4, rule 6 check). Owner: sre-devops-engineer.
# Written before the binding ran green. Binding: infra/tests/test_restore_drill_scenarios.py.
# The @integration examples run the real scripts/ops/restore_drill.py on a Compose project of
# their own (the G05-03 drill); the @unit example checks a recorded drill report.
@ticket-ST-076c @nfr-045
Feature: A restore loses no confirmed correction
  Rule: NFR-045.3 Corrections fingerprint is equal after restore

    @integration
    Example: clean drill
      Given a seeded stack with a fresh backup
      When the volumes are destroyed and restored
      Then the corrections count and SHA-256 equal the values before
      And the object count and SHA-256 equal the values before
      And the RPO is at most 24 hours and the RTO at most 240 minutes
      And the drill exits with code 0

    @integration
    Example: a correction lost
      Given a backup taken after one confirmed correction was deleted
      When the drill compares fingerprints
      Then the drill fails naming "corrections"

  Rule: The drill verdict fails closed

    @unit
    Example: the recorded report of a planted drill fails the check
      Given the recorded report of a drill with a planted deleted correction
      When the report is checked
      Then the drill fails naming "corrections"
