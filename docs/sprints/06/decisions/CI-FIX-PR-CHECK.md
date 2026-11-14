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

## 3. Red first

Command: `cd infra && uv run pytest -q -p no:cacheprovider tests/test_pr_check.py tests/test_pr_check_scenarios.py` on the red-first commit (Gherkin feature, scenario bindings, unit tests and the throwaway-checkout helper; no implementation).

Red: `27 failed in 6.87s`. Each failure is for the right reason: `scripts/pr-check.sh` and `.githooks/pre-push` do not exist (`No such file or directory`, exit 127) and `make` has no `hooks` or `pr-check` target (`No rule to make target`).

Green: the same command, `27 passed`.

## 4. Cost per PR (ADR 0056 decision 1)

| Round | wall_time_min | total_cost_usd | Note |
|---|---|---|---|
| Author build (red, green, checks) | not measured | not measured | the session does not expose per-ticket wall time or cost to the agent |
