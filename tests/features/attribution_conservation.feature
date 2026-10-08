# Sprint 3 §7.4 (QA-ACC-3, written for ST-045; FR-109, ADR 0003). Owner: senior-qa-engineer.
# Domain binding: backend/tests/features/test_attribution_conservation.py (the product's
# attribution over the projected sheet). The >= 1,000-match property is ST-045's
# (tests/unit/analytics/test_attribution.py, profile ci, marker conservation).
@M0 @story-ST-045 @fr-109 @conservation
Feature: Attribution conservation
  Scenario: Every lost rally is accounted for once
    Given side A lost 14 rallies in game 1, 6 on serve and 8 on receive
    When the lost rallies are attributed
    Then the attributed and unattributed rallies on serve total 6
    And on receive they total 8
