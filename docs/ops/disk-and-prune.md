# Disk floor and prune procedure (dev sandbox and CI hosts)

Owner: sre-devops-engineer. Rule: working-agreement 1a and ADR 0030 rule 3. Findings: QA-R3-03, QA-R2V-05, PE-R2-S1-04.

## Why

Below about 10 GB free, SeaweedFS refuses writes (`No more free space left`). Uploads, the live goal run and the object-store parity tests then fail for a reason that is not the code. Review round 2 measured this: 4.7 GB free gave `live_goal --runs 5` → 2/5 and 5 failed parity tests; 19 GB free on the same tree gave 5/5 and 7 passed.

## The check (start of every smoke, verifier and reviewer run)

```bash
bash scripts/disk-precheck.sh          # prints `df -h /`; exit 0 ok, 3 below the floor, 2 bad input
RA_MIN_FREE_GB=12 bash scripts/disk-precheck.sh   # a higher floor, e.g. before the 1 GB G01-05 fixture plus an image rebuild
```

Before `docker compose up --build` use `RA_MIN_FREE_GB=16`. `make up` does this itself (OPS-DISK-06): its recipe runs `RA_MIN_FREE_GB=$(BUILD_MIN_FREE_GB) bash scripts/disk-precheck.sh` before Compose, with `BUILD_MIN_FREE_GB` defaulting to 16, so a disk under the floor stops the build before Docker writes a layer. Override it only with a measured reason, e.g. `make up BUILD_MIN_FREE_GB=12` on a warm build cache, and record the `df -h /` line. `infra/tests/test_makefile_disk_precheck.py` fails any new Makefile target that builds images without the precheck first. A fresh build of the five app images plus the stack's volumes took 6 GB (measured 2026-10-05: `df -h /` 16G free before `up --build`, 10G after), and the run itself still needs the 10 GB floor.

`scripts/measure/live_goal.py` runs the same check itself (`--min-free-gb`, default 10). Below the floor it exits 2 before any request, so a full disk cannot produce a false red. Its JSON summary records `disk_free_gb_start` and `disk_free_gb_end`. A run whose `disk_free_gb_end` is under the floor is not valid evidence; prune and run it again.

## Prune (only what no running agent uses)

1. `docker ps` first. Never stop or remove another agent's Compose project. Tear down only your own: `docker compose -p <your-project> down -v`.
2. `docker builder prune -af`. This removes build cache that no running build uses; the next build is slower but still correct.
3. `docker image prune -f`. This removes dangling images only.
4. `docker volume prune -f`. This removes only volumes that no container uses.
5. Drop your own isolated state: `RA_DEV_STATE=.local/<you> bash scripts/dev-postgres.sh stop` and `… dev-objectstore.sh stop`.
6. Run `bash scripts/disk-precheck.sh` again and paste both `df` lines into the evidence.

Do not run `docker system prune -a --volumes` while other agents' stacks are up: it deletes their stopped containers and images.

## Stale worktrees (OPS-DISK-06)

Each agent works in its own worktree under `/home/user/wt` and removes it at done. To find the ones left behind:

```bash
python3 scripts/ops/worktree_report.py              # action, PR state, PR number, branch, path
python3 scripts/ops/worktree_report.py --json       # the same rows as JSON (EM status step)
```

The report only reads (`git rev-parse` per directory and GitHub `GET /pulls?head=<owner>:<branch>&state=all`). Actions: `remove` when the branch's PR is merged or closed; `keep` when it is open or no PR exists (unpushed work is never removed); `check` for a detached HEAD or a directory that is not a worktree. A `remove` row is removed by its owner, or by the SRE when the owner's session has ended: `git -C /home/user/racket-analytics worktree remove <path>`, then `git worktree prune`. Never remove a `keep` or `check` row without asking its owner.

## Footage and model weights (Sprint 6 video analysis)

Video and weights are the largest files the team will handle, and the disk floor above has no room for them by accident. Rules (footage rights and consent: ADR 0062 and FR-174; weights licences: NFR-062):

1. **Outside the repository.** No video (`.mp4`, `.mov`, `.webm`) and no weights file (`.pt`, `.onnx`, `.safetensors`, `.bin`) is committed. Only `models/manifest.json` (licence + SHA-256 per weights file, ST-175b) and synthetic fixtures live in git. Footage with people is stored in the footage bucket (`docs/ops/media-serving.md`), never in a worktree.
2. **Outside image layers.** Weights and footage are never `COPY`ed into an image and never downloaded at build or run time (no runtime model download, ST-175b). They live on the host under `.local/footage/` and `.local/models/` (both git- and docker-ignored via `.local`) or a path set in `infra/.env`.
3. **Mounted read-only.** A service that needs them gets a bind mount with `:ro` (for example `../.local/models:/models:ro`). Workers write derived results to Postgres or the object store, never back into the mount.
4. **Size cap, relative to the floor.** There is no fixed GB allowance: a footage or weights file may be added only if the disk stays at or above the floor after it lands. With `S` the file's size in whole GB (rounded up) and `F` the floor that applies next (`RA_MIN_FREE_GB`, default 10, for a run; `BUILD_MIN_FREE_GB`, 16, when `make up` follows), the budget is `free - F`, so today (`df -h /` shows 12G free, which `disk-precheck.sh` reads as 11 GB, 2026-11-13) the run budget is about 1 GB and the build budget is 0: nothing large goes in before the SRE prunes. Procedure:
   1. Before adding: `du -sh .local/footage .local/models`, then `RA_MIN_FREE_GB=$(( F + S )) bash scripts/disk-precheck.sh`; exit 3 means the file does not fit, so do not copy it.
   2. After adding: `bash scripts/disk-precheck.sh` (the plain run floor), and `RA_MIN_FREE_GB=16 bash scripts/disk-precheck.sh` before any `make up`; if either exits 3, delete the file you just added (rule 5) rather than prune other agents' state.
   3. Record both `df` lines and the `du` line in the evidence.
   A set that does not fit needs a host with room and the EM's approval, not a prune of other agents' state.
5. **Prune.** Footage and weights are pruned by their owner only: delete the local copy (the bucket or the manifest's source stays the record), then run `bash scripts/disk-precheck.sh` and paste both `df` lines. Footage under a deletion request follows `docs/ops/purge-schedule.md`, not this runbook.

## Record

Log every prune in the run's evidence as the `df -h /` line before and after. Example (2026-10-05, review round 2, SRE): 12G free → steps 2-3 (4.866 GB of build cache reclaimed) → 17G free, with the `racket-qav2` stack left running. After the SRE's own isolated stack: `down -v --rmi local` plus step 2 (3.753 GB) → 16G free.
