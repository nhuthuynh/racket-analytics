# Sprint 3, ticket C3-04 (sre-devops-engineer; QA-RV3-04). Added in the per-ticket port (P13).
# Binding: infra/tests/test_dev_chrome_scenarios.py (runs scripts/dev-chrome.sh as a developer
# does, against a stand-in CfT zip served over file:// and a temporary install dir).
# Rule: ADR 0036 (Chrome for Testing 141.0.7390.54 is the local H.264 evidence browser).
@M0 @ticket-C3-04
Feature: The evidence browser is installed only as the pinned, checksummed build

  Rule: Nothing is installed unless the zip matches the ADR 0036 sha256

    Scenario: A zip with the wrong sha256 is refused and nothing is installed
      Given the evidence browser is not installed
      And the download does not match the pinned sha256
      When the developer installs the evidence browser
      Then the install is refused with "sha256 mismatch"
      And no evidence browser is installed

  Rule: Installing is idempotent and check mode reports the installed version

    Scenario: Installing twice downloads once and check mode reports the pinned version
      Given the evidence browser is not installed
      And the download matches the pinned sha256
      When the developer installs the evidence browser
      And the developer installs the evidence browser again with the download gone
      Then the second install reports "already installed"
      And check mode reports "Google Chrome for Testing 141.0.7390.54"
