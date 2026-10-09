# Branch protection on `main` and the merge check

Ticket CI-PR-GATE (Sprint 3). User request (2026-10-08): CI must pass on every PR before it can
merge. PO rule (2026-10-07): one PR per ticket, reviewed by the principal-engineer and a senior
engineer, merged only when both latest verdicts approve the current head and every CI job incl.
`ci-gate` is green.

There are two layers. GitHub enforces the first. The orchestrator runs the second before every
merge, because GitHub cannot check the review verdicts (see §3).

## 1. State on 2026-10-08

```text
$ curl -sS https://api.github.com/repos/nhuthuynh/racket-analytics/branches/main
"protected": false, "required_status_checks": {"enforcement_level": "off", "contexts": []}
```

`main` has no protection yet. A repo admin (the human PO) applies §2. Agents cannot do it,
because they have no admin rights.

## 2. Settings for the repo admin to apply

Go to **Settings → Branches → Add branch protection rule**. Set the branch name pattern to
`main` and choose these settings:

| Setting | Value | Why |
|---|---|---|
| Require a pull request before merging | on | No direct pushes, so every change runs CI first |
| Required approvals | **0** | All agents post as one account, and GitHub does not let that account approve its own PR. Verdicts are checked by §3 instead (po-input 2026-10-07) |
| Require status checks to pass before merging | on | |
| Require branches to be up to date before merging | **on** (`strict`) | `ci-gate` must have run on the code that will land, not on an older base |
| Required status check | **`ci-gate`** (source: GitHub Actions) | `ci-gate` needs every other CI job (`docs/process/ci-cd.md`) |
| Require conversation resolution | off | Findings are tracked in `review-rounds.md` |
| Do not allow bypassing the above settings (include administrators) | **on** | The agents' account is the admin account, so without this it could merge red |
| Allow force pushes / Allow deletions | off / off | No history rewrite (working agreement) |

The same settings as one API call, for an admin token (`gh` or curl):

```bash
gh api -X PUT repos/nhuthuynh/racket-analytics/branches/main/protection --input - <<'JSON'
{
  "required_status_checks": {"strict": true, "checks": [{"context": "ci-gate", "app_id": 15368}]},
  "enforce_admins": true,
  "required_pull_request_reviews": {"required_approving_review_count": 0},
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_conversation_resolution": false
}
JSON
```

`app_id` 15368 is GitHub Actions. To verify, run
`curl -sS https://api.github.com/repos/nhuthuynh/racket-analytics/branches/main`. The result
should show `"protected": true` and `"contexts": ["ci-gate"]`.

**Known effect on the nightly job.** `nightly-quality.yml` (`publish`) pushes its
`status.json` commit straight to `main`. Once PRs are required, that push is refused, so the
`publish` job fails. PR CI is not affected. Exempting `github-actions[bot]` from the PR rule is only
possible where GitHub offers bypass actors (rulesets or organisation repos; unverified for this
personal repo). The follow-up is to have `publish` open a PR or write to a
`nightly-status` branch. That needs its own ticket, which the EM schedules.

## 3. Merge check the orchestrator runs before every merge

```bash
python3 scripts/ci/merge_ready.py --repo nhuthuynh/racket-analytics --pr <N> --sha <head SHA>
```

It uses only the standard library. `GITHUB_TOKEN` or `GH_TOKEN` is optional while the repo is
public. Exit 0 means merge-ready. Exit 1 means not ready, and the script prints the reasons.
Exit 2 means GitHub could not be read, so the check fails closed. The check refuses unless all
of these hold on that SHA:

- The SHA is the head of an **open** PR into `main`. An approval on an older commit does not
  count.
- The latest run of every job in the newest suite of each workflow concluded `success`, and
  `ci-gate` itself is `success`. Any
  other check may be `skipped` or `neutral`, for example the schedule-only `flaky-report`
  (`docs/sprints/03/decisions/CI-PR-GATE.md`, row 1).
- Only the **current workflow run** of each workflow and event on that SHA counts. Adding or
  removing a label, or re-opening the PR, starts a new run of `ci.yml` on the same SHA, and
  `cancel-in-progress` cancels the older one. The check reads
  `GET /repos/{repo}/actions/runs?head_sha=<SHA>` and ignores the check suites of the other
  runs. A check run outside GitHub Actions is never ignored (`docs/sprints/03/decisions/CI-PR-GATE.md`, row 5).
- The current run is the **newest run**, skipping a **cancelled run that was replaced**: a
  run that was not cancelled was created in the same second or later. When two triggers start
  runs in the same second, the concurrency group may cancel the newer one (PR #49), so that run
  is skipped. A cancelled run that nothing replaced (cancelled by hand or by infra, no run after
  it) stays current and refuses the merge with `the newest <workflow> run on <SHA> was cancelled
  and no later run replaced it`, because `pr-policy` reads the labels from that run's event and
  the older green run saw an older label set. A newer run that failed, is queued or is in
  progress still wins, so a newer failure is never hidden. If every run of a workflow on the SHA
  was cancelled, the check refuses with `all <workflow> runs on <SHA> were cancelled`
  (`docs/sprints/03/decisions/CI-MERGE-READY-CANCELLED.md`).
- The **principal-engineer's** latest review and at least one **senior-\*** role's latest
  review start with `Verdict: APPROVE` and were given on that SHA. No role's latest review on
  that SHA says `Verdict: CHANGES REQUESTED`.

**Review format.** All agents share one GitHub account, so each review names its role:

```text
Verdict: APPROVE
Reviewer: senior-qa-engineer
```

The `Reviewer:` line must be the line right after the `Verdict:` line. The check ignores a
review when:

- its body does not *start* with the verdict, or the next line is not `Reviewer: <role>`;
- it was not submitted (only `COMMENTED`, `APPROVED` and `CHANGES_REQUESTED` count, so a
  `PENDING` or `DISMISSED` review never counts);
- its author is not trusted. GitHub's `author_association` must be `OWNER`, `MEMBER` or
  `COLLABORATOR`, because anyone can review a PR on this public repo.

With strict status checks, updating a branch creates a new head. CI then runs again,
and both reviewers must post their verdicts again on the new SHA.

## 4. PR labels that CI reads

| Label | Who applies it | When | CI job |
|---|---|---|---|
| `qa-approved-test-change` | senior-qa-engineer only | The PR modifies, deletes or renames an existing file under `backend/tests/`, `web/e2e/`, `fixtures/gold/` or `tests/features/`. It needs a row in `docs/sprints/<nn>/test-change-requests.md` that the senior-qa-engineer has decided | `pr-policy` (`check_test_immutability.py`) |
| `size-waiver` | engineering-manager only | More than 400 changed lines (lockfiles and fixtures do not count). The waiver row must exist before the commit (ADR 0030; ticket SIZE-WAIVERS-03) | `pr-policy` (`check_pr_size.py`) |
| `skip-claude-review` | EM | Skip the automated Claude review. This label does not exist on the repo yet (2026-10-08) | `claude-review.yml` |

GitHub cannot limit who applies a label. Reviewers check the label events in the PR timeline
(ADR 0014).
