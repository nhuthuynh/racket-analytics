# SRE-PURGE-a (NFR-066 c, NFR-047; ADR 0038 Proposed). Owner: sre-devops-engineer.
# Written before the binding ran green. Binding: infra/tests/test_purge_schedule_scenarios.py runs
# infra/docker/purge_schedule.py as PID 1 of a real container under the API image's runtime rules
# (read-only root, /tmp tmpfs, no capabilities, unprivileged user). The purge job itself is ST-050;
# a stand-in command plays it here.
@ticket-SRE-PURGE-a @nfr-066 @nfr-047
Feature: The purge job runs on a schedule of at least once a day
  Rule: The schedule never runs less often than daily, logs every run as one JSON line,
        survives a failed run and stops cleanly when the container is stopped

    Scenario: An interval longer than a day is refused before any run
      Given the purge schedule is set to every 90000 seconds
      And a purge job that prints "job-ran"
      When the purge schedule starts in a container
      Then the container exits with code 2 naming "PURGE_INTERVAL_S"
      And the purge job never ran

    Scenario: A failed run is logged as an error and the schedule keeps going
      Given the purge schedule is set to every 1 seconds
      And a purge job that prints "job-ran" and fails with exit code 3
      When the purge schedule starts in a container
      Then at least 2 runs are logged as JSON lines with status "failed" at level "ERROR"
      And the consecutive failures of the first two runs are 1 and 2
      And the container is still running with a fresh heartbeat

    Scenario: Stopping the container stops the in-flight job and the schedule gracefully
      Given the purge schedule is set to every 60 seconds
      And a purge job that runs until it is told to stop
      When the purge schedule starts in a container
      And the container is stopped while the job is running
      Then the container exits with code 0 within 10 seconds
      And the purge job received SIGTERM
      And the last log line is "purge.schedule.stopped"

    Scenario: Stopping the container between runs stops the schedule promptly, even with the longest tick
      Given the purge schedule is set to every 600 seconds
      And the heartbeat tick is 300 seconds
      And a purge job that prints "job-ran"
      When the purge schedule starts in a container
      And the container is stopped after the first run has finished
      Then the container exits with code 0 within 5 seconds
      And the last log line is "purge.schedule.stopped"

    Scenario: The job runs at start and again after each interval
      Given the purge schedule is set to every 3 seconds
      And a purge job that prints "job-ran"
      When the purge schedule starts in a container
      Then the first run is logged with status "ok" at level "INFO" announcing the next run in 3 seconds
      And the second run is logged between 3 and 5 seconds after the first, also with status "ok"
      And the job's own output "job-ran" passed through for each run
