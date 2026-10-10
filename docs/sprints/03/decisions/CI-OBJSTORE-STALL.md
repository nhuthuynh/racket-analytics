# CI-OBJSTORE-STALL decisions

Small decisions for ticket CI-OBJSTORE-STALL (PR #66). It finds the cause of the ~15 s object-store write stalls that failed the throughput floor on main run [38059526467](https://github.com/nhuthuynh/racket-analytics/actions/runs/38059526467) (job 114234764022, head `25a5af0`, the merge of DOCS-03 PR #64). One file per ticket (PO rule 2026-10-07).

## The failing run

- `tests/integration/harness/test_ci_objstore_throughput.py` failed with `slowest 0.158 MB/s < 1 MB/s`. Rates in MB/s per writer: (31.3, 69.6, 65.5), (30.9, 61.9, 72.4), (…, 9.48, 80.7), and **writer 4: (28.8, 0.169, 0.158)**. One writer, which is one boto3 client and one kept-alive connection, was fast in round 1. It then crawled in rounds 2 and 3, while the other three writers finished by 14:26:26.
- Store log, writer 4: the round-2 stage `PutObjectHandler` started at 14:26:25.734 and its `PutObjectPartHandler` at 14:26:30.159 (4.4 s for 862 KB). The next stage started at 14:26:41.035 (10.9 s for the 1.72 MB part), and its part at 14:26:46.50. A volume growth (`volumes 8-14, Reason: grpc assign`) happened at 14:26:42.46, after the stall had started, so it is not the cause.
- At 14:26:40.9, while writer 4 was crawling, the telemetry sampler's fresh `curl` PUT of the same 1.72 MB through the same docker-proxy took 0.015 s (114 MB/s). The stall belonged to one connection, not to the store or the port.
- Runner facts: kernel `6.17.0-1022-azure`, cubic, `tcp_rmem 4096 131072 33554432`, docker 28.0.4. The userland proxy is on (the nat `OUTPUT` rule skips `127.0.0.0/8`, so `127.0.0.1:8333` goes through `docker-proxy`), and conntrack `be_liberal=1`.
- **Re-run of the failed job** (attempt 2, job [114238591070](https://github.com/nhuthuynh/racket-analytics/actions/runs/38059526467/job/114238591070)): success. The floor before the suites ran 14:46:04-14:46:09 and passed, the floor after the suites 14:49:49-14:49:53 passed, and the backend suites took 3 min 40 s. The stall did not come back on that runner.

## Experiments on the CI runners

Only the CI runners stall (local kernel `6.18.44`, bbr). Locally, 30 fresh Compose-equivalent stores x 12 clip writes through docker-proxy gave 360 writes, 0 under 1 MB/s, min 6.59 MB/s. So two temporary workflows ran on this PR's branch. They were removed before merge: `objstore-stall-experiment.yml` plus `scripts/ci/experiments/` at `8fdbd73` and `917b4d6`.

| Run | What | Result |
|---|---|---|
| [38062207301](https://github.com/nhuthuynh/racket-analytics/actions/runs/38062207301) (4 runners, 15 fresh stores per phase, 4x3 clip writes per path) | Phase 1: through docker-proxy (`127.0.0.1:8333`) vs the container's bridge IP, alternating. Phase 2: daemon `userland-proxy: false`, then kernel DNAT on `127.0.0.1:8333` vs the bridge IP | docker-proxy **0/720** stalls; bridge IP, phase 1 **3/720**; phase 2 DNAT **14/720**, bridge IP **9/720**. Every slow write showed the same client socket (`ss -tin`): `Send-Q 0`, `bytes_acked = bytes_sent`, idle 4-11 s while waiting for the response. **The runner's path to the store is not the cause, and docker-proxy is ruled out.** The time is spent inside the store. Durations repeat to the millisecond (stage 5.66-5.67 s and part 11.287-11.296 s; or 4.42 s / 10.4-10.9 s; or 9.2 s / 18.36 s): timer-driven, not load-driven |
| [38064153385](https://github.com/nhuthuynh/racket-analytics/actions/runs/38064153385) (6 runners, 8 iterations, the three store variants interleaved in each iteration, both client paths) | `base` = the Compose store as on main. `rmem` = `sysctls: net.ipv4.tcp_rmem: "4096 1048576 33554432"`. `mtu` = the store's loopback at MTU 1500 (`cap_add: NET_ADMIN`). Each variant ran on a fresh store, with the store namespace's own `ss -tinmo` every 0.25 s (via `nsenter`) and `/proc/<pid>/net/netstat` before and after | **base 10/1,152 stalls** (on 3 of 6 runners). **rmem 0/1,152. mtu 0/1,152.** If rmem had the base rate (0.87 %), 0 in 1,152 would have a chance of about 4.5e-5. The store's own sockets during a base stall (runner 1, it 6): the filer -> volume-server connection `172.19.0.2:41058 -> 172.19.0.2:8080`, `mss:65483`, with 727 KB in `Send-Q`. `bytes_retrans` went from 32768 to 180224, `cwnd:2 ssthresh:2`, then `timer:(persist,…)`, moving about 32 KiB per 0.27 s. The volume server's socket had `rb152745`. Counters for base: `TCPRcvQDrop`, `PruneCalled`, `TCPRcvCollapsed`, and `TCPTimeouts` 6 in the 2 stalled iterations. For mtu: `TCPTimeouts 0`, `TCPRcvQDrop 0`, `PruneCalled 0` on all runners. For rmem: `TCPTimeouts 0` on 5 of 6 runners (1 on one runner, with no stall), and fewer drops |

## Root cause

SeaweedFS `weed server` runs master, volume, filer and S3 gateway in one container. The S3 gateway hands each object to the filer. The filer uploads the chunk to the volume server over HTTP to `objectstore:8080`, which is the container's own IP and is therefore routed through **the container's loopback: MTU 65536, MSS 65483 bytes**. The container's network namespace inherits the runner kernel's default receive buffer, **`tcp_rmem` default 131072 bytes, which is two loopback segments**.

When the volume server reads a little late, two 64 KiB skbs overrun the receive memory budget. The receive queue is pruned or collapsed, and segments are dropped (`TCPRcvQDrop`, `PruneCalled`). With so few segments in flight the sender cannot fast-retransmit. It takes retransmission timeouts and falls to `cwnd 2`, then waits on zero-window persist probes. That kept-alive filer -> volume connection then moves about 150 KB/s. Go's HTTP transport hands the same idle connection back to the next upload, so the slowness sticks to one writer's sequence of requests, as with writer 4. Every request that drew a healthy pooled connection stayed fast, and so did the sampler's curl.

The 64 KiB/s stalls of runs 37764445816 and 37961668800 (CI-OBJSTORE-SLOW) are, in judgment, the same mechanism at a larger backoff: one loopback segment, or part of one, per probe interval of about 1 s. They predate this evidence and cannot be re-measured.

"Flaky" and "slow runner" are not the cause. It is a store configuration that the runner kernel exposes: a 128 KiB receive buffer for a 64 KiB MSS.

## Decisions

| Date | Who | Decision | Evidence | Reasoning |
|---|---|---|---|---|
| 2026-10-10 | sre-devops-engineer | **The object store's network namespace gets `net.ipv4.tcp_rmem: "4096 1048576 33554432"` (`sysctls:` on the `objectstore` service in `infra/compose.yaml`), a 1 MiB default = 16 loopback segments** | Run 38064153385: base 10/1,152 vs rmem 0/1,152 (interleaved, same runners). Red `35fc9c0`, green `06df3b6` (commands below) | Removes the 2-segment receive window that turns a small drop into timeouts and probes. It is declarative and namespaced (only the store container's TCP), it applies to every Compose stack (dev, the CI integration job, E2E, Locust), and it needs no capability |
| 2026-10-10 | sre-devops-engineer | **Not chosen: loopback MTU 1500 in the store** | Also 0/1,152, with no drops at all in run 38064153385 | It needs `cap_add: NET_ADMIN` on the store and an `ip link` call before `exec weed`. That widens the store's privileges for a gain the 1 MiB buffer already gives (judgment). It stays the fallback if a stall comes back with the buffer in place |
| 2026-10-10 | sre-devops-engineer | **Not changed: docker-proxy / the userland proxy, the boto3 client (`Expect: 100-continue`, timeouts, retries), volume pre-growth, and the readiness check** | Run 38062207301: docker-proxy 0/720 and the other paths stalled. The client socket was idle with every byte acknowledged, so the client was not waiting on a 100-continue or a retry. The volume growth in run 38059526467 came after the stall had started | Each was a hypothesis in the brief. The evidence names the store's internal filer -> volume connection, so changing these would treat a cause that is not there |
| 2026-10-10 | sre-devops-engineer | **The throughput floor test and its floors are unchanged** (`FLOOR_SLOWEST` 1 MB/s, `FLOOR_MEDIAN` 5 MB/s, the 64 KiB/s negative control), with no retries and no quarantine. No TCR row is needed | `git diff origin/main -- backend/tests/` is empty | The floor did its job: it failed fast and by name on a real defect |
| 2026-10-10 | sre-devops-engineer | **TDD for a config fix:** the red tests are a scenario (the runner's 128 KiB refused first), unit tests of the segment arithmetic, the Compose config binding and a live store that reports its own `tcp_rmem` and stores the clip. The stall itself is reproduced only on the CI runners (run 38064153385, base variant); the local kernel does not stall even with a 32 KiB buffer (`TCPToZeroWindowAdv=883`, min 7.59 MB/s, 12 writes) | Red: `uv run pytest -q -p no:cacheprovider tests/test_store_netns.py tests/test_ci_objstore_stall_scenarios.py tests/test_compose_objectstore_netns_live.py` (in `infra/`) -> `2 failed, 9 passed`: `assert 'net.ipv4.tcp_rmem' in {}` and the running store's `4096 131072 33554432` -> `assert 2 >= 16`. Green -> `11 passed in 38.33s` | A test that waits for a kernel-dependent stall on a dev machine would never go red. The CI preflight remains the live detector of the stall itself |

## Follow-ups

- The telemetry sampler (`scripts/ci/objectstore_telemetry.sh`) reads the runner's counters, not the store namespace's. Adding `/proc/<store pid>/net/netstat` (`TCPRcvQDrop`, `TCPTimeouts`) and `nsenter … ss` of port 8080 would name this mechanism directly if it comes back. Proposed as a small follow-up (owner: sre-devops-engineer; the EM decides).

## Done check

Done when the preflight passes and its slowest write stays above the floor in 3 consecutive CI runs at the head, and a local 30-iteration loop has zero stalls.

| Check | Head | Result |
|---|---|---|
| Local loop: 30 fresh Compose stores (`infra/compose.yaml` at the fix) x 4 writers x 3 rounds of the clip through docker-proxy | `06df3b6` | (filled when it completes) |
| CI run 1 | | |
| CI run 2 | | |
| CI run 3 | | |
