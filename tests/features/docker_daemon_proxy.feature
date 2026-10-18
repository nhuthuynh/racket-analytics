# FIX-04-1a (G04-01; SRE-V04R1-01): the shared dockerd keeps the agent-proxy port it was started
# with; when the session's proxy moves, every Compose build fails with "connection refused".
Feature: A stale Docker daemon proxy is named before a Compose build, and can be bridged
  As an engineer or verifier starting the local stack
  I want the daemon proxy checked against the session proxy before `make up`
  So that a stale port fails fast with its cause, and can be fixed without restarting the shared dockerd

  Rule: The check fails closed on a daemon proxy that does not listen

    Scenario: A daemon proxy on a closed port is reported stale
      Given a session proxy that listens
      And a daemon proxy on a port where nothing listens
      When the daemon proxy check runs
      Then the check exits 4 with "stale"
      And the output names both proxy addresses

    Scenario: A daemon without a proxy passes
      Given a session proxy that listens
      And a daemon with no proxy
      When the daemon proxy check runs
      Then the check exits 0 with "no daemon proxy"

  Rule: The bridge forwards the stale port to the session proxy without restarting dockerd

    Scenario: After bridging, the stale port reaches the session proxy
      Given a session proxy that listens
      And a daemon proxy on a port where nothing listens
      When the daemon proxy check runs with --bridge
      Then the check exits 0 with "bridged"
      And bytes sent to the daemon proxy port come back from the session proxy

    Scenario: No bridge is started when the session proxy does not listen either
      Given a session proxy on a port where nothing listens
      And a daemon proxy on a port where nothing listens
      When the daemon proxy check runs with --bridge
      Then the check exits 4 with "session proxy does not listen"
