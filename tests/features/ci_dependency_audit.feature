# Sprint 4, ticket CI-DAILY-AUDIT (sre-devops-engineer). Written before the implementation.
# Binding: infra/tests/test_ci_dependency_audit_scenarios.py (runs scripts/ci/security_upgrade.py
# as the workflow runs it, over pip-audit and pnpm audit JSON reports, and reads the real
# .github/workflows/dependency-audit.yml).
# Incident: 2026-10-21 main's CI went red overnight with no code change, because advisory
# PYSEC-2026-4320 was published against the locked certifi (fixed by #148). PO 2026-10-28.
@M0 @story-ST-002 @nfr-062 @ticket-CI-DAILY-AUDIT
Feature: A daily dependency audit opens an upgrade pull request before main goes red

  Rule: A vulnerable Python package with a fix version is upgraded in a pull request

    Scenario: A package with a fix version is upgraded and listed in the pull request
      Given the backend lock lists "certifi" at "2026.7.22"
      And pip-audit reports "PYSEC-2026-4320" against "certifi" "2026.7.22" fixed in "2026.10.19"
      When the security upgrade runs on "2026-10-28"
      Then uv upgrades only "certifi" in the backend project
      And the pull request title is "[DEPS-AUDIT] security upgrades 2026-10-28"
      And the pull request body lists "PYSEC-2026-4320" with "2026.7.22" and "2026.10.19"
      And no issue is written

  Rule: An advisory without a fix version is reported in an issue instead

    Scenario: A package without a fix version opens an issue and is not upgraded
      Given the backend lock lists "certifi" at "2026.7.22"
      And pip-audit reports "PYSEC-2026-9999" against "certifi" "2026.7.22" with no fix version
      When the security upgrade runs on "2026-10-28"
      Then uv is not run
      And no pull request is written
      And the issue body lists "PYSEC-2026-9999" for "certifi"

  Rule: A clean audit changes nothing

    Scenario: A clean audit writes neither a pull request nor an issue
      Given the backend lock lists "certifi" at "2026.10.19"
      And pip-audit reports no vulnerability
      When the security upgrade runs on "2026-10-28"
      Then uv is not run
      And no pull request is written
      And no issue is written

  Rule: The audit fails closed

    Scenario: A missing audit report fails the job
      When the security upgrade runs without the backend audit report
      Then the job fails naming "backend"

  Rule: The workflow runs daily with least privilege and never merges

    Scenario: The workflow is scheduled daily and can be started by hand
      Then the dependency audit workflow runs on a daily schedule and on manual dispatch

    Scenario: The workflow token can only push a branch, edit a pull request and an issue
      Then the dependency audit job may only write contents, pull requests and issues

    Scenario: Only the steps that push or call GitHub get the write token
      Then the dependency audit checks out without persisting the token
      And only the steps that fetch, push or call GitHub get the token
      And the commit and the push run no git hook

    Scenario: The repository setting that lets the job open a pull request is documented
      Then ci-cd.md lists "Allow GitHub Actions to create and approve pull requests" for a human admin
      And a failed pull request creation names that setting

    Scenario: The workflow never merges and never applies a policy label
      Then the dependency audit workflow never merges a pull request
      And it never applies the "size-waiver" or "qa-approved-test-change" labels

    Scenario: The upgrade pull request is a draft so a reviewer starts CI
      Then the dependency audit opens its pull request from "deps/security-audit" as a draft
      And an updated pull request is turned back into a draft

    Scenario: The workflow audits with the same pip-audit command as CI
      Then the dependency audit runs the pip-audit export and audit of ci.yml for backend and infra
      And it runs "pnpm audit --prod --audit-level critical" for web
