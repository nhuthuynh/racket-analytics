# Data classification map (NFR-063)

- **Status:** v1, ST-077 (Sprint 5). The classes and every row are **proposed by the senior-backend-engineer and decided by the security-privacy-engineer in review** (sprint-05 §3.7 ST-077); until that review the classes below are a proposal. The legal adequacy of every retention window is not decided here (P16, NFR-070; [ADR 0006](../decisions/0006-retention-and-deletion-defaults.md) is an interim default).
- **Date:** 2026-11-05. **Requirement:** NFR-063.1 (stored data types without a class: 0) and NFR-063.2 (classes without an encryption, retention or access rule: 0), [`non-functional-requirements.md`](../requirements/non-functional-requirements.md) NFR-063; [AQS/SEC-05] 14.1.1, 14.1.2.
- **Checked by:** IT-05-05, [`backend/tests/integration/test_it_05_data_classification.py`](../../backend/tests/integration/test_it_05_data_classification.py) with the scenarios in [`tests/features/data_classification.feature`](../../tests/features/data_classification.feature). It walks the SQLAlchemy metadata and the live migrated schema, the key prefixes a demo upload writes to the media bucket and every file of a set taken by the ST-076a backup service ([`scripts/ops/backup.py`](../../scripts/ops/backup.py)), and fails on any item without a row in §3, on a row whose class or rule code is not defined in §1-§2, on a column or backup row naming nothing the walk found, and when it finds zero backup artefacts. It also reads an unfinished upload as its owner (`GET /matches/{id}` and the tus `HEAD`) and fails on any `upload_sessions` column marked `A-SERVER` whose live value the response carries. The parser and checks are [`backend/tests/support/classification.py`](../../backend/tests/support/classification.py).
- **How to change it:** a PR that adds a table, column, key prefix or backup file adds its row here in the same PR, or IT-05-05 fails. Tables in §1-§3 are machine-read: keep their header rows exactly.

## 1. Classes

Each class sets the minimum rule of each kind; a row in §3 names the concrete store rule that meets it.

| Class | Holds | Encryption | Retention | Access |
|---|---|---|---|---|
| **High** | Video and anything cut from it (originals, staging chunks; later clips, thumbnails, pose and frame artefacts, NFR-063); email addresses; credential material (token hashes); every backup file that holds a copy of the database | `E-HIGH` | `R-HIGH` | `A-HIGH` |
| **Medium** | Names and free text a player typed (username, display name, nicknames, match titles, "not for me" reasons, file names), pseudonymous keys (`email_key`, rate-limit keys that hold an `email_key` or an IP), labels, consent and preference choices, age confirmation | `E-MEDIUM` | `R-MEDIUM` | `A-MEDIUM` |
| **Low** | Score sheets, rallies, corrections, aggregated metrics and plans built from them, media technical facts | `E-LOW` | `R-LOW` | `A-LOW` |
| **Internal** | Generated ids, versions, timestamps, states, queue and lease fields, schema version, backup metadata; nothing a person typed or recorded | `E-INTERNAL` | `R-INTERNAL` | `A-INTERNAL` |

## 2. Rules

