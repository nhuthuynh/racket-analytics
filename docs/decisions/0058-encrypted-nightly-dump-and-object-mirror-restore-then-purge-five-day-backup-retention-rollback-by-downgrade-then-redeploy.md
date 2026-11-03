# 0058. Backup and restore: a nightly encrypted Postgres dump and object-store mirror, restore into empty volumes then purge, five-day backup retention inside the deletion window; rollback by downgrade, then redeploy

- **Status:** Accepted (principal-engineer) for the backup, restore, encryption and rollback design. The residual in decision 6 (a deletion made after the newest backup can come back with a restore) is **Accepted for R1 only**: R1 has no real users and its privacy flags are off (ADR 0051 rule 4). The residual must be closed before any real-user beta. The security-privacy-engineer records it as a threat-note row in SEC-5 that names this ADR, and the legal review (P16, NFR-070) may tighten any window.
- **Date:** 2026-11-03
- **Deciders:** principal-engineer (design); security-privacy-engineer (the residual in decision 6, through SEC-5)
- **Consulted:** sre-devops-engineer (owner of ST-076a, ST-076c, ST-082), senior-backend-engineer (ST-076b), security-privacy-engineer (SEC-5 threat notes: backup encryption, credentials, deletion inside backups)
- **Related:** ticket PE-5b, stories ST-076 (gates ST-076a, ST-076b; feeds ST-076c) and ST-082 (REL-1.2, REL-1.3); NFR-045 and its atomic rows NFR-045.1-.5 in `docs/sprints/05/requirements-breakdown.md`; NFR-066 (b) and ADR 0006 (deletion windows); ADR 0034 (deployment edge; the production backup target is a deployment item); ADR 0038 and ADR 0042 (purge service; objects deleted before rows); ADR 0045 (fail-closed purge keys); ADR 0051 (flags off until legal review); ADR 0056 (tier 0 review); goals G05-03 and G05-09 (`docs/sprints/05/goal-scorecard.md`)

## Context and problem statement

NFR-045 asks for an RPO of 24 h or less, an RTO of 4 h or less, and no lost confirmed corrections, all shown by a restore drill. The R1 stack has no backup at all: the sprint 5 plan (§0 gap table) found no `pg_dump`, `pg_basebackup`, `wal-g` or `pgbackrest` anywhere in `infra/`, `scripts/` or `docs/ops/`. Its state lives in two named Compose volumes, `pgdata` (Postgres 16) and `s3data` (SeaweedFS, media bucket), and `make down` runs `docker compose down -v`, which deletes both (`Makefile`, target `down`).

Four facts constrain the design:

1. **Deletion windows.** ADR 0006 and NFR-066 (b) say a deleted match or account is fully purged in 7 days or less. `docs/architecture/deletion-and-purge.md` §2 left "database backups and object-store versioning" out of scope "(none in the dev stack)". A backup would keep purged data alive past the window unless its retention is bounded.
2. **Roles live outside the database dump.** Migration 0012 creates the cluster role `racket_media_worker` and grants to it. `pg_dump` does not dump roles, so a plain restore into a new cluster fails (evidence E2).
3. **Corrections are append-only.** Migrations 0010 and 0011 put triggers on `match_corrections` that refuse `UPDATE`, `DELETE` and `TRUNCATE` except through the match cascade. A restore must load the data without fighting those triggers and must leave them in place.
4. **No release image tags.** `make up` always builds from the working tree (`up -d --build --wait`), and no service in `infra/compose.yaml` has an `IMAGE_TAG`. REL-1.2 asks that `make up IMAGE_TAG=<prev>` redeploys the previous release, so the build path has to change in ST-082.

The decision covers what a backup holds, how it is encrypted, where it is kept and for how long, how a restore runs, how deletions hold across backups, and how a release is rolled back.

## Decision drivers

