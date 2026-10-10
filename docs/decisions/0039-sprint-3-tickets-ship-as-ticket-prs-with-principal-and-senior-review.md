# 0039. Sprint 3 tickets ship as ticket PRs, each reviewed by the principal engineer and a senior engineer before merge

- **Status:** Accepted (engineering-manager is R/A for sprint process, working-agreement §4). The PO confirmed it for Sprint 3 on 2026-10-08 (P13: "Per-ticket PRs for Sprint 3 too", `po-input-2026-10-05.md`).
- **Amended:** 2026-10-10 by the principal-engineer (PE-R3S3-04): the round-2 ticket map is **replaced by the per-ticket plan (P13)** below. The plan names every commit of `origin/main..origin/sprint-03` exactly once, with its ticket, PR, base and reviewers, and a script checks that (`scripts/ci/adr_commit_plan.py`, rc=0).
- **Date:** 2026-10-07 (review round 1, Sprint 3); amended 2026-10-10
- **Deciders:** engineering-manager; plan: principal-engineer
- **Consulted:** review round 1 findings PE-R1S3-01 (principal-engineer) and QA-R1S3-04 (senior-qa-engineer); review round 3 finding PE-R3S3-04; `po-input-2026-10-05.md` addendum "Ticket-level PRs and reviews" and addendum "P13 answered by the PO (2026-10-08)"
- **Related:** ADR 0022 (one story = one commit), ADR 0030 (dispositions, slices and waivers before the commit), ADR 0037 (human-gated items), ADR 0046 (red-first E2E listed, not gated); `docs/sprints/sprint-03.md` §9; `docs/sprints/03/review-rounds.md` review rounds 1-3; `docs/sprints/03/decisions/PE-R3S3-04.md`

## Context and problem statement

The PO's request, in their words: "each ticket in a sprint needs to have a PR, and each PR need to be reviewed by principle and senior engineers before merge and tested scenarios with integration and unit tests, and the ticket needs to be developed using TDD and DDD". It names no start sprint.

The commit in plan row 68 (author: the agent session, not the PO) recorded the rule in `po-input-2026-10-05.md` and added a row "Effective from | **Sprint 4.** Sprint 3 … ships as one sprint PR". That date is not in the PO's sentence, and nothing in the repository showed that the PO agreed to it (PE-R1S3-01, QA-R1S3-04). An agent cannot grant itself a deferral of a PO rule. On 2026-10-08 the PO answered P13: "Per-ticket PRs for Sprint 3 too".

At that commit, Sprint 3 had no ticket PR: `mcp__github__list_pull_requests state=all` returned only #1 (`sprint-01`), #2 (`sprint-02`) and #3 (`hotfix/gitleaks-ignore`), all closed. The Sprint 3 commits went straight to `sprint-03`, with tickets interleaved.

The round-2 ticket map (plan row 97) covered the commits up to review round 2 only. Review round 3 found that it had no row for the red-until CI change (plan row 96) or for any goal-round commit (plan rows 102 to 133) (PE-R3S3-04, major). By then the ticket PRs had been built a different way from the map's stacked cherry-pick runbook: each ticket became its own branch from `main` (P13), not a stack. So the map no longer described what shipped.

## Decision drivers

- The PO's words are the rule. An agent-written start date does not count as PO consent.
- `sprint-03` is never merged as one PR, and its history is not rewritten. Ticket branches from `main` take cherry-picks of its commits.
- A review on a PR has to cover the code that merges. Review rounds on the sprint branch did not check each ticket's diff against `main`.
- (PE-R3S3-04) The plan must be checkable: every commit of the sprint range is either in exactly one ticket PR or explicitly has none, so nothing ships twice by accident and nothing is left behind.

## Considered options

1. **Ship Sprint 3 as ticket PRs into `main`, each with a principal-engineer and a senior-engineer verdict before merge, and no sprint-wide PR** (chosen; PO P13 confirms it).
2. Keep the "Sprint 4" date and ship Sprint 3 as one sprint PR. Rejected: the PO did not give that date, and on 2026-10-08 chose per-ticket PRs for Sprint 3 (P13). Sprint PR #4 is closed as superseded once every ticket PR has merged.
3. Retroactively label the sprint review rounds as "the ticket reviews". Rejected: no reviewer saw a ticket's diff against `main`, and the rule says "PR … reviewed … before merge".

For the plan itself (amendment, PE-R3S3-04):

- **(a) Replace the map with the plan as shipped, one row per commit, checked by a script** (chosen). Every commit is named once, in a table, and the cherry-pick trailers on `main` show which PR carried it.
- (b) Add rows to the round-2 map for the missing commits only. Rejected: the map's stacked bases and build runbook no longer match the PRs that merged (every base is `main`), so the added rows would sit next to rows that are wrong.
- (c) Keep the commit-to-ticket mapping only in the sprint decision log. Rejected: that is what PE-R3S3-04 found missing, and a decision log row cannot be checked against `git log` mechanically.

