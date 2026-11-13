# Restore from backup (runbook)

Owner: sre-devops-engineer. Story: ST-076 "Nothing a player corrected is lost" (NFR-045.1-.5). Design: ADR 0058 rule 4 (restore procedure), rule 3 (verify before decrypting), rule 6 (dangling object refs). Backups: the `backup` Compose service, profile `ops` (ST-076a, `scripts/ops/backup.py`). Integrity check: `racket-integrity` (ST-076b). Drill: `scripts/ops/restore_drill.py` (ST-076c), goal G05-03.

Targets: RPO ≤ 24 h (age of the newest complete set when the restore starts), RTO ≤ 240 min (step 1 to the end of step 10), 0 confirmed corrections lost, object count and SHA-256 equal.

## Before you start

- You need the **private** `age` identity that matches `backup.json.recipient` (`.local/backup/age-identity.txt`, mode 0600; in production the secret store, ADR 0034). The backup service never has it.
- Restore only into **empty volumes of a stopped stack**, never on top of live data.
- Write down the time you start: it is the start of the RTO.
- **Save the deletion log lines before step 1.** Step 1 removes the containers and their logs with them. If the old stack's containers still exist, copy their JSON log lines to a host file first: `$C logs --no-color --no-log-prefix api purge > .local/restore-logs.jsonl` (they hold ids only, deletion-and-purge.md §4.5). Otherwise take them from any log store that survived. Step 9 needs them.

All commands run from the repository root. `C` stands for `docker compose -f infra/compose.yaml --profile ops`. `ID` is the identity file and `SET` the chosen backup directory, for example `.local/backups/20261112T101500Z`.

## Steps (ADR 0058 rule 4)

