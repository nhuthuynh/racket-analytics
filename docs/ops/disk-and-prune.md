# Disk floor and prune procedure (dev sandbox and CI hosts)

Owner: sre-devops-engineer. Rule: working-agreement 1a and ADR 0030 rule 3. Findings: QA-R3-03, QA-R2V-05, PE-R2-S1-04.

## Why

Below about 10 GB free, SeaweedFS refuses writes (`No more free space left`). Uploads, the live goal run and the object-store parity tests then fail for a reason that is not the code. Review round 2 measured this: 4.7 GB free gave `live_goal --runs 5` → 2/5 and 5 failed parity tests; 19 GB free on the same tree gave 5/5 and 7 passed.

## The check (start of every smoke, verifier and reviewer run)

```bash
bash scripts/disk-precheck.sh          # prints `df -h /`; exit 0 ok, 3 below the floor, 2 bad input
RA_MIN_FREE_GB=12 bash scripts/disk-precheck.sh   # a higher floor, e.g. before the 1 GB G01-05 fixture plus an image rebuild
```

Before `docker compose up --build` use `RA_MIN_FREE_GB=16`. A fresh build of the five app images plus the stack's volumes took 6 GB (measured 2026-10-05: `df -h /` 16G free before `up --build`, 10G after), and the run itself still needs the 10 GB floor.

`scripts/measure/live_goal.py` runs the same check itself (`--min-free-gb`, default 10). Below the floor it exits 2 before any request, so a full disk cannot produce a false red. Its JSON summary records `disk_free_gb_start` and `disk_free_gb_end`. A run whose `disk_free_gb_end` is under the floor is not valid evidence; prune and run it again.

## Prune (only what no running agent uses)

1. `docker ps` first. Never stop or remove another agent's Compose project. Tear down only your own: `docker compose -p <your-project> down -v`.
2. `docker builder prune -af`. This removes build cache that no running build uses; the next build is slower but still correct.
3. `docker image prune -f`. This removes dangling images only.
4. `docker volume prune -f`. This removes only volumes that no container uses.
5. Drop your own isolated state: `RA_DEV_STATE=.local/<you> bash scripts/dev-postgres.sh stop` and `… dev-objectstore.sh stop`.
6. Run `bash scripts/disk-precheck.sh` again and paste both `df` lines into the evidence.

Do not run `docker system prune -a --volumes` while other agents' stacks are up: it deletes their stopped containers and images.

## Record

Log every prune in the run's evidence as the `df -h /` line before and after. Example (2026-10-05, review round 2, SRE): 12G free → steps 2-3 (4.866 GB of build cache reclaimed) → 17G free, with the `racket-qav2` stack left running. After the SRE's own isolated stack: `down -v --rmi local` plus step 2 (3.753 GB) → 16G free.
