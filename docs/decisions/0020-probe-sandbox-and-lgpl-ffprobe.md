# 0020. Probe stage sandbox: a pinned LGPL ffprobe, per-process limits inside an internal-network container

- **Status:** Proposed (accept at the ST-009 review; principal-engineer A, security-privacy-engineer consulted on the licence reading)
- **Date:** 2026-10-03
- **Deciders:** senior-ml-cv-engineer (R, ST-009); principal-engineer (A)
- **Consulted:** security-privacy-engineer (NFR-062 licence check, threat model v0 "worker sandbox"), sre-devops-engineer (Compose `worker`, `backend.Dockerfile`), senior-backend-engineer (probe stage and `MediaFacts` already in place, decision-log row 2026-10-03), senior-qa-engineer (IT-00-09, IT-00-10)
- **Related:** ST-009, ST-001; FR-081, FR-025, NFR-054, NFR-055, NFR-062; ADR 0008 ("Media probe: FFmpeg/ffprobe binaries, LGPL build only"), ADR 0012 (seams), ADR 0017 (runner); blockers.md rows "Worker image FFmpeg licence" and "Worker image could not be built"

## Context and problem statement

ST-009 runs `ffprobe` on an uploaded video through a presigned URL. The video is untrusted input, and FFmpeg demuxers parse it. Sprint-00 §ST-009 asks that the worker container has no network route except the object store, has CPU, memory and wall-clock limits, never passes user-supplied filenames to tools (NFR-054) [AQS/SEC-06 13.2.4] [AQS/SEC-10], and logs tool versions at startup [EP/ENG-20]. ADR 0008 requires an LGPL FFmpeg build. Two gaps were open when ST-009 started: the worker image installed Debian's `ffmpeg` (GPL-enabled, and `apt-get` fails in this sandbox, so the image never built here), and limits existed only at container level (2 CPU, 2 GB), with a plain `subprocess.run` that passed the full worker environment (DB URL, S3 keys) to ffprobe.

Questions: (1) where does the LGPL ffprobe come from, and (2) which limits apply to the ffprobe process itself?

## Decision drivers

- D1. LGPL only: no `--enable-gpl`, no `--enable-nonfree` (ADR 0008; NFR-062).
- D2. Reproducible: pinned version and checksum; the build fails on a mismatch.
- D3. The parser of untrusted input gets the least: no secrets in its environment, no local files, no network beyond the object store, bounded CPU, memory, time, output and file writes (NFR-054) [AQS/SEC-10].
- D4. Safe with the runner's lease-heartbeat thread (ADR 0017): no `preexec_fn`.
- D5. Testable without Docker for the process limits; the container limits are proven against the real Compose stack when a daemon exists.
- D6. Fewest moving parts [AQS/ENG-04].

## Considered options

### Q1: LGPL ffprobe source

| Option | Pros | Cons |
|---|---|---|
| A. Debian `apt-get install ffmpeg` (status quo) | One line; distro security updates | GPL-enabled build (fails D1); `apt-get` exits 100 here, so the image never built locally (blockers.md) |
| B. Build FFmpeg from source with a minimal LGPL `configure` (demuxers + parsers + http/tcp only) | Smallest attack surface; full control of flags | Needs a toolchain via apt (blocked here, so unverifiable this sprint); build time; we own CVE rebuilds |
| C. **BtbN FFmpeg-Builds static `linux64-lgpl` release, pinned to a month-end `autobuild-*` tag, sha256-verified** | No apt; one static binary; LGPL flags visible in `-version`; downloadable here and in CI; month-end tags are kept upstream | 141 MB binary with many enabled libraries (larger attack surface than B); third-party build pipeline; LGPL **v3** (`--enable-version3`), not v2.1 |
| D. johnvansickle.com static builds | Popular | GPL builds (fails D1) |

### Q2: process limits for ffprobe

| Option | Pros | Cons |
|---|---|---|
| E. Container limits only (status quo) | Nothing to write | One hostile file can use the whole worker's 2 GB / 2 CPU and stall other stages; ffprobe inherits DB and S3 secrets |
| F. `subprocess.Popen(preexec_fn=setrlimit)` | Simple | `preexec_fn` is unsafe with threads (the lease heartbeat runs in a thread) (judgment, Python `subprocess` docs) |
| G. **A tiny Python launcher (`python -I -S -c …`) sets rlimits and execs ffprobe; the parent scrubs the environment, enforces a wall-clock deadline and an output cap** | Thread-safe; no extra tool; every limit testable with stand-in binaries | ~20 ms start-up per probe; RLIMIT_NPROC does not bind root (the container `pids` limit covers it) |
| H. nsjail / bubblewrap / gVisor around ffprobe | Strongest isolation (namespaces, seccomp) | Extra binary and privileges inside a `cap_drop: ALL` container; not installable here; more moving parts (D6) |

