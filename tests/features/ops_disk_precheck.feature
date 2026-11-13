# OPS-DISK-06 (sprint-06 PRC-06, PRC-13.1): a Compose build needs the disk floor checked before it
# starts, and stale worktrees are found from their branch's PR state, never by guessing.
Feature: Disk precheck before every image build, and a worktree report
  As the sre-devops-engineer keeping the shared sandbox above its disk floor
  I want every Makefile build target to run the disk precheck first
  And a report that names the worktrees whose branch is merged or closed
  So that a full disk stops a build early and stale worktrees are removed

  Scenario: make up runs the disk precheck before it builds images
    When the recipe of "make up" is listed with make -n
    Then "bash scripts/disk-precheck.sh" comes before the Compose build

  Scenario: make up stops before Compose when the disk is under the build floor
    Given a build floor no disk can meet
    When "make up" runs with a stand-in for Compose
    Then make fails and the stand-in for Compose never ran

  Scenario: A worktree whose branch was merged is listed as "remove"
    Given a worktree on branch "s06/merged-ticket" whose pull request is merged
    And a worktree on branch "s06/open-ticket" whose pull request is open
    When the worktree report runs
    Then the worktree on "s06/merged-ticket" is listed as "remove"
    And the worktree on "s06/open-ticket" is listed as "keep"
