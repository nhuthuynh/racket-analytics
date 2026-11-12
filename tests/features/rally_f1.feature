# ST-084b (story ST-084 "R2 entry is measurable", P2). NFR-006.1-.4; ADR 0004 (matching rule),
# ADR 0060 row M11 (rally F1, %, regression label). Owner: senior-ml-cv-engineer.
# Steps: backend/tests/features/test_rally_f1.py (pure matcher, no I/O).
# Unit + property: backend/tests/unit/dataset/test_rally_f1.py.
@story-ST-084 @nfr-006
Feature: Rally segmentation F1 matching
  A predicted rally counts as correct only when its start and its end are each within 1.0 s of a
  gold rally and it neither merges two gold rallies nor is one piece of a split gold rally. Each
  gold rally matches at most one prediction. Rally F1 is the R2 gate (spec M2).

  Rule: NFR-006.1 Start and end within 1.0 s

    Example: within tolerance gives 1 true positive
      Given the gold rallies "10.0-20.0"
      And the predicted rallies "11.0-19.0"
      When the predictions are matched against the gold rallies
      Then there are 1 true positives, 0 false positives and 0 false negatives
      And the rally F1 is 100.0 %

    Example: end 1.01 s off gives 0 true positives, 1 FP, 1 FN
      Given the gold rallies "10.0-20.0"
      And the predicted rallies "10.0-21.01"
      When the predictions are matched against the gold rallies
      Then there are 0 true positives, 1 false positives and 1 false negatives
      And the rally F1 is 0.0 %

  Rule: NFR-006.2 A prediction spanning two gold rallies is a merge

    Example: one prediction over two close gold rallies matches neither
      Given the gold rallies "10.0-20.0, 20.5-30.0"
      And the predicted rallies "10.0-20.6"
      When the predictions are matched against the gold rallies
      Then there are 0 true positives, 1 false positives and 2 false negatives

  Rule: NFR-006.3 Two predictions inside one gold rally are a split

    Example: two pieces of one gold rally match nothing
      Given the gold rallies "10.0-20.0"
      And the predicted rallies "10.0-19.5, 19.6-20.0"
      When the predictions are matched against the gold rallies
      Then there are 0 true positives, 2 false positives and 1 false negatives

  Rule: NFR-006.4 Matching is one-to-one

    Example: two predictions near one gold rally give 1 TP and 1 FP
      Given the gold rallies "10.0-20.0"
      And the predicted rallies "10.2-20.1, 10.5-19.8"
      When the predictions are matched against the gold rallies
      Then there are 1 true positives, 1 false positives and 0 false negatives
      And the rally F1 is 66.7 %
