---
release: r1-rc1
status: release candidate, waiting on the PO sign-off (P18, REL-1.4)
alembic_revision: "0021"
previous_release: r1-rehearsal-0020
previous_ref: 09d279ddb42563bfd014a26d74e84db30c90e237
previous_alembic_revision: "0020"
scoring_preset: PROVISIONAL-UNVERIFIED
---
# R1 release notes (release candidate 1)

> **Notice:** Scores are **unofficial scoring (rules not yet verified)**. Release 1 uses the `PROVISIONAL-UNVERIFIED` rules preset. No scoring rule has been checked against the official rulebook yet (waiting on P7).

- **Release:** R1 "Walking skeleton" (`docs/requirements/functional-requirements.md` §0.3): upload, Quick Tag, score sheet, starter stats and a rules-only plan, with no computer vision.
- **Who may use it:** the team and invited testers only. No real-user exposure before the legal review (P16) and the PO sign-off (P18).
- **Written by:** sre-devops-engineer (ST-082; REL-1.1-1.3, FR-055.R1), with the domain wording of `docs/domain/rc-copy-review.md` §2 (COACH-5). The front matter is read by `scripts/ops/rollback_drill.py`; `scripts/ci/check_release_notes.py` checks this file in the `doc-check` job.

## Features

Every FR whose release in `docs/requirements/traceability-matrix.md` starts with R1. "Delivered in" is that matrix's sprint column; VERIFY-05 measures the release gates live.

| FR | Title | Delivered in | In this release |
|---|---|---|---|
| FR-001 | Passwordless sign-in | S1 (ST-013) | shipped |
| FR-002 | Only the owner can access their resources | S0 (ST-006, match); extended every sprint | shipped |
| FR-003 | Age confirmation and footage notice | S4 | behind `FEATURE_AGE_GATE` (off); interim wording (P16) |
| FR-004 | First-run promise | S1 (ST-015) | shipped |
| FR-005 | Match participants by nickname | S1 (ST-016) | shipped |
| FR-006 | Delete a match and everything derived from it | S3 | shipped; purge windows interim (P16) |
| FR-007 | Delete my account | S3 | shipped |
| FR-008 | Video retention setting | S4 | behind `FEATURE_RETENTION_SETTING` (off); interim windows (P16) |
| FR-009 | Training-data consent | S4 | behind `FEATURE_TRAINING_CONSENT` (off); interim wording (P16) |
| FR-011 | Sign out clears local data | S1 (ST-014) | shipped |
| FR-020 | Capture guide | S1 (ST-015) | shipped |
| FR-021 | Match setup flow | S1 (ST-016) | shipped |
| FR-022 | Resumable upload | S0 (ST-008, core); S1 (ST-017) | shipped |
| FR-023 | Upload validation | S1 (ST-018, ST-025) | shipped |
| FR-024 | Abandoned uploads expire | S2 (ST-038) | shipped |
| FR-025 | Footage quality report | S0 (ST-009, facts); S1 (ST-019, stretch); S6 (court visibility) | shipped: fps, resolution and duration; court visibility is R2 |
| FR-027 | Jump to the video moment | S2 (ST-037) | shipped |
| FR-040 | Versioned, parameterised rules engine | S1 (ST-020, part a); preset after OQ-01 | shipped; provisional rules (P7) |
| FR-041 | Side-out doubles scoring | S1 (ST-020, ST-023, part a); preset after OQ-01 | shipped; provisional rules (P7) |
| FR-042 | Side-out singles scoring | S2 (ST-035, ST-041, part a) | shipped; provisional rules (P7) |
| FR-044 | Faults end the rally against the faulting side | S1 (ST-020, ST-023, part a) | shipped; provisional rules (P7) |
| FR-045 | Match structure | S1 (ST-021, part a) | shipped; provisional rules (P7) |
| FR-046 | Start the score sheet mid-game | S2 (ST-034, ST-041, part a) | shipped; provisional rules (P7) |
| FR-047 | Gaps and resync | S2 (ST-036, stretch); else S3 | shipped |
| FR-048 | Score call and announcement | S2 (ST-029) | shipped; provisional rules (P7) |
| FR-049 | Score sheet | S2 (ST-026, ST-030) | shipped; provisional rules (P7) |
| FR-050 | Quick Tag a rally | S2 (ST-027) | shipped |
| FR-051 | Keyboard tagging | S2 (ST-028) | shipped |
| FR-052 | Undo and correction audit | S2 (ST-031) | shipped |
| FR-053 | Corrections replay the score and keep conflicting rallies | S2 (ST-032, ST-041, part a) | shipped; provisional rules (P7) |
| FR-054 | Show the consequences of a correction | S2 (ST-033, stretch); else S3 | shipped |
| FR-055 | "Unofficial scoring" label | S2 (ST-030) | shipped |
| FR-081 | Media probe and normalisation | S0 (ST-009, probe); S6 (normalise) | shipped: probe; normalisation is R2 |
| FR-100 | Starter stats from Quick Tag | S3 | shipped; metric definitions not human-coach-verified (P15) |
| FR-101 | Sample size and uncertainty on every metric | S3 | shipped |
| FR-102 | Versioned metric dictionary | S3 | shipped |
| FR-103 | "Show me" evidence for every metric | S3 | shipped |
| FR-109 | Attribution conservation | S3 | shipped |
| FR-120 | Rank weaknesses by rallies lost | S4 | shipped; unit `rallies_lost_per_game` interim (OQ-08); side-out split provisional (P7) |
| FR-121 | Rules-only general training plan | S4 | shipped |
| FR-122 | Every drill explains why | S4 | shipped |
| FR-123 | Plan built on limited data says so | S4 | shipped |
| FR-124 | Mark sessions done and swap drills | S4 | shipped |
| FR-140 | Drill schema, lint and immutability | S3 | shipped |
| FR-141 | Starter drill library by coverage | S4 | shipped; drills `coach-reviewed`, not human-verified (P15) |
| FR-150 | Full Tag labelling tool (internal) | S3 | internal tool only; consent behind `FEATURE_TRAINING_CONSENT` (off) |
| FR-151 | Frozen, versioned gold sets | S0 (ST-011, manifest check); S2 (ST-040, schema); S3 | shipped |
| FR-160 | Upload and job rate limits | S4 | behind `FEATURE_QUOTAS` (off); interim limits (P8) |
| FR-162 | Pricing fake door | S5 (Could, stretch) | not in R1 (out of scope for Sprint 5; OQ-14) |

