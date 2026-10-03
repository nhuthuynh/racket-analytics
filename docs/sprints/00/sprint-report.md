# Sprint 0 report: Foundations and walking skeleton

- **Prepared by:** engineering-manager, 2026-10-03, for the sprint review planned on 2026-10-16.
- **Timing caveat:** the sprint was planned for 2026-10-05 to 2026-10-16, but all the work and three review rounds ran in one compressed agent session on 2026-10-03. Calendar metrics (lead time, time-to-merge, nightly streaks) therefore cannot be measured.
- **Inputs:** lane results, `review-rounds.md`, the round-3 findings, `blockers.md`, `decision-log.md`, `test-change-requests.md`, `test-report.md`, ADRs 0008 to 0021, and the EM's own re-run of the suites (§5).
- **Machine-readable status:** [`status.json`](status.json). **Retro:** [`docs/retros/2026-10-16-sprint-00.md`](../../retros/2026-10-16-sprint-00.md).

## 1. Verdict

**Goal partly met.** The walking skeleton works end to end on real services: Compose with Postgres 16, SeaweedFS 3.97, the API, the worker and the web app. Playwright Chromium passes 7 of 7, and 21 of 21 with `--repeat-each=3`. All backend, infra and web suites are green locally. The sprint still cannot close, for three reasons:

1. CI has **never run on GitHub**. There is no remote, so there is no green `main`, no failing sample PR and no nightly E2E streak.
2. **Six test-change requests are waiting for QA approval**, so the §8 test-immutability gate would fail on the PR.
3. The QA test report is stale and unsigned. Before this report, `status.json`, `progress.md` and the retro were missing. They now exist.

The fix loop ran 3 rounds. Under working-agreement §7 step 5, the open blocker and major findings left after round 3 are **escalated to the human product owner** (§8).

## 2. Committed vs done per story

Units come from ADR 0010. "Implemented" means the story was built, went through 3 fresh-context review rounds and was verified locally with command evidence. **No story meets the full story-level DoD yet**: nothing has merged through a green CI gate, and the test-change approvals are pending.

