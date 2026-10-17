# Coaching design: weakness ranking and the rules-only training plan (R1)

- **Status:** Accepted for build (principal-engineer, 2026-10-17, gate ticket PE-4, ADR 0047 rule 2). Review: senior-backend-engineer (required), senior-frontend-engineer and security-privacy-engineer (comments). A change after merge goes through the ticket PR of the story that needs it, with a row in that ticket's `docs/sprints/04/decisions/<ID>.md`.
- **Stories:** ST-055 (weakness), ST-056 (aggregate, assembly), ST-057 (citations, limited data), ST-061a (persistence), ST-061b (API), ST-062 (done, swap), ST-060 (eval). HTTP: [`api-sprint-04.md`](api-sprint-04.md). Canvas: [`contexts/coaching.md`](contexts/coaching.md). Map: [`context-map.md`](context-map.md) R8, R12.
- **Inputs:** FR-120..FR-124, FR-141; QD-PL-01..06; ADR 0003 (unit), 0005 and 0041 (low sample), 0042 (purge order), 0051 rules 2-3; `docs/process/ddd-guidelines.md` §4; the weakness catalogue and warm-up rule of COACH-4 (`docs/domain/weakness-catalogue.md`, `docs/domain/drill-review-checklist.md`), which own every coaching *value* this file only names.
- **Not in R1:** the LLM step (FR-125, R11 ACL); efficacy claims (ADR 0005); plans across sports.

## 1. Modules and layers

| Module | Layer | Holds | May import |
|---|---|---|---|
| `racket.coaching.weakness.domain` | domain (pure) | `RallyLoss`, `Weakness`, `WeaknessRanking`, `rank()` | `racket.sports` (R5), standard library |
| `racket.coaching.weakness.acl` | ACL (application) | translation of the Analytics and Match read models into `RallyLoss` and `MetricFact` | `racket.analytics.public`, `racket.matches.public`, the domain above |
| `racket.coaching.plan.domain` (package) | domain (pure) | `TrainingPlan`, `Session`, `DrillAssignment`, `Citation`, `Preferences`, `assemble()`, events | `racket.coaching.weakness.domain`, `racket.coaching.drills` (pure loaders), standard library |
| `racket.coaching.plan.repository` | infrastructure | SQLAlchemy mapping, owner filter, optimistic version check | SQLAlchemy |
| `racket.coaching.service`, `racket.coaching.api` | application, HTTP | use cases (generate, read, done, undo, swap), router | everything above, FastAPI |
| `racket.coaching.public` | published port | `purge_match`, `purge_account` for the purge job | the repository |

The `domain` names are deliberate: `backend/tests/unit/test_architecture.py` checks every `domain.py` and `domain/` package for framework imports, so these modules are covered with no test change. ST-055 ships `weakness/domain.py` (the scorecard's mutation target `src/racket/coaching/weakness` is the package). Analytics data enters Coaching only through §4.

## 2. Ubiquitous language (adds to the canvas and the glossary)

| Term | Meaning |
|---|---|
| Rally lost | A counted rally that the player's side did not win (sheet rules 0.1, 0.2). Attributed exactly once (FR-109) |
| Lost on serve / on receive | The player's side was serving / receiving in that rally. Which side serves follows the side-out rule, unverified until P7 (`side_out_verified: false`) |
| Weakness | A catalogue category (COACH-4) to which lost rallies are attributed, with its target metric. Ranked by rallies lost per game |
| Point conceded | A lost rally that gave the opponent a point; shown beside the weakness, never used to rank (ADR 0003) |
| Training plan | The player's current 2-week plan; exactly one per account |
| Session, drill assignment | A planned practice, and one drill at a stated number of minutes in it |
| Citation | The evidence behind an assignment: metric, value, n and the rallies (QD-PL-04) |
| Limited-data plan | A plan whose top weakness's metric is low-sample (QD-PL-06; ADR 0041 dictionary rule) |
| Stale plan | A plan that cites a match that has since been deleted |

## 3. Weakness ranking (ST-055; FR-120; ADR 0003)

- **Scope:** the account's live (not tombstoned) matches with at least one counted rally ("tagged") and a participant marked `is_me`. A match without `is_me` (the Sprint 0 client) is skipped and counted in `skipped_matches` (judgment: guessing the side would rank the opponent's weaknesses).
- **Value objects** (frozen dataclasses): `RallyLoss(match_id, rally_id, game_key, phase: "serve"|"receive", category, conceded_point: bool)`; `Weakness(id, metric_id, catalogue_order, lost: int, lost_on_serve: int, lost_on_receive: int, conceded: int, games: int)` with `per_game`, `on_serve_per_game`, `on_receive_per_game` as `Fraction` (rounded to 2 places only when serialised); `WeaknessRanking(unit, side_out_verified, games, rallies, weaknesses, skipped_matches)`.
- **Rule:** `rank(losses, games, catalogue)` groups by catalogue weakness, sorts by **(−lost/games, catalogue_order, id)**, and returns every weakness with `lost > 0`. Losses in the catalogue's "unattributed" category (an opponent's winner, `attribution.UNATTRIBUTED`) are shown when the catalogue names them as a weakness, else only counted. Zero games → empty ranking with reason `no_tagged_match`, never an error.
- **Invariant (property test ≥ 1,000 examples):** for each match and phase, the sum of attributed losses equals the side's rallies lost (FR-109 conservation, as `analytics.attribution.check_conservation`).
- **Unit:** `unit` is the setting `COACHING_WEAKNESS_UNIT` (only `rallies_lost_per_game`, ADR 0051 rule 2). `side_out_verified` is `false` while `rules-verified.md` has no verified side-out row (P7).
- **Top 3** weaknesses feed the plan (FR-121).

