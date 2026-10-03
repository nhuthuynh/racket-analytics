# Sprint 0 test-plan status

> **Superseded for current counts (2026-10-03, review round 1):** the totals below are from before ST-005..ST-010 landed. Current suites, counts and commands are in [test-report.md](test-report.md). This file stays as the red-first history.

- **Owner:** senior-qa-engineer · **Stories:** ST-004 (harness), ST-011 (fixture + ManifestCheck), ST-012 (scenarios and suites written first)
- **As of:** 2026-10-03, before ST-005..ST-010 start
- **Totals (backend):** 150 tests: **74 green, 74 red, 2 skipped**. E2E (Playwright): 7 tests, all red (no web app yet).
- **Rule:** red tests are red on purpose (ST-012). Each one fails on its own with `RED until ST-xxx: seam … is not implemented yet`, and the implementing story turns it green **without editing it** (EP/ENG-28; CI immutability job from ST-003). None is `xfail`; red-first tests carry the marker `red_until(story=…)`, which `scripts/test-unit.sh` (Stop hook) deselects. The seams are listed in ADR 0012 and `backend/tests/support/contract.py`.

## How to reproduce

```bash
cd backend && uv sync                                   # Python 3.11, uv; dev group = pytest, pytest-bdd, hypothesis, httpx, ruff, mypy
eval "$(../scripts/dev-postgres.sh start)"              # real Postgres 16 -> DATABASE_URL (never SQLite, AQS/OPS-05)
eval "$(../scripts/dev-objectstore.sh start)"           # SeaweedFS 3.97 -> S3_* (ADR 0008 part C)
uv run pytest -q                                        # everything
uv run pytest -q -m "unit and not red_until"            # what the Stop hook runs (scripts/test-unit.sh)
HYPOTHESIS_PROFILE=ci uv run pytest -q -m unit          # >= 1,000 examples per property
uv run pytest tests/features --junitxml=../.local/scenarios.xml && \
  uv run python -m tests.tools.scenario_report --junit ../.local/scenarios.xml   # @needs-verification listed separately
uv run racket-manifest-check ../fixtures/clips/synthetic-60s                     # or ../scripts/ci/check_fixtures.sh <base-ref>
```

## Evidence (commands run on 2026-10-03 in the dev container)

