# 0013. Agent hooks: deterministic gates that never wedge a session

- **Status:** Proposed (needs review by security-privacy-engineer and senior-qa-engineer, ST-003)
- **Date:** 2026-10-03
- **Deciders:** sre-devops-engineer
- **Consulted:** none yet
- **Related:** ST-003; working-agreement §7.1; [DPA/AI-10]; NFR-056, NFR-073, NFR-078; ADR 0014; `docs/process/ci-cd.md` §3

## Context and problem statement

ST-003 asks for Claude Code hooks: format and lint on every edit (PostToolUse), blocked writes to secret paths plus a Bash audit log (PreToolUse), and a unit-test gate before a turn ends (Stop) [DPA/AI-10]. Hooks run on every tool call of every agent. A hook that is slow, crashes, or blocks for reasons the agent cannot fix would stall the whole team. Sprint-00 §11 lists "hooks slow agents down too much" as a risk. We must decide how hooks behave on errors, which failures block, and how to keep them fast.

## Decision drivers

- Hooks are deterministic, unlike prompt instructions [DPA/AI-10]. Exit code 2 denies a PreToolUse call and feeds stderr back [DPA/AI-10, research G-VER-4].
- Secrets never enter agent edits (NFR-056).
- Unit tests must pass before a turn ends (working-agreement §7.1), and the unit suite must be fast (NFR-073).
- QA's red-first tests (ST-012) fail by design until their story lands.
- CI remains the authoritative gate (ADR 0014).

## Considered options

1. **Deterministic but defensive.** Each rule blocks only on a condition the agent can fix: a secret-path write, a remaining lint error, or a failing unit test. Malformed input, missing tools and internal hook errors allow the call and warn on stderr.
2. **Fully fail closed.** Any hook error blocks.
3. **Do nothing:** rely on CLAUDE.md instructions and CI only.

## Decision outcome

Chosen: **option 1**, with these specifics:

- **PreToolUse:**
  - resolves `..` and symlinks before matching, and denies `.env*`, `*.pem`, `*.key` and `infra/secrets/**`;
  - parses Bash for redirection, `tee`, `cp`, `mv` and `install` targets (best effort; reading is governed by `permissions.deny`);
  - audits every Bash command, including denied ones.
- **PostToolUse:**
  - runs `ruff check --fix` → `ruff format` → `ruff check`. Exit 2 reports what is left (the edit is kept);
  - for TS/JS, runs `eslint --fix`;
  - a missing linter is a note, not a block.
- **Stop:**
  - runs `scripts/test-unit.sh`: marker `unit and not slow and not red_until`. pytest's exit code 5 (no tests collected) counts as a pass;
  - blocks with the last 60 lines of output; enforces a 180 s budget inside a 240 s hook timeout;
  - never loops (`stop_hook_active`) and does nothing under GitHub Actions;
  - caches the fingerprint of the last green run (HEAD + diff + untracked file hashes + command), so turns that change nothing cost nothing.
- Stdlib only, no network, Python 3 from `PATH`.

## Pros and cons of the options

### 1. Deterministic, defensive
- Good: blocks exactly the conditions ST-003 names; a hook bug cannot stall agents; fast on no-op turns.
- Bad: a crash in the secret-path hook *allows* the write. Mitigations: tests cover the deny paths (62 cases), `permissions.deny` blocks reads, `.gitignore` excludes the paths, and gitleaks in CI catches committed secrets (defence in depth, judgment).

### 2. Fully fail closed
- Good: strongest guarantee for the secret rule.
- Bad: any environment glitch (missing interpreter, unexpected JSON shape after a Claude Code upgrade) blocks every edit for every agent. That is exactly the sprint-00 §11 risk.

### 3. Do nothing
- Bad: instructions are advisory, and hooks are the documented way to make actions always happen [DPA/AI-10].

## Consequences

- Good: all three hook types are demonstrable (sprint-00 §9 DoD).
- Trade-off: excluding `red_until` from the Stop gate means agents can end a turn while QA's red-first tests fail. Those tests stay red in CI until the story lands, by design.
- Follow-up: measure hook friction (Stop-hook duration, block count from the audit log) for the retro focus "tooling, hooks and the auto-review loop".

## Evidence

| Claim | Evidence | Type |
|---|---|---|
| Deny/allow behaviour, audit log, malformed input, speed | `cd infra && uv run pytest -q tests/test_hook_pre_tool_use.py` → `62 passed` | test result |
| Format/fix/report and ESLint paths | `uv run pytest -q tests/test_hook_post_tool_use.py` → `11 passed` | test result |
| Stop gate: blocks on failure, time budget, loop guard, cache keyed on tree and command, CI skip | `uv run pytest -q tests/test_hook_stop.py` → `13 passed` | test result |
| Settings wire every hook to an existing script; reads of secrets denied | `uv run pytest -q tests/test_claude_settings.py` → `7 passed` | test result |
| Demo on the real repo: `.env` write → exit 2 with reason; Bash `echo > infra/secrets/db` → exit 2 and audited `"decision": "deny"`; unformatted file → formatted, unused import removed; failing unit test → Stop exit 2 with the pytest failure; real `scripts/test-unit.sh` → `42 passed, 92 deselected in 0.48s` | commands and outputs in `docs/sprints/00/decision-log.md` (2026-10-03 rows) | test result |
| Exit-2 semantics, Stop gating, Bash audit via PreToolUse | [DPA/AI-10]; research G-VER-4 | verified source |
