# Sprint 1 §14.3.8 (ST-024). Owner: senior-qa-engineer. Written before implementation.
# Binding: backend/tests/features/test_nightly_quality.py (the SLI arithmetic and the
# status.json result fields; the workflow itself is checked by infra/tests, SRE lane).
@M0 @story-ST-024 @nfr-041 @nfr-042
Feature: Nightly quality jobs and service-level indicators

  Rule: Nightly results are published where the team reads them

    Scenario: Nightly run completes
      Given the nightly quality run has finished
      When the team opens the sprint status file
      Then it shows the oracle result and the mutation score with the run date

  Rule: Upload completion and availability are measured

    Scenario Outline: Upload outcome counted
      Given an upload that <outcome>
      When the upload completion indicator is read
      Then that upload is counted as <counted>
      Examples:
        | outcome                                   | counted         |
        | reached full length                       | completed       |
        | was resumed by a live client and finished | completed       |
        | was abandoned by the user                 | not in the base |

    Scenario: Rate-limited requests do not count against availability
      Given 100 requests of which 2 were rate limited and none failed
      When the availability indicator is read
      Then availability is 100%
