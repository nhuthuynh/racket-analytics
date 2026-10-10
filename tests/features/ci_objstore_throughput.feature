# CI-OBJSTORE-SLOW (NFR-073, NFR-074). Owner: sre-devops-engineer. Bound by
# infra/tests/test_ci_objstore_throughput_scenarios.py; the real-store floor is
# backend/tests/integration/harness/test_ci_objstore_throughput.py.
@nfr-073 @ci-objstore-slow
Feature: The CI object store keeps its write throughput, and a slow store is caught and explained
  Runs 37764445816 and 37961668800: minutes into the integration job, the SeaweedFS store took
  the 1.72 MB clip at about 64 KiB/s (one 64 KiB window per ~1.01 s) while small writes stayed
  fast, and IT-02-13 and the red_until rows timed out. A test may rely on the store taking the
  clip at 5 MB/s or more; the job checks that before the suites and before the red_until rows,
  and keeps the evidence that names the cause when it does not hold.

  Scenario: The job checks the store's write throughput around the suites
    Given the CI integration job
    Then the job checks the store's write throughput before the backend suites
    And the job checks the store's write throughput again before the red_until rows
    And each check is the backend floor test for the 1.72 MB clip from 4 parallel writers

  Scenario: The job records the runner facts that can slow a TCP transfer to the store
    Given the runner telemetry script
    When it records the runner facts
    Then the facts name the Docker daemon settings and the store's published port path
    And the facts name the conntrack settings and the firewall rules for invalid packets
    And the facts name the free disk, the memory and the kernel

  Scenario: The job samples the store's throughput and the TCP counters during the suites
    Given the runner telemetry script
    When it takes one sample of a running store
    Then the sample times one 1.72 MB write to the store
    And the sample holds the TCP retransmission and timeout counters
    And the sample holds the conntrack statistics and the store's sockets

  Scenario: The job keeps the evidence on every run
    Given the CI integration job
    Then the job records the runner facts once the services run
    And the job samples the store during the suites and the red_until rows
    And the job keeps the whole object store log and the telemetry on every run