- NFR-045.1-.4 targets, measured live by the G05-03 drill (`scripts/ops/restore_drill.py`, ST-076c) (planned).
- NFR-066 (b): purged in 7 days or less, backups included (scheduled deletion of unneeded data [AQS/SEC-05] 14.2.7).
- Least privilege and secrets outside git: config from the environment [AQS/OPS-01]; no credential in an image or a commit.
- Dev/prod parity: the same backing services and tools locally as in production [AQS/OPS-05].
- NFR-045's row names the means "daily backup + WAL". This ADR keeps the measurable targets (RPO ≤ 24 h, RTO ≤ 4 h, 0 confirmed corrections lost) but departs from "+ WAL" for R1 (option 2 is rejected until the pre-beta ADR in rule 6). BA-5 notes the departure in the NFR-045 row, so traceability does not show a WAL that does not exist.
- The simplest option that meets the targets; no new paid service; no speculative over-engineering [AQS/ENG-04].

## Considered options

1. **Nightly logical dump (`pg_dump -Fc`) plus a full object-store mirror, encrypted with `age`, every copy kept less than 5 days, restored into empty volumes, then one purge pass before traffic** (chosen).
2. **Continuous WAL archiving with point-in-time recovery (pgBackRest or WAL-G) plus a versioned object mirror.** Good: RPO of minutes, and deletions made after the base backup are replayed from the WAL, which closes the residual in decision 6. Bad: a new long-running tool and an archive store to run and secure, `archive_command` on the shared Postgres service, and a second retention to keep inside the 7-day window. More than R1 needs for an RPO of 24 h (judgment). This is the closure path for decision 6 before a real-user beta.
3. **Volume snapshots (copy `pgdata` and `s3data` with `docker run … tar`).** Good: no new tool. Bad: a file-level copy of a running Postgres is not consistent unless the server is stopped, so every backup costs downtime; the copy is tied to Postgres 16's on-disk format; no per-table check (judgment).
4. **Per-account encryption keys (crypto-shredding), so a deletion destroys the key and every backup copy at once.** Good: deletion inside backups is instant. Bad: a key store, key-per-row encryption in every context, and a schema change across all owned tables. Far beyond R1 scope (judgment).
5. **Do nothing until beta.** Bad: NFR-045 is an R1 item (before beta), and G05-03 cannot be measured.

## Decision outcome

Chosen: **option 1**, with these rules. ST-076a, ST-076b, ST-076c and ST-082 implement them; each rule names the ticket that tests it.

### 1. What a backup set holds (ST-076a)

One backup set is one directory, `<BACKUP_DIR>/<taken_at UTC, YYYYMMDDTHHMMSSZ>/`, with four files:

| File | Content | Made by |
|---|---|---|
| `globals.sql.age` | `pg_dumpall --globals-only --no-role-passwords`: the cluster roles (today `racket` and `racket_media_worker`) without any password hash | step 1 |
| `db.dump.age` | `pg_dump -Fc` of `POSTGRES_DB`: one consistent snapshot of schema, data, grants and the append-only triggers | step 2 |
| `objects.tar.age` | every object of `S3_BUCKET_MEDIA`, as a tar stream, with a manifest member `objects.manifest.json` (key, size, SHA-256 per object) | step 3 |
| `backup.json` | metadata in plain text (below); holds no personal data | step 4, written last |

Order: **roles, then the database, then the objects.** The dump comes before the mirror on purpose. The purge deletes objects before rows (ADR 0042), so an object that disappears between the two steps belongs to a tombstoned match, and the post-restore purge (rule 4) removes that match. The other order would leave live rows naming objects that were never copied. An object written after the dump has no row in the restored database; such orphans can occur only for uploads started in that window, and the drill measures a quiet stack (NFR-045.4). The argument holds only for matches already tombstoned in the dump's snapshot: with `PURGE_MIN_AGE_S` 0, a match can be deleted **and** purged after the snapshot and before the mirror reaches its objects. It is then restored as a live match whose objects are missing; rule 6 covers that case.