| Command | Result |
|---|---|
| `uv run pytest -q` with DATABASE_URL and S3_* set | `17 failed, 74 passed, 2 skipped, 57 errors in 6.61s`. All 74 failed/errored results are `RED until …` messages (72 stop at `racket.platform.db:upgrade_to_head`, the first seam every DB-backed test needs; 2 at `racket.platform.settings:ConfigurationError`) |
| `uv run pytest -q` with no services | `17 failed, 51 passed, 2 skipped, 64 errors`. The extra red results say `DATABASE_URL is not set … SQLite is not allowed (AQS/OPS-05)` or `S3_ENDPOINT_URL is not set` |
| `scripts/test-unit.sh` | `54 passed, 96 deselected in 1.78s` (budget: domain < 10 s, backend unit ≤ 60 s, NFR-073) |
| `HYPOTHESIS_PROFILE=ci uv run pytest tests/unit/dataset/test_manifest_check_properties.py` | `4 passed in 14.48s` |
| `uv run ruff check src tests` / `uv run ruff format --check src tests` | `All checks passed!` / `75 files already formatted` |
| `uv run mypy` (strict on `racket.dataset`, `scoring`, `analytics`, `coaching`, `sports`) / `uv run mypy tests --explicit-package-bases` | `Success: no issues found in 16 source files` / `… in 59 source files` |
| `scripts/ci/check_fixtures.sh` (SRE gate calling QA's CLI) | `OK … synthetic-60s v1, 2 files`, exit 0 |
| Test-code validation against a throwaway in-memory fake of the HTTP seams (scratchpad only, never committed; `-p fakeimpl`) | `51 passed, 3 failed` over the error-body, trace-header, BOLA, upload-resume, IT-00-01 and IT-00-14 suites and the dev-environment, BOLA, upload-resume and errors/tracing features. 2 failures need the ObjectStore/worker seams the fake lacks; 1 is caused by global state in the fake (it passes alone). This shows the red tests can go green and are not broken in themselves |
| Playwright specs in a scratch project with `@playwright/test@1`, `@axe-core/playwright@4`, `typescript@5` | `tsc --noEmit` strict exit 0; `playwright test --list` → `Total: 7 tests in 3 files` |

## Summary by suite

| Suite / ID | File(s) | State | Turns green with |
|---|---|---|---|
| ManifestCheck unit (TDD plan §5) | `backend/tests/unit/dataset/test_manifest_check.py`, `…_properties.py` | 30 green | done (ST-011) |
| ManifestCheck on disk + CLI | `backend/tests/integration/dataset/test_manifest_check_cli.py` | 7 green | done (ST-011) |
| Committed sets intact; clip is 60 s 1080p60 H.264+AAC | `backend/tests/integration/dataset/test_committed_fixture_sets.py` | 4 green | done (ST-011) |
| Architecture: domain code framework-free | `backend/tests/unit/test_architecture.py` | 4 green (scans `domain.py`/`domain/`, `sports/`, `dataset/manifest.py` as they appear) | guards ST-006+ |
| Harness self-tests (DB rollback, BOLA inventory, log scanner, formatters, scenario report) | `backend/tests/integration/harness/`, `backend/tests/tools/` | 23 green | done (ST-004) |
| Feature: gold_set_integrity | `tests/features/gold_set_integrity.feature` | 2 green | done (ST-011) |
| Feature: dev_environment | `tests/features/dev_environment.feature` | 2 red | ST-005 (Settings, ST-001 env) |
| Feature: errors_and_tracing | `tests/features/errors_and_tracing.feature` | 3 red | ST-005 (+ ST-007 for the probe trace) |
| Feature: object_level_authorisation | `tests/features/object_level_authorisation.feature` | 5 red | ST-006 |
| Feature: upload_resume_core | `tests/features/upload_resume_core.feature` | 3 red | ST-008 |
| Feature: job_resilience | `tests/features/job_resilience.feature` | 2 red | ST-007 + ST-009 |
| Feature: walking_skeleton (API level) | `tests/features/walking_skeleton.feature` | 2 red | ST-008 + ST-009 (UI level: E2E-00-01) |
| IT-00-01 matches API | `backend/tests/integration/test_it_00_01_matches_api.py` | 4 red | ST-006 |
| IT-00-02 BOLA matrix (regression) | `backend/tests/regression/test_bola_matrix.py` | 8 red | ST-006 (+ ST-008 for upload routes) |
| IT-00-03 queue | `backend/tests/integration/test_it_00_03_queue.py` | 4 red | ST-007 |
| IT-00-04 worker crash (regression) | `backend/tests/regression/test_worker_crash.py` | 3 red | ST-007 + ST-009 |
| IT-00-05 fail closed (regression) | `backend/tests/regression/test_fail_closed.py` | 3 red | ST-007 + ST-009 |
| IT-00-06 tus upload, sha256 equal | `backend/tests/integration/test_it_00_06_tus_upload.py` | 1 red | ST-008 |
| IT-00-07 upload resume, 409 (regression) | `backend/tests/regression/test_upload_resume.py` | 9 red | ST-008 |
| IT-00-08 probe only after final byte | `backend/tests/integration/test_it_00_08_probe_after_final_byte.py` | 1 red | ST-008 + ST-007 |
| IT-00-09 probe stage facts | `backend/tests/integration/test_it_00_09_probe_stage.py` | 1 red | ST-009 |
| IT-00-10 worker sandbox | `backend/tests/integration/test_it_00_10_worker_sandbox.py` | 2 **skipped** locally: no Docker daemon in the dev container. Fails (does not skip) when `CI=true` | ST-009 + ST-001 (Compose) |
| IT-00-11 one trace API → queue → worker | `backend/tests/integration/test_it_00_11_trace_propagation.py` | 1 red | ST-005 + ST-007 |
| IT-00-12 trace header (regression) | `backend/tests/regression/test_trace_header.py` | 10 red | ST-005 |
| IT-00-13 error bodies (regression) | `backend/tests/regression/test_error_bodies.py` | 6 red | ST-005 (+ ST-006 for the match service) |
| IT-00-14 security headers (JSON/error) | `backend/tests/integration/test_it_00_14_security_headers.py` | 4 red | ST-005 (HTML part: `web/e2e/security-headers.spec.ts`, ST-010) |
| IT-00-15 log scan | `backend/tests/integration/test_it_00_15_log_scan.py` | 2 red | ST-005 (+ ST-007/ST-009 for the worker part of the flow) |
| IT-00-16 object store parity | `backend/tests/integration/test_it_00_16_object_store_parity.py` | **4 green** against SeaweedFS 3.97 (`scripts/dev-objectstore.sh`) | done locally; Compose run in CI pending (ST-001/ST-002) |
| E2E-00-01 walking skeleton + axe on every page | `web/e2e/walking-skeleton.spec.ts` (2 tests) | red: no web app or Playwright config yet | ST-010 (+ ST-008, ST-009) |
| E2E BOLA (demo step 6) | `web/e2e/object-level-authorisation.spec.ts` | red | ST-010 + ST-006 |
| E2E security headers and service-worker cache (IT-00-14 HTML part) | `web/e2e/security-headers.spec.ts` (4 tests) | red | ST-010 |

## Needs verification

No Sprint 0 scenario depends on a pickleball rule, so the scenario report's `## Needs verification` section is `None.` The mapping `@needs-verification` → marker `needs_verification` works and is unit-tested (`backend/tests/tools/test_scenario_report.py`).

## Hand-offs and contracts for other lanes

- **senior-backend-engineer:** confirm or amend the seams in ADR 0012 at the start of ST-005/ST-006/ST-007. QA makes the edits in `backend/tests/support/contract.py`. Implementers do not edit the tests. `RACKET_FAULT_INJECTION` must be honoured only when `APP_ENV=test` (regression test included).
- **senior-frontend-engineer:** `web/e2e/` needs a `playwright.config.ts` (baseURL, Chromium and WebKit projects, ST-002) and the dev dependencies `@playwright/test` and `@axe-core/playwright`. Selectors are role/label based (`helpers/journey.ts`): buttons "Ivy"/"Carlos", heading "Matches", link "New match", labels "Title", "Format" (option "Doubles"), "Match video", button "Create match", a `progressbar` named "Upload…", text "No matches yet", "Video received", "Duration 1:00 · 60 fps · 1920×1080", and the "not found" page in `main`.
- **senior-backend-engineer and sre-devops-engineer:** the images expect `racket.platform.app:app` (blockers.md, SRE row) and the tests use `racket.platform.app:create_app`. Both can coexist. QA recommends `uvicorn --factory racket.platform.app:create_app`, so that importing the module never reads the environment; the dev-environment scenario passes either way.
- **sre-devops-engineer:** `scripts/test-unit.sh` and `scripts/ci/check_fixtures.sh` already match the QA markers and CLI. In CI, set `CI=true` so IT-00-10 fails instead of skipping, `HYPOTHESIS_PROFILE=ci`, and protect `fixtures/clips/` and `backend/tests/` with the immutability job.
- **business-analyst:** traceability rows: feature file → `backend/tests/features/test_<feature>.py`; IT-00-nn → the files above.

## Per-test state (generated from `--junitxml` of the full run above)

**`backend/tests/features/test_dev_environment.py`**: 2 red

| Test | State | Reason |
|---|---|---|
| `test_a_required_setting_is_missing` | red | RED until ST-005: seam `racket.platform.settings:ConfigurationError` |
| `test_development_identities_cannot_run_in_production` | red | RED until ST-005: seam `racket.platform.settings:ConfigurationError` |

**`backend/tests/features/test_errors_and_tracing.py`**: 3 red

| Test | State | Reason |
|---|---|---|
| `test_an_unexpected_server_error` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_one_trace_covers_upload_to_probe` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_a_malformed_trace_header_is_ignored_safely` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |

**`backend/tests/features/test_gold_set_integrity.py`**: 2 green

| Test | State | Reason |
|---|---|---|
| `test_a_fixture_file_changes_without_a_new_version` | green |  |
| `test_an_unlisted_file_is_added` | green |  |

**`backend/tests/features/test_job_resilience.py`**: 2 red

| Test | State | Reason |
|---|---|---|
| `test_worker_stops_in_the_middle_of_probing` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_probe_stage_fails_after_writing_part_of_its_result` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |

**`backend/tests/features/test_object_level_authorisation.py`**: 5 red

| Test | State | Reason |
|---|---|---|
| `test_carlos_tries_to_use_ivys_match[open]` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_carlos_tries_to_use_ivys_match[upload to]` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_carlos_tries_to_use_ivys_match[see facts of]` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_my_match_list_shows_only_my_matches` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_a_new_route_without_bola_coverage` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |

**`backend/tests/features/test_upload_resume_core.py`** (IT-00-07): 3 red

| Test | State | Reason |
|---|---|---|
| `test_resume_from_the_servers_offset` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_chunk_sent_from_the_wrong_offset` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_stored_names_never_come_from_the_users_file_name` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |

**`backend/tests/features/test_walking_skeleton.py`**: 2 red

| Test | State | Reason |
|---|---|---|
| `test_upload_the_fixture_clip_and_see_its_facts` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_no_probing_before_the_upload_is_complete` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |

**`backend/tests/integration/dataset/test_committed_fixture_sets.py`**: 4 green

| Test | State | Reason |
|---|---|---|
| `test_there_is_at_least_one_set` | green |  |
| `test_committed_set_matches_its_manifest[clips/synthetic-60s]` | green |  |
| `test_committed_clip_is_under_the_size_limit` | green |  |
| `test_synthetic_clip_has_the_required_properties` | green |  |

**`backend/tests/integration/dataset/test_manifest_check_cli.py`**: 7 green

| Test | State | Reason |
|---|---|---|
| `test_hash_set_excludes_the_manifest_and_uses_posix_relative_paths` | green |  |
| `test_cli_fails_and_names_changed_file` | green |  |
| `test_cli_fails_and_names_unlisted_file` | green |  |
| `test_cli_rejects_malformed_manifest_with_exit_code_2` | green |  |
| `test_cli_rejects_symlinks_in_a_set` | green |  |
| `test_cli_version_rule_against_base_manifest` | green |  |
| `test_cli_passes_for_intact_set` | green |  |

**`backend/tests/integration/harness/test_db_fixture.py`**: 3 green

| Test | State | Reason |
|---|---|---|
| `test_connection_fixture_rolls_back_ddl_and_rows` | green |  |
| `test_session_commit_inside_the_fixture_is_still_rolled_back` | green |  |
| `test_uncommitted_work_is_invisible_to_other_connections` | green |  |

**`backend/tests/integration/test_it_00_01_matches_api.py`** (IT-00-01): 4 red

| Test | State | Reason |
|---|---|---|
| `test_create_get_and_list` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_response_is_an_allowlist_without_owner_internals` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_unknown_request_field_is_rejected` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_unauthenticated_create_is_refused` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |

**`backend/tests/integration/test_it_00_03_queue.py`** (IT-00-03): 4 red

| Test | State | Reason |
|---|---|---|
| `test_enqueue_claim_complete` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_same_key_enqueued_twice_is_one_job` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_running_job_is_not_claimed_again` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_concurrent_claims_on_separate_connections_skip_locked` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |

**`backend/tests/integration/test_it_00_06_tus_upload.py`** (IT-00-06): 1 red

| Test | State | Reason |
|---|---|---|
| `test_three_chunk_upload_stores_identical_bytes` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |

**`backend/tests/integration/test_it_00_08_probe_after_final_byte.py`** (IT-00-08): 1 red

| Test | State | Reason |
|---|---|---|
| `test_probe_enqueued_only_after_last_byte` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |

**`backend/tests/integration/test_it_00_09_probe_stage.py`** (IT-00-09): 1 red

| Test | State | Reason |
|---|---|---|
| `test_probe_records_the_fixture_facts` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |

**`backend/tests/integration/test_it_00_10_worker_sandbox.py`** (IT-00-10): 2 skip

| Test | State | Reason |
|---|---|---|
| `test_public_internet_is_blocked_from_the_worker` | skip | needs the Compose stack (docker compose -f infra/compose.yaml up -d) |
| `test_object_store_is_reachable_from_the_worker` | skip | needs the Compose stack (docker compose -f infra/compose.yaml up -d) |

**`backend/tests/integration/test_it_00_11_trace_propagation.py`** (IT-00-11): 1 red

| Test | State | Reason |
|---|---|---|
| `test_one_trace_from_final_patch_to_probe` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |

**`backend/tests/integration/test_it_00_14_security_headers.py`** (IT-00-14): 4 red

| Test | State | Reason |
|---|---|---|
| `test_health_json_has_baseline_headers` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_error_response_has_baseline_headers` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_authenticated_json_is_no_store` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_server_banner_does_not_reveal_versions` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |

**`backend/tests/integration/test_it_00_15_log_scan.py`** (IT-00-15): 2 red

| Test | State | Reason |
|---|---|---|
| `test_no_personal_data_or_signed_urls_in_logs` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_request_log_lines_are_json_with_correlation_fields` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |

**`backend/tests/integration/test_it_00_16_object_store_parity.py`** (IT-00-16): 4 green

| Test | State | Reason |
|---|---|---|
| `test_multipart_upload_round_trips` | green |  |
| `test_presigned_get_works_then_expires` | green |  |
| `test_tampered_presigned_url_is_refused` | green |  |
| `test_delete_removes_the_object` | green |  |

**`backend/tests/regression/test_bola_matrix.py`** (IT-00-02): 8 red

| Test | State | Reason |
|---|---|---|
| `test_other_user_gets_the_same_404_as_for_a_missing_resource[GET /matches/{match_id}]` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_other_user_gets_the_same_404_as_for_a_missing_resource[GET /matches/{match_id}/media]` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_other_user_gets_the_same_404_as_for_a_missing_resource[POST /matches/{match_id}/uploads]` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_other_user_gets_the_same_404_as_for_a_missing_resource[HEAD /uploads/{upload_id}]` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_other_user_gets_the_same_404_as_for_a_missing_resource[PATCH /uploads/{upload_id}]` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_anonymous_caller_is_refused_on_every_id_route` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_endpoint_inventory_has_no_route_missing_from_the_matrix` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_match_ids_are_random_uuid4` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |

**`backend/tests/regression/test_error_bodies.py`** (IT-00-13): 6 red

| Test | State | Reason |
|---|---|---|
| `test_unhandled_exception_returns_generic_500` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_failing_dependency_returns_generic_500` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_unknown_route_returns_generic_404` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_wrong_method_returns_generic_405` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_validation_error_is_generic_and_does_not_echo_input` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_support_refs_are_unique_per_error` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |

**`backend/tests/regression/test_fail_closed.py`** (IT-00-05): 3 red

| Test | State | Reason |
|---|---|---|
| `test_partial_write_is_rolled_back_and_job_failed` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_failure_reason_holds_no_internals` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_fault_injection_is_ignored_outside_test_env` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |

**`backend/tests/regression/test_trace_header.py`** (IT-00-12): 10 red

| Test | State | Reason |
|---|---|---|
| `test_malformed_traceparent_still_succeeds_under_a_new_trace[garbage]` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_malformed_traceparent_still_succeeds_under_a_new_trace[00-xyz-bad-01]` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_malformed_traceparent_still_succeeds_under_a_new_trace[00-4bf92f3577b34da6a3ce929d0e0e4736-00f0]` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_malformed_traceparent_still_succeeds_under_a_new_trace[00-00000000000000000000000000000000-00f0]` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_malformed_traceparent_still_succeeds_under_a_new_trace[00-4bf92f3577b34da6a3ce929d0e0e4736-0000]` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_malformed_traceparent_still_succeeds_under_a_new_trace[ff-4bf92f3577b34da6a3ce929d0e0e4736-00f0]` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_malformed_traceparent_still_succeeds_under_a_new_trace[00-4BF92F3577B34DA6A3CE929D0E0E4736-00F0]` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_malformed_traceparent_still_succeeds_under_a_new_trace[00-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa]` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_valid_traceparent_is_continued` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_tracestate_garbage_is_ignored` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |

**`backend/tests/regression/test_upload_resume.py`** (IT-00-07): 9 red

| Test | State | Reason |
|---|---|---|
| `test_head_reports_offset_and_length` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_patch_at_wrong_offset_is_409_and_upload_unchanged[0]` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_patch_at_wrong_offset_is_409_and_upload_unchanged[30]` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_patch_at_wrong_offset_is_409_and_upload_unchanged[41]` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_patch_at_wrong_offset_is_409_and_upload_unchanged[100]` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_resume_from_reported_offset_completes` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_patch_beyond_declared_length_is_rejected` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_patch_without_tus_resumable_is_412` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_patch_with_wrong_content_type_is_415` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |

**`backend/tests/regression/test_worker_crash.py`** (IT-00-04): 3 red

| Test | State | Reason |
|---|---|---|
| `test_sigterm_requeues_within_10s_and_rerun_leaves_one_row` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_sigkill_mid_stage_does_not_lose_the_job` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |
| `test_two_workers_never_run_the_same_job_twice` | red | RED until ST-005: seam `racket.platform.db:upgrade_to_head` |

**`backend/tests/tools/test_bola_inventory.py`**: 5 green

| Test | State | Reason |
|---|---|---|
| `test_route_with_id_and_no_matrix_entry_is_reported_by_name` | green |  |
| `test_routes_without_path_parameters_are_not_in_the_inventory` | green |  |
| `test_each_method_on_an_id_route_needs_its_own_entry` | green |  |
| `test_exempt_route_is_not_reported` | green |  |
| `test_matrix_covers_the_sprint_0_id_routes` | green |  |

**`backend/tests/tools/test_format.py`**: 7 green

| Test | State | Reason |
|---|---|---|
| `test_negative_duration_rejected` | green |  |
| `test_human_units[0-0:00]` | green |  |
| `test_human_units[59499-0:59]` | green |  |
| `test_human_units[60000-1:00]` | green |  |
| `test_human_units[3600000-1:00:00]` | green |  |
| `test_fixture_facts_render_as_in_the_sprint_goal` | green |  |
| `test_seconds_field_is_always_two_digits` | green |  |

**`backend/tests/tools/test_logscan.py`**: 4 green

| Test | State | Reason |
|---|---|---|
| `test_email_is_found` | green |  |
| `test_signed_url_is_found` | green |  |
| `test_nickname_is_found_as_a_whole_word_only` | green |  |
| `test_clean_structured_line_passes` | green |  |

**`backend/tests/tools/test_scenario_report.py`**: 4 green

| Test | State | Reason |
|---|---|---|
| `test_needs_verification_scenarios_are_flagged_with_inherited_tags` | green |  |
| `test_results_come_from_junit` | green |  |
| `test_render_puts_needs_verification_in_its_own_section` | green |  |
| `test_scenario_without_junit_result_is_reported_not_run` | green |  |

**`backend/tests/unit/dataset/test_manifest_check.py`**: 26 green

| Test | State | Reason |
|---|---|---|
| `test_changed_file_fails_and_names_the_file` | green |  |
| `test_unlisted_file_fails_and_names_the_file` | green |  |
| `test_file_listed_but_absent_fails_and_names_the_file` | green |  |
| `test_matching_set_passes` | green |  |
| `test_malformed_file_entry_is_rejected[sha256-not-a-hash]` | green |  |
| `test_malformed_file_entry_is_rejected[sha256-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA]` | green |  |
| `test_malformed_file_entry_is_rejected[path-../escape.mp4]` | green |  |
| `test_malformed_file_entry_is_rejected[path-/abs/clip.mp4]` | green |  |
| `test_malformed_file_entry_is_rejected[path-]` | green |  |
| `test_manifest_without_required_field_is_rejected[id]` | green |  |
| `test_manifest_without_required_field_is_rejected[version]` | green |  |
| `test_manifest_without_required_field_is_rejected[licence]` | green |  |
| `test_manifest_without_required_field_is_rejected[consent_status]` | green |  |
| `test_manifest_without_required_field_is_rejected[files]` | green |  |
| `test_version_must_be_a_positive_integer[0]` | green |  |
| `test_version_must_be_a_positive_integer[-1]` | green |  |
| `test_version_must_be_a_positive_integer[1]` | green |  |
| `test_version_must_be_a_positive_integer[1.5]` | green |  |
| `test_version_must_be_a_positive_integer[True]` | green |  |
| `test_duplicate_path_is_rejected` | green |  |
| `test_hash_changed_in_manifest_without_version_bump_fails_naming_file` | green |  |
| `test_file_added_or_removed_without_version_bump_fails` | green |  |
| `test_version_going_backwards_fails` | green |  |
| `test_hash_change_with_version_bump_passes` | green |  |
| `test_unchanged_manifest_passes_version_rule` | green |  |
| `test_problem_describes_itself_for_ci_output` | green |  |

**`backend/tests/unit/dataset/test_manifest_check_properties.py`**: 4 green

| Test | State | Reason |
|---|---|---|
| `test_a_set_always_matches_its_own_manifest` | green |  |
| `test_any_single_hash_change_is_detected_and_named` | green |  |
| `test_any_added_file_is_detected_and_named` | green |  |
| `test_any_change_to_the_file_set_without_a_bump_fails` | green |  |

**`backend/tests/unit/test_architecture.py`**: 4 green

| Test | State | Reason |
|---|---|---|
| `test_domain_module_imports_no_framework[dataset/manifest.py]` | green |  |
| `test_domain_module_imports_no_framework[sports/__init__.py]` | green |  |
| `test_domain_module_imports_no_framework[sports/pickleball/__init__.py]` | green |  |
| `test_scanner_detects_a_forbidden_import` | green |  |
