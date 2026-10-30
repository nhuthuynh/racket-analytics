# Sprint 4 fix wave, ticket ADR-0053-0049 (sre-devops-engineer with principal-engineer).
# Retro action C4 (docs/retros/2026-12-11-sprint-04.md §8; major M6): keep main green while no
# session runs. ADR 0053 is Accepted only when (1) a planted advisory opens a draft upgrade PR the
# same day and (2) a red scheduled run produces a notice to the product owner (an issue).
# Binding: infra/tests/test_ci_scheduled_red_notice_scenarios.py. It runs the REAL `run:` scripts
# of .github/workflows/dependency-audit.yml and .github/workflows/scheduled-red-notice.yml with
# bash, on a throwaway git checkout with a local bare `origin`, a recording `uv` and a recording
# `gh` on PATH. Written before the implementation.
@M0 @story-ST-002 @nfr-062 @ticket-ADR-0053-0049
Feature: Main stays green while no session runs

  Rule: A planted advisory opens a draft upgrade pull request the same day (ADR 0053)

    Scenario: The daily audit turns a planted advisory into a pushed branch and a draft pull request dated today
      Given a checkout whose backend lock lists "certifi" at "2026.7.22"
      And a planted pip-audit advisory "PYSEC-2026-4320" against "certifi" "2026.7.22" fixed in "2026.10.19"
      And no upgrade pull request is open
      When the dependency audit workflow's upgrade, push and pull request steps run
      Then the branch "deps/security-audit" on origin locks "certifi" at "2026.10.19"
      And gh opened a draft pull request into "main" from "deps/security-audit" titled with today's UTC date

    Scenario: A second planted advisory updates the open pull request and turns it back into a draft
      Given a checkout whose backend lock lists "certifi" at "2026.7.22"
      And a planted pip-audit advisory "PYSEC-2026-4320" against "certifi" "2026.7.22" fixed in "2026.10.19"
      And upgrade pull request 42 is open
      When the dependency audit workflow's upgrade, push and pull request steps run
      Then gh edited pull request 42 and turned it back into a draft
      And gh opened no new pull request

    Scenario: A clean audit pushes nothing and opens no pull request
      Given a checkout whose backend lock lists "certifi" at "2026.10.19"
      And pip-audit finds nothing
      And no upgrade pull request is open
      When the dependency audit workflow's upgrade, push and pull request steps run
      Then origin has no branch "deps/security-audit"
      And gh was not asked to open or edit a pull request

  Rule: A red scheduled run sends the product owner a notice (retro C4)

    Scenario: A failed scheduled run opens an issue assigned to the product owner
      Given no notice issue is open
      When the scheduled "Dependency audit" run ends with "failure"
      Then gh opened an issue titled "[CI-RED] scheduled Dependency audit run failed" assigned to the repository owner
      And the issue body links the failed run and names the commit

    Scenario: A second red run of the same workflow comments on the open notice
      Given notice issue 77 is open
      When the scheduled "CI" run ends with "timed_out"
      Then gh commented on issue 77 with the failed run
      And gh opened no new issue

    Scenario: A green scheduled run closes the open notice
      Given notice issue 77 is open
      When the scheduled "Nightly quality" run ends with "success"
      Then gh closed issue 77 naming the green run

    Scenario: A red run that was not scheduled sends no notice
      Given no notice issue is open
      When a "pull_request" run of "CI" ends with "failure"
      Then gh was not asked to open, comment on or close an issue

    Scenario: A notice the job cannot decide fails the job
      When the notice step runs without a run URL
      Then the notice job fails naming "--run-url"

  Rule: The notice workflow watches every scheduled workflow with least privilege

    Scenario: The notice workflow listens to every workflow that has a schedule
      Then the notice workflow runs on the completion of every workflow with a "schedule" trigger
      And its job runs only for scheduled runs

    Scenario: The notice workflow can only write issues and never touches code or pull requests
      Then the notice job may only read contents and write issues
      And only the step that calls GitHub gets the token
      And the notice workflow never merges, labels or pushes
