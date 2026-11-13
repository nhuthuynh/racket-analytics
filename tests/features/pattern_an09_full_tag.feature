# Sprint 6 ST-171b (FR-171.R2, R3, R6; pattern-catalogue §2): AN-09 third-shot drop share from
# Full Tag labels. Steps: backend/tests/features/test_pattern_an09_full_tag.py. Pure domain: the
# label documents are team-made (no real people) and read through the Analytics ACL.
# The two-bounce rule behind the pattern's meaning is unverified (catalogue §0.9).
@story-ST-171 @analytics @needs-verification
Feature: Third-shot drop share from Full Tag labels
  Of a side's third shots, the share hit as a drop. A rally that cannot have a third shot, or
  whose third shot has no trajectory, is excluded with a reason and never counted as a drive.

  Rule: FR-171.R2 AN-09 = third shots with trajectory drop / third shots with a trajectory

    Scenario: 6 drops and 4 drives give 0.60 with n 10
      Given side A serves 10 rallies whose third shots are 6 drops and 4 drives
      When the pattern measures of the labels are taken from Full Tag
      Then "AN-09" for side A is 0.6 with n 10 and n_excluded 0

    Scenario: a rally that ends before the third hit is excluded, never a drive
      Given side A serves 10 rallies whose third shots are 6 drops and 4 drives
      And side A serves a rally that ends after the return
      When the pattern measures of the labels are taken from Full Tag
      Then "AN-09" for side A is 0.6 with n 10 and n_excluded 1
      And side A's exclusions are "no_third_shot" 1

  Rule: FR-171.R3 A third shot with no trajectory facet is excluded as facet_missing

    Scenario: 10 third shots, 2 without a facet
      Given side A serves 10 rallies whose third shots are 4 drops, 4 drives and 2 without a facet
      When the pattern measures of the labels are taken from Full Tag
      Then "AN-09" for side A is 0.5 with n 8 and n_excluded 2
      And side A's exclusions are "facet_missing" 2

  Rule: FR-171.R6 Below min_n 20 the measure is flagged and not rankable

    Scenario: 25 third shots are rankable
      Given side A serves 25 rallies whose third shots are 5 drops and 20 drives
      When the pattern measures of the labels are taken from Full Tag
      Then "AN-09" for side A is rankable

    Scenario: 7 third shots are a low sample
      Given side A serves 7 rallies whose third shots are 3 drops and 4 drives
      When the pattern measures of the labels are taken from Full Tag
      Then "AN-09" for side A is flagged as a low sample and is not rankable

  Rule: A facet with no measured labeller agreement says so

    Scenario: a single-labeller trajectory
      Given side A serves 10 rallies whose third shots are 6 drops and 4 drives
      When the pattern measures of the labels are taken from Full Tag
      Then "AN-09" for side A is labelled "single-labeller, agreement not measured"
