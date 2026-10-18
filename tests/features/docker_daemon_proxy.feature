# FIX-04-1a (G04-01; SRE-V04R1-01): the shared dockerd keeps the agent-proxy port it was started
# with; when the session's proxy moves, every Compose build fails with "connection refused".
Feature: A stale Docker daemon proxy is named before a Compose build, and can be bridged
  As an engineer or verifier starting the local stack
  I want the daemon proxy checked before `make up`
  So that a stale port fails fast with its cause, and is fixed without restarting the shared dockerd

  Scenario: A daemon proxy on a closed port is reported stale, with the remedy
    Given a session proxy that listens
    And a daemon proxy on a port where nothing listens
    When the daemon proxy check runs
    Then the check exits 4 with "stale"
    And the output names both proxy addresses and "--bridge"

  Scenario: After bridging, the stale port reaches the session proxy
    Given a session proxy that listens
    And a daemon proxy on a port where nothing listens
    When the daemon proxy check runs with --bridge
    Then the check exits 0 with "bridged"
    And 70000 bytes sent to the daemon proxy port come back from the session proxy
    And a second check without --bridge exits 0 with "listens"

  Scenario: No bridge is started when the session proxy does not listen either
    Given a session proxy on a port where nothing listens
    And a daemon proxy on a port where nothing listens
    When the daemon proxy check runs with --bridge
    Then the check exits 4 with "session proxy does not listen"