| Code | Kind | Rule |
|---|---|---|
| `E-HIGH` | encryption | Encrypted in transit on every hop and at rest in every store; any copy outside the live stores is encrypted by the app before it touches disk (age, [ADR 0058](../decisions/0058-encrypted-nightly-dump-and-object-mirror-restore-then-purge-five-day-backup-retention-rollback-by-downgrade-then-redeploy.md) rule 3; T5-BK-1). |
| `E-MEDIUM` | encryption | As `E-HIGH`. |
| `E-LOW` | encryption | Encrypted at rest with the store that holds it; in transit inside the deployment network. |
| `E-INTERNAL` | encryption | As `E-LOW`; may sit in plaintext next to an encrypted artefact when it holds no personal data (`backup.json`, T5-BK-1). |
| `E-PG` | encryption | Postgres data volume. At rest: the host or provider volume encryption of the deployment (deployment item, see §4 open item DC-1); in a backup set only inside `E-AGE`. |
| `E-S3` | encryption | Media bucket. At rest: the store's server-side encryption in the deployment (deployment item, §4 DC-1); objects are served only through short-lived signed URLs; in a backup only inside `E-AGE` (ST-076a-part2). |
| `E-AGE` | encryption | Streamed through `age` to an X25519 recipient; no plaintext file is written (ST-076a, `verify_encrypted` in `scripts/ops/backup.py`); the private identity is held off the backup host. |
| `E-META` | encryption | Plaintext JSON on the backup volume; holds times, sizes, SHA-256 digests, versions and the public recipient only, no personal data (T5-BK-1). |
| `R-HIGH` | retention | Kept only as long as the feature needs it; never past the owner's deletion + 7 days in live stores (NFR-066) or 5 days in a backup ([ADR 0058](../decisions/0058-encrypted-nightly-dump-and-object-mirror-restore-then-purge-five-day-backup-retention-rollback-by-downgrade-then-redeploy.md) rule 2). |
| `R-MEDIUM` | retention | As `R-HIGH`. |
| `R-LOW` | retention | While the match or account it describes exists; purged with it (NFR-066). |
| `R-INTERNAL` | retention | With the row or set it belongs to. |
| `R-ACCOUNT` | retention | While the account exists; `DELETE /me` purges it within 7 days (NFR-066; [ADR 0042](../decisions/0042-deletion-tombstones-now-purge-objects-before-rows.md)). |
| `R-MATCH` | retention | While the match exists; a deleted match is hidden in ≤ 1 min and its rows and objects are purged in ≤ 7 days ([ADR 0006](../decisions/0006-retention-and-deletion-defaults.md), [ADR 0042](../decisions/0042-deletion-tombstones-now-purge-objects-before-rows.md)); and with its account. |
| `R-ORIGINAL` | retention | `R-MATCH`, and earlier by the review-video retention rule ([ADR 0006](../decisions/0006-retention-and-deletion-defaults.md) option 3; the player's 30/90/365-day setting, ST-069, behind `FEATURE_RETENTION_SETTING`). |
| `R-UPLOAD` | retention | Staged bytes are freed when the upload completes or expires (24 h sliding, 72 h cap; ADR 0006, ST-038); the session row goes with its match (`R-MATCH`). |
| `R-TOKEN` | retention | Until used, refused or expired (sign-in link, pending sign-in, session), or until the mail job has sent it (sign-in request); deleted with the account ([ADR 0025](../decisions/0025-magic-link-sign-in-design.md), [ADR 0032](../decisions/0032-account-identity-is-the-address-not-the-email-key.md)). |
| `R-RATE` | retention | Pruned when the same key is hit again after its window (`platform/ratelimit.py`); rows keyed by an account id go with the account. Rows keyed by an `email_key` or an IP can outlive their window: open finding SEC-S3-TM-04 (T-DL-7), §4 DC-2. |
| `R-BACKUP` | retention | Every copy of a set is gone less than `BACKUP_KEEP_DAYS` (≤ 5) days after its `taken_at` while the schedule runs ([ADR 0058](../decisions/0058-encrypted-nightly-dump-and-object-mirror-restore-then-purge-five-day-backup-retention-rollback-by-downgrade-then-redeploy.md) rule 2). |
| `R-SCHEMA` | retention | For the life of the database. |
| `A-HIGH` | access | The owner through the API with object-level authorisation (another user gets 404, the BOLA matrix); service roles by least privilege; the backup login reads it (`pg_read_all_data`, ADR 0058); never in a log line or a metric label (NFR-069). |
| `A-MEDIUM` | access | As `A-HIGH`. |
| `A-LOW` | access | The owner through the API with object-level authorisation; service roles by least privilege. |
| `A-INTERNAL` | access | Service roles; shown to the owner only where an API response needs it. |
| `A-OWNER` | access | Returned only to its owner, through routes with object-level authorisation (`backend/tests/regression/bola.py` matrix); the media worker role only where its grants allow (ST-042); read by the backup login. |
| `A-SERVER` | access | Server side only: no API response returns its value or a state read from it; app role and the backup login. A column an `*Out` schema, a JSON body or a tus header carries is `A-OWNER` (or `A-LABEL`), never `A-SERVER` (SPE-ST077-01; IT-05-05 checks `upload_sessions` on a live unfinished upload). |
| `A-LABEL` | access | The labeller role (`account_roles`) through the dataset routes; the owner's training consent gates the label set (FR-150, FR-151); the media worker role gets nothing (ST-042). |
| `A-OPS` | access | An operator who holds the age identity, for a restore or the restore drill only; the app has no route to it ([ADR 0058](../decisions/0058-encrypted-nightly-dump-and-object-mirror-restore-then-purge-five-day-backup-retention-rollback-by-downgrade-then-redeploy.md) rule 4). |

## 3. Inventory

One row per stored type. `column` names are `<table>.<column>` from the SQLAlchemy metadata and the migrated schema; `prefix` names are the first segment of an object key in the media bucket ([`video_ingest/domain/uploads.py`](../../backend/src/racket/video_ingest/domain/uploads.py) `ObjectKeyPolicy`); `backup` names are the files of one set under `BACKUP_DIR/<taken_at>/`.

### 3.1 Object-store key prefixes (media bucket)

| Kind | Name | Class | Encryption | Retention | Access |
|---|---|---|---|---|---|
| prefix | `originals/` | High | `E-S3` | `R-ORIGINAL` | `A-OWNER` |
| prefix | `staging/` | High | `E-S3` | `R-UPLOAD` | `A-SERVER` |

### 3.2 Backup artefacts (one set of the ST-076a service)

`objects.tar.age`, the media mirror that ST-076a-part2 (planned) adds, is High, `E-AGE`, `R-BACKUP`, `A-OPS` (proposed); its row is added by that PR, because IT-05-05 also fails on a backup row naming no file the service writes. `backup.json.tmp` exists only inside a failed, incomplete set, which the next prune deletes (ADR 0058 rule 2); it has no row.

| Kind | Name | Class | Encryption | Retention | Access |
|---|---|---|---|---|---|
| backup | `db.dump.age` | High | `E-AGE` | `R-BACKUP` | `A-OPS` |
| backup | `globals.sql.age` | Internal | `E-AGE` | `R-BACKUP` | `A-OPS` |
| backup | `backup.json` | Internal | `E-META` | `R-BACKUP` | `A-OPS` |

### 3.3 Database columns

| Kind | Name | Class | Encryption | Retention | Access |
|---|---|---|---|---|---|
| column | `account_roles.account_id` | Internal | `E-PG` | `R-ACCOUNT` | `A-SERVER` |
| column | `account_roles.role` | Internal | `E-PG` | `R-ACCOUNT` | `A-SERVER` |
| column | `account_roles.granted_at` | Internal | `E-PG` | `R-ACCOUNT` | `A-SERVER` |
| column | `accounts.id` | Internal | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `accounts.username` | Medium | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `accounts.display_name` | Medium | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `accounts.created_at` | Internal | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `accounts.email_key` | Medium | `E-PG` | `R-ACCOUNT` | `A-SERVER` |
| column | `accounts.email` | High | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `accounts.deleted_at` | Internal | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `accounts.age_confirmed_at` | Medium | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `alembic_version.version_num` | Internal | `E-PG` | `R-SCHEMA` | `A-SERVER` |
| column | `jobs.id` | Internal | `E-PG` | `R-MATCH` | `A-SERVER` |
| column | `jobs.match_id` | Internal | `E-PG` | `R-MATCH` | `A-SERVER` |
| column | `jobs.pipeline_version` | Internal | `E-PG` | `R-MATCH` | `A-SERVER` |
| column | `jobs.stage` | Internal | `E-PG` | `R-MATCH` | `A-SERVER` |
| column | `jobs.status` | Internal | `E-PG` | `R-MATCH` | `A-SERVER` |
| column | `jobs.attempts` | Internal | `E-PG` | `R-MATCH` | `A-SERVER` |
| column | `jobs.failure_reason` | Internal | `E-PG` | `R-MATCH` | `A-SERVER` |
| column | `jobs.worker_id` | Internal | `E-PG` | `R-MATCH` | `A-SERVER` |
| column | `jobs.lease_expires_at` | Internal | `E-PG` | `R-MATCH` | `A-SERVER` |
| column | `jobs.trace_context` | Internal | `E-PG` | `R-MATCH` | `A-SERVER` |
| column | `jobs.created_at` | Internal | `E-PG` | `R-MATCH` | `A-SERVER` |
| column | `jobs.updated_at` | Internal | `E-PG` | `R-MATCH` | `A-SERVER` |
| column | `label_consents.match_id` | Internal | `E-PG` | `R-MATCH` | `A-LABEL` |
| column | `label_consents.reference` | Medium | `E-PG` | `R-MATCH` | `A-LABEL` |
| column | `label_consents.recorded_by` | Internal | `E-PG` | `R-MATCH` | `A-LABEL` |
| column | `label_consents.recorded_at` | Internal | `E-PG` | `R-MATCH` | `A-LABEL` |
| column | `label_sessions.match_id` | Internal | `E-PG` | `R-MATCH` | `A-LABEL` |
| column | `label_sessions.owner_id` | Internal | `E-PG` | `R-MATCH` | `A-LABEL` |
| column | `label_sessions.version` | Internal | `E-PG` | `R-MATCH` | `A-LABEL` |
| column | `label_sessions.rallies` | Medium | `E-PG` | `R-MATCH` | `A-LABEL` |
| column | `label_sessions.events` | Medium | `E-PG` | `R-MATCH` | `A-LABEL` |
| column | `label_sessions.updated_at` | Internal | `E-PG` | `R-MATCH` | `A-LABEL` |
| column | `match_corrections.id` | Internal | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `match_corrections.match_id` | Internal | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `match_corrections.version` | Internal | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `match_corrections.kind` | Low | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `match_corrections.actor_id` | Internal | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `match_corrections.at` | Internal | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `match_corrections.rally_id` | Internal | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `match_corrections.game_number` | Low | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `match_corrections.field` | Low | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `match_corrections.old_value` | Low | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `match_corrections.new_value` | Low | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `match_corrections.undoes` | Internal | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `match_games.match_id` | Internal | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `match_games.number` | Low | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `match_games.first_serving_side` | Low | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `match_games.ends_switched` | Low | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `match_games.created_version` | Internal | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `match_participants.match_id` | Internal | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `match_participants.slot` | Low | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `match_participants.nickname` | Medium | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `match_participants.is_me` | Low | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `match_rallies.id` | Internal | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `match_rallies.match_id` | Internal | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `match_rallies.game_number` | Low | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `match_rallies.seq` | Low | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `match_rallies.start_ms` | Low | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `match_rallies.end_ms` | Low | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `match_rallies.ending` | Low | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `match_rallies.winning_side` | Low | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `match_rallies.responsible_player` | Low | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `match_rallies.fault_kind` | Low | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `match_rallies.withdrawn` | Low | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `match_rallies.created_version` | Internal | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `matches.id` | Internal | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `matches.owner_id` | Internal | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `matches.title` | Medium | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `matches.format` | Internal | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `matches.status` | Internal | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `matches.media_asset_id` | Internal | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `matches.created_at` | Internal | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `matches.updated_at` | Internal | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `matches.scoring_system` | Internal | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `matches.rules_version` | Internal | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `matches.played_on` | Low | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `matches.rejection_code` | Internal | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `matches.rejected_at` | Internal | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `matches.best_of` | Internal | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `matches.version` | Internal | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `matches.deleted_at` | Internal | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `media_assets.id` | Internal | `E-PG` | `R-MATCH` | `A-SERVER` |
| column | `media_assets.owner_id` | Internal | `E-PG` | `R-MATCH` | `A-SERVER` |
| column | `media_assets.match_id` | Internal | `E-PG` | `R-MATCH` | `A-SERVER` |
| column | `media_assets.object_key` | Internal | `E-PG` | `R-MATCH` | `A-SERVER` |
| column | `media_assets.size_bytes` | Internal | `E-PG` | `R-MATCH` | `A-SERVER` |
| column | `media_assets.probe_status` | Internal | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `media_assets.created_at` | Internal | `E-PG` | `R-MATCH` | `A-SERVER` |
| column | `media_assets.updated_at` | Internal | `E-PG` | `R-MATCH` | `A-SERVER` |
| column | `media_facts.media_asset_id` | Internal | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `media_facts.match_id` | Internal | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `media_facts.container` | Low | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `media_facts.video_codec` | Low | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `media_facts.duration_ms` | Low | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `media_facts.fps` | Low | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `media_facts.vfr` | Low | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `media_facts.width` | Low | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `media_facts.height` | Low | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `media_facts.has_audio` | Low | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `media_facts.created_at` | Internal | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `metric_snapshots.match_id` | Internal | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `metric_snapshots.metric_def_version` | Internal | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `metric_snapshots.rules_version` | Internal | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `metric_snapshots.owner_id` | Internal | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `metric_snapshots.sheet_version` | Internal | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `metric_snapshots.stats` | Low | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `metric_snapshots.computed_at` | Internal | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `pending_sign_ins.token_sha256` | High | `E-PG` | `R-TOKEN` | `A-SERVER` |
| column | `pending_sign_ins.email` | High | `E-PG` | `R-TOKEN` | `A-SERVER` |
| column | `pending_sign_ins.email_key` | Medium | `E-PG` | `R-TOKEN` | `A-SERVER` |
| column | `pending_sign_ins.created_at` | Internal | `E-PG` | `R-TOKEN` | `A-SERVER` |
| column | `pending_sign_ins.expires_at` | Internal | `E-PG` | `R-TOKEN` | `A-SERVER` |
| column | `plan_assignments.id` | Internal | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `plan_assignments.session_id` | Internal | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `plan_assignments.owner_id` | Internal | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `plan_assignments.position` | Low | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `plan_assignments.drill_ref` | Low | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `plan_assignments.minutes` | Low | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `plan_assignments.weakness_id` | Low | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `plan_assignments.metric_id` | Low | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `plan_assignments.metric_version` | Low | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `plan_assignments.value` | Low | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `plan_assignments.n` | Low | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `plan_assignments.k` | Low | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `plan_assignments.low_sample` | Low | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `plan_assignments.reason_not_for_me` | Medium | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `plan_citation_rallies.assignment_id` | Internal | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `plan_citation_rallies.match_id` | Internal | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `plan_citation_rallies.rally_id` | Internal | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `plan_citation_rallies.position` | Low | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `plan_done_ops.account_id` | Internal | `E-PG` | `R-ACCOUNT` | `A-SERVER` |
| column | `plan_done_ops.op_id` | Internal | `E-PG` | `R-ACCOUNT` | `A-SERVER` |
| column | `plan_done_ops.session_id` | Internal | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `plan_done_ops.plan_version` | Internal | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `plan_done_ops.created_at` | Internal | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `plan_sessions.id` | Internal | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `plan_sessions.plan_id` | Internal | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `plan_sessions.owner_id` | Internal | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `plan_sessions.week` | Low | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `plan_sessions.session_index` | Low | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `plan_sessions.minutes_budget` | Low | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `plan_sessions.done_at` | Internal | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `plan_source_matches.plan_id` | Internal | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `plan_source_matches.match_id` | Internal | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `rate_limit_events.id` | Internal | `E-PG` | `R-RATE` | `A-SERVER` |
| column | `rate_limit_events.key` | Medium | `E-PG` | `R-RATE` | `A-SERVER` |
| column | `rate_limit_events.at` | Internal | `E-PG` | `R-RATE` | `A-SERVER` |
| column | `retention_settings.account_id` | Internal | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `retention_settings.review_video_days` | Medium | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `retention_settings.changed_at` | Internal | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `sessions.token_sha256` | High | `E-PG` | `R-TOKEN` | `A-SERVER` |
| column | `sessions.account_id` | Internal | `E-PG` | `R-TOKEN` | `A-SERVER` |
| column | `sessions.created_at` | Internal | `E-PG` | `R-TOKEN` | `A-SERVER` |
| column | `sessions.expires_at` | Internal | `E-PG` | `R-TOKEN` | `A-SERVER` |
| column | `sessions.last_seen_at` | Internal | `E-PG` | `R-TOKEN` | `A-SERVER` |
| column | `sign_in_links.token_sha256` | High | `E-PG` | `R-TOKEN` | `A-SERVER` |
| column | `sign_in_links.email_key` | Medium | `E-PG` | `R-TOKEN` | `A-SERVER` |
| column | `sign_in_links.created_at` | Internal | `E-PG` | `R-TOKEN` | `A-SERVER` |
| column | `sign_in_links.expires_at` | Internal | `E-PG` | `R-TOKEN` | `A-SERVER` |
| column | `sign_in_links.used_at` | Internal | `E-PG` | `R-TOKEN` | `A-SERVER` |
| column | `sign_in_links.email` | High | `E-PG` | `R-TOKEN` | `A-SERVER` |
| column | `sign_in_requests.id` | Internal | `E-PG` | `R-TOKEN` | `A-SERVER` |
| column | `sign_in_requests.email` | High | `E-PG` | `R-TOKEN` | `A-SERVER` |
| column | `sign_in_requests.email_key` | Medium | `E-PG` | `R-TOKEN` | `A-SERVER` |
| column | `sign_in_requests.created_at` | Internal | `E-PG` | `R-TOKEN` | `A-SERVER` |
| column | `training_consent_events.id` | Internal | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `training_consent_events.account_id` | Internal | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `training_consent_events.opt_in` | Medium | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `training_consent_events.changed_at` | Internal | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `training_consents.account_id` | Internal | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `training_consents.opt_in` | Medium | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `training_consents.changed_at` | Internal | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `training_plans.id` | Internal | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `training_plans.owner_id` | Internal | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `training_plans.version` | Internal | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `training_plans.library_version` | Low | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `training_plans.preferences` | Medium | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `training_plans.weaknesses` | Low | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `training_plans.unfitted` | Low | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `training_plans.excluded_drills` | Low | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `training_plans.limited_data` | Low | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `training_plans.stale` | Low | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `training_plans.content_digest` | Low | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `training_plans.created_at` | Internal | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `training_plans.updated_at` | Internal | `E-PG` | `R-ACCOUNT` | `A-OWNER` |
| column | `upload_sessions.id` | Internal | `E-PG` | `R-UPLOAD` | `A-OWNER` |
| column | `upload_sessions.owner_id` | Internal | `E-PG` | `R-UPLOAD` | `A-SERVER` |
| column | `upload_sessions.match_id` | Internal | `E-PG` | `R-UPLOAD` | `A-OWNER` |
| column | `upload_sessions.length` | Internal | `E-PG` | `R-UPLOAD` | `A-OWNER` |
| column | `upload_sessions.offset` | Internal | `E-PG` | `R-UPLOAD` | `A-OWNER` |
| column | `upload_sessions.object_key` | Internal | `E-PG` | `R-UPLOAD` | `A-SERVER` |
| column | `upload_sessions.s3_upload_id` | Internal | `E-PG` | `R-UPLOAD` | `A-SERVER` |
| column | `upload_sessions.parts` | Internal | `E-PG` | `R-UPLOAD` | `A-SERVER` |
| column | `upload_sessions.staged` | Internal | `E-PG` | `R-UPLOAD` | `A-SERVER` |
| column | `upload_sessions.status` | Internal | `E-PG` | `R-UPLOAD` | `A-OWNER` |
| column | `upload_sessions.media_asset_id` | Internal | `E-PG` | `R-UPLOAD` | `A-SERVER` |
| column | `upload_sessions.created_at` | Internal | `E-PG` | `R-UPLOAD` | `A-SERVER` |
| column | `upload_sessions.updated_at` | Internal | `E-PG` | `R-UPLOAD` | `A-SERVER` |
| column | `upload_sessions.expires_at` | Internal | `E-PG` | `R-UPLOAD` | `A-OWNER` |
| column | `upload_sessions.file_name` | Medium | `E-PG` | `R-UPLOAD` | `A-OWNER` |
| column | `upload_sessions.file_last_modified_ms` | Medium | `E-PG` | `R-UPLOAD` | `A-OWNER` |
| column | `upload_sessions.head_sha256` | Internal | `E-PG` | `R-UPLOAD` | `A-OWNER` |

## 4. Open items for the security-privacy-engineer

| Id | Item | Owner | Why it is open |
|---|---|---|---|
| DC-1 | At-rest encryption of the Postgres volume and the media bucket is a deployment item: [ADR 0034](../decisions/0034-deployment-edge-acceptance-criteria.md) has no criterion for it yet, and the dev stack (Compose volumes, SeaweedFS) has none. `E-PG` and `E-S3` are therefore met only for backup copies (`E-AGE`) today | security-privacy-engineer (decides whether ADR 0034 gets a criterion before beta) | `grep -n -i 'encrypt\|at rest' docs/decisions/0034-deployment-edge-acceptance-criteria.md` → no line about storage encryption |
| DC-2 | `rate_limit_events.key` rows keyed by an `email_key` or an IP outlive their window (`R-RATE`) | senior-backend-engineer (SEC-S3-TM-04, deferred to C4-MIN) | [`docs/sprints/03/review-rounds.md`](../sprints/03/review-rounds.md) SEC-S3-TM-04, "Partly fixed, deferred" |
| DC-3 | `globals.sql.age` holds role names and attributes only (`--no-role-passwords`); proposed Internal, but inside `E-AGE` like the dump | security-privacy-engineer (class decision) | `take_set` in `scripts/ops/backup.py` |

## 5. Not in this map

Stores outside the four kinds the requirement names are classified where they are designed: the Prometheus TSDB and its labels (ST-075, [threat notes Sprint 5](threat-notes-sprint-05.md) §1, NFR-069.1), the backup encryption key (Secret, never in git, threat notes T5-BK-2), and usability-test data (ST-083, threat notes §4).