`backup.json` fields: `schema_version` (1), `taken_at` (UTC, RFC 3339), `status` (`complete`, written only after the other three files are fsynced; anything else means the set is unusable), `alembic_revision`, `image_tag`, `postgres_server_version`, `artefacts` (file name → size and SHA-256 of the encrypted file), `objects` (count and SHA-256 of the manifest), `corrections` (the ST-076b fingerprint: confirmed-correction count and SHA-256), `recipient` (the `age` public key used, so a restore can find the matching identity). An age above 24 h at drill start is `stale` (NFR-045.1; the ST-076a unit test plants 25 h).

### 2. Schedule, identity and where sets are kept (ST-076a)

- A `backup` Compose service in profile `ops` (planned in ST-076a) runs one set at start and then every `BACKUP_INTERVAL_S` (default 86,400; a value above 86,400 is refused with exit 2, like the purge schedule in ADR 0038), and on demand with `docker compose --profile ops run --rm backup --once`. It logs one JSON line per run (`event` `backup.run`, `status`, `duration_ms`, sizes, `last_complete_at`: the `taken_at` of the newest local set with `status: complete`, or null), and never a key, a password or an object key. A failed run logs `backup.run` too, so a `backup.run` line alone does not mean a usable set exists.
- **Read-only identities.** The service connects as its own login, a member of the PostgreSQL predefined role `pg_read_all_data`, created by the `db-roles` one-shot in the same way as the worker login. It cannot write a row (evidence E4). It reads objects with a third SeaweedFS identity, `racket-backup`, that has `Read` and `List` on the media bucket only. It never gets the app's key or `POSTGRES_PASSWORD`.
- **Outside the Compose volumes.** `BACKUP_DIR` is a host bind mount, default `.local/backups/` (git-ignored, like all of `.local/`), so `make down` (`down -v`) and the drill's volume wipe do not delete the backups they are about to restore. In production the same directory is synced to a separate bucket in another account or region (the **off-site copy**). Which provider, bucket and credentials is a deployment item (ADR 0034); its expiry is not, see the invariant below.
- **Fixed-rate schedule.** Scheduled runs start at `first_start + k × BACKUP_INTERVAL_S`. A run that overruns its slot skips to the next slot; it never pushes later runs back. So two scheduled runs are never more than `BACKUP_INTERVAL_S` apart while the service is up.
- **Retention invariant: every copy of a set is gone less than `BACKUP_KEEP_DAYS` days after its `taken_at` while the schedule runs** (default 5; a value above 5 is refused with exit 2, see rule 5). This covers scheduled sets, on-demand sets (`--once`, the set taken before a rollback in rule 7), incomplete sets and the off-site copy. It is enforced as follows:
  - **Prune with the interval subtracted.** Every run, scheduled or on-demand, prunes **first** (before it checks its recipient or takes its set, so a restarted or misconfigured service still prunes) and again after its set is written, complete or failed. A prune deletes every set whose age at that moment is **at least** `BACKUP_KEEP_DAYS × 86,400 − BACKUP_INTERVAL_S` seconds (4 days at the defaults). The next scheduled run is at most one interval later, so a set reaches that age, and is deleted, before it is `BACKUP_KEEP_DAYS` days old, whatever its offset to the schedule (evidence E9: the earlier rule, "more than `BACKUP_KEEP_DAYS` days old", let a set live 6 days, a scheduled set exactly 5 days old at a run or an on-demand set taken between runs). Incomplete sets older than one interval are deleted too.
  - **The off-site copy expires on the same bound.** The sync runs right after each prune and propagates deletions (a mirror, never an additive copy). The target bucket also has an object-lifecycle rule that expires every object `BACKUP_KEEP_DAYS − 1` days (4 days) after upload, as a backstop for a failed sync: providers round lifecycle ages up to the next midnight UTC and apply them asynchronously, so a 4-day rule removes an object at about 5 days (judgment; the ADR 0034 deployment check records the provider's stated bound). Bucket versioning and object lock are off on the target, or non-current versions expire after 1 day.
  - **Alerts when the prune does not happen.** Each run logs `backup.retention` with `oldest_set_age_s` (local, and off-site when a target is set) and sets the gauge `racket_backup_oldest_set_age_seconds`. ST-076a adds two alert rules next to `purge.overdue` (deletion-and-purge.md §4.3): `backup.retention_overdue` when, after a prune, a set at or above the prune age is still present locally or off-site (the prune or the sync failed; it fires at the run, while the set is still less than 5 days old), and `backup.stalled` when no `backup.run` line with `status: complete` has arrived for `BACKUP_INTERVAL_S + 3,600` s. It keys on the last **successful** run, not on any run line: a service that runs but fails every night (no recipient, a dump, mirror or sync error) still logs `backup.run` and still prunes first, so an alert on any run line would never fire while the prune deletes the last complete sets (review round 2, F5; evidence E10). It also fires when the service is down or hangs (no line at all), in which case nothing prunes. The gauge `racket_backup_last_complete_age_seconds` (from `last_complete_at`; with no complete set yet, the age counts from the service's first start) backs it. The newest complete set is deleted at `BACKUP_KEEP_DAYS × 86,400 − BACKUP_INTERVAL_S` s, so the alert leads that loss by `BACKUP_KEEP_DAYS × 86,400 − 2 × BACKUP_INTERVAL_S − 3,600` s, at least 71 h at the defaults and the 86,400 s cap: the operator fixes the run before no complete set is left (NFR-045.1, RPO ≤ 24 h). For a stopped or hung service `backup.stalled` fires before the oldest set is 5 days and 1 hour old, at least 23 h before the 7-day window of rule 5 ends for a match purged on time; the operator runs `--once` (it prunes first) or deletes the set by hand.

### 3. Encryption and integrity (ST-076a; SEC-5 reviews)

- Every artefact except `backup.json` is encrypted with **`age`** to an X25519 recipient, streaming (`pg_dump … | age -r "$BACKUP_AGE_RECIPIENT" > db.dump.age`), so no plaintext is ever written to disk. The `age` format is authenticated, so a changed byte makes decryption fail instead of yielding wrong data (judgment from the `age` design; the security-privacy-engineer confirms it in SEC-5).
- **Split keys.** The backup service has only the **public** recipient (`BACKUP_AGE_RECIPIENT` in `infra/.env`). The private identity lives in `.local/backup/age-identity.txt` (mode 0600, never in git, never in an image) and is mounted only into the restore step. A compromised backup host can write backups but cannot read them. In production the identity lives in the secret store and offline (ADR 0034).
- **Fail closed.** With no recipient set, the backup service exits 2 and writes nothing; it never falls back to plaintext. `infra/compose.yaml` must not use `${BACKUP_AGE_RECIPIENT:?}` interpolation, because Compose interpolates every service and that would break `make up` for everyone; the check lives in the service.
- **Verify before restore.** The restore checks each artefact's SHA-256 against `backup.json` before it decrypts anything, and refuses a set whose `status` is not `complete`.
- **What the backup host can still read.** The split keys protect the backup files only. The backup host still reads all live data through `pg_read_all_data` and the bucket `Read` identity, so SEC-5 rates it as a host with read access to all personal data, not as a write-only drop box.
- **Licence:** `age` is BSD-3-Clause (judgment; ST-076a records it in `infra/licence-exceptions.json` only if `scripts/ci/check_licences.py` asks for it). It ships as an Alpine package, so the backup image stays `postgres:16-alpine` plus `age` and a small standard-library Python script for the object mirror.

### 4. Restore procedure (ST-076c; `docs/ops/restore-runbook.md`) (planned)

Always into **empty volumes** of a stopped stack, never on top of live data:

1. Stop the stack; delete `pgdata` and `s3data` (the drill: `down -v` on its own project).
2. Start `postgres`, `objectstore` and `objectstore-init` only (a subset of `make up-deps`, which also starts `mailpit` and `tracing`; those are harmless to start).
3. Choose the newest set with `status: complete`; verify its SHA-256s (rule 3).
4. Decrypt `globals.sql.age`, drop the `CREATE ROLE` line for `POSTGRES_USER` (the image already made that role; its `ALTER ROLE` line is kept), and apply the rest with `psql -v ON_ERROR_STOP=1`, so any error stops the restore.
5. Decrypt `db.dump.age` into `pg_restore --exit-on-error --single-transaction -d "$POSTGRES_DB"`. A failure leaves an empty database, not a half-restored one (evidence E2). The append-only triggers are restored with the data and are not disabled: a restore only inserts.
6. Check that `alembic_version` equals `backup.json.alembic_revision`. If the image to run is newer, the normal `migrate` one-shot then upgrades it; if it is older, stop and follow rule 7.
7. Decrypt `objects.tar.age` and upload every object back to the media bucket; compare count and SHA-256 with the manifest (NFR-045.4).
8. Run `db-roles` (sets the worker and backup logins' passwords from `infra/.env`, since the dump has none).
9. **Run one purge pass before any traffic:** `python -m racket.platform.purge --once` (rule 5).
10. Start the rest (`make up`), wait for `/healthz` 200, run the ST-076b check (`racket-integrity`) (planned) and compare with `backup.json.corrections` (NFR-045.3). RTO is the time from step 1 to the end of this step (NFR-045.2).

A restore reports `rpo_hours` (now minus `taken_at` at drill start), `rto_minutes`, `corrections.equal` and `objects.equal` as JSON (ST-076c).

### 5. Deletion within backups (NFR-066 b)

Three rules keep deleted data inside the 7-day window:

1. **Bounded retention.** A match tombstoned at time T is purged from the live stack at P = T + L, where L is the purge lag; L ≤ 1 day while the daily pass is healthy (`PURGE_MIN_AGE_S` 0). The last backup set that holds its rows or objects is taken at B ≤ P. By the rule 2 invariant every copy of that set, the off-site one included, is gone before B + `BACKUP_KEEP_DAYS` days while the backup schedule runs. So the last copy is gone before T + L + 5 days:
   - L ≤ 1 day (healthy purge): before T + 6 days, one day of slack.
   - L = 2 days: before T + 7 days, no slack. This is the largest purge lag the 7-day window tolerates with `BACKUP_KEEP_DAYS` = 5.
   - L > 2 days: the window can be missed inside backups before `purge.overdue` (6 days, deletion-and-purge.md §4.3) fires. So each backup run also reads the oldest tombstone age (the `pg_read_all_data` login can) and logs `backup.purge_lag` at ERROR, an alert in ST-076a, when it is above 172,800 s (2 days). The operator fixes the purge, then deletes the sets taken before it caught up that would outlive T + 7 days.
   - A stopped or hung backup service prunes nothing; a misconfigured or failing one still prunes (rule 2 prunes first) but takes no complete set. `backup.stalled` (keyed on the last run with `status: complete`) and `backup.retention_overdue` (rule 2) are their signals; for a stopped or hung service they fire at least 23 h before T + 7 days for a match purged on time.
2. **Restored tombstones are purged before traffic.** A backup taken between T and P holds the tombstoned match. Rule 4 step 9 runs the purge before the API serves anyone, so a restore never brings a tombstoned match back into reach. While the match waits for that pass, every read path hides it anyway (ADR 0042).
3. **No backup outside the set.** No other copy of `pgdata` or `s3data` is kept, and no object-store versioning is turned on for the media bucket. The only copies of a set are the local one in `BACKUP_DIR` and the off-site copy, and both follow the rule 2 retention invariant (sync with deletions plus a lifecycle expiry). ST-077 classifies the backup artefacts and fails when it finds a backup file this ADR does not list.

### 6. Accepted residual for R1: deletions after the newest backup

A deletion acknowledged after the newest backup's `taken_at` and before a disaster is not in that backup. Restoring it brings the match or account back as **live** data: at most 24 h of deletions (the RPO) are undone. Neither the dump nor the mirror can know about them. The same holds for a match deleted and purged between the dump snapshot and the end of the mirror (rule 1): it comes back live with **dangling object refs**, and `objects.equal` cannot see that, because it compares the mirror with its own manifest. So ST-076c also checks that every `object_ref` of a restored live match exists in the bucket, and lists those that do not as rule 6 candidates.

- **R1 (no real users, privacy flags off):** accepted. The runbook tells the operator to list the `match.deleted` and `account.deleted` log lines after `taken_at` from any log store that survived (they hold ids only, deletion-and-purge.md §4.5) and to delete those again before opening traffic. No replay tool is built in Sprint 5.
- **Before any real-user beta:** closed by option 2 (WAL archiving and point-in-time recovery to the moment before the disaster, which replays the deletions) or by an ids-only deletion journal kept outside the database. The principal-engineer writes that ADR before the beta gate; SEC-5 records the residual as a threat-note row with this ADR's id. `docs/security/tools/check_threat_notes.py` does not check that today; SEC-5 either adds that check or the beta-gate checklist names this row, so the gate does not rest on a check that does not exist.

### 7. Rollback path (ST-082; REL-1.2, REL-1.3)

- **Release images are tagged.** ST-082 gives every built service (today `migrate`, `api`, `worker`, `mailer`, `purge` and `web`) `image: racket-<service>:${IMAGE_TAG:-dev}`. `make up` keeps building when `IMAGE_TAG` is unset or `dev`; with `IMAGE_TAG=<release>` it starts that tag without `--build`, so it cannot rebuild the working tree under an old tag. A release is the git tag `r1.<n>` and the images built from it.
- **Every migration is reversible.** Each migration has a `downgrade()` that restores the previous schema. REL-1.3 is tested by an IT that, on a seeded copy, steps down one migration and up again for every migration since the R1 baseline, and fails on a migration without a `downgrade()`. The 21 migrations at `origin/main` pass that round trip on an empty database today (evidence E5); ST-082 adds seed data.
- **Destructive changes are split (expand, then contract).** A migration that drops or narrows a column, or rewrites data, so that its downgrade cannot give back what it removed, ships in two releases: the expand step and the code that stops using the old shape first, the contract step one release later. Within one release, a downgrade then loses no R1 data.
- **Rollback order:**
  1. Take an on-demand backup (rule 2) and write down its `taken_at`; it is the fallback.
  2. With the **current** image (it holds the downgrade scripts), run `alembic downgrade <previous release head>`; the previous head is the `alembic_revision` in the release notes (REL-1.1).
  3. `make up IMAGE_TAG=<previous release>`; wait for `/healthz` 200 (REL-1.2).
  4. If step 2 or 3 fails: restore the backup from step 1 with rule 4, then run step 3. Data written between the deploy and the rollback is lost; the release notes say so.
- **Never** run an older image against a newer schema: the older `migrate` one-shot does not know the newer revision and stops, and the API could write rows the newer schema would reject.

## Consequences

- Good: NFR-045.1-.4 become measurable with standard Postgres tools, `age` and one small Python script; no new daemon, no paid service.
- Good: backup credentials are read-only, the backup host cannot decrypt, and nothing plaintext touches disk.
- Good: deleted data in backups expires inside the 7-day window by arithmetic (rule 5.1) while the backup schedule runs and the purge lag is 2 days or less, with alerts when either stops holding, and a restore cannot bring a tombstoned match back into reach.
- Bad: with the interval subtracted, a scheduled set at the defaults is kept 4 days, so 4 restore points exist at a time instead of 5 (judgment: enough for an RPO of 24 h).
- Good: rollback is one documented order with a tested downgrade and a backup fallback.
- Bad: a full object mirror every night grows with the media bucket. At the ENG design point (about 31 TB rolling, ADR 0006) five full copies are not affordable. Before beta the mirror becomes incremental (an rclone-style sync of new keys into a versioned target, with the same 5-day expiry); that design is part of the pre-beta ADR in rule 6 (judgment).
- Bad: up to 24 h of deletions can be undone by a restore until rule 6 is closed. Accepted for R1 only.
- Bad: the expand/contract rule makes some schema changes take two releases.
- Neutral: `globals.sql` holds role names and attributes but no password hashes (evidence E3); passwords come back from `infra/.env` through `db-roles`.

## Confirmation

- (planned) ST-076a: `infra/tests/test_backup_service.py` (red first: a 25 h old set is `stale`; no recipient → exit 2 and no file, but the prune still ran; `BACKUP_KEEP_DAYS=6` → exit 2; prune boundary at the defaults: a set aged 4 d − 1 s is kept and one aged exactly 4 d is deleted; with `BACKUP_INTERVAL_S=3600` a set aged 5 d − 1 h is deleted and one aged 5 d − 1 h − 1 s is kept; **negative case:** over a simulated 10-day fixed-rate schedule, no set, scheduled or on-demand at any offset, is ever seen at an age of 5 days or more, the case the earlier rule failed; a set the prune could not delete → `backup.retention_overdue`; **no recipient on consecutive scheduled runs** (complete sets on days 0-2, then every run fails) → each failed run still logs `backup.run` and prunes, `last_complete_at` stays at day 2, `backup.stalled` fires at day 2 + `BACKUP_INTERVAL_S` + 3,600 s, and at that moment the day-2 complete set is still present locally and off-site (the regression case of review round 2, F5); an oldest tombstone of 2 d + 1 s → `backup.purge_lag`) and IT-05-03 (a backup restores into a scratch database). The `backup.stalled` and `backup.retention_overdue` alert rules and the off-site lifecycle rule are checked by the ADR 0034 deployment check.
- ST-076b: IT-05-04 (fingerprint equal after dump and restore; differs after a planted deleted row).
- ST-076c: the G05-03 live drill (`rpo_hours` ≤ 24, `rto_minutes` ≤ 240, `corrections.equal`, `objects.equal` true, no dangling `object_ref` on a live match; `--plant-delete-correction` → rc 1) and `docs/ops/restore-runbook.md` (planned) following rule 4 step by step, including step 9.
- ST-077: every backup artefact named in rule 1 is classified; an unlisted one fails.
- ST-082: the REL-1.3 round-trip IT; the REL-1.2 drill (`make up IMAGE_TAG=<prev>` healthy, rule 7 order).
- SEC-5: a threat-note row for the rule 6 residual naming ADR 0058.
- The principal-engineer reviews ST-076a, ST-076c and ST-082 against rules 1-7.

## Evidence

All commands were run on 2026-11-03 at `origin/main` `7b71daa3` against throwaway local Postgres 16 clusters started with `scripts/dev-postgres.sh` (`RA_DEV_STATE` in a scratch directory), after `python -m racket.platform.migrate` (→ "migrate: database is at head", `alembic_version` = `0021`, roles `racket` and `racket_media_worker`).

| Id | Claim | Command | Result |
|---|---|---|---|
| E1 | No backup tooling exists | sprint-05.md §0 gap table: `git grep -E 'pg_dump\|pg_basebackup\|wal-g\|pgbackrest'` over `infra/`, `scripts/`, `docs/ops/` | nothing (plan evidence) |
| E2 | `pg_dump` omits roles, so a restore into a new cluster fails without them; `--single-transaction` leaves nothing behind | `pg_dump -Fc -f db.dump "$A"`; `pg_restore -l db.dump \| grep -ci ' ROLE '` → `0`; into cluster B: `pg_restore --exit-on-error --single-transaction --no-owner -d "$B" db.dump` | rc 1, `ERROR: role "racket_media_worker" does not exist` / `GRANT USAGE ON SCHEMA public TO racket_media_worker` |
| E3 | Globals first, then the dump, restores the schema with triggers and grants; no password hash in globals | `pg_dumpall --globals-only --no-role-passwords -d "$A" -f globals.sql` (rc 0; `grep -c PASSWORD` → `0`); `psql "$B" -f globals.sql` (one error: role `racket` already exists); `pg_restore --exit-on-error --single-transaction -d "$B" db.dump` | rc 0; `alembic_version` `0021`; 2 `match_corrections%` triggers; `has_table_privilege('racket_media_worker','jobs','UPDATE')` → `t` |
| E4 | A `pg_read_all_data` login can take both dumps and cannot write | `CREATE ROLE … LOGIN … IN ROLE pg_read_all_data`; `pg_dump -Fc` and `pg_dumpall --globals-only --no-role-passwords` as that login; `DELETE FROM alembic_version` as that login | rc 0, rc 0; `ERROR: permission denied for table alembic_version` |
| E5 | Every migration downgrades one step and upgrades again (empty database) | a scratch script calling `alembic.command.downgrade(cfg, "-1")`, `upgrade(cfg, "+1")`, `downgrade(cfg, "-1")` 21 times with `racket.platform.db.MIGRATIONS_DIR`, then `upgrade(cfg, "head")` | `steps 21 back at 0021` |
| E6 | `age` streams and round-trips a dump exactly | `age-keygen -o id.txt`; `age -r "$(age-keygen -y id.txt)" -o db.dump.age db.dump`; `age -d -i id.txt db.dump.age \| cmp - db.dump` (`age --version` 1.1.1) | equal |
| E7 | `make down` deletes both data volumes | `Makefile` target `down`: `$(COMPOSE) down -v`; `infra/compose.yaml` `volumes:` `pgdata`, `s3data` | read at `7b71daa3` |
| E8 | Corrections are append-only by trigger | `backend/src/racket/migrations/versions/0010_corrections_append_only.py`, `0011_corrections_cascade_only_and_no_truncate.py` | `BEFORE UPDATE OR DELETE`, `BEFORE TRUNCATE` triggers |
| E9 | The earlier prune rule ("more than `BACKUP_KEEP_DAYS` days old") lets a set live 6 days; the rule 2 prune (age ≥ `KEEP × 86,400 − INTERVAL`) keeps every set under `KEEP` days at any offset | a scratch simulation of a fixed-rate schedule, sets taken at every 600 s offset in one interval, for both rules (run in the PE-5b review fix, 2026-11-03) | old, KEEP 5, I 86,400 → max 6.0000 d; old, KEEP 5, I 3,600 → 5.0417 d; new, KEEP 5, I 86,400 or 3,600 → 4.9931 d (< 5 d) |
| E10 | With prune-first, an alert on any `backup.run` line never fires for a service that fails every night, and no complete set is left about 4 days after the last success; an alert on the last `status: complete` run fires while the newest complete set is still present | a scratch simulation of a fixed-rate schedule, KEEP 5, complete runs until day 3, every run failing after (logs `backup.run`, prunes first, writes no set) (run in the PE-5b review round-2 fix, 2026-11-03) | I 86,400: last complete set day 2.0000, no complete set left at day 6.0000, old alert never, new alert day 3.0417, newest complete set present at the alert, lead 71.0 h; I 3,600: last complete day 2.9583, none left day 7.9167, old alert never, new alert day 3.0417, present, lead 117.0 h |
| — | Scheduled deletion of unneeded sensitive data | [AQS/SEC-05] 14.2.7 | verified source |
| — | Config in the environment; dev/prod parity | [AQS/OPS-01], [AQS/OPS-05] | verified sources |
| — | `age` authenticated format and BSD-3-Clause licence; costs of WAL-G/pgBackRest and crypto-shredding | — | judgment (SEC-5 and ST-076a confirm) |
