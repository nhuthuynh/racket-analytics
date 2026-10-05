# Phone fixtures and the R-05 upload-cap measurement (ST-025)

Owner: senior-ml-cv-engineer. Status on 2026-10-05: **tooling and synthetic profile set done; real phone recordings (`phones-v1`) and the R-05 numbers are blocked on a human with phones** (blockers.md row 2026-10-05, senior-ml-cv-engineer).

Sources: sprint-01 §14.1 ST-025 and §14.3.9; NFR-025; FR-023 conflict K12; OQ-06 / ADR 0023; QD §8 (manifest fields); contract seam `backend/tests/support/contract.py` ("phone fixtures").

## 1. What exists

| Set | Path | What it is | Used for |
|---|---|---|---|
| `phone-profiles-v1` | `fixtures/clips/phone-profiles-v1/` | 6 synthetic 2 s clips that reproduce the **shapes** phones write. Generated from FFmpeg lavfi test sources by `scripts/fixtures/generate_phone_profiles.sh` (deterministic: two runs gave identical sha256 for all 6 files). CC0, no people, `consent_status: synthetic`. Device names are `synthetic-profile/<shape>`: these are **not phone models** | Probe and validation tests now (container, codec, frame rate, VFR, rotation, no audio) |
| `phones-v1` | `fixtures/clips/phones-v1/` (not created) | Real recordings from at least 5 phone models, at least one VFR | NFR-025 coverage, R-05, `phone_fixtures.feature` scenarios 1 and 3 |

The profile clips cover:

| File | Container | Codec | Frame rate | Note |
|---|---|---|---|---|
| `h264-mp4-1080p30.mp4` | MP4 | H.264 | 30 CFR | AAC audio |
| `h264-mp4-1080p60.mp4` | MP4 | H.264 | 60 CFR | AAC audio |
| `h264-mp4-1080p-vfr.mp4` | MP4 | H.264 | VFR: `r_frame_rate` 60/1, `avg_frame_rate` 47/1 | Product VFR rule (`media_facts.py`: real differs from average) returns `True` |
| `h264-mov-720p30-noaudio.mov` | MOV | H.264 | 30 CFR | No audio track |
| `hevc-mov-1080p60-rotated.mov` | MOV | HEVC (`hvc1`) | 60 CFR | Display matrix rotation 90 (phone held upright) |
| `hevc10-mov-2160p30.mov` | MOV | HEVC Main10 (`yuv420p10le`) | 30 CFR | 4K, 10-bit (no HDR signalling claimed) |

The synthetic clips' MB per minute (5 to 30) **must not be used for R-05**: test patterns at CRF 35 compress far better than camera footage.

## 2. Why `phones-v1` is not in the repo yet

This sandbox has no phones and no camera, and an encoder cannot stand in for a phone's encoder settings. Naming a synthetic file after a phone model would make the coverage scenario pass on a false claim. So `phone_fixtures.feature` "Coverage of the set" and "Probe every fixture" stay red on purpose. The consent scenario is green (commit `30baddc`).

## 3. How to record `phones-v1` (for the person with the phones)

1. **Who and what:** an empty court, or team members who have signed written consent (OQ-06, ADR 0023). Bystanders must not be in frame.
2. **Phones:** at least 5 different models, both iOS and Android if possible. Use the camera app's defaults first. Then, on each phone that offers it, record 1080p at 60 fps (the capture guide's setting). Write down the exact menu path you used: this also checks the device-specific lines in `docs/domain/capture-guide-wording.md` §3.
3. **Clips:** for each model and setting, record about 60 s of court play or a static court with movement (enough for a stable MB/min). Keep at least one clip from a phone in its default "auto frame rate" or low-light mode, which is the likely VFR file. Do not edit, trim or re-share the files (messaging apps re-encode). Copy them by cable or AirDrop/"original quality" export.
4. **Lay out** the files as `fixtures/clips/phones-v1/<model-slug>/<setting>.<mp4|mov>` and write `recordings.csv` with `path,device_model,shows_people,consent_record` (consent record = the path or ID of the signed form, empty when nobody is in frame).
5. **Size:** if the set is over the repo limit (15 MiB per committed clip, `test_committed_fixture_sets.py`), the SRE decides Git LFS or the object store (sprint-01 ST-025 "Files / interfaces", P6).
6. **Build and check:**

```bash
uv run --project backend python scripts/fixtures/build_phone_manifest.py fixtures/clips/phones-v1 \
  --id phones-v1 --version 1 --licence <licence> --consent-status consented --created <date> \
  --r05-out docs/data/r05-measurement.json
cd backend && uv run racket-manifest-check ../fixtures/clips/phones-v1
env -u APP_ENV uv run pytest -q tests/features/test_phone_fixtures.py
```

The manifest build probes each file with ffprobe, hashes it and writes one `clips` entry per video: `device_model`, `fps` (nominal), `avg_fps`, `vfr`, codec, size, duration, `mb_per_minute`, `shows_people`, `consent_record`. A file with `shows_people=true` and no consent record fails `racket-manifest-check` and is named.

## 4. R-05: how the caps are decided

The provisional caps are 10 GB and 150 min (K12). Both caps bind at the same time at a **break-even rate**:

`10,000,000,000 B / 150 min = 66.67 MB per minute (8.89 Mbit/s)`

This value is computed by `racket.dataset.phone_set.assess_caps` and pinned by `test_break_even_rate_for_10_gb_and_150_minutes`.

- If the highest measured MB/min across the ≥ 5 models is **at or below 66.7**, the duration cap binds first. 10 GB and 150 min can stay.
- If it is **above 66.7**, a player recording at that setting hits the 10 GB cap before 150 min. For example, at 120 MB/min that happens after 83 min (pinned in `test_size_cap_binds_first_when_a_phone_records_above_break_even`). The team then either raises the size cap to `max MB/min × 150` (security-privacy-engineer owns the abuse trade-off, NFR-053), or keeps it and changes the copy to say how long a recording at 1080p60 fits.

No phone bitrate is claimed here. The vendor pages that publish per-minute sizes could not be fetched from this sandbox (`support.apple.com` blocked by the egress proxy on 2026-10-05), and the role's citation rule allows only verified sources. The decision waits for the measured numbers.

## 5. Finding for the probe (routed to senior-backend-engineer)

`hevc-mov-1080p60-rotated.mov` has a 90° display matrix. `MediaFacts.from_ffprobe` reports 1920×1080 (the stored size), not the displayed 1080×1920. If the UI or a later stage shows or uses the display size (portrait recordings are common on phones), the rotation side data must be read (`streams[].side_data_list[].rotation`). Evidence: an ad-hoc run of `MediaFacts.from_ffprobe` over the six profile clips on 2026-10-05 printed `hevc-mov-1080p60-rotated.mov ... hevc vfr= False 1920 1080`.

## Changelog

| Date | Who | Change |
|---|---|---|
| 2026-10-05 | senior-ml-cv-engineer | Written: profile set, build tool, recording protocol, R-05 decision rule; `phones-v1` blocked on recordings |
