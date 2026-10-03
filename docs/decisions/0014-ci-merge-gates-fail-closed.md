# 0014. CI merge gates: fail closed, one required check, pinned actions, SBOM-based licence gate

- **Status:** Proposed (needs review by senior-qa-engineer and security-privacy-engineer, ST-002)
- **Date:** 2026-10-03
- **Deciders:** sre-devops-engineer
- **Consulted:** none yet (written in Sprint 0 lane work; reviewers per working-agreement §6)
- **Related:** ST-002, ST-003; NFR-015, NFR-027, NFR-056, NFR-062, NFR-071, NFR-073, NFR-074, NFR-077, NFR-078; ADR 0008; `docs/process/ci-cd.md`

Note: 0011 is left free for the ST-008 tus server decision that `sprint-00.md` §3.1 names as "ADR 0011"; 0012 was taken concurrently by the senior-qa-engineer, so this ADR is 0014.

## Context and problem statement

Sprint 0 must run every §8 gate on every PR, and "a red gate blocks the merge" (sprint-00 §1). Most product code does not exist yet, so many gates have nothing to check on day 1. We must decide:

- how a gate behaves when its target is missing;
- how branch protection learns which checks are required;
- how third-party actions are trusted;
- how the NFR-062 licence check sees only the *shipped* dependency graph.

## Decision drivers

- A red gate must block. A gate that silently passes gives false assurance (EP/ENG-24, "evidence, not claims").
- Supply chain: no AGPL or non-commercial components (NFR-062). Secrets only in secret stores (NFR-056).
- Least privilege for CI tokens and the review bot [DPA/AI-11, DPA/AI-13].
- Keep the pipeline simple to reason about [EP/ENG-25].

## Considered options

1. **Fail closed, plus one aggregate `ci-gate` check** that `needs` every per-PR job and fails unless each one succeeded.
2. Conditional jobs (`if: hashFiles(...)`) that skip until the project exists, each job listed separately in branch protection.
3. Do nothing yet: add CI when code exists.

Sub-choices:

- **Action trust:** (a) pin every action to a commit SHA and prefer GitHub-owned actions; (b) use floating major tags.
- **Secret scan:** (a) the gitleaks binary, version-pinned and sha256-checked; (b) `gitleaks/gitleaks-action`.
- **Licence gate:** (a) Syft CycloneDX SBOM of the installed runtime graph (`uv sync --no-dev`, `pnpm install --prod`), then our checker `scripts/ci/check_licences.py`; (b) per-ecosystem tools (pip-licenses, license-checker).

## Decision outcome

Chosen: **option 1, with 1(a), 2(a) and 3(a).**

- **Fail closed.** A skipped job counts as a failure in `ci-gate`. The one exception is `pr-policy` outside PR events, which has nothing to check. This makes expected-red gates visible from day 1, which is what QA's red-first suites (ST-012) need.
- **One required check (`ci-gate`).** Branch protection names one check. Adding a job only needs a change to `needs`, and `infra/tests/test_workflows.py` asserts that `needs` lists every per-PR job.
- **SHA pinning.** Tags were resolved with `git ls-remote` on 2026-10-03. The only third-party actions are `anchore/sbom-action` (Apache-2.0, fetched) and `anthropics/claude-code-action` (MIT, fetched). uv, pnpm, actionlint and diff-cover are installed from PyPI or corepack at pinned versions.
- **gitleaks binary.** `gitleaks-action` needs a `GITLEAKS_LICENSE` for organisation accounts (its README, fetched 2026-10-03). The MIT-licensed binary does not.
- **Licence gate on SBOMs.** One checker covers Python and npm. The denied set is AGPL and non-commercial licences (NFR-062). SSPL, BUSL, Commons Clause and PolyForm Noncommercial are also denied, because they restrict commercial use (judgment). LGPL passes, because ADR 0008 accepts unmodified-library use, pending confirmation by the security-privacy-engineer. Components with unknown licences are listed but do not fail the gate (judgment: Syft's licence detection is incomplete). Exceptions need an ADR reference (`infra/licence-exceptions.json`).

## Pros and cons of the options

### 1. Fail closed + aggregate check
- Good: no false greens; one branch-protection entry; red-first suites are visible.
- Bad: `main` is red until ST-005..ST-010 land, so merges in Sprint 0 need the EM to accept known-red gates or land in dependency order (judgment).

### 2. Conditional skips
- Good: green pipeline on day 1.
- Bad: a renamed or deleted project would silently skip its gates forever. `hashFiles` is not available in job-level `if` (judgment, from actionlint behaviour), so step-level checks would be needed everywhere.

### 3. Do nothing
- Bad: violates the sprint goal and the DoD.

### SHA pinning vs tags
- Good (SHA): immutable and reviewable. Bad: updates are manual (a Dependabot config for actions is a follow-up).

### SBOM checker vs per-ecosystem tools
- Good (SBOM): one policy, and the SBOM artefact is produced anyway (NFR-062). Bad: depends on Syft's licence extraction quality.

## Consequences

- Good: every §8 gate exists and blocks; the gate list is test-guarded.
- Trade-off: known-red gates during Sprint 0; the EM tracks them in `progress.md`.
- Follow-up:
  - a human admin applies branch protection, labels and the `ANTHROPIC_API_KEY` secret (`ci-cd.md` §2.1);
  - add Dependabot for `github-actions` and the lockfiles (S, Sprint 1);
  - security-privacy-engineer confirms the SSPL/BUSL deny list and the LGPL allowance.

## Evidence

| Claim | Evidence | Type |
|---|---|---|
| Workflows are valid; shell steps pass shellcheck | `actionlint -color=false` → exit 0 (2026-10-03) | test result |
| Gate helpers behave as specified (time budget, licence deny/allow/fail-closed, flaky report, PR size, first-route JS, immutability guard) | `cd infra && uv run pytest -q tests/test_ci_scripts.py tests/test_test_immutability_guard.py` → `26 passed`, `14 passed` | test result |
| `ci-gate` needs every per-PR job; actions SHA-pinned; review bot guarded | `uv run pytest -q tests/test_workflows.py` → `7 passed` | test result |
| gitleaks detects a planted token with our config, and the repo is clean | `gitleaks dir <tmp-with-ghp_ token> --config .gitleaks.toml` → `leaks found: 1`; `gitleaks dir .` → `no leaks found` | test result |
| gitleaks-action needs a licence key for organisations | https://raw.githubusercontent.com/gitleaks/gitleaks-action/master/README.md (fetched 2026-10-03), "required for organizations" | fetched |
| Licences: Syft, sbom-action, diff-cover Apache-2.0; actionlint MIT; claude-code-action MIT; Jaeger Apache-2.0 | LICENSE files fetched 2026-10-03 from raw.githubusercontent.com (anchore/syft, anchore/sbom-action, Bachmann1234/diff_cover, rhysd/actionlint, anthropics/claude-code-action, jaegertracing/jaeger) | fetched |
| Ubuntu 24.04 runners ship PostgreSQL 16 (used by `infra-tests`) | https://raw.githubusercontent.com/actions/runner-images/main/images/ubuntu/Ubuntu2404-Readme.md (fetched 2026-10-03): "PostgreSQL 16.15" | fetched |
| Events created by `GITHUB_TOKEN` do not start new workflow runs (review-bot loop guard) | GitHub Actions documentation; not in our research sources | (judgment) |
| A CI run on GitHub | Not yet available: no remote in this session | — |