| Story | Size (units) | Status | Evidence | Open items |
|---|---|---|---|---|
| ST-001 Dev env, prod parity | M (2) | Implemented | Round 3: `docker compose -p r3review … up -d --no-build --wait` → rc=0, every service healthy (migrate and objectstore-init exited 0). IT-00-16 parity is green on SeaweedFS 3.97, both as the local binary and in Compose | `compose up --build` needs the `extra_ca` build secret behind the proxy. F-1: api and worker share one DB owner role and S3 key. QA-R2-06: SeaweedFS admin ports are reachable from the sandbox network |
| ST-002 CI and merge gates | L (4) | **Partial** | `actionlint -color=false` → rc=0. `cd infra && uv run pytest -q` → 197 passed (workflow structure tests included) | **Never run on GitHub** (QA-R3-02, blocker). A human admin must set up branch protection, labels and the `ANTHROPIC_API_KEY` secret |
| ST-003 Hooks and immutability guard | M (2) | Implemented | PreToolUse on `.env` → exit 2. PostToolUse formats the file. Stop blocks on a failing unit test (exit 2). Hook tests: 86 passed. Guard: 14 passed | QA-R1-12: `fixtures/clips/` is not protected (nit). ADR 0013 is Proposed |
| ST-004 Test harness | M (2) | Implemented | Markers, pytest-bdd tag mapping, fixtures and builders are in place. Hypothesis `ci` profile: 262 passed in 16.8 s (90 s budget). The CI marker filter drops no test: `--co -m "not (unit or integration or scenario or regression)"` → 0 collected | The conftest `APP_ENV` change is pending QA. 22 modules still carry stale `red_until` markers (QA-R3-08) |
| ST-005 API skeleton | M (2) | Implemented | Error-body, trace-header and IT-00-11..15 suites are green. The `dev_environment` and `errors_and_tracing` features pass | R3-04: a 500 on a tus route has no `Tus-Resumable`. R3-05: the JSON charset differs from the contract (both minor) |
| ST-006 Ownership and BOLA | M (2) | Implemented | The BOLA matrix covers 5 ID routes, anonymous access and the route inventory, and is green. Ad-hoc probes as Carlos returned 404 everywhere (security rounds 2 and 3) | SEC-R3-01: dev sign-in is accepted with `APP_ENV=staging` (nit). R1-09: N+1 queries on the match list |
| ST-007 Queue and worker + SPIKE-09 | M (2) | Implemented | IT-00-03/04/05 and `job_resilience` are green. SPIKE-09 handled 504 to 888 jobs/s with 0 double claims (note on ADR 0008). ADR 0017. R1-06: the worker survives a Postgres restart (verified on Compose) | R2-08: worker coverage is under the 85% floor (runner 80%, `__main__` 32%) |
| ST-008 tus core | M (2) | Implemented | IT-00-06/07/08, `upload_resume_core` and the tus regression tests from rounds 1 and 2 are green. Live Compose checks passed: 1 MiB chunks, a short body is atomic, PATCH after completion → 409 | R3-03: contract chunk size vs ADR 0019 (major, principal-engineer). R3-06: the retry-after-commit-failure path has no test |
| ST-009 Probe stage in sandbox | M (2) | Implemented | IT-00-09 is green. IT-00-10 (old and strict files) on Compose → 12 passed. LGPL ffprobe pinned by checksum (ADR 0020). The format allowlist closes the DASH SSRF (ADR 0021) | QA-R3-07: retire the weak IT-00-10 probe. The LGPLv3 reading needs security sign-off. HTTPS presigned URLs are untested. QA-R3-05: `nan`/`inf` durations escape as `ValueError` |
| ST-010 PWA shell | L (4) | **Partial** | Vitest: 132 passed. `tsc` and ESLint are clean. First-route JS is 103.1 KB gzipped. Playwright Chromium on Compose: 7 passed; `--repeat-each=3` → 21 passed; axe found 0 serious or critical issues | WebKit has never run (QA-R3-09). The design and security reviews of ST-010 have not been held. The manual keyboard and screen-reader pass is not done. QA-R3-06: the reload test does not resume from a non-zero offset |
| ST-011 Fixture and manifest check | S (1) | Implemented | Two runs give the same sha256. `check_fixtures.sh HEAD` → OK. `gold_set_integrity`: 2 passed | — |
| ST-012 Scenarios and regression scaffolds | M (2) | Implemented | 74 tests were red before implementation. Now all 7 features (19 collected scenarios) and all 6 regression suites are green | 6 test-change rows are pending (R3-02). The test report is stale (QA-R3-04) |
| SPIKE-01 CV licence posture | S (1) | **Partial** | ADR 0015 is Proposed: 45 rows; the GitHub licences were fetched and hashed | The PE and security reviews have not been held. Sources outside GitHub are unverified (blocked by egress). Needs the PO's decision on OQ-12 |

**Totals:** 28 units planned. 19 implemented (68%). 9 partial (ST-002, ST-010, SPIKE-01). 0 meet the full DoD.

## 3. Quality gates (sprint-00 §8)

"Local" means run in this dev container on real services. "CI" means a GitHub Actions run, and there has been none.