## Decision outcome

**C + G**, inside the existing Compose network sandbox:

1. `infra/docker/backend.Dockerfile` gets an `ffprobe` stage that downloads `ffmpeg-n8.1.3-9-g29e619e767-linux64-lgpl-8.1.tar.xz` from BtbN tag `autobuild-2026-09-30-13-08`, checks sha256 `dfa863a00ca81f1bdf58a372b18cff4820f0017e55de32778de8ecd8ed92a02e`, keeps only `bin/ffprobe` and `LICENSE.txt`, and **fails the build** if `ffprobe -version` shows `--enable-gpl` or `--enable-nonfree`. The worker stage copies it to `/opt/ffmpeg` and sets `FFPROBE_BIN`. No apt ffmpeg.
2. `racket.video_ingest.probe.run_ffprobe` runs ffprobe with: a fixed argv whose only variable is the server-generated URL, refused unless it is `http(s)://host/…` (`ffprobe_argv`); `-protocol_whitelist http,https,tcp,tls` (no `file`, `concat`, `subfile`); stdin `/dev/null`; stderr discarded (it can echo the presigned URL); environment reduced to `PATH` and `LC_ALL=C` (`child_environment`); `cwd=/`; a new session; and `ProbeLimits` defaults of 120 s wall clock, 60 s CPU, 1 GiB address space, 64 open files, 256 processes, 4 MiB stdout, 0-byte file writes, no core dumps. Any breach kills the process and raises `ProbeFailed`, whose message never contains the URL.
3. Compose `worker`: unchanged network sandbox (`sandbox` network, `internal: true`), plus `deploy.resources.limits.pids: 256`.

Reading of "no network route except the object store": the worker also reaches Postgres (the queue lives there, ADR 0008 part B) and the tracing collector (AQS/OPS-06). Neither gives a route out: both sit on the internal network, and the worker cannot reach any host off it (evidence below). Accepting this reading is part of this ADR (judgment; security-privacy-engineer to confirm in threat model v0).

## Consequences

- Positive: the worker image builds in this sandbox for the first time and is LGPL-only; one hostile file cannot take more than 1 GiB / 60 CPU-s / 120 s or write files, and ffprobe never sees the DB URL or S3 keys; startup logs the ffprobe version.
- Negative: we depend on a third-party build pipeline and a 141 MB static binary (larger attack surface than option B). LGPL v3 (not v2.1) needs confirmation by security-privacy-engineer in the NFR-062 check (we distribute no binary to users; the worker runs it server-side).
- Follow-ups: (a) mirror the pinned tarball into our own artifact store before production, so upstream pruning cannot break builds; (b) Sprint 1+: evaluate option B (minimal LGPL `configure`) or a seccomp profile for the worker; (c) HTTPS presigned URLs (production S3) need ffprobe to find CA certificates; `child_environment` passes no `SSL_CERT_*` today, so the first non-HTTP object store must add a test and a fixed CA path; (d) IT-00-10 classifies a TLS-certificate failure as "BLOCKED" although the route is open (see evidence); QA may add a plain-HTTP-to-IP check so an intercepting network cannot give a false pass.

## Evidence

