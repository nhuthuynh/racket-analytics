# Sprint 4, ticket CI-OBJSTORE-PORT-RACE (sre-devops-engineer). CI-first: main 0415be6 went red
# (run 40874800467) when scripts/dev-objectstore.sh start died with "weed exited during startup"
# and the weed log said "Filer listener error: ... bind: address already in use".
# Binding: infra/tests/test_dev_objectstore_ports_scenarios.py (runs the real script against a
# stand-in weed binary that collides on demand; the real-weed case is in
# infra/tests/test_dev_objectstore_ports.py).
@M0 @ticket-CI-OBJSTORE-PORT-RACE
Feature: The local object store starts on distinct free ports and survives a port collision

  Rule: Only a port collision is retried; every other startup failure fails closed at once

    Scenario: A startup failure that is not a port collision fails at once
      Given the object store binary fails at startup with "invalid -dir"
      When the developer starts the local object store
      Then the start fails with "weed exited during startup"
      And the object store binary was started 1 time
      And no retry was logged

    Scenario: A port collision is retried with fresh ports and the store starts
      Given the object store binary hits "address already in use" on its first 1 start
      When the developer starts the local object store
      Then the store starts and prints the S3 endpoint
      And the object store binary was started 2 times
      And the log says "port collision, retry 1/3 with fresh ports"
      And the second start used different ports from the first

    Scenario: A port collision that persists fails after three retries
      Given the object store binary hits "address already in use" on its first 9 starts
      When the developer starts the local object store
      Then the start fails with "weed exited during startup"
      And the object store binary was started 4 times
      And the log says "port collision, retry 3/3 with fresh ports"

  Rule: One start never hands the same port to two listeners

    Scenario: Every port given to the object store is distinct
      Given the object store binary starts normally
      When the developer starts the local object store
      Then the store starts and prints the S3 endpoint
      And the 8 ports given to the object store binary are distinct
