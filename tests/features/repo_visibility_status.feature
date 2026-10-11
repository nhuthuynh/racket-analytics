# FIX-03-1c (sprint-03 §9.1, S3-DoD-P10; finding SEC-RV3-01; PO P12 option b): repository
# visibility is a human item (P10). Its status is measured from what GitHub tells an
# unauthenticated reader and from the PO's recorded P10 answer, never written by hand, so no
# report can call it met while the repository is world-readable and the PO has not confirmed it.
Feature: The S3-DoD-P10 status is measured from the repository's visibility
  As the product-manager reporting the sprint-DoD rows
  I want the repository's visibility read from GitHub as an anonymous reader sees it
  So that "met" is only ever reported when the repository is private or the PO confirmed public

  Rule: The measurement fails closed

    Scenario: A GitHub answer without a visibility is refused
      Given GitHub answers with HTTP 200 and no visibility field
      When the visibility is measured
      Then the measurement is refused as malformed

    Scenario: A GitHub error other than "not found" is refused
      Given GitHub answers with HTTP 403 "API rate limit exceeded"
      When the visibility is measured
      Then the measurement is refused as malformed

  Rule: The status is "met" only when the repository is private or the PO confirmed public

    Scenario Outline: A P10 row that negates, questions or declines public is not a confirmation
      Given GitHub reports the repository as public
      And the PO record answers P10 with "<decision>"
      When the visibility is measured
      Then the status is 'not met: waiting on P10 (GitHub reports "visibility": "public")'
      Examples:
        | decision                                                                |
        | Asked again 2026-10-10: make private or keep public? Not yet answered.  |
        | Not confirmed public; still open.                                       |
        | PO declined to keep public; make it private                             |
        | Not confirmed public yet; PO to decide                                  |
        | Do not keep public: make it private                                     |
        | Open: confirmed public is not decided                                   |

    Scenario: A public repository without a PO answer is not met, waiting on P10
      Given GitHub reports the repository as public
      And the PO record has no P10 answer
      When the visibility is measured
      Then the status is 'not met: waiting on P10 (GitHub reports "visibility": "public")'

    Scenario: A repository an anonymous reader cannot see is met
      Given GitHub answers an anonymous reader with HTTP 404
      And the PO record has no P10 answer
      When the visibility is measured
      Then the status is "met (repository is private: anonymous GitHub API returns 404)"

    Scenario: A public repository the PO confirmed public is met
      Given GitHub reports the repository as public
      And the PO record answers P10 with "Confirmed public: keep the repository public"
      When the visibility is measured
      Then the status is "met (PO confirmed public)"

  Rule: The sprint-DoD row says what the measurement says

    Scenario: A sprint-DoD row that claims met for a public repository is refused
      Given GitHub reports the repository as public
      And the PO record has no P10 answer
      And a sprint plan whose S3-DoD-P10 row says "met (repository is private)"
      When the visibility is measured against the sprint plan
      Then the measurement reports that the sprint-DoD row disagrees
