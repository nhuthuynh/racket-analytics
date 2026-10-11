# CI-OBJSTORE-INIT-HANG (found on PR #71, run 38096146829, job 114347835595): the one-shot
# objectstore-init ran `weed shell` with no time limit. Started before the master listed the
# filer ("master: objectstore:9333 filer: "), the shell never returned, and `compose up --wait`
# hung until the E2E job's 45-minute timeout cancelled it.
Feature: Creating the media bucket is bounded in time
  As the SRE running the stack in CI and locally
  I want the bucket one-shot to retry a stuck object-store shell and give up within a bound
  So that a slow object-store start delays the stack instead of hanging it

  Scenario: A shell that never answers fails the one-shot within the bound
    Given the object-store shell never answers
    When the bucket one-shot runs
    Then it exits non-zero within the bound and names the media bucket

  Scenario: A shell that hangs at first and then answers creates the bucket
    Given the object-store shell hangs on its first call and then answers
    When the bucket one-shot runs
    Then it exits zero with the media bucket listed