## Flags

Every `FEATURE_*` flag of `infra/env.example`. The default is the value a new deployment starts with. The API refuses to start on a value other than `true` or `false`, and `GET /config/public` shows the flags. They stay off until the legal review of the interim wording (P16, NFR-070; ADR 0051 rule 4).

| Flag | Default | What it turns on | Waits on |
|---|---|---|---|
| `FEATURE_AGE_GATE` | `false` | age confirmation and the footage notice (FR-003; OQ-05) | P16 |
| `FEATURE_RETENTION_SETTING` | `false` | the video retention choice and the scheduled purge (FR-008; OQ-07) | P16 |
| `FEATURE_TRAINING_CONSENT` | `false` | the training-data consent (FR-009; OQ-06) | P16, P11 |
| `FEATURE_QUOTAS` | `false` | the match-creation rate limit and the storage quota (FR-160; OQ-13) | P8 |

## Known limitations

| Id | Limitation | Waits on |
|---|---|---|
| L-1 | **Scoring.** Side-out doubles and singles scoring, the game target and the win-by margin, the server number and the score call follow provisional values. Rally scoring is not offered. A match keeps the preset it was scored under. | P7 |
| L-2 | **Coaching.** The plan's split between serving and receiving weaknesses depends on the unverified side-out rule, so the plan page also carries the "unofficial scoring" notice. | P7 |
| L-3 | **Drills.** Every drill is `coach-reviewed` by the team's coaching role, not by a human coach. No drill claims to improve a metric. Warm up first, and stop any drill that hurts. | P15 |
| L-4 | **"Not for me".** Pressing "Not for me" may answer "No other drill fits your setup for this", on the first press for some setups and on the second press for the same weakness in a plan, because a drill the player turned down is not offered again in that plan (COACH-S5-04). | P15 |
| L-5 | **What the app does not do.** It makes no line calls, no automatic fault detection and no refereeing. The player marks every rally. | P7 |
| L-6 | **Privacy and age texts are interim.** The age, footage, consent and retention wording has had no legal review, so those flags stay off. | P16 |
| L-7 | **Quotas and budgets are interim values** (match creations per hour, storage quota, GPU budget). | P8 |
| L-8 | **Screen readers and real phones are not yet tested by a person.** Automated axe, keyboard and browser-matrix checks only. | P6, P20 |
| L-9 | **SLOs are drafts.** The latency and availability targets and the error-budget policy are not committed. | P17 |
| L-10 | **Backup residual (ADR 0058 decision 6).** A deletion made after the newest backup can come back with a restore; up to 24 h of deletions. Accepted for R1 only. | P19 |
| L-11 | **A rollback can lose recent data.** If the downgrade or the redeploy fails, the backup taken before the rollback is restored, and data written between the deploy and the rollback is lost (ADR 0058 rule 7 step 4). | P19 |

## Database and rollback (ADR 0058 rule 7)

- **Schema:** this release is at Alembic revision `0021` (front matter `alembic_revision`). Every migration from `0001` steps down one revision and up again on a seeded database (IT-05-10, `backend/tests/integration/test_it_05_migration_roundtrip.py`; REL-1.3).
- **Previous release:** R1 is the first release, so the drill rehearses the rollback to `r1-rehearsal-0020`: the images built from `main` at `09d279dd` (revision `0020`, the last commit before migration `0021`, 2026-10-19).
- **Images:** a release is the git tag and the images built from it, `racket-<service>:<tag>` for `migrate`, `api`, `worker`, `mailer`, `purge` and `web` (`infra/compose.release.yaml`). `make release-images IMAGE_TAG=<tag>` builds them from the working tree; `make up IMAGE_TAG=<tag>` starts them without building. `make up` with no tag still builds the working tree.
- **Build the previous tag set** (once, from the previous commit's tree, with this tree's override):
  ```
  git worktree add --detach .local/prev 09d279ddb42563bfd014a26d74e84db30c90e237
  IMAGE_TAG=r1-rehearsal-0020 docker compose -f .local/prev/infra/compose.yaml \
    -f infra/compose.release.yaml --env-file infra/.env build
  git worktree remove .local/prev
  ```
- **Rollback order:** `python3 scripts/ops/rollback_drill.py --project <compose project> --to-previous-tag --backup-cmd "<on-demand backup>"` (1) takes the on-demand backup, (2) runs `alembic downgrade <previous_alembic_revision>` with the **current** `migrate` image, (3) starts the previous tag set with `--no-build` and waits for the API's `/healthz`, (4) when step 2 or 3 fails, runs `--restore-cmd` (the restore of ADR 0058 rule 4) and then redeploys the **current** release (`release` in the front matter), whose schema the restored backup has, or stops and names the restore runbook. It never runs an older image on a newer schema, so after a restore it does not start the previous tag.
