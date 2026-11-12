# CI-FFMPEG decisions

Per-ticket decision file (working-agreement §3, "Daily sync"). Ticket: CI-FFMPEG "Fast, bounded ffmpeg install in CI (cached, checksum-pinned)", story "CI first". Owner: sre-devops-engineer. Review tier 1 (ADR 0056): principal-engineer plus the senior-qa-engineer test review plus green CI.

## Root cause (measured)

CI run 42019671445 (PR #225), integration job 127218978690: `sudo apt-get install -y -q --no-install-recommends ffmpeg` fetched 62.8 MB at 58.9 kB/s from azure.archive.ubuntu.com and took 17 m 48 s of the job's 20 min timeout, so the backend suites were cancelled. The same unbounded apt install ran in three jobs of `.github/workflows/ci.yml`: `integration` and `flaky-report` (ffprobe for the probe stage and its tests) and `e2e` (ffmpeg with libvpx for the rally-video VP9 stand-in).

## Fix

- `.github/actions/install-ffmpeg/action.yml`: the one place CI installs ffmpeg and ffprobe. `actions/cache` (v6.1.0, pinned by commit) restores `~/.cache/racket-ffmpeg` under the key `ffmpeg-<ImageOS>-<RUNNER_ARCH>-<sha256 of the pin, 16 hex>`; then `scripts/ci/install_ffmpeg.py` runs, and the step prints `ffmpeg -version` and `ffprobe -version` from PATH. The three jobs call it with `timeout-minutes: 4`.
- `scripts/ci/ffmpeg-pin.json`: the build, its archive SHA-256, its sources and the SHA-256 of each installed file (`bin/ffmpeg`, `bin/ffprobe`, `LICENSE.txt`).
- `scripts/ci/install_ffmpeg.py`: cache hit = every pinned file matches its checksum (no network). Otherwise it discards the pinned files, downloads the archive (2 attempts × 75 s, cycling over the pin's sources, inside a 180 s budget; the deadline is checked between reads, so a trickling transfer like run 42019671445 is cut off), verifies the archive, extracts only the pinned files and verifies each. Exit 1 on any checksum or archive failure (nothing unverified is left in place), exit 3 with `CI-FFMPEG: ffmpeg install exceeded its budget of 180 s after N attempts (...)` when every attempt failed.

## Decisions

| Date | Who | Decision | Evidence | Why |
|---|---|---|---|---|
| 2026-11-12 | sre-devops-engineer | **Pinned static build, not cached apt packages** | Local: cold install (download + verify + extract) 18.1 s; cache hit 0.34 s (commands below) | Cached `.deb` files still need `apt-get update` against the same mirror and a dependency set that changes with the runner image; a pinned archive has one checksum and no mirror index |
| 2026-11-12 | sre-devops-engineer | **The same BtbN LGPL build the worker image pins** (`autobuild-2026-09-30-13-08`, `ffmpeg-n8.1.3-9-g29e619e767-linux64-lgpl-8.1`) | Scenario "CI uses the build the worker image pins" compares the pin with the `FFMPEG_BUILD_*` ARGs of `infra/docker/backend.Dockerfile`; the binary's configure line has `--enable-libvpx` and no `--enable-gpl` | Dev/CI/prod parity (AQS/OPS-05): the probe tests now run the ffprobe that ships, not Ubuntu's 6.1. One pin to bump; the drift scenario fails CI when they differ |
| 2026-11-12 | sre-devops-engineer | **Cache the extracted binaries, verify them on every hit** | Unit `test_a_changed_cached_file_is_a_mismatch`; scenario "A tampered cache is discarded and the pinned build is fetched again" | Restoring ~280 MB of binaries and hashing them takes about a second; caching the 137 MB archive would pay an xz extraction (~13 s) on every hit |
| 2026-11-12 | sre-devops-engineer | **Retry policy: 2 attempts cycling over `sources`; the pin lists one source today** | Scenario "A stalled download is retried once on the next source" (2 local sources, 1 s limit) | No second public host serves this exact archive (judgment); a retry opens a fresh connection to GitHub's release CDN, which is not the apt mirror that stalled. Any mirror added to `sources` is safe because the archive is SHA-256 verified |
| 2026-11-12 | sre-devops-engineer | **Cache key: runner image (`ImageOS`), architecture and the pin's hash; no `ImageVersion`** | Action step `Cache key` | A static binary does not depend on the weekly image version; adding it would only add weekly misses (each ~18 s) |

## NFR-062 licence note

FFmpeg from BtbN FFmpeg-Builds, `lgpl` variant: LGPL-3.0-or-later (built with `--enable-version3`, without `--enable-gpl` or `--enable-nonfree`); `LICENSE.txt` from the archive is installed and checksum-pinned next to the binaries. It is a **CI-only** tool here: it is downloaded onto the throwaway runner, never copied into an image or artefact, so it is outside the shipped graph that `scripts/ci/check_licences.py` gates (ADR 0014). The worker image already ships ffprobe from this same build under ADR 0008 "LGPL build only". No new licence and no exception in `infra/licence-exceptions.json`.

## Test change request (TCR), decided by the senior-qa-engineer

| Date | Test | Change | Why | Decision |
|---|---|---|---|---|
| 2026-11-12 | `infra/tests/test_workflows_ci_run2.py::test_backend_suite_jobs_never_run_without_ffprobe` | `"apt-get install" in runs` and `"ffmpeg" in runs` become "the job uses `./.github/actions/install-ffmpeg`"; `"ffprobe -version"` is now checked in the action | The guard's intent (no backend suite job without ffprobe, presence checked) is kept; apt was the mechanism this ticket replaces | **Open: senior-qa-engineer** |
| 2026-11-12 | `infra/tests/test_workflows_sprint02.py::test_e2e_job_has_ffmpeg_for_the_decodable_stand_in` | the apt command string becomes "the e2e job uses the shared action, and the action checks `ffmpeg -version`"; the step-order check (install before Playwright) is unchanged | Same | **Open: senior-qa-engineer** |

No test is deleted or skipped; `infra/tests/` is not a path `check_test_immutability.py` protects, so the TCR rows are the record. The new scenario "no CI job installs ffmpeg with apt" is stricter than the old guards.

## Evidence

- Red (commit `ba33aec7`): `cd infra && uv run --no-sync pytest -q --tb=line tests/test_ci_ffmpeg_install.py` → collection error, `scripts/ci/install_ffmpeg.py` not found; `uv run --no-sync pytest -q --tb=line tests/test_ci_ffmpeg_install_scenarios.py tests/test_workflows_sprint02.py tests/test_workflows_ci_run2.py` → `10 failed, 14 passed` (no shared action in any job, no pin, no script).
- Green (commit `ef04a91c`): same files plus `tests/test_workflows.py` → `52 passed in 7.45s`.
- Real build, local: `python3 scripts/ci/install_ffmpeg.py --pin scripts/ci/ffmpeg-pin.json --dest <tmp>/cache/racket-ffmpeg --github-path <tmp>/gh_path` → `attempt 1 downloaded ... from github.com in 18.0 s; archive and 3 files verified` (exit 0); run again → `cache hit, 3 files verified in 0.3 s` (exit 0, 0.34 s wall).
- `actionlint -no-color` → exit 0; shellcheck on the action's `run:` blocks → exit 0.
- Still to confirm live (QA): on this PR's CI run, the install step's duration in `integration` and each `e2e` leg (≤ 60 s on a cache hit); `flaky-report` runs only on schedule or dispatch, so its first cache-hit duration is the next nightly run.
