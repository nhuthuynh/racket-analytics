# CI-FIX-PR-CHECK decisions (sre-devops-engineer, 2026-11-14)

Ticket CI-FIX-PR-CHECK (`ci_fix`), branch `s06/ci-fix-pr-check-local` (bootstrap owner pattern `s<nn>/ci-fix-*` in `scripts/ci/review_tiers.py`). Bounded context: platform/CI.

## 1. Problem

Since 2026-10-05, 205 of about 1,645 CI runs failed. Of the 287 failing jobs in those runs, 136 (47%) were PR-policy gates: PR size 77, test/gold immutability 35, red first 14, decisions ledger 4. Most of the rest were the doc checks, Ruff and the unit suites. Every one of these checks is a script under `scripts/ci/` or `scripts/measure/` that runs the same way locally: `python3 scripts/ci/check_red_first.py --base origin/main --head HEAD` on the branch of PR #226 reproduces that PR's CI failure exactly, and with `PR_NUMBER`, `GITHUB_REPOSITORY` and a token the scripts read the PR's live labels as CI does. Nothing ran them before a push (no Makefile target, no git hook), so agents used CI as their test runner and every red push cost a CI round.

## 2. Decisions

| # | Decision | Why | Alternatives |
|---|---|---|---|
| 1 | One script, `scripts/pr-check.sh`, runs ci.yml's own commands: the five `pr-policy` run lines verbatim (with `BASE_REF=main`), the `doc-check` job's two steps (the same `BASE_SHA` snippet, `BASE_SHA` = the fetched `origin/main`), Ruff check and format in `backend/`, and `scripts/test-unit.sh` | The same command gives the same verdict; `infra/tests/test_pr_check.py` reads ci.yml and fails when a step's command or name is not in the script, so the two cannot drift silently | Parse and run ci.yml's steps at run time: rejected, it needs PyYAML and GitHub expression handling in a pre-push path (judgment) |
| 2 | Every check runs; one `PASS`/`FAIL`/`SKIP` line per check names the CI job and step; exit 1 when any failed | One run shows every failure, as a CI run does | Stop at the first failure: rejected, it hides the next red step until the next push |
| 3 | The open PR is looked up with `gh api "repos/<repo>/pulls?head=<owner>:<branch>&state=open"`; when found, `PR_NUMBER`, `PR_TITLE`, `GITHUB_REPOSITORY` and `GITHUB_TOKEN` (`$GITHUB_TOKEN`, else `gh auth token`) are exported | `pr_labels.py` then reads the live labels, so `size-waiver` and `qa-approved-test-change` count exactly as in CI, and `check_cost_table.py` gets the title | Ask for the labels on the command line: rejected, a local override would not match CI |
| 4 | `reconcile_due.py --pr` runs with or without an open PR; `check_cost_table.py` runs only with one (else `SKIP`) | The ledger rule reads only the branch's diff, so it can be checked before the first push; the cost-table rule needs the PR title | Skip both without a PR (the ticket's first wording): rejected for the ledger step, which would then fail only in CI |
| 5 | Ruff runs as `uv run ruff check .` (CI adds `--output-format=github`, which only formats annotations) and `uv run ruff format --check .`; no `uv sync --locked` | Same rules and verdict; `uv sync --locked` would remove packages a developer installed beyond the lock | Add `--output-format=github`: rejected, unreadable in a terminal |
| 6 | `--fast` skips only the unit suites; no other skip exists | The unit suites take about 26 s (2,975 passed on 2026-11-14); the policy, doc and Ruff checks take seconds | A skip per check: rejected by the ticket |
| 7 | `.githooks/pre-push`, installed by `make hooks` (`git config core.hooksPath .githooks`), runs `pr-check.sh --branch <remote branch>` for each pushed `refs/heads/s<nn>/*` ref and refuses the push on failure; other refs, deletions and `--no-verify` are not checked | Ticket branches are the PRs the policy gates judge; `deps/security-audit` is pushed by the dependency-audit workflow with `--no-verify`; `core.hooksPath` keeps the hook versioned and reviewed | `.claude/settings.json` PreToolUse hook on `git push`: rejected, it misses humans and pushes from other tools |
| 8 | The hook refuses a ticket push whose commit is not checked out | pr-check judges the working tree (Ruff, unit suites), so another commit would be judged on the wrong files | Check out the pushed commit in a temporary worktree: rejected, slow and surprising inside a hook (judgment) |
| 9 | The checks left to CI are mypy, the budgeted unit steps, integration, E2E, web checks, secrets and SBOM jobs | They need services, budgets or toolchains a pre-push check cannot assume | Run mypy too: deferred; it was not among the failing gates this ticket targets |
| 10 | **Review B1:** pr-check stops with `FAIL  tree / no uncommitted or untracked changes` when `git status --porcelain --untracked-files=all` is not empty | Ruff, the unit suites and the doc checks read the files on disk; a fix left uncommitted gave a false PASS on a commit that fails `ruff format --check` (principal-engineer review 5904438374) | Run the checks in a throwaway worktree of HEAD: rejected, a second `uv` environment and test run per push (judgment) |
| 11 | **Review B2:** pr-check stops with `FAIL  base / branch contains origin/main` when `git merge-base --is-ancestor origin/main HEAD` is false, naming `git merge origin/main` | CI runs main's gate scripts on the merged PR; the ST-085 branch (95 commits behind) has no `check_cost_table.py` and a 90-line older `check_docs.py`. A merge is enough; pushed history is never rebased | Run main's copy of each script: rejected, the scripts import their siblings and read the tree |
| 12 | **Review S1:** `PR_NUMBER`, `PR_TITLE`, `GITHUB_REPOSITORY` and `GITHUB_TOKEN` reach the five pr-policy steps only (`env` prefix), not Ruff or the unit suites | In CI only the pr-policy steps get them (security-privacy-engineer review 5904437651) | Export to every step: the first version; rejected |
| 13 | **Review N1:** the PR lookup is `gh api -X GET repos/<repo>/pulls -f head=<owner>:<branch> -f state=open` | gh encodes the branch name as a query field | Interpolate it into the URL: the first version; rejected |
| 14 | A failed PR lookup (as opposed to no open PR) makes the cost-table step `FAIL`; the web unit suite is `SKIP` when the `node_modules` directory under `web/` or its `test:unit` script is missing (when it runs, inside `scripts/test-unit.sh`, its line carries that step's verdict) | A lookup error leaves unknown whether CI will run the step; a suite that did not run never shows `PASS` (principal-engineer, optional items) | — |
| 15 | With `make hooks`, the hook and script that run are the checked-out branch's copies (`docs/process/ci-cd.md` §2.2) | `core.hooksPath .githooks` is relative to the work tree (security-privacy-engineer O1) | An absolute path to one clone: rejected, it breaks worktrees |

## 3. Red first

Command: `cd infra && uv run pytest -q -p no:cacheprovider tests/test_pr_check.py tests/test_pr_check_scenarios.py` on the red-first commit (Gherkin feature, scenario bindings, unit tests and the throwaway-checkout helper; no implementation).

Red: `27 failed in 6.87s`. Each failure is for the right reason: `scripts/pr-check.sh` and `.githooks/pre-push` do not exist (`No such file or directory`, exit 127) and `make` has no `hooks` or `pr-check` target (`No rule to make target`).

Green: the same command, `27 passed`.

Corrections to the red tests made in the green commit `f19f164d`, before any review accepted them (QA O2). None weakens a check; each made the planted situation match the case it names:
- **`infra/tests/pr_check_repo.py` gains the citation register** (`docs/research/agentic-sdlc-best-practices.md`, copied from the repo). `check_docs.py` fails closed without it ("register ... not found"), so the clean throwaway branch failed for a missing harness file, not for anything a real branch does. The doc check still runs on every scenario.
- **`unit_not_run` matched `pytest` in the stub log's working-directory column** (`/tmp/pytest-of-root/...`), so it failed whatever ran. It now looks only at the recorded command arguments; a `pytest` call still fails the step.
- **"Every check runs after one has failed": the commit order was reversed.** With the test edit first, `check_red_first.py` correctly passed (an earlier test-only commit is a red step), so the scenario did not plant a red-first failure. Production code now comes first, so three gates are planted to fail as the scenario says.

### Review round 1 fixes (red, then green)

Command: `cd infra && uv run pytest -q -p no:cacheprovider tests/test_pr_check.py tests/test_pr_check_scenarios.py` on the red commit `4298443a` (new scenarios and steps only).

Red: `9 failed, 23 passed`, each for the reason the review gave:
- dirty tree (both examples), branch behind main and a failed PR lookup: `pr-check` exited 0 (`assert 0 != 0`);
- the open-PR scenario: the lookup was `gh api repos/.../pulls?head=nhuthuynh:s06/planted&state=open`, not the encoded `-X GET ... -f head=...` form;
- the web scenario: no `Web unit suite (pnpm test:unit)` line;
- the clean, every-check and `--fast` scenarios: 11 summary lines, not 14 (no tree, base or web line).

Green: the same command, `32 passed`. One more correction in the green commit: the `--fast` step that re-runs pr-check without `--fast` restores the stub log afterwards, so the next step ("the unit suites did not run") judges the `--fast` run only. Mutation check (QA O1): with `--fast` also skipping `ruff check`, the `--fast` scenario fails (`1 failed`); restored.

## 4. Cost per PR (ADR 0056 decision 1)

| Round | wall_time_min | total_cost_usd | Note |
|---|---|---|---|
| Author build (red, green, checks) | not measured | not measured | the session does not expose per-ticket wall time or cost to the agent |