## Decision outcome

Chosen option: **1**, with plan **(a)**.

1. **No sprint-wide merge.** `sprint-03` is not merged into `main` as one PR. It stays as the integration and evidence branch. Its history is not rewritten and it is not force-pushed.
2. **One branch and PR per ticket, from `main`.** For each ticket, the owner (or the orchestrator for them) creates `s03/<ticket-slug>` from current `main`, cherry-picks that ticket's `sprint-03` commits in their original (tests-first) order with `git cherry-pick -x`, so each commit on `main` names its `sprint-03` original ("cherry picked from commit …"), adds the ticket's review fixes and its own `docs/sprints/03/decisions/<TICKET-ID>.md`, and opens a PR into `main` (PO P13). Ticket PRs do not edit the shared sprint records; the DOCS ticket carries those.
3. **Reviews before merge.** Each PR gets a review from the **principal-engineer** and from a **senior engineer** in a different role from the author, each starting "Verdict: APPROVE" or "Verdict: CHANGES REQUESTED" (PO addendum). Each reviewer checks TDD (a test commit, or a red run, before the implementation), DDD (bounded context, ubiquitous language, a framework-free domain), and the Gherkin, integration and unit tests for the ticket. A PR merges only when both latest verdicts approve its current head SHA and every CI job including `ci-gate` is green. Only the gated merge step merges, after `merge_ready.py` passes (separation of duties, 2026-10-09).
4. **Size.** A ticket PR over 400 changed lines needs the EM's size decision in its ticket's decisions file (or `SIZE-WAIVERS-03`) **before** the `size-waiver` label is applied (ADR 0030 rule 4).
5. **Secret-scan fingerprint.** A cherry-pick gets a new commit hash, so the `.gitleaksignore` fingerprint of the synthetic test key (plan row 10) does not match the cherry-picked copy. The SEC-RV3-02 PR (#7) carries the key and an ignore entry for **its own** commit hash, guarded by `infra/tests/test_gitleaks_ignore.py`. It merged first, which ended the red nightly on `main` (QA-R1S3-02).
6. **Work not built at the round-2 close** (ST-046 to ST-051, ST-038, ST-052 b/c) was built on ticket branches and cherry-picked from `sprint-03` where it had landed there first; the plan below names each such commit.
7. **The per-ticket plan (P13) below is the record.** Every commit of `origin/main..origin/sprint-03` appears in it **exactly once**: in the commit table, with its ticket PR, or with "none" and the reason. A commit added to `sprint-03` later gets its row here before its PR opens. The check: `python3 scripts/ci/adr_commit_plan.py --adr docs/decisions/0039-sprint-3-tickets-ship-as-ticket-prs-with-principal-and-senior-review.md --range origin/main..origin/sprint-03` → rc=0. Elsewhere in this ADR a `sprint-03` commit is cited by its plan row number, not its hash, so that each hash appears once.

### Per-ticket plan (P13): ticket PRs

Every PR below is based on `main`. "Commits" counts the `sprint-03` commits the PR carries (commit table below). The head reviewed, the merge commit and the verdicts were read from GitHub on 2026-10-10 (Evidence). A verdict marked "(on an earlier head)" was not given on the merged head (findings F1 and F2 below).

| Ticket | PR | Commits | Branch (base `main`) | Head reviewed | Merged into `main` as | Latest verdicts ("Verdict:" lines on the PR) |
|---|---|---|---|---|---|---|
| SEC-RV3-02 | #7 | 2 | `s03/sec-rv3-02-staging-prod-refuse-a-dev-only-auth-emai` | `d6b5646` | `d88e909` | principal-engineer APPROVE; sre-devops-engineer APPROVE |
| PE-R1S3-07 | #12 | 4 | `s03/pe-r1s3-07-ci-pipeline-repairs-infra-tests-job-runs` | `b46d58e` | `4f5b8f1` | principal-engineer APPROVE; senior-qa-engineer APPROVE |
| ST-052 | #14 | 3 | `s03/st-052-l-01-full-tag-and-l-02-keys-for-labeller` | `5e10cfd` | `3f2c268` | principal-engineer APPROVE; senior-qa-engineer APPROVE |
| C3-01 | #19 | 1 | `s03/c3-01-qa-decisions-on-sprint-2-tcr-rows-24-28-` | `9fceaaa` | `8e3cf16` | principal-engineer APPROVE; senior-backend-engineer APPROVE |
| HARNESS-03 | #20 | 2 | `s03/harness-03-sprint-3-goal-harness-statslib-reference` | `c1800f7` | `1adfd80` | principal-engineer APPROVE; senior-backend-engineer APPROVE |
| C3-04 | #21 | 2 | `s03/c3-04-scripts-dev-chrome-sh-installs-the-adr-0` | `286321b` | `54fe4b3` | principal-engineer APPROVE; senior-qa-engineer APPROVE |
| C3-03 | #22 | 3 | `s03/c3-03-s-01-offers-move-to-the-next-game-only-o` | `bd78ea5` | `dbc84b5` | principal-engineer APPROVE; senior-qa-engineer APPROVE |
| QA-R1S3-01 | #23 | 1 | `s03/qa-r1s3-01-not-found-page-go-to-your-matches-link-g` | `48fdebb` | `219ffa5` | principal-engineer APPROVE; senior-qa-engineer APPROVE |
| ST-043 | #24 | 1 | `s03/st-043-pickleball-metric-dictionary-an-01-an-07` | `898883b` | `7650f07` | principal-engineer CHANGES REQUESTED (on an earlier head); senior-qa-engineer APPROVE |
| SRE-PURGE-a | #25 | 1 | `s03/sre-purge-a-purge-scheduler-slice-a-at-least-daily-j` | `9c501a8` | `803bd6c` | senior-backend-engineer APPROVE; principal-engineer APPROVE |
| ST-044 | #26 | 1 | `s03/st-044-starter-stats-an-01-an-07-over-the-proje` | `7974a9b` | `e7c6447` | principal-engineer APPROVE (on an earlier head); senior-qa-engineer APPROVE (on an earlier head) |
| ST-042 | #27 | 3 | `s03/st-042-least-privilege-media-sandbox-worker-own` | `52582fd` | `ff64e0d` | principal-engineer APPROVE; sre-devops-engineer APPROVE |
| C3-02 | #28 | 1 | `s03/c3-02-contract-amendment-decision-not-last-in-` | `e1e2f85` | `63b5a18` | principal-engineer APPROVE; senior-frontend-engineer APPROVE |
| ST-045 | #29 | 1 | `s03/st-045-attribution-conservation-per-game-and-se` | `c22dbf1` | `16bb787` | principal-engineer APPROVE; senior-qa-engineer APPROVE |
| C3-10 | #30 | 4 | `s03/c3-10-carried-minors-t-02-shared-error-summary` | `695b5ca` | `9e7624e` | principal-engineer APPROVE; senior-qa-engineer APPROVE |
| DR-02-FE | #31 | 3 | `s03/dr-02-fe-dr-02-fe-follow-ups-s-01-focus-after-a-d` | `5994ae7` | `4008fc9` | principal-engineer APPROVE; senior-qa-engineer APPROVE |
| ST-049 | #32 | 2 | `s03/st-049-golden-matches-gs-an-1-v1-three-frozen-t` | `c3a3607` | `bcb1a51` | principal-engineer APPROVE; senior-backend-engineer APPROVE |
| COACH-1 | #33 | 1 | `s03/coach-1-qd-an-03-hand-count-of-gs-an-1-an-01-an-` | `c6c15e7` | `278628c` | principal-engineer APPROVE; senior-qa-engineer APPROVE |
| QA-ACC-3 | #34 | 12 | `s03/qa-acc-3-acceptance-first-gherkin-7-1-7-6-with-bi` | `4ca7db3` | `575dfaa` | principal-engineer APPROVE; senior-backend-engineer APPROVE |
| QA-FUZZ-3 | #35 | 1 | `s03/qa-fuzz-3-it-03-12-rule-l11-on-delete-confirmation` | `b0956fb` | `144bb62` | principal-engineer APPROVE; senior-backend-engineer APPROVE |
| GS-AN-1-V2 | #36 | 3 | `s03/gs-an-1-v2-an-07-per-share-low-sample-rule-and-an-0` | `f2fabe4` | `713202d` | principal-engineer APPROVE; senior-qa-engineer APPROVE |
| ST-054 | #37 | 3 | `s03/st-054-e2e-journey-v2-evidence-crawl-and-timing` | `6aa7733` | `10cdd5c` | principal-engineer APPROVE; sre-devops-engineer APPROVE (on an earlier head); senior-backend-engineer APPROVE |
| PE-DESIGN-3 | #38 | 3 | `s03/pe-design-3-pe-1-pe-2-pe-3-api-sprint-03-contract-an` | `637e50e` | `a100038` | senior-backend-engineer APPROVE; principal-engineer APPROVE |
| VR1-S3-01 | #39 | 1 | `s03/vr1-s3-01-mutation-gate-scores-resolve-the-repo-ro` | `5280853` | `8ae5949` | principal-engineer APPROVE; senior-backend-engineer APPROVE |
| ST-053 | #40 | 7 | `s03/st-053-drill-json-schema-v1-and-racket-drill-li` | `2beedde` | `09dbf92` | senior-backend-engineer APPROVE; principal-engineer APPROVE |
| ST-046a | #41 | 1 | `s03/st-046a-metricsnapshot-aggregate-its-repository-` | `865dea0` | `4e99fab` | principal-engineer APPROVE; senior-qa-engineer APPROVE |
| ST-046b | #42 | 1 | `s03/st-046b-stats-recomputed-after-each-scorebook-co` | `47bb28e` | `dbaabec` | principal-engineer APPROVE; senior-qa-engineer APPROVE |
| ST-052a | #43 | 3 | `s03/st-052a-full-tag-domain-access-decision-team-hel` | `d189f2a` | `bfe6f33` | principal-engineer APPROVE; senior-backend-engineer APPROVE |
| ST-047-API | #44 | 1 | `s03/st-047-api-get-matches-id-stats-metric-id-evidence-` | `b7b4173` | `7838def` | principal-engineer APPROVE; senior-qa-engineer APPROVE |
| ST-050a | #45 | 1 | `s03/st-050a-delete-matches-id-tombstones-the-match-e` | `24ca0ef` | `df7beaf` | principal-engineer APPROVE; senior-qa-engineer APPROVE |
| ST-048 | #46 | 4 | `s03/st-048-d-01-stats-dashboard-with-its-states-and` | `6f2334f` | `2961c83` | principal-engineer APPROVE; senior-qa-engineer APPROVE |
| ST-050b | #47 | 3 | `s03/st-050b-purge-fail-closed-purge-refs-and-per-con` | `563e391` | `149e28e` | principal-engineer APPROVE; senior-qa-engineer APPROVE |
| ST-051-API | #53 | 2 | `s03/st-051-api-delete-me-deletes-every-match-erases-the` | `bf02c61` | `0c5d513` | principal-engineer APPROVE; senior-qa-engineer APPROVE |
| SRE-PURGE-b | #54 | 1 | `s03/sre-purge-b-compose-purge-service-runs-the-purge-job` | `dd53fee` | `049aff2` | principal-engineer APPROVE; senior-backend-engineer APPROVE |
| ST-038 | #55 | 1 | `s03/st-038-the-purge-pass-frees-abandoned-uploads-i` | `a48b46c` | `728ce5f` | senior-qa-engineer APPROVE; principal-engineer APPROVE |
| ST-050 | #56 | 1 | `s03/st-050-x-01-delete-this-match-dialog-on-m-02-st` | `d5bf341` | `7552d66` | senior-qa-engineer APPROVE; principal-engineer APPROVE |
| ST-051 | #58 | 1 | `s03/st-051-x-00-your-account-with-x-02-delete-your-` | `82484bb` | `c92cb7a` | senior-qa-engineer APPROVE; principal-engineer APPROVE |
| ST-052b | #60 | 1 | `s03/st-052b-labeller-role-team-held-consent-record-a` | `ec6ac37` | `150c1fe` | principal-engineer APPROVE; senior-backend-engineer APPROVE |
| ST-052c | #61 | 1 | `s03/st-052c-full-tag-label-routes-get-post-export-un` | `34ea807` | `67e918d` | principal-engineer APPROVE; senior-backend-engineer APPROVE |
| VR2-S3-01 | #62 | 3 | `s03/vr2-s3-01-sprint-3-its-scenarios-and-bola-probes-f` | `e0bea28` | `7593710` | senior-backend-engineer APPROVE; principal-engineer APPROVE |
| DOCS-03 | #64 | 56 | `s03/docs-03-sprint-3-records-plan-scorecard-decision` | `9aa150e` | `25a5af0` | senior-qa-engineer APPROVE; principal-engineer APPROVE |

Tickets with a PR into `main` but no `sprint-03` commit (built on their ticket branch from the start, rule 6, or CI fixes found while shipping) are not rows here, because this plan maps the `sprint-03` range: for example CI-PR-GATE (#5), SIZE-WAIVERS-03 (#6), CI-WEBKIT-PD-R3S2-02 (#8), CI-FLAKE-RESUMABLE (#9, #10), CI-POLICY-BASE (#11), CI-PERF-GATES (#13), CI-INTEG-BUDGET (#15), CI-IT0213-HANG (#17), CI-DOMAIN-BUDGET (#48), CI-E2E-MAIN-RED (#49), CI-MERGE-READY-CANCELLED (#50), CI-REDUNTIL-HANG (#51), CI-OBJSTORE-SLOW (#52), CI-E2E-JOURNEYS-TIMEOUT (#57), G03-FE-404 (#59) and PE-R3S3-03-ITS (#63).

### Per-ticket plan (P13): every `sprint-03` commit, in order

Rows are in `git log --reverse origin/main..origin/sprint-03` order. "Type (scope)" is the commit subject's prefix (the full subject is `git log -1 <commit>`). The PR is the one whose merge into `main` brought a commit with the trailer "cherry picked from commit <this commit>".

| # | Commit | Type (scope) | Ticket PR |
|---|---|---|---|
| 1 | `75338b9` | test(measure) | HARNESS-03 (#20) |
| 2 | `ccc2fe9` | docs(sprint-03) | DOCS-03 (#64) |
| 3 | `783cfd2` | feat(analytics) | ST-044 (#26) |
| 4 | `6059930` | fix(C3-03) | C3-03 (#22) |
| 5 | `61dbdd5` | feat(migrations) | ST-042 (#27) |
| 6 | `a678a01` | feat(analytics) | ST-045 (#29) |
| 7 | `984d1d4` | fix(C3-10) | C3-10 (#30) |
| 8 | `3f13b05` | fix(C3-10) | C3-10 (#30) |
| 9 | `bd7593c` | feat(sports) | ST-043 (#24) |
| 10 | `9ca52fe` | fix(platform) | SEC-RV3-02 (#7) |
| 11 | `810c990` | docs(sprint-01) | DOCS-03 (#64) |
| 12 | `954e7bd` | docs(platform) | C3-10 (#30) |
| 13 | `9bdbe46` | docs(sprint-03) | DOCS-03 (#64) |
| 14 | `1c1535d` | test(C3-01) | C3-01 (#19) |
| 15 | `a200f1a` | docs(design) | DOCS-03 (#64) |
| 16 | `1265966` | feat(DR-02) | DR-02-FE (#31) |
| 17 | `975338e` | test(C3-03) | C3-03 (#22) |
| 18 | `c371369` | test(ST-049) | ST-049 (#32) |
| 19 | `39f624a` | test(ST-049) | ST-049 (#32) |
| 20 | `9c18697` | fix(DR-02) | DR-02-FE (#31) |
| 21 | `c2be16e` | fix(DR-02) | DR-02-FE (#31) |
| 22 | `4f3de7f` | docs(sprint-03) | DOCS-03 (#64) |
| 23 | `c0fb6ad` | feat(C3-04) | C3-04 (#21) |
| 24 | `79ad8c3` | test(QA-ACC-3) | QA-ACC-3 (#34) |
| 25 | `979b23c` | test(QA-ACC-3) | QA-ACC-3 (#34) |
| 26 | `8880b55` | test(QA-ACC-3) | QA-ACC-3 (#34) |
| 27 | `5ffce1c` | test(QA-ACC-3) | QA-ACC-3 (#34) |
| 28 | `152c57c` | test(QA-FUZZ-3) | QA-FUZZ-3 (#35) |
| 29 | `c5f7049` | test(C3-03) | C3-03 (#22) |
| 30 | `de1b894` | test(QA-ACC-3) | QA-ACC-3 (#34) |
| 31 | `00430c4` | test(QA-ACC-3) | QA-ACC-3 (#34) |
| 32 | `8745dd5` | test(QA-ACC-3) | QA-ACC-3 (#34) |
| 33 | `ab0c279` | test(QA-ACC-3) | QA-ACC-3 (#34) |
| 34 | `a1bf473` | feat(ST-042) | ST-042 (#27) |
| 35 | `ece0f30` | docs(C3-05) | DOCS-03 (#64) |
| 36 | `610e853` | docs(C3-06) | DOCS-03 (#64) |
| 37 | `e5324cc` | test(C3-10) | C3-10 (#30) |
| 38 | `78644f3` | docs(ST-054) | DOCS-03 (#64) |
| 39 | `a2367d7` | docs(sprint-03) | DOCS-03 (#64) |
| 40 | `e7e86ef` | fix(ci) | SEC-RV3-02 (#7) |
| 41 | `0903a54` | docs(po) | DOCS-03 (#64) |
| 42 | `d0ac61c` | docs(ST-054) | DOCS-03 (#64) |
| 43 | `ecee023` | feat(SRE-PURGE) | SRE-PURGE-a (#25) |
| 44 | `20ad39e` | test(QA-ACC-3) | QA-ACC-3 (#34) |
| 45 | `5421ce7` | test(QA-ACC-3) | QA-ACC-3 (#34) |
| 46 | `9c64d79` | test(ST-054) | ST-054 (#37) |
| 47 | `fb69a7d` | docs(sprint-03) | DOCS-03 (#64) |
| 48 | `4fff02c` | docs(SRE-SMOKE-3) | DOCS-03 (#64) |
| 49 | `c7a6443` | ci(ST-054) | ST-054 (#37) |
| 50 | `a69ff7d` | docs(sprint-03) | DOCS-03 (#64) |
| 51 | `70fa33f` | feat(ST-053) | ST-053 (#40) |
| 52 | `1955d74` | feat(ST-053) | ST-053 (#40) |
| 53 | `2408bff` | feat(ST-053) | ST-053 (#40) |
| 54 | `bac3d81` | feat(ST-053) | ST-053 (#40) |
| 55 | `b5cd5ac` | docs(ST-053) | ST-053 (#40) |
| 56 | `99a711f` | fix(QA-ACC-3) | QA-ACC-3 (#34) |
| 57 | `56048d8` | docs(sprint-03) | DOCS-03 (#64) |
| 58 | `98f4c7c` | feat(ST-052) | ST-052a (#43) |
| 59 | `9562871` | docs(sprint-03) | DOCS-03 (#64) |
| 60 | `f621c51` | docs(sprint-03) | DOCS-03 (#64) |
| 61 | `f493c02` | test(QA-ACC-3) | ST-053 (#40) |
| 62 | `0a8b0ba` | docs(sprint-03) | DOCS-03 (#64) |
| 63 | `83357d8` | docs(sprint-03) | DOCS-03 (#64) |
| 64 | `316a514` | docs(sprint-03) | DOCS-03 (#64) |
| 65 | `4d8af6d` | ci(ST-053) | ST-053 (#40) |
| 66 | `01811d1` | docs(SRE-SMOKE-3) | DOCS-03 (#64) |
| 67 | `2fbc36c` | docs(ST-053) | DOCS-03 (#64) |
| 68 | `94cdb99` | docs(po) | DOCS-03 (#64) |
| 69 | `bd770f8` | docs(C3-02) | C3-02 (#28) |
| 70 | `15a7551` | test(QA-R1S3-11) | ST-052a (#43) |
| 71 | `6f07640` | docs(sprint-03) | DOCS-03 (#64) |
| 72 | `86d7839` | docs(PE-1,PE-2,PE-3) | PE-DESIGN-3 (#38) |
| 73 | `e54b754` | fix(ST-042) | ST-042 (#27) |
| 74 | `fee4fa3` | fix(ST-044) | GS-AN-1-V2 (#36) |
| 75 | `48988f4` | docs(sprint-03) | DOCS-03 (#64) |
| 76 | `8b451d9` | ci(PE-R1S3-07) | PE-R1S3-07 (#12) |
| 77 | `0efd0be` | docs(sprint-03) | DOCS-03 (#64) |
| 78 | `6f3bfce` | test(ST-054) | ST-054 (#37) |
| 79 | `39eb73c` | test(ST-047,ST-050,ST-051,ST-052) | QA-ACC-3 (#34) |
| 80 | `47c34e8` | test(ST-048) | ST-048 (#46) |
| 81 | `055bf74` | docs(sprint-03) | DOCS-03 (#64) |
| 82 | `dc9e73a` | docs(PD-1,DR-03) | DOCS-03 (#64) |
| 83 | `af3dd99` | docs(SEC-1,DR-02-SEC) | DOCS-03 (#64) |
| 84 | `8d805d0` | test(ST-052,ST-053) | ST-052a (#43) |
| 85 | `d59d156` | docs(COACH-1,DR-02-COACH) | COACH-1 (#33) |
| 86 | `4ef07de` | docs(DR-02-BA,PD-R1S3-02) | DOCS-03 (#64) |
| 87 | `09f1f67` | test(C3-04) | PE-R1S3-07 (#12) and C3-04 (#21): carried by both PRs (the runner-safe Chrome check is part of both tickets) |
| 88 | `56b2f6b` | docs(DR-01-PM,DR-02-PM) | DOCS-03 (#64) |
| 89 | `de4613c` | docs(sprint-03) | DOCS-03 (#64) |
| 90 | `921ed53` | fix(ST-043) | GS-AN-1-V2 (#36) |
| 91 | `38b5da4` | docs(ST-044,PE-R2S3-04) | PE-DESIGN-3 (#38) |
| 92 | `99d08e9` | docs(SEC-S3-TM-01,SEC-S3-TM-02,SEC-S3-TM-05) | PE-DESIGN-3 (#38) |
| 93 | `7a6ffe5` | test(ST-049,ST-052) | GS-AN-1-V2 (#36) |
| 94 | `0ba1a22` | docs(sprint-03) | DOCS-03 (#64) |
| 95 | `d98fac8` | docs(DR-03,PD-R1S3-01,PD-R1-06) | DOCS-03 (#64) |
| 96 | `606edcd` | ci(PE-R1S3-07) | PE-R1S3-07 (#12) |
| 97 | `8e25478` | docs(PE-R1S3-01,PE-R2S3-03) | DOCS-03 (#64) |
| 98 | `9726add` | docs(QA-R1S3-06,DR-03) | DOCS-03 (#64) |
| 99 | `fdeeb53` | docs(QA-R2S3-04,PE-R1S3-07) | DOCS-03 (#64) |
| 100 | `19815e8` | docs(QA-VR1-S3) | DOCS-03 (#64) |
| 101 | `9e07c4b` | fix(QA-R1S3-01) | QA-R1S3-01 (#23) |
| 102 | `bd6d1be` | feat(ST-046a) | ST-046a (#41) |
| 103 | `c038dee` | feat(ST-046b) | ST-046b (#42) |
| 104 | `5e0b7ac` | feat(ST-047-API) | ST-047-API (#44) |
| 105 | `d83ee1b` | feat(ST-048,ST-047) | ST-048 (#46) |
| 106 | `87322ad` | feat(ST-050a) | ST-050a (#45) |
| 107 | `96044d9` | feat(ST-050) | ST-050 (#56) |
| 108 | `1040cfb` | feat(ST-051) | ST-051 (#58) |
| 109 | `aac9a8e` | feat(ST-050b-1) | ST-050b (#47) |
| 110 | `48d5889` | feat(ST-050b-2) | ST-050b (#47) |
| 111 | `a1b28bd` | feat(ST-050b-3) | ST-050b (#47) |
| 112 | `9590092` | feat(ST-051-API) | ST-051-API (#53) |
| 113 | `a3bc305` | feat(ST-038) | ST-038 (#55) |
| 114 | `cd8856f` | feat(ST-052) | ST-052 (#14) |
| 115 | `c5476c8` | feat(ST-052b) | ST-052b (#60) |
| 116 | `e45db46` | feat(ST-052c) | ST-052c (#61) |
| 117 | `2a8dbe6` | fix(ST-048) | ST-048 (#46) |
| 118 | `45bf6e6` | fix(ST-051-API) | ST-051-API (#53) |
| 119 | `e925ea0` | docs(G03-01,G03-02,G03-03,G03-04,G03-05,G03-08) | DOCS-03 (#64) |
| 120 | `6a245e5` | docs(G03-06,G03-07,G03-10) | DOCS-03 (#64) |
| 121 | `6332349` | docs(G03-09,ST-052,ST-053) | DOCS-03 (#64) |
| 122 | `661f6c9` | test(ST-054,G03-11) | VR1-S3-01 (#39) |
| 123 | `593f7ff` | docs(G03-12) | DOCS-03 (#64) |
| 124 | `b889dc3` | docs(QA-VR2-S3) | DOCS-03 (#64) |
| 125 | `8643a86` | fix(G03-01,BE-GR1-01) | HARNESS-03 (#20) |
| 126 | `cad2451` | feat(SRE-PURGE) | SRE-PURGE-b (#54) |
| 127 | `912255c` | docs(G03-04,G03-08,G03-10,VR2-S3-01) | DOCS-03 (#64) |
| 128 | `1345187` | test(G03-04,G03-08) | VR2-S3-01 (#62) |
| 129 | `be07fc1` | test(G03-04,G03-11,VR2-S3-01) | VR2-S3-01 (#62) |
| 130 | `723bb7f` | test(G03-06,G03-09,G03-10) | ST-052 (#14) |
| 131 | `81091cb` | fix(G03-06,G03-07) | ST-048 (#46) |
| 132 | `6528205` | docs(G03-07) | DOCS-03 (#64) |
| 133 | `a88dee4` | test(G03-04,G03-11) | VR2-S3-01 (#62) |
| 134 | `74dfd45` | docs(G03-09) | DOCS-03 (#64) |
| 135 | `6af5e1a` | docs(G03-12) | DOCS-03 (#64) |
| 136 | `1433a92` | docs(DR-01,DR-02,DR-03) | DOCS-03 (#64) |
| 137 | `fb920bc` | docs(G03-01,G03-04,G03-06,G03-08,G03-10,G03-11) | DOCS-03 (#64) |
| 138 | `c1fba6a` | docs(QA-VR3-S3) | DOCS-03 (#64) |
| 139 | `1351533` | docs(sprint-03) | DOCS-03 (#64) |
| 140 | `2ba4dd1` | chore(sprint-03) | none: the merge of `main` into `sprint-03`; everything it brings is already on `main` |
| 141 | `8be152d` | ci(PE-R3S3-05) | PE-R1S3-07 (#12) |
| 142 | `c0a7230` | docs(SRE-REL-3) | DOCS-03 (#64) |
| 143 | `bbd95ff` | ci(G03-06,ST-052) | ST-052 (#14) |
| 144 | `f554edd` | docs(SRE-REL-3) | DOCS-03 (#64) |
| 145 | `7ef4c50` | docs(SRE-REL-3) | DOCS-03 (#64) |
| 146 | `72d8364` | docs(SRE-REL-3) | DOCS-03 (#64) |
| 147 | `efd5316` | docs(po) | DOCS-03 (#64) |

Totals: 147 commits; 146 carried by 41 ticket PRs (row 87 by two of them, so the PR table counts 147); 1 with no PR (row 140, a merge commit).

### Findings from building the plan (principal-engineer, 2026-10-10)

- **F1 (major, process): PR #24 (ST-043) merged without a principal-engineer APPROVE.** The principal-engineer's only verdict on #24 is "CHANGES REQUESTED" on an earlier head; the senior-qa-engineer approved the merged head `898883b`. This breaks rule 3. Owner: engineering-manager (route a post-merge principal-engineer review of the #24 diff at `898883b`, and record the miss for the retro). It does not change this plan: the commit (row 9) is on `main` either way.
- **F2 (minor, process): PR #26 (ST-044) merged one commit after its two APPROVE verdicts.** Both verdicts are on `b3ec328`; the merged head `7974a9b` adds only the ticket's own size and test-immutability decision rows (`docs/sprints/03/decisions/ST-044.md`). Rule 3 asks for verdicts on the current head. Owner: engineering-manager (retro).
- **F3 (info): row 87 is carried by two PRs.** PE-R1S3-07 (#12) merged it first; C3-04 (#21) carried the same change again. The second copy is a no-op on `main`; nothing to fix.

## Pros and cons of the options

### Option 1
- Good: it follows the PO's words, and each merged diff is reviewed against `main` by the two roles the PO named.
- Bad: about 40 PRs, cherry-pick work, and a CI run for each one. The red nightly ended only when SEC-RV3-02 (#7) merged.

### Option 2
- Good: one merge and less work.
- Bad: it relies on a start date the PO never gave, and the PO chose otherwise (P13).

### Option 3
- Good: no extra work.
- Bad: it misstates what was reviewed.

### Plan (a), one row per commit with a check
- Good: complete by construction; `git log` and the cherry-pick trailers on `main` are the source, and the script fails on a missing or doubled commit.
- Bad: a long table, and prose must cite commits by row number.

## Consequences

- **Good:** Sprint 3 meets the PO rule, the record no longer claims a PO date the PO did not give, and every `sprint-03` commit has a known ticket PR and reviewers.
- **Trade-offs accepted:** sprint-DoD-done counts only merged ticket PRs. The shared record files (decision log, blockers, scorecard) ship in DOCS-03 (#64), not in the ticket PRs.
- **Follow-up work:** F1 and F2 to the engineering-manager. PR #4 is closed as superseded (P13). The DOCS/RETRO ticket folds `docs/sprints/03/decisions/PE-R3S3-04.md` into the sprint decision log and closes PE-R3S3-04 there.

## Evidence

| Claim | Evidence | Type |
|---|---|---|
| The start date was written by the agent | `git show <plan row 68>` → Author: Claude; the row "Effective from \| **Sprint 4.**" | data |
| The PO chose per-ticket PRs for Sprint 3 | `po-input-2026-10-05.md`, addendum "P13 answered by the PO (2026-10-08)" | data |
| No Sprint 3 ticket PR existed at round 1 | `mcp__github__list_pull_requests state=all` (2026-10-07) → #1 `sprint-01`, #2 `sprint-02`, #3 `hotfix/gitleaks-ignore`, all closed | data |
| The round-2 map missed the goal-round commits | review-rounds.md PE-R3S3-04: `grep -c` of the commits of rows 96, 102, 103, 104, 105, 114, 126, 129, 131 and 133 in this ADR → 0 each (before this amendment) | data |
| Each commit's ticket PR | for each first-parent merge of `origin/main` (`git log --first-parent --format='%H %P %s' origin/main`), the commits `git rev-list <first parent>..<second parent>` whose message has "cherry picked from commit <sha>"; the PR number from the merge subject "Merge pull request #N" (2026-10-10, `origin/main` `25a5af0`) → 146 of 147 commits found, row 140 (the merge commit) none | data |
| Bases, heads and merges | GitHub REST `GET /repos/nhuthuynh/racket-analytics/pulls/{n}` for each PR in the table → `base.ref` = `main` for all 41; `head.sha` and `merge_commit_sha` as listed | data |
| Verdicts | GitHub REST `GET …/pulls/{n}/reviews` and `GET …/issues/{n}/comments`, the latest "Verdict:" per "Reviewer:" role, with the commit it names → two APPROVE on the merged head for 39 PRs; #24 and #26 as in F1 and F2 | data |
| The plan names every commit exactly once | `python3 scripts/ci/adr_commit_plan.py --adr docs/decisions/0039-sprint-3-tickets-ship-as-ticket-prs-with-principal-and-senior-review.md --range origin/main..origin/sprint-03` → before: rc=1, "103 of 147 commits … not named exactly once" (81 missing, 22 named 2 to 6 times); after: rc=0, "147 commits … each named once" | test result |
| The check fails closed | `cd infra && uv run pytest -q tests/test_adr_commit_plan.py tests/test_adr_commit_plan_scenarios.py` → red first 17 failed (script missing), then 17 passed: missing, doubled, glued or longer hex words, empty or unreadable range, missing ADR | test result |
| The round-2 build of the superseded map | the ADR as committed in plan row 97 (`git show <row 97>:docs/decisions/0039-…md`): built from `main` `259a0a8`, all 24 rows without conflict, unit-green per row | history |

## Confirmation

- `python3 scripts/ci/adr_commit_plan.py --adr docs/decisions/0039-…md --range origin/main..origin/sprint-03` → rc=0.
- `list_pull_requests state=all` shows one PR per ticket in the PR table, each with two "Verdict: APPROVE" reviews (principal-engineer and a senior engineer) on its merged head SHA, except F1 and F2.
- `git log main` shows no merge of `sprint-03` itself.