1. **Stop the stack and delete its volumes:** `$C down -v --remove-orphans`. `BACKUP_DIR` is a host directory, so the backups stay.
2. **Start the stores only:** `$C up -d --wait postgres objectstore`, then `$C run --rm objectstore-init`.
3. **Choose and verify the set.** Take the newest directory whose `backup.json` has `"status": "complete"`. Check each artefact before decrypting anything: `sha256sum $SET/*.age` must equal `backup.json.artefacts.<name>.sha256`. Any difference: stop and take the next older complete set. Note `taken_at`: the RPO is the restore start minus `taken_at`.
4. **Roles.** Decrypt `globals.sql.age` with the backup image (`$C run --rm --no-deps -T -u "$(id -u):$(id -g)" -v "$ID:/run/id.txt:ro" -v "$SET:/in:ro" --entrypoint age backup -d -i /run/id.txt /in/globals.sql.age`), drop only the line `CREATE ROLE <POSTGRES_USER>;` (the image made that role; keep its `ALTER ROLE` line), and pipe the rest into `$C exec -T postgres psql -X -v ON_ERROR_STOP=1 -U <POSTGRES_USER> -d <POSTGRES_DB>`.
5. **Database.** Decrypt `db.dump.age` the same way and pipe it into `$C exec -T postgres pg_restore --exit-on-error --single-transaction -U <POSTGRES_USER> -d <POSTGRES_DB>`. A failure leaves an empty database. Do not disable the append-only triggers: a restore only inserts.
6. **Schema revision.** `SELECT version_num FROM alembic_version` must equal `backup.json.alembic_revision`. If the image you will run is newer, the `migrate` one-shot in step 10 upgrades it; if it is older, stop and follow ADR 0058 rule 7 (rollback).
7. **Objects.** Decrypt `objects.tar.age` and upload every `objects/<key>` member back to the media bucket under `<key>`; the uploaded keys, sizes and SHA-256s must equal the tar's `objects.manifest.json` (NFR-045.4). The drill does this inside the API image: `restore_drill.py objects restore` reads the tar on stdin.
8. **Logins.** `$C run --rm --no-deps db-roles` (the dump holds no password; this sets the worker and backup logins from `infra/.env`).
9. **Delete again what was deleted after the backup, then purge, before any traffic** (ADR 0058 rule 5 and the R1 residual of [decision 6](../decisions/0058-encrypted-nightly-dump-and-object-mirror-restore-then-purge-five-day-backup-retention-rollback-by-downgrade-then-redeploy.md#6-accepted-residual-for-r1-deletions-after-the-newest-backup)). A deletion acknowledged after `taken_at` is not in the set, so without this step up to 24 h of deletions (the RPO) come back live when step 10 opens traffic.
   1. **List the deletions after `taken_at`.** From the lines saved before step 1, keep the `match.deleted` and `account.deleted` lines (lines that are not JSON objects are skipped) whose `ts` is at or after `taken_at` (log fields: [deletion-and-purge.md §4.5](../architecture/deletion-and-purge.md#45-log-lines-nfr-057-it-03-13)). The comparison is to the second, so a line from the same second is kept; deleting again what the set already holds as a tombstone is harmless. Matches are listed by `match_id` alone: sub-step 2 reads each owner from the restored database, so a line's `user_id` is never needed for a match:
      ```
      T=<taken_at from backup.json>
      LOGS=.local/restore-logs.jsonl
      jq -rR --arg t "$T" 'fromjson? | objects | select(.event == "account.deleted" and (.ts // "")[0:19] >= $t[0:19]) | .user_id' \
        "$LOGS" | sort -u > .local/redelete-accounts.txt
      jq -rR --arg t "$T" 'fromjson? | objects | select(.event == "match.deleted" and (.ts // "")[0:19] >= $t[0:19]) | .match_id' \
        "$LOGS" | sort -u > .local/redelete-matches.txt
      UUID='^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
      NEWER=$(jq -R --arg t "$T" 'fromjson? | objects | select((.ts // "")[0:19] >= $t[0:19]) | 1' "$LOGS" | wc -l)
      if [ "$NEWER" -eq 0 ]; then
        echo "STOP: no log line at or after taken_at; keep the stack closed and escalate"
      elif grep -vE "$UUID" .local/redelete-accounts.txt .local/redelete-matches.txt; then
        echo "STOP: the deletion lines above carry no id; keep the stack closed and escalate"
      else
        echo "ids ok: $(wc -l < .local/redelete-accounts.txt) accounts, $(wc -l < .local/redelete-matches.txt) matches"
      fi
      ```
      Go on only after `ids ok`. Every deletion line names its account and match (`JsonFormatter` keeps an explicit `user_id`, ADR 0058 decision 6), so a `null` or missing id means the lines cannot be trusted, and no line after `taken_at` means the log does not cover the gap: on either `STOP`, record it in the incident notes and do not open traffic on a guess.
   2. **Delete those ids again** through the same code as `DELETE /me` and `DELETE /matches/{id}` (deletion-and-purge.md §3.1 and §3.2: tombstone, uploads closed, address and names erased, sessions deleted). The owner of each match is read from the restored database. An id the restored database holds as already deleted, or does not hold at all, is skipped, so running it twice changes nothing:
      ```
      $C run --rm --no-deps -T -e REDELETE_ACCOUNTS="$(cat .local/redelete-accounts.txt)" \
        -e REDELETE_MATCHES="$(cat .local/redelete-matches.txt)" --entrypoint python api - <<'EOF'
      import os, uuid
      import sqlalchemy as sa
      from racket.matches.domain import MatchId, OwnerId
      from racket.matches.repository import matches as matches_table
      from racket.matches.service import MatchService
      from racket.platform.db import engine_for, session_factory
      from racket.platform.errors import Unauthenticated
      from racket.players.service import AccountDeletion
      new = session_factory(engine_for(os.environ["DATABASE_URL"]))
      for user in os.environ.get("REDELETE_ACCOUNTS", "").split():
          with new() as s:
              try:
                  AccountDeletion(s).delete(uuid.UUID(user), {"confirm": "delete"})
                  print("account deleted again", user)
              except Unauthenticated:
                  print("account already deleted or absent", user)
      for raw in os.environ.get("REDELETE_MATCHES", "").split():
          match_id = MatchId(raw)
          with new() as s:
              owner = s.execute(
                  sa.select(matches_table.c.owner_id).where(matches_table.c.id == uuid.UUID(raw))
              ).scalar_one_or_none()
              service = MatchService(s)
              match = None if owner is None else service.matches.get_owned(match_id, OwnerId(str(owner)))
              if match is None:
                  print("match already deleted or absent", raw)
              else:
                  service.delete(match, {"confirm": "delete"})
                  print("match deleted again", raw)
      EOF
      ```
      Keep its output with the incident notes: one line per id.
   3. **Purge:** `$C run --rm --no-deps -T --entrypoint python api -m racket.platform.purge --once`. It removes the tombstones restored from the set and those of sub-step 2 (a tombstoned match in the backup never comes back into reach).
10. **Start and check.** `make up` (or `$C up -d --build --wait`), wait for `/healthz` 200, then `$C exec -T api racket-integrity --expect-count <N> --expect-sha256 <HEX>` with the fingerprint recorded before the incident (`backup.json.corrections` once ST-076a writes it). Exit 1 names `corrections`: a confirmed correction is missing or changed; keep the stack closed and escalate. The RTO ends here.

After step 10, list the object keys of live matches (`SELECT a.object_key FROM media_assets a JOIN matches m ON m.id = a.match_id WHERE m.deleted_at IS NULL`) and check each exists in the bucket. A missing one is a rule 6 candidate (a match deleted and purged between the dump and the mirror): record it, do not invent the object.

## The drill (G05-03, NFR-045.5)

```
python3 scripts/ops/restore_drill.py --project racket-drill05 --flags on --json reports/restore-drill.json
python3 scripts/ops/restore_drill.py --project racket-drill05b --flags on --plant-delete-correction \
  --json reports/restore-drill-planted.json   # expect rc 1 naming "corrections"
python3 scripts/ops/restore_drill.py --check reports/restore-drill.json   # re-read the verdict
```

The drill runs the steps above on a Compose project of its own (`.local/drill/<project>/`, every host port remapped, `FEATURE_*` on with `--flags on`), so it never touches your `make up` stack. It starts the stack, seeds two live matches with a media object each and three confirmed corrections, records the `racket-integrity` fingerprint and the bucket inventory (key, size, SHA-256), takes a set with `backup --once` and a fresh `age` key pair, then times steps 1-10. The drill deletes nothing after `taken_at`, so its step 9 runs the purge only; sub-steps 9.1 and 9.2 are an operator step (ADR 0058 decision 6: no replay tool in Sprint 5). `--plant-delete-correction` deletes one correction after the fingerprint and before the backup, so the restored data must differ: the drill exits 1 naming `corrections`. At the end it runs `down -v --rmi local` on its project and deletes its directory (`--keep` leaves them). `--services api` starts only the API and what it needs (used by the test binding); the G05-03 measurement uses the default, the whole stack.

Report fields: `rpo_hours`, `rto_minutes`, `corrections.{before,after,equal}`, `objects.{before,after,equal,manifest_equal}`, `alembic_revision.{backup,restored,equal}`, `dangling_object_refs`, `healthz`, `error`. Exit 0 only when every target holds; 1 when any is missed or a step failed (`error` names it); 2 on a usage error. Behind a TLS-intercepting proxy set `EXTRA_CA_FILE` (the drill passes it to the image builds); `DOCKERHUB_REGISTRY` overrides the registry in the drill's env file.

Cadence (NFR-045.5): once a quarter; this sprint is the first measurement only.
