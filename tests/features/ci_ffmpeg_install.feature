# Sprint 5, ticket CI-FFMPEG (sre-devops-engineer), story "CI first". Written before the fix.
# Binding: infra/tests/test_ci_ffmpeg_install_scenarios.py. It reads the real
# .github/workflows/ci.yml and .github/actions/install-ffmpeg/action.yml, and runs the real
# scripts/ci/install_ffmpeg.py against a local HTTP source on 127.0.0.1 serving a small archive
# with the pinned layout (no download from the internet).
# Incident: CI run 42019671445 (PR #225), integration job 127218978690: `apt-get install ffmpeg`
# fetched 62.8 MB at 58.9 kB/s and took 17 m 48 s of the job's 20 min timeout, so the backend
# suites were cancelled.
@M0 @story-ST-002 @nfr-073 @nfr-062 @ticket-CI-FFMPEG
Feature: CI installs ffmpeg fast, from a pinned build, within a time bound

  Rule: One shared install, the same LGPL build the worker image ships

    Scenario: Every job that needs ffmpeg uses the one shared install
      Then the jobs "integration", "e2e" and "flaky-report" install ffmpeg only through the shared install action
      And no CI job installs ffmpeg with apt
      And every shared install step has a time limit of at most 4 minutes

    Scenario: CI uses the build the worker image pins
      Then the build pinned for CI is the ffprobe build the backend Dockerfile pins

  Rule: A cache hit needs no network

    Scenario: A cached, verified build installs with no download
      Given the pinned build is already in the install directory
      When the install runs
      Then it succeeds reporting "cache hit"
      And it downloaded nothing
      And it took less than 60 seconds
      And the install directory's bin is added to the job's PATH

    Scenario: A tampered cache is discarded and the pinned build is fetched again
      Given the pinned build is already in the install directory
      And the cached ffprobe was changed
      When the install runs
      Then it succeeds reporting "discarding the cache"
      And it downloaded the archive once
      And the cached ffprobe matches its pinned checksum

  Rule: A wrong checksum fails closed

    Scenario: A download whose checksum does not match the pin fails closed
      Given the source serves an archive whose SHA-256 differs from the pin
      When the install runs
      Then it fails with exit code 1 naming "sha256 mismatch"
      And no ffmpeg or ffprobe is left in the install directory

  Rule: The install is bounded and says why it stopped

    Scenario: A stalled download is retried once on the next source
      Given the first source stalls and the second source serves the pinned build
      When the install runs with a 1 second limit per attempt
      Then it succeeds reporting "attempt 2"
      And each source was asked once

    Scenario: An install that runs out of time stops with a named failure
      Given every source stalls
      When the install runs with a 1 second limit per attempt
      Then it fails with exit code 3 naming "CI-FFMPEG: ffmpeg install exceeded its budget"
      And it stopped within 10 seconds after 2 attempts
