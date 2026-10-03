# 0021. ffprobe may demux only the MP4/MOV family (input-format allowlist)

- **Status:** Proposed (accept at the round-1 review; security-privacy-engineer A for the threat-model control, principal-engineer consulted)
- **Date:** 2026-10-03
- **Deciders:** senior-backend-engineer (R, review auto-fix round 1); security-privacy-engineer (A)
- **Consulted:** senior-ml-cv-engineer (owner of the probe sandbox, ADR 0020), sre-devops-engineer (worker network)
- **Related:** finding SEC-R1-01; threat model v0 T-WS-2 / F-2 and T-WS-3; ST-009; NFR-054; ADR 0020 (probe sandbox); ADR 0011 (object keys have no extension)

## Context and problem statement

The worker runs `ffprobe` on an uploaded original through a presigned URL (ADR 0020). `ffprobe_argv` set a protocol whitelist (`http,https,tcp,tls`) but no input format, so FFmpeg **auto-detected** the container. A DASH manifest uploaded as a "video" was detected as `dash` and ffprobe fetched the manifest's `BaseURL`, an arbitrary http URL chosen by the uploader: server-side request forgery from the worker. The worker shares the sandbox network with SeaweedFS (master, volume and filer ports are unauthenticated HTTP), Postgres and Jaeger, so the network sandbox does not contain this. FFmpeg's "non standard extension" guard stops HLS only when the URL has an extension, and our object keys (`originals/{random hex}`) have none.

## Decision drivers

- D1. The parser of untrusted input must not become an HTTP client for attacker-chosen URLs (NFR-054; T-WS-2).
- D2. Product scope: phone and camera uploads are MP4/MOV (H.264/HEVC); Sprint 0 accepts nothing else.
- D3. Works on the ffprobe builds we run: distro 6.1.1 in dev/test and the pinned BtbN LGPL 8.1.3 in the worker image.
- D4. Fewest moving parts [AQS/ENG-04]: one flag in the fixed argv, pinned by a unit test.

## Considered options

| Option | Pros | Cons |
|---|---|---|
| A. `-format_whitelist mov,mp4,m4a,3gp,3g2,mj2` (chosen) | Detection still picks the demuxer inside the family; anything else (dash, hls, concat, image2, ...) is refused before it opens a nested URL | Other containers (MKV/WebM, AVI) are refused; they are out of scope until a story asks for them |
| B. `-f mov` (force the demuxer) | Strictest | A non-MOV file gives a less clear error; no difference in practice for the MOV family |
| C. Rely on the network sandbox only | No code change | Fails D1: the sandbox network reaches SeaweedFS master/volume/filer, Postgres and Jaeger |
| D. Sniff magic bytes in Python before probing | Explicit | A second parser to maintain; ffprobe would still auto-detect |

## Decision

Option A. `ffprobe_argv` passes `-format_whitelist mov,mp4,m4a,3gp,3g2,mj2` before the URL. The unit test `tests/unit/video_ingest/test_probe_input_format_policy.py` pins the exact value and its position. The integration test `tests/integration/video_ingest/test_probe_input_formats.py` serves a DASH MPD and an HLS playlist at extensionless key-like paths and asserts `ProbeFailed` and **zero** requests to a canary server (T-WS-2 red-first test).

## Consequences

- Positive: closes the SSRF path through manifest demuxers for every input, whatever its URL looks like.
- Negative: MKV/WebM/AVI uploads now end as `probe_failed`. That is the Sprint 0 scope (D2); widening the list is an ADR amendment with a new canary case per added demuxer.
- Follow-up (sre-devops-engineer, not done here): put the SeaweedFS master/volume/filer ports on a network the worker cannot reach, so only the S3 port is reachable from the sandbox (defence in depth).

## Evidence

- Red first: `APP_ENV=test uv run pytest tests/integration/video_ingest/test_probe_input_formats.py` before the fix → `1 failed, 1 passed`; `AssertionError: assert ['/ssrf-dash.mp4'] == []` (the canary received the DASH fetch; HLS was already blocked by the extension guard, as the reviewer reported). Unit pin before the fix → `2 failed`.
- Manual repro (distro ffprobe 6.1.1): `ffprobe -v debug -protocol_whitelist http,https,tcp,tls http://127.0.0.1:8765/originals/0123…cdef` → `[dash] DASH request for url 'http://127.0.0.2:8766/via-run-ffprobe.mp4'` and the second server logged `GET /via-run-ffprobe.mp4 404`. Same command with `-format_whitelist mov,mp4,m4a,3gp,3g2,mj2` → `[dash] Format not on whitelist`, rc=1, no new request.
- Worker image ffprobe (BtbN `n8.1.3-9-g29e619e767`, `racket-worker:r1` built from this tree): the fixture `clip.mp4` with the flag → `format_name=mov,mp4,m4a,3gp,3g2,mj2`; the DASH manifest with the flag → `[dash] Format not on whitelist`, rc=1.
- Green: `uv run pytest tests/unit/video_ingest/ tests/integration/video_ingest/test_probe_input_formats.py tests/integration/video_ingest/test_probe_sandbox.py tests/integration/test_it_00_09_probe_stage.py` → `64 passed` (IT-00-09 still records the fixture facts).

## Reasoning

The protocol whitelist answers "which transports may ffprobe use" but not "which nested URLs may a demuxer open"; manifest demuxers open URLs by design. Restricting the demuxer set is the control that matches the threat, and it costs one fixed argv entry (judgment).
