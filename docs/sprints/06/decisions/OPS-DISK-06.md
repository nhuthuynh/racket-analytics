# OPS-DISK-06 decisions (sre-devops-engineer)

- **Which targets build images:** read from `make -n <target>` for every target in the `Makefile`; today only `up` (`compose up -d --build --wait`). `up-deps` starts pulled images only, so it has no precheck. The test re-derives the list, so a future build target without the precheck fails.
- **Floor for a build: 16 GB** (`BUILD_MIN_FREE_GB ?= 16`), the measured build floor already in `docs/ops/disk-and-prune.md` (6 GB build + 10 GB run floor). Overridable on the command line with a recorded reason. Consequence: on the shared sandbox at 13 GB free, `make up` now stops with exit 3 until the SRE prunes; that is the intended behaviour (sprint-06 §1 disk row).
- **Risk, nightly `perf-r1`:** it runs `make up` on `ubuntu-24.04`. If a runner ever has under 16 GB free on `/`, the job stops at the precheck with the `df` line as evidence instead of failing later in the build. Not changed here (`.github/` is outside this ticket's dirs); watch the next nightly.
- **Worktree report, no PR → keep:** unpushed work is never marked for removal; detached HEAD → `check`.
- **Footage and weights cap** (4 GB / 2 GB in the sandbox) is judgment from today's free space, to be revisited when P11 footage exists.