| Gate | Threshold | Status | Command → result |
|---|---|---|---|
| Ruff, mypy, ESLint, tsc | 0 errors | **Pass (local)** | `uv run ruff check .` → All checks passed!; `ruff format --check .` → 144 files already formatted; `uv run mypy` → no issues in 55 files; `eslint --max-warnings=0 .` rc=0; `tsc --noEmit` rc=0 (round 3) |
| Unit suites and budgets | 100%; domain < 10 s; backend unit ≤ 60 s | **Pass (local)** | `run_with_budget.py 10` → 262 passed, 3.8 s; `run_with_budget.py 60 -m unit` → 282 passed, 4.3 s (round 3). EM re-run: `--co -m unit` → 282 tests |
| Integration and scenario on Compose | 100%; < 10 min | **Pass locally; never run in CI** | EM re-run: `env -u APP_ENV uv run pytest -q -rs` → **439 passed, 5 skipped in 51.87s**. The 5 skips are IT-00-10, which needs Compose; on Compose it gives 12 passed (round 3) |
| Mandatory regression suites | 100% | **Pass (local)** | BOLA, error bodies, trace header, worker crash, fail closed and upload resume are in `backend/tests/regression/`: 39 tests, all green in the run above |
| Coverage on changed lines | API ≥ 85%, worker ≥ 85%, web ≥ 80% | **Partial** | `diff-cover --fail-under=85` → 92% (backend). Web: 87.66% lines. Per area, worker `runner.py` is at 80% and `__main__.py` at 32%; CI does not measure per area (R2-08) |
| axe-core | 0 serious or critical | **Pass (Chromium only)** | Playwright `7 passed` with axe on every page. WebKit has not run |
| First-route JS | ≤ 200 KB gz | **Pass (local)** | `check_first_route_js.py --budget-kb 200` → 103.1 KB |
| gitleaks, audit, licence, SBOM | 0 secrets; 0 criticals; 0 AGPL/NC | **Partial** | `pnpm audit --prod` and `pip-audit --strict` → no known vulnerabilities (round 2). gitleaks 8.28.0 found 0 leaks in round 0 but is not installed for later rounds. The Syft SBOM licence gate has not been run locally |
| Test and gold immutability | No unapproved test change | **Fail** | `grep -c '\| Pending \|' test-change-requests.md` → 6 (R3-02, QA-R3-03) |
| PR size | about 100 lines; > 400 needs an EM waiver | **Fail** | `git log --shortstat`: commit 1d10ec8 → 173 files, +15,020; commit 3492042 → 138 files, +15,280. Rounds 1-3 uncommitted: 26 files, +360/−62 plus ~20 new test files. No waiver was recorded |
| Fresh-context review | No open Blocking; ≤ 3 iterations | **Fail → escalated** | 3 rounds ran. After round 3 there are 4 open blockers (R3-01, R3-02, QA-R3-01, QA-R3-02) and 3 majors (R3-03, QA-R3-03, QA-R3-04). This report closes R3-01 and QA-R3-01 (§6) |
| Per sprint: E2E green on ≥ 3 nightly runs | 3 runs | **Not met** | No CI |

## 4. Definition of Done (sprint-00 §9 plus sprint-level DoD)

| Item | Met? | Evidence |
|---|---|---|
| Every §8 gate runs in CI on `main`, and a failing sample PR shows each gate blocking | **No** | No remote (`git remote -v` is empty); blockers.md |
| Every ST-003 hook is demonstrated | Yes | decision-log.md, SRE row "Hook demo on the real repo" |
| ADR 0011 and the SPIKE-01 ADR are written; ADR 0008 has a SPIKE-09 note | Yes | ADR 0011, ADR 0015, ADR 0008 Notes |
| Context canvases and the context map are merged | Yes | `docs/architecture/contexts/`, `context-map.md` (commit 1d10ec8) |
| Sprint 1 stories meet the DoR | **No** | sprint-01 §14.5 has 12 pending items (QA testability P2, PO ratification of ADR 0009 P3, design review P7, OQ-06 P12, …) |
| `status.json` has planned and completed units | Yes (this sprint) | [`status.json`](status.json) |
| Retro written with owned, dated actions | Yes | [retro](../../retros/2026-10-16-sprint-00.md) |
| Test report, `status.json` and `progress.md` are up to date | **Partly** | `status.json` and `progress.md` written; `test-report.md` is stale (QA-R3-04) |
| DORA and PR time-to-merge recorded | **No (not measurable)** | Nothing deployed and no PRs; recorded as N/A in the retro |
| Every story meets the story-level DoD | **No** | §2 |
| No untriaged Blocking security findings | Yes | SEC-R1-01 (SSRF) was fixed in round 1. The open security items are nits or minors with owners |

## 5. Test counts by level

The EM re-ran the suites on 2026-10-03 against a throwaway local Postgres 16 and SeaweedFS (`scripts/dev-postgres.sh` and `scripts/dev-objectstore.sh` with `RA_DEV_STATE` in the scratchpad; both stopped afterwards).

