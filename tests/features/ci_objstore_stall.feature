# CI-OBJSTORE-STALL (NFR-073, NFR-074). Owner: sre-devops-engineer. Bound by
# infra/tests/test_ci_objstore_stall_scenarios.py (config) and
# infra/tests/test_compose_objectstore_netns_live.py (a running store).
@nfr-073 @ci-objstore-stall
Feature: The object store's own connections keep a receive buffer of many loopback segments
  Run 38059526467: two of the throughput floor's 12 clip writes took 15-16 s. Experiments on the
  CI runners (runs 38062207301 and 38064153385) found the time inside the store: its filer sends
  each chunk to its volume server over the container's loopback (MSS 65483 B) into a 128 KiB
  default receive buffer, the runner kernel default. That buffer holds two loopback segments;
  the receive queue is pruned and drops segments, and the sender falls back to retransmission
  timeouts with a congestion window of 2 and zero-window probes, about 150 KB/s for the life of
  the kept-alive connection. With a 1 MiB default receive buffer in the store's network
  namespace the same experiment had no stall in 1,152 writes (128 KiB: 10 in 1,152).

  Scenario: The runner's 128 KiB default receive buffer is too small for loopback segments
    Given a store network namespace whose default TCP receive buffer is 131072 bytes
    Then that buffer holds fewer than 16 loopback segments of 65483 bytes

  Scenario: The Compose store's network namespace holds at least 16 loopback segments
    Given the Compose object store service
    Then its default TCP receive buffer holds at least 16 loopback segments of 65483 bytes
    And the buffer is set as a namespaced sysctl of the store, with no added capability

  Scenario: A running store has the receive buffer it was given
    Given a running Compose object store
    Then its network namespace reports a default TCP receive buffer of at least 16 loopback segments
    And it stores the 1.72 MB clip
