# 0053. The daily dependency audit opens a draft upgrade PR; a reviewer marking it ready starts CI

- **Status:** Proposed
- **Date:** 2026-10-28
- **Deciders:** sre-devops-engineer (proposed); principal-engineer and senior-qa-engineer review the PR
- **Consulted:** human product owner (decision 2026-10-28, in chat: a daily scheduled audit that opens an upgrade PR through the normal review and merge gates)
- **Related:** CI-DAILY-AUDIT, NFR-062, ST-002, ADR 0014 (fail closed), ADR 0050 (merge_ready), ADR 0052 (CI skips drafts), PR #148 (certifi)

## Context and problem statement

On 2026-10-21 main's CI went red overnight with no code change, because advisory PYSEC-2026-4320
was published against the locked certifi (fixed by #148). The PO asked for a daily job that
audits the dependencies and opens an upgrade PR before main goes red.

The job runs with `GITHUB_TOKEN`. GitHub does not start other workflows for events caused by
`GITHUB_TOKEN` (except `workflow_dispatch` and `repository_dispatch`), so a PR the job opens or
pushes to gets no `pull_request` CI run, and `merge_ready.py` needs `ci-gate` success on the
exact head. How does the upgrade PR get a CI result that the merge gate can trust?

## Decision drivers

- The upgrade PR must pass the same gates as any PR: `pr-policy` (size, test immutability),
  every job, `ci-gate` on the head, two reviews, merge by the gated merge step only.
- Least privilege; no new long-lived secret (PATs and GitHub Apps are a new credential to manage).
- Never force-push; never merge; never apply `size-waiver` or `qa-approved-test-change`.

## Considered options

1. **Draft PR; a reviewer marks it ready for review** (chosen). The job opens the PR as a draft
   (drafts run no CI job, ADR 0052) and turns it back into a draft on every update. Marking it
   ready is done with the reviewer's or orchestrator's own token, so the `ready_for_review`
   event starts the full `pull_request` CI run, `pr-policy` included.
2. **Dispatch `ci.yml` (`workflow_dispatch`) on the PR branch.** `workflow_dispatch` is exempt
   from the `GITHUB_TOKEN` rule.
3. **Push with a personal access token or GitHub App token.**
4. **Do nothing** (keep finding advisories when main goes red).

## Decision outcome

Chosen option 1, because it is the only option that runs the PR's own `pull_request` CI
(with `pr-policy`) without a new secret or a wider token.

## Pros and cons of the options

### Option 1: draft PR, reviewer marks it ready
- Good: the full PR run, `pr-policy` included; nothing new to store; the reviewer looks at the
  diff before CI spends minutes on it; consistent with ADR 0052 (drafts are where decisions are made).
- Bad: CI does not start by itself; someone must mark the PR ready. Acceptable: the PR needs two
  human-role reviews anyway, and the PR body says so.

### Option 2: dispatch `ci.yml`
- Good: CI starts automatically.
- Bad: needs `actions: write` on top of the three write scopes. On `workflow_dispatch`, ci-gate
  accepts a skipped `pr-policy` (ci.yml `ci-gate` step), so a green `ci-gate` on the head would
  not include the size and test-immutability checks; `merge_ready.py` reads check runs per SHA,
  so that run could count towards the merge. Weakens the gate.

### Option 3: PAT or App token
- Good: normal `pull_request` events.
- Bad: a new long-lived credential with write access; no such token exists in the repo today
  (the workflows use only `GITHUB_TOKEN` and `ANTHROPIC_API_KEY`).

### Option 4: do nothing
- Bad: the 2026-10-21 incident repeats; today's audit finds two new advisories (below).

## Consequences

- Permissions: workflow `permissions: {}`; the job has `contents: write` (push
  `deps/security-audit`), `pull-requests: write` (open, edit, turn into draft) and `issues: write`
  (one issue for advisories without a fix). The PO's scope named `contents` and `pull-requests`;
  `issues: write` is needed for the issue the same scope asks for.
- The branch is never force-pushed: it is merged with `origin/main` and the locks re-upgraded on top.
- Web is audited (`pnpm audit --prod --audit-level critical`) but never upgraded automatically;
  critical web advisories go into the issue (scope: upgrades are for Python packages).
- Follow-up: if a branch rule requires PRs from bots to be approved by a code owner, nothing changes.

## Evidence

| Claim | Evidence | Type |
|---|---|---|
| The script upgrades a real vulnerable package on the real locks | Scratch copy of `backend/` and `infra/` locks, today's real reports: `python3 scripts/ci/security_upgrade.py --root repo --audit backend=... --audit infra=... --web-audit ... --date 2026-10-28 --out-dir out` -> `Updated opentelemetry-api v1.45.0 -> v1.45.1`, `1 upgraded, 1 need an issue`, rc 0; then `pip-audit --strict` on the result -> `No known vulnerabilities found` | test result |
| Main is exposed today | `pip-audit` on `origin/main` 1f7e1cc backend -> `opentelemetry-api 1.45.0 CVE-2026-114603 (fix 1.45.1)`; `pnpm audit --prod --audit-level critical` -> `next 15.5.27 GHSA-2464-fhr4-w9xw` critical; the last three scheduled CI runs on main concluded `failure` (runs 40666026362, 40477476835, 40295666097) | data |
| Behaviour per report kind (with fix, without fix, clean, missing) | `cd infra && uv run pytest -q tests/test_security_upgrade.py tests/test_ci_dependency_audit_scenarios.py` -> 35 passed | test result |
| `GITHUB_TOKEN` events start no workflow except dispatch events | GitHub Actions documentation, "Triggering a workflow from a workflow" (not in the verified source list) | (judgment) |

## Confirmation

`infra/tests/test_ci_dependency_audit_scenarios.py` pins the draft PR, the turn-back-to-draft on
update, the three permissions, the absence of any merge or policy-label command, and the same
pip-audit command as ci.yml. actionlint passes on the workflow.

## Notes