| Level | Count | Command → result |
|---|---|---|
| Backend, all | 444 | `cd backend && env -u APP_ENV uv run pytest -q -rs` → `439 passed, 5 skipped in 51.87s` |
| Backend unit | 282 | `uv run pytest --co -m unit` → `282/444 tests collected` |
| Backend integration | 143 | `--co -m integration` → `143/444` |
| Backend scenario (Gherkin) | 19 | `--co -m scenario` → `19/444` (7 features, 17 scenarios, and the outline expands to 3) |
| Backend regression | 39 | `--co -m regression` → `39/444` |
| Infra, hooks and CI scripts | 197 | `cd infra && uv run pytest -q` (clean env) → `197 passed in 46.29s` |
| Web unit (Vitest) | 132 | `cd web && pnpm exec vitest run` → `Test Files 17 passed (17)`, `Tests 132 passed (132)` |
| E2E (Playwright Chromium) | 7 | Round 3, on Compose: `7 passed (14.0s)`; `--repeat-each=3` → `21 passed`. Not re-run by the EM, because it needs the Compose stack and a web build |

The level counts add up to more than 444 because some tests carry two markers.

### 5.1 A false red in the EM's own run

The first infra run was `6 failed, 191 passed in 66.68s`, for example `test_object_store_parity.py::test_aborted_multipart_upload_leaves_no_object`. The cause was the EM's script, not the code. It stopped the local SeaweedFS and then ran the infra suite in the same shell, so `S3_ENDPOINT_URL` still pointed at the stopped server. Re-running with those variables unset (`env -u S3_ENDPOINT_URL -u DATABASE_URL … uv run pytest -q`) gave `197 passed`. The lesson, that stale service variables give false reds, is recorded in the retro.

## 6. Unresolved findings after round 3 (escalation, working-agreement §7.5)

| ID | Severity | Status after this EM pass | Owner | Needed |
|---|---|---|---|---|
| R3-01 / QA-R3-01 | blocker | **Closed by this pass**: `status.json`, `progress.md`, the retro and this report now exist | engineering-manager | QA fills the test fields at sign-off |
| R3-02 / QA-R3-03 | blocker / major | Open | senior-qa-engineer | A decision on the 6 rows. Round-3 QA evidence supports approving all 6 and retiring the weak IT-00-10 probe |
| QA-R3-02 | blocker | Open (environment) | Human PO / repo admin | Push to GitHub, set branch protection, labels and secret, open the failing sample PR, and collect 3 nightly runs |
| R3-03 | major | Open | principal-engineer | Accept or amend ADR 0019, and amend api-sprint-00 §1, §8 and §9 |
| QA-R3-04 | major | Open | senior-qa-engineer | Rewrite and sign the test report from the round-3 counts and §5 |
| Minors and nits | — | Open, recorded | various | R3-04/05/06/07, SEC-R3-01/02, QA-R3-05..10, R2-05..09 leftovers, QA-R2-04/06; carried over (§8) |

## 7. Deviations from plan

- The sprint ran on 2026-10-03, before its planned dates.
- Work landed in two very large commits instead of ~100-line PRs.
- Docker turned out to be available; QA's initial brief said it was not, which caused stale skip and blocker rows.
- The backend wrote the probe stage and `MediaFacts` (ST-009 units) because the ST-007 suites needed a real stage.
- `GET /media` returns 204 while not probed, a contract amendment (R1-07).
- A third dev user, `dana`, was added to fix an E2E ordering problem.
- One-shot `migrate` service added to Compose.
- Jaeger `tracing` service added.
- Package name is `racket`, not `racket_analytics` (ADR 0008 note).
- The FastAPI tus core was chosen over tusd (ADR 0011).
- A hand-written SKIP LOCKED queue was chosen over procrastinate (ADR 0017).
- The browser reaches the API through a Next `/api` rewrite with 8 MiB chunks, instead of the contract's 64 MiB (ADR 0019).
- ADRs 0016 and 0017 were missing from the ADR README index. The EM appended them on 2026-10-03.