| Claim | Evidence | Type |
|---|---|---|
| Debian `ffmpeg` is GPL-enabled | `ffprobe -version \| grep -o -- --enable-gpl` on the dev container's Ubuntu build → `--enable-gpl` | test result |
| Pinned build is LGPL without GPL/nonfree | `ffprobe -version` of the pinned build: `configuration: … --enable-version3 … --disable-libx264 --disable-libx265 …`; grep for `--enable-gpl`/`--enable-nonfree` → none; `LICENSE.txt` head: "GNU LESSER GENERAL PUBLIC LICENSE Version 3" | test result |
| Month-end autobuild tags are kept long-term | `git ls-remote --tags https://github.com/BtbN/FFmpeg-Builds` lists `autobuild-2024-11-30-13-12`, `autobuild-2024-12-31-13-02`, `autobuild-2025-01-31-12-58`, …, and daily tags only for the last days | data |
| Checksum | `checksums.sha256` of tag `autobuild-2026-09-30-13-08` → `dfa863a0…02e  ffmpeg-n8.1.3-9-g29e619e767-linux64-lgpl-8.1.tar.xz`; local `sha256sum -c` → OK | test result |
| Worker image builds with it | `docker build --secret id=extra_ca,… --build-arg PYTHON_IMAGE=mirror.gcr.io/library/python:3.11-slim -f infra/docker/backend.Dockerfile --target worker -t racket-worker:st009 .` → rc=0; GPL guard step printed `ffprobe version n8.1.3-9-g29e619e767-20260930` | test result |
| Policy unit tests (negative first) | `uv run pytest tests/unit/video_ingest/test_probe_sandbox_policy.py` → red `ImportError: cannot import name 'ProbeLimits'`, then `22 passed` (incl. `file:`, `concat:`, `subfile`, `ftp:`, `-i`, empty URL refused) | test result |
| Process limits enforced on a real child | `uv run pytest tests/integration/video_ingest/test_probe_sandbox.py` → red `ImportError`, then `10 passed`: hang killed at 1 s wall clock, CPU spinner killed by RLIMIT_CPU, 1 GiB allocation refused under 512 MiB, file write refused, 256 open files refused, endless stdout cut at 1 MiB, no secrets in child env, stdin EOF, argv fixed; real ffprobe (system and pinned LGPL via `FFPROBE_BIN`) probes the fixture over HTTP within the default limits | test result |
| Found by those tests | first run: real ffprobe exited 1 because `os.execv` does not search `PATH` (bare `ffprobe`), and `setrlimit` raised "not allowed to raise maximum limit" for RLIMIT_NPROC above the hard limit; fixed by resolving the binary with `shutil.which` in the parent and capping each limit at the current hard limit | test result |
| IT-00-09 green with both binaries | local Postgres 16 + SeaweedFS 3.97 (`scripts/dev-postgres.sh`, `scripts/dev-objectstore.sh`): `pytest tests/integration/test_it_00_09_probe_stage.py` → `1 passed` (system ffprobe); with `FFPROBE_BIN=<pinned LGPL>` IT-00-08/09/11 + features job_resilience + walking_skeleton → `7 passed` | test result |
| IT-00-10 green against the real Compose stack | `docker compose -f infra/compose.yaml (+ local image override) up -d --wait postgres objectstore objectstore-init tracing worker`, then from `backend/`: `pytest tests/integration/test_it_00_10_worker_sandbox.py -v` → `2 passed` (not skipped) | test result |
| The block is caused by the internal network (control) | from the worker: `https://example.com/` → `Temporary failure in name resolution`; `http://1.1.1.1/` → `Network is unreachable`; `http://objectstore:8333/` → HTTP 403 (open); `http://tracing:4318/` → HTTP 404 (open). Same image on the non-internal `edge` network: `http://1.1.1.1/` → HTTP 403 (route open, answered by the intercepting proxy); `https://example.com/` → `CERTIFICATE_VERIFY_FAILED` (route open, TLS intercepted) | test result |
| Probe works inside the hardened container | `docker compose exec -T worker python -c <put clip; run_ffprobe(presigned_get)>` → `uid 999`, `MediaFacts(container='mov,mp4,m4a,3gp,3g2,mj2', video_codec='h264', duration_ms=60000, fps=60.0, vfr=False, width=1920, height=1080, has_audio=True)` in 0.10 s; `touch /app/x` → `Read-only file system`; worker log `"ffprobe": "ffprobe version n8.1.3-9-g29e619e767-20260930 …"` | test result |
| Container controls in config | `infra/tests/test_worker_sandbox.py` → 5 of 7 fail against the previous Dockerfile/compose (mutation check), `7 passed` after; `tests/test_compose.py` still green (`18 passed` together) | test result |
| `preexec_fn` unsafe with threads | Python `subprocess` documentation warning (not in our research set) | (judgment) |
| 1 GiB / 60 s CPU / 120 s defaults are enough for a 60 s clip | pinned ffprobe on the 1.7 MB fixture: 0.10 s; AS 1 GiB passes with both binaries. Long (90 min) phone videos are not yet measured | data + (judgment) |
