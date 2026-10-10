# FIX-03-1d (sprint-03 §9.1, S3-DoD-P11; finding BLK-GOLD-01; PO P12 option b): the provider of
# the private footage bucket is a human decision (P11). The row's status is measured from the
# PO's recorded P11 answer and from a probe of the bucket itself, never typed by hand, so no
# report can call it met before footage of people has a private home (ADR 0006).
Feature: The S3-DoD-P11 status is measured from the PO's answer and the footage bucket
  As the product-manager reporting the sprint-DoD rows
  I want the footage bucket's status measured from the PO record and the object store
  So that "met" is only reported when the PO named a provider and the bucket refuses strangers

  Rule: The measurement fails closed

    Scenario: A probe with an unexpected anonymous answer is refused
      Given the PO record answers P11 with "Provider: Example Cloud, eu-west"
      And the footage bucket exists and an anonymous read gets HTTP 500
      When the footage bucket is measured
      Then the measurement is refused as malformed

  Rule: The status is "met" only with a PO provider and a bucket that refuses anonymous reads

    Scenario: Without a PO answer the row is not met, waiting on P11
      Given the PO record has no P11 answer
      And the footage bucket exists and an anonymous read gets HTTP 403
      When the footage bucket is measured
      Then the status is "not met: waiting on P11"

    Scenario: A provider without a bucket is not met
      Given the PO record answers P11 with "Provider: Example Cloud, eu-west"
      And the footage bucket does not exist and an anonymous read gets HTTP 403
      When the footage bucket is measured
      Then the status is "not met: P11 answered, footage bucket not built (C3-08)"

    Scenario: A bucket that anyone can read is not met
      Given the PO record answers P11 with "Provider: Example Cloud, eu-west"
      And the footage bucket exists and an anonymous read gets HTTP 200
      When the footage bucket is measured
      Then the status is "not met: footage bucket is readable without credentials"

    Scenario: A provider and a private bucket are met
      Given the PO record answers P11 with "Provider: Example Cloud, eu-west"
      And the footage bucket exists and an anonymous read gets HTTP 403
      When the footage bucket is measured
      Then the status is "met (provider: Example Cloud, eu-west; anonymous read refused)"

  Rule: The sprint-DoD row says what the measurement says

    Scenario: A sprint-DoD row that claims met without a PO answer is refused
      Given the PO record has no P11 answer
      And a sprint plan whose S3-DoD-P11 row says "met (bucket built)"
      When the footage bucket is measured against the sprint plan
      Then the measurement reports that the sprint-DoD row disagrees