## 8. Carried over to Sprint 1

1. ST-002 CI evidence: first GitHub run, the failing sample PR, 3 nightly runs, and WebKit (human admin + SRE).
2. ST-010 remainder: WebKit, the design review, the security review, the manual a11y pass, and a reload test that resumes from a non-zero offset (FE + designer + security + QA).
3. SPIKE-01 reviews and the PO decision on OQ-12 (ML + PE + security + PO).
4. QA decisions on the 6 test-change rows, retiring the weak IT-00-10 probe and the stale `red_until` markers, and the signed test report (QA).
5. Contract hygiene: ADR 0019 and §8/§9 (R3-03), `Tus-Resumable` on 500 and 405 responses (R3-04, QA-R3-10), charset (R3-05) (PE + BE).
6. Robustness: a regression test for the retry-after-commit-failure path (R3-06), `nan`/`inf` duration handling (QA-R3-05), worker subprocess coverage (R2-08), and the N+1 on the match list (R1-09) (BE / ML).
7. Security hardening: separate DB roles (F-1); bind SeaweedFS admin ports off the sandbox network (QA-R2-06); refuse dev sign-in outside dev/test (SEC-R3-01); harden the migrate and api containers (SEC-R2-03); HTTPS presign CA (SRE / BE / ML / security).
8. Sprint 1 DoR items P1 to P12 (BA, PM, PO).

## 9. Demo script outcome (sprint-00 §12)

| Step | What can be shown in this sandbox | Needs Docker / CI / PO |
|---|---|---|
| 1. `compose up`, `/readyz` ready | Yes. Docker works here; round 3 ran `up --wait` rc=0 and `/readyz` returned `ready` | `--build` needs `--secret id=extra_ca` behind this proxy |
| 2-4. Sign in as Ivy, empty state, create a match, upload, facts 1:00 · 60 fps · 1920×1080 | Yes. Playwright Chromium on Compose passed (E2E-00-01); the empty state is shown with Dana | WebKit |
| 5. One trace across API, enqueue and worker | Yes, in Jaeger and in IT-00-11 (in-memory exporter) | — |
| 6. Carlos gets "not found" plus a security-log line | Yes. BOLA UI spec and ad-hoc probes | — |
| 7. SIGTERM the worker; job requeued; one set of facts | Yes. `test_worker_crash.py` and the `job_resilience` feature (SIGTERM requeue 1.1 s, SIGKILL recovery 17 s) | A live `docker compose kill` was not rehearsed by the EM |
| 8. Red CI gate blocks a bad PR; hook blocks a `.env` write | Hook: yes. CI: **no** | A GitHub remote and branch protection |
| 9. SPIKE-01 table, ask for OQ-12 | Yes (ADR 0015) | PO decision |
| 10. Ratify ADRs 0001, 0002, 0007, 0009 and the ADR 0010 time assumption | — | PO |

Evidence for the live demo goes into `docs/sprints/00/demo.md` on the review day. It was not produced here, because the EM did not run the Compose demo in this pass.

## 10. Appendix: EM re-run output, infra and web

```text
$ cd backend && env -u APP_ENV uv run pytest -q -p no:cacheprovider -rs
SKIPPED [2] tests/integration/test_it_00_10_worker_sandbox.py:42: needs the Compose stack
SKIPPED [3] tests/integration/test_it_00_10_worker_sandbox_strict.py:103: needs the Compose stack
439 passed, 5 skipped in 51.87s
$ uv run pytest -q --co -m unit|integration|scenario|regression
282/444, 143/444, 19/444, 39/444 tests collected
$ cd infra && uv run pytest -q   # clean env
197 passed in 46.29s
$ cd web && pnpm exec vitest run
Test Files  17 passed (17)
     Tests  132 passed (132)
$ scripts/dev-objectstore.sh stop; scripts/dev-postgres.sh stop
dev-objectstore: stopped and removed /tmp/racket-s3.PR0jdD
dev-postgres: stopped and removed /tmp/racket-pg.K1PCIL
```