## 4. The Analytics ACL (R8) and the Match port (R12)

Coaching owns the translation; it never imports `racket.analytics.{sheet,snapshot,attribution,repository,service}` or any table.

| Port function (added by ST-055, read-only) | Returns |
|---|---|
| `racket.matches.public.player_sides(session, owner_id) -> list[(match_id, side)]` | live matches of the owner with an `is_me` participant and that slot's side (`A`/`B`), ordered by `(played_on, match_id)` |
| `racket.analytics.public.rally_facts(session, match_id) -> RallyFacts \| None` | `sheet_version`, `rules_version`, `games` (game keys in play order), and per counted rally `rally_id, number, game, serving_side, winning_side, ending, fault_kind, actor, point_to` (the `CountedRally` fields, as plain values). `None` when the match is gone |
| `racket.analytics.public.metric_facts(session, match_id, side) -> dict[metric_id, MetricFact]` | per published metric of the current snapshot (read repair as `GET …/stats`): `k`, `n`, `value`, `low_sample`, `min_sample`, `metric_version`, and the evidence `rally_ids` in `start_ms` order |

`acl.losses_for(owner_id)` turns these into `RallyLoss` for the player's side, using the catalogue's (ending, actor, phase) → weakness table. `acl.citation_facts(owner_id, metric_id)` pools a metric over the scope: `k` and `n` summed, `value = k / n` (AN-04: `count / games`, n = games; AN-07: the share of the weakness's category, n = rallies ended by the side), `low_sample` by the dictionary rule on the pooled numbers. With one match in scope the pooled numbers equal `GET /matches/{id}/stats` for that side (G04-01 step 6).

## 5. The `TrainingPlan` aggregate (ST-056, ST-057, ST-062)

```
TrainingPlan (root)  id, owner_id, version, library_version, preferences, weaknesses (ranking snapshot),
                     limited_data, unfitted (weakness ids with "no drill fits your setup"),
                     source_match_ids, excluded_drills, stale, content_digest
 └─ Session          id, week (1..2), index (1..sessions_per_week), minutes_budget, done_at
     └─ DrillAssignment  id, position, drill_ref (id@version), minutes, weakness_id | None (warm-up),
                         citation: Citation(metric_id, metric_version, value, n, k, low_sample, rally_refs ≤ 10), reason_not_for_me
```

Invariants, checked by the root on creation **and** after every command (done, undo, swap); a violation raises `PlanInvariantBroken` and nothing is saved:

| Id | Invariant |
|---|---|
| QD-PL-01 | Σ assignment minutes of a session ≤ `minutes_budget` = min(`minutes_per_session`, ⌊`weekly_minutes` / `sessions_per_week`⌋); Σ per week ≤ `weekly_minutes`; each `minutes` within the drill's `duration_min..duration_max` |
| QD-PL-02 | every drill: `players ≤ players_available`, `needs ⊆ equipment`, level in `level_min..level_max`, `review_status` ∈ {`coach-reviewed`, `verified`}, not deprecated, present in the pinned `library_version` |
| QD-PL-03 | position 1 of every session is a drill with skill `warm-up` (5-10 minutes, COACH-4); every assignment's `minutes`, the warm-up's included, ≤ ⌊0.4 × `minutes_budget`⌋. So the smallest budget that can hold a warm-up is 13 (⌊0.4 × 13⌋ = 5); the API's lower bound of 15 (api §2.1) keeps every accepted budget above it (⌊0.4 × 15⌋ = 6) |
| QD-PL-04 | every assignment, warm-ups included, has a citation with `n ≥ 1` and a non-null `value`; the cited metric is in the drill's `target_metrics`; `rally_refs` ⊆ the metric's evidence. A non-warm-up cites its weakness's metric; a warm-up cites the highest-ranked weakness metric among its `target_metrics`, else its first target metric with `n ≥ 1`. A drill with no citable metric is not eligible |
| QD-PL-06 | `limited_data = {"rallies": R}` (R = counted rallies in scope) exactly when the top weakness's citation is `low_sample` |
| plan | 2 weeks × `sessions_per_week` sessions; a drill appears at most once per session. `excluded_drills` is **not** a plan-wide invariant: assembly reuses a drill across sessions (§6 step 2), so a swapped-out drill stays in the other sessions where it was placed; the set only limits what `swap` may pick (below) |

Commands: `TrainingPlan.mark_done(session_id, at)`, `undo_done(session_id)`, `swap(assignment_id, library, reason)`. Each accepted change returns its event and adds 1 to `version`; a no-op (done twice, undo when not done) changes nothing and returns no event. `swap` picks the first eligible drill (assembly order, §6) that cites the same metric, keeps every invariant with the session's other assignments, and is not the current drill and not in `excluded_drills`; the swapped-out drill then joins `excluded_drills`, so no later swap in this plan offers it again (ST-062 AC "swapped-out drill not offered again in that plan"). The swap changes only the one assignment: other sessions that hold the same drill keep it, and the post-command check does not test `excluded_drills` against existing assignments. None → `NoAlternative`, plan unchanged. A done session is not swapped (`SessionDone`).

**Optimistic concurrency:** the repository saves with `UPDATE … WHERE id = :id AND version = :loaded`; 0 rows → the service reloads and retries the command once, then answers 409 `plan_conflict`. Done ops are idempotent by `(account_id, op_id)` (api §3.3).

## 6. Assembly and the determinism rule (ST-056, ST-060)

`assemble(ranking, citations, preferences, library) -> PlanDraft | Infeasible` is a pure function. Drafts carry no ids, no clock values and no randomness; the service adds `uuid4` ids and `created_at` when it saves.

1. **Eligible drills** (QD-PL-02) sorted by `(id, version)`. Warm-ups: skill `warm-up`. Per top-3 weakness: drills whose `target_metrics` contain its metric.
2. **Slots:** for session s (s = 0..2n−1 in week/index order) the warm-up is eligible warm-up `s mod W`; the rest of the budget is filled by weaknesses in rank order, weighted 3:2:1 for ranks 1-3 (judgment; ST-056 pins it in its decisions file), drill `j mod D_w` for that weakness's j-th use, minutes = min(drill `duration_max`, the 40% cap, remaining budget), skipping a drill whose `duration_min` does not fit.
3. A top-3 weakness with no eligible drill goes to `unfitted` and its share passes to the next weakness. No eligible warm-up, or no session with at least one non-warm-up assignment → `Infeasible("no_plan_fits")`.
4. **Ordering and numbers:** every sort has a total key ending in an id; arithmetic uses `int` and `Fraction`; values are rounded half-even to 4 places once, at serialisation; sets are serialised sorted.
5. **Digest:** `content_digest` = SHA-256 of the canonical JSON (sorted keys, no spaces, UTF-8) of the plan **without** `id`, session/assignment ids, `version`, `created_at`, done state and reasons. Same (ranking, citations, preferences, library) → same digest and byte-identical content (G04-03 d, ST-060 pass^3).

## 7. Domain events

Raised by the root, returned to the service, logged after commit as structured events with ids and counts only (no reason text, no names; NFR-057). No consumer in R1, so no outbox (judgment; CM-2 still applies when one appears).

| Event | Fields |
|---|---|
| `TrainingPlanGenerated` | `plan_id, owner_id, version, library_version, content_digest, source_match_ids, sessions, unfitted_count, limited_data` |
| `SessionMarkedDone` / `SessionDoneUndone` | `plan_id, session_id, op_id` (done only), `version` |
| `DrillSwapped` | `plan_id, assignment_id, from_drill, to_drill, metric_id, reason_given: bool, version` |

## 8. Deletion (ADR 0042; deletion-and-purge.md)

- **Account deleted** (`DELETE /me`): plan routes answer 401 at once (the sessions are gone). The purge calls `racket.coaching.public.purge_account(session, account_id)` before the account row: every plan, session, assignment, citation rally, source-match and done-op row of the account goes (rows only; Coaching stores no object). The purge inventory test (IT-03-06 form) gains these tables.
- **Match deleted** (`DELETE /matches/{id}`): from the request on, `matches.public.live_ids` no longer returns it, so `GET /me/plan` sees a plan whose `source_match_ids` include a non-live match as **stale**. The purge calls `racket.coaching.public.purge_match(session, match_id)`: it deletes the citation-rally and source-match rows naming the match and sets `stale = true` on those plans, so no `match_id` row survives (G03-03 a).
- **Stale on read:** `GET /me/plan` regenerates the plan with its stored preferences in the same request (NFR-019 budget) and answers it with `regenerated: "source_match_deleted"`; done marks are not carried over (judgment; the product-manager may ask for carry-over by drill in R2). If no tagged match remains, the stale plan is deleted and the answer is 404 `no_plan`. A cited rally of a deleted match is never served.

## 9. Persistence and migration numbers

| Migration | Ticket | Content |
|---|---|---|
| `0018_training_plans` | ST-061a | `training_plans` (one per `owner_id`, unique), `plan_sessions`, `plan_assignments` (citation columns), `plan_citation_rallies (assignment_id, match_id, rally_id, position)`, `plan_source_matches (plan_id, match_id)`, `plan_done_ops (account_id, op_id, session_id, plan_version, created_at; unique (account_id, op_id))`; `owner_id`/`account_id` on every root; app-role grants as 0012/0013, no media-worker access |
| `0019_age_confirmation` | ST-068a | `accounts.age_confirmed_at` (nullable); `pending_sign_ins` (token hash, `email_key`, expiry; no address, no birth date) |
| `0020_review_video_retention` | ST-069 | `accounts.review_video_days` (30, 90, 365 or null = until I delete; default 90) |
| `0021_training_consent` | ST-070 | `accounts.training_opt_in` (default false), `training_consent_events (account_id, opt_in, at)` |

ST-072a needs **no migration**: the rate limit reuses `rate_limit_events` and usage is computed from existing media and upload rows. The chain is serial (ST-061a → ST-068a → ST-069 → ST-070); a ticket that finds its number taken stops and asks the principal-engineer (no renumbering of a merged migration).

## 10. Tests that pin this design

| Rule | Test (owner ticket) |
|---|---|
| no framework import in `coaching/*/domain` | `test_architecture.py` (exists) |
| Coaching reads Analytics only through `public` | `test_architecture_context_imports.py` (exists) |
| ranking, conservation | `tests/unit/coaching/test_weakness.py`, IT-04-01 (ST-055) |
| invariants, determinism, property ≥ 1,000 | `test_training_plan.py`, IT-04-02a (ST-056); `racket-plan-eval` (ST-060) |
| citations equal stats and evidence | `test_citations.py`, IT-04-02b (ST-057) |
| round trip, owner filter, purge leaves 0 rows | IT-04-02c (ST-061a) |
| done idempotent, swap | IT-04-04, IT-04-05 (ST-062) |
