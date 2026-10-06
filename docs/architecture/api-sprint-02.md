# API contract: Sprint 2 (tagging, score sheet, corrections, rally video)

- **Status:** Accepted for Sprint 2 (principal-engineer, 2026-10-06; design review D1 of `match-aggregate.md`, outcome recorded there in §0). Written after the routes were built (blockers.md 2026-10-05, BE start on the Proposed design): this file states the contract the code at `40de20a` implements, with the D1 answers BE-D1-01..06, and changes nothing the FE, the harness or the tests already rely on except BE-D1-01 (§1.1). Changes go through a PR on this file reviewed by BE, FE and QA; `scripts/measure/tagcontract.py` (the harness mirror) changes in the same commit (ADR 0033 rule 2).
- **Owner:** principal-engineer. **Domain design:** `match-aggregate.md` (Accepted). **Security:** threat-model rows of ST-031 (audit) and ST-037 (media link) are acceptance criteria of those stories (ADR 0022 rule 4).
- **Stories:** ST-026, ST-027, ST-030, ST-031, ST-032, ST-034 (domain), ST-035 (singles, red until the preset exists), ST-037.
- **Builds on:** `api-sprint-00.md` and `api-sprint-01.md`. Everything there still holds (root path behind `/api`, `application/json`, UUIDv4 ids with 404 for malformed ids, closed request schemas, security headers, `Cache-Control: no-store`, Origin check on state-changing requests, session cookie).
- **Product-owner inputs:** ADR 0023, `po-input-2026-10-05.md`: scoring presets stay PROVISIONAL-UNVERIFIED, so every sheet says it is unofficial (FR-055).

## 1. Conventions

### 1.1 Error body: unchanged envelope (BE-D1-01)

Every refusal uses the api-sprint-00 §3 envelope, with `fields` on 422 only (api-sprint-01 §1.1):

```json
{"error": {"code": "stale_match", "message": "…", "support_ref": "ref_…"}}
```

There is **no top-level `code`**. Clients read `error.code` (and `error.fields[].code` on 422). The G02-01 harness (`scripts/measure/live_tagging.py` `_code()`) reads only this shape since this commit; a body of any other shape has no code. The FE client may drop its top-level-`code` fallback (`web/src/lib/api/client.ts`, routed to FE as a nit).

### 1.2 Optimistic lock: `If-Match` and `ETag` (BE-D1-02)

- Every command (§3) carries the scorebook `version` the client last saw in `If-Match`. Accepted forms: `3`, `"3"`, `W/"3"` (RFC 9110 entity tag, weak or strong; the bare integer is kept for the harness). At most 9 digits.
- Missing, malformed or not the current version → **409 `stale_match`**, nothing written. No 428: a missing header means "the client has not loaded the sheet", which the client handles exactly like a stale one (reload, then retry) (IT-02-04).
- Every command response and `GET …/score-sheet` send `ETag: "<version>"`.

### 1.3 Command responses (BE-D1-04)

Commands answer `{"version": <int>, "sheet": <Sheet>}`; the tag command adds `"rally_id"`. The sheet itself never carries the version, timestamps or correction ids, so a correction followed by an undo restores the sheet **byte for byte** under the canonical encoder (sorted keys, no spaces, UTF-8; C-04, NFR-075).

### 1.4 Ownership

Every route loads the match through the owner filter: another account's match, an unknown id and a malformed id all give **404 `not_found`** with the same body (I9, IT-02-05). A rally id that is malformed, unknown in this match, or withdrawn gives 404 `not_found` on the rally routes.

## 2. Sheet and history shapes

### 2.1 `Sheet` (ST-030; FR-049, FR-055)

```json
{"rules_version": "PROVISIONAL-UNVERIFIED", "unofficial": true,
 "label": "unofficial scoring (rules not yet verified)",
 "format": "doubles", "best_of": 3, "match_winner": null,
 "games": [{"number": 1, "first_serving_side": "A", "ends_switched": false,
            "rules_version": "PROVISIONAL-UNVERIFIED", "score_a": 11, "score_b": 7, "winner": "A"}],
 "rows":  [{"number": 1, "rally_id": "…", "game": 1, "start_ms": 1200, "end_ms": 9800,
            "winning_side": "A", "ending": "winner", "responsible_player": "A1",
            "fault_kind": null, "corrected_by_user": false,
            "serving_side": "A", "server": "A1", "score_before": "0-0-2", "score_after": "1-0-2",
            "marker": null}]}
```

- `unofficial` is `true` and `label` is the fixed text above while any rule of the preset is unverified (today always; ADR 0009, ADR 0023).
- `rows` are the **kept** (non-withdrawn) rallies, ordered by `start_ms`, then `seq`, grouped by game. `number` is the 1-based position among kept rallies of the whole match, so a withdrawn or undone tag leaves no gap (BE-D1-03).
- `marker` is `null` or `"needs_decision"`: the rally is after the end of its game, or in a game after an unfinished one (C-02, C-03; FR-053; `@needs-verification`). A marked row has `serving_side`, `server`, `score_before` and `score_after` all `null`; it is never scored and never deleted.
- `corrected_by_user` is derived: the rally has a correction or resolution that is not undone.
- `games[].score_*` and `winner` are `null` when the game cannot be scored (no preset for the (`rules_version`, `format`) pair, or an earlier game is unfinished). There is no silent default preset (BE-D1-05); commands on such a match are refused with 409 `rules_unavailable` (§4.1).

### 2.2 History item (ST-031; FR-052)

`GET …/corrections` → `{"items": [Item, …]}`, oldest first:

```json
{"id": "…", "kind": "correction", "rally_id": "…", "rally_number": 2, "game": 1,
 "field": "winning_side", "old_value": "A", "new_value": "B", "undoes": null,
 "at": "2026-10-06T09:14:03.120Z"}
```

`kind` ∈ `game_started`, `correction`, `withdrawal`, `resolution`, `undo`. `rally_number` is the rally's current `number` in the sheet, or `null` when the rally is withdrawn or the item is a game start. `old_value`/`new_value` hold tag values only (sides, slots, enums, integers, booleans): no names, no free text (IT-02-09). The audit table refuses UPDATE and DELETE (§5).

## 3. Routes

All routes need a session; state-changing ones also need an allowed `Origin`. Request bodies are closed JSON objects: an unknown key gives 422 with `{"field": null, "code": "unknown_field"}`; a body that is not an object gives 422 with `{"field": null, "code": "invalid"}`. A JSON list or object in a string field is a 422 with that field's code, never a 5xx (IT-02-10).

| Route | Body | Success | Refusals (besides 401, 403 Origin, 404 §1.4, 409 `stale_match`) | Story |
|---|---|---|---|---|
| `POST /matches/{id}/games` | `{"first_serving_side": "A"\|"B", "ends_switched": bool = false}` | 201 `{version, sheet}` | 409 `match_not_ready`, `game_not_over`, `match_over`; 422 `validation_failed` (`first_serving_side`/`side_invalid`, `ends_switched`/`invalid`) | ST-021, ST-027 |
| `POST /matches/{id}/rallies` | `{"start_ms", "end_ms", "ending", "winning_side", "responsible_player"?, "fault_kind"?}` | 201 `{version, rally_id, sheet}` | 409 `match_not_ready`, `game_not_started`, `decision_needed`, `game_over`, `match_over`; 422 `invalid_rally`, `invalid_outcome` (§4.2) | ST-026, ST-027 |
| `GET /matches/{id}/score-sheet` | none | 200 `Sheet`, `ETag` | none | ST-030 |
| `PATCH /matches/{id}/rallies/{rally_id}` | `{"field": <correctable>, "value": …}`, both required | 200 `{version, sheet}` | 422 `validation_failed` (`field`/`field_invalid`, `value`/`invalid`, `value`/`unchanged`), `invalid_rally`, `invalid_outcome` | ST-031, ST-032 |
| `POST /matches/{id}/undo` | none (any body is ignored) | 200 `{version, sheet}` | 409 `nothing_to_undo` | ST-031 |
| `GET /matches/{id}/corrections` | none | 200 `{"items": […]}` | none | ST-031 |
| `POST /matches/{id}/rallies/{rally_id}/resolution` | `{"decision": "withdraw" \| "move_to_next_game"}` | 200 `{version, sheet}` | 409 `game_not_started` (move with no next game); 422 `validation_failed` (`decision`/`decision_invalid`, `decision`/`not_needed`) | ST-032 (provisional) |
| `GET /matches/{id}/rallies/{rally_id}/media` | none | 200 `{"url", "expires_in_s", "start_ms": <rally start>}` | 409 `match_not_ready` | ST-037 |
| `GET /matches/{id}/video` | none | 200 `{"url", "expires_in_s", "start_ms": 0}` | 409 `match_not_ready` | ST-037, FR-UX-60 (T-01) |

Notes:

- **Correctable fields:** `winning_side`, `ending`, `responsible_player`, `fault_kind`, `start_ms`, `end_ms`, `withdrawn`. `{"field": "withdrawn", "value": true}` withdraws a kept rally (audited `withdrawal`); any other `withdrawn` value is 422 `value`/`invalid`. The whole outcome is re-validated after the change (§4.2), and changed times are re-checked against the video length and the other kept rallies. Later rallies are re-scored in the same step by the projection (FR-053, C-01).
- **Undo** reverses the newest change not yet undone: a correction, withdrawal, resolution or game start, or the newest tag (which becomes a withdrawal). Repeated undo walks back one change at a time; there is no redo in R1 (match-aggregate §8 Q4).
- **Resolution** applies only to a kept rally the sheet marks `needs_decision`; `move_to_next_game` needs the next game started first. There is no `keep_in_game` decision: a rally after the end of its game can never be scored in that game.
- **Order of checks** on a command: a missing or malformed `If-Match` (409 `stale_match`), then the body's shape and values (422), then, under the match row lock, the version (409 `stale_match`), the received video (`match_not_ready`), the game and match state, and last the rally times against the video length and the other kept rallies. Nothing is written on any refusal (IT-02-02).
- **Media links (ST-037):** a fresh presigned GET of the received original, signed for `S3_PUBLIC_ENDPOINT_URL` (the web origin behind `web-tls`, SRE-MEDIA), valid `MEDIA_URL_TTL_SECONDS` (default 300, never more than 900; NFR-055). Responses send `Cache-Control: no-store` and `Referrer-Policy: no-referrer`; the URL never carries the session token and is never logged (NFR-069). `GET /matches/{id}/media` keeps its api-sprint-00 §5.2 meaning (the probed facts), so the whole-video link is the separate `/video` route.

## 4. Codes added in Sprint 2

### 4.1 Error codes (`error.code`)

| Code | Status | Meaning |
|---|---|---|
| `stale_match` | 409 | `If-Match` missing, malformed or not the current version (§1.2) |
| `match_not_ready` | 409 | no received video yet (I1, NFR-060) |
| `game_not_started` | 409 | tag before the first game is started; move to a next game that is not started |
| `game_not_over` | 409 | start game *n*+1 while game *n* is not over in the projection |
| `game_over` | 409 | tag while the current game is over: start the next game |
| `match_over` | 409 | the match is decided, or all `best_of` games exist |
| `decision_needed` | 409 | a tag while rallies are marked `needs_decision` |
| `nothing_to_undo` | 409 | undo with no open change and no kept tag |
| `rules_unavailable` | 409 | the match's (`rules_version`, `format`) pair has no preset (today: singles until ST-035), so no game starts and no rally is tagged. Added for PE-S2-R1-05 (senior-backend-engineer); applies to `POST …/games` and `POST …/rallies` from the commit that lands it |
| `invalid_rally` | 422 | the rally's times (fields below) |
| `invalid_outcome` | 422 | the rally's outcome (fields below) |

### 4.2 Field codes (`error.fields[].code`, closed)

| Field | Codes |
|---|---|
| `start_ms`, `end_ms` | `time_invalid` (not an integer ms in range), `end_before_start` (on `end_ms`), `overlaps_rally` (on `start_ms`), `time_after_video` (on `end_ms`: the rally ends after the probed video length; `end_ms` is exclusive, so it may equal the length) |
| `ending` | `ending_invalid` (not one of `winner`, `unforced_error`, `forced_error`, `fault`, `replay`) |
| `winning_side` | `side_invalid`, `side_required`, `replay_has_no_side` |
| `responsible_player` | `player_invalid` (not a slot of the match format: doubles `A1 A2 B1 B2`, singles `A1 B1`), `replay_has_no_player`, `must_be_on_winning_side` (`winner`), `must_be_on_losing_side` (errors and faults) |
| `fault_kind` | `fault_kind_invalid` (not one of `serve`, `foot`, `two_bounce`, `nvz`, `other`), `only_for_fault` |
| `first_serving_side` | `side_invalid` |
| `field`, `value`, `decision` | `field_invalid`, `invalid`, `unchanged`, `decision_invalid`, `not_needed` |
| `null` | `unknown_field`, `invalid` |

The responsible-player side rules are provisional until the pickleball-domain-coach answers match-aggregate §8 Q2.

## 5. Persistence and audit (BE-D1-06)

Migrations `0009_match_scorebook` and `0010_corrections_append_only`, owned by `racket.matches` only. `match_rallies` has no score column (FR-049). `match_corrections` is append-only: `REVOKE UPDATE, DELETE, TRUNCATE … FROM PUBLIC` and a `BEFORE UPDATE OR DELETE` trigger that raises, except a `DELETE` with `pg_trigger_depth() > 1` (the `ON DELETE CASCADE` from deleting the match, Sprint 3 account/match deletion). A direct `DELETE` or `UPDATE` by the app role is refused (IT-02-03).

## 6. Status per route (BOLA matrix additions, IT-02-05)

| Route | No session | Other account | Owner |
|---|---|---|---|
| `POST …/games`, `POST …/rallies`, `PATCH …/rallies/{rally_id}`, `POST …/undo`, `POST …/rallies/{rally_id}/resolution` | 401 | 404 | 201/200 or §3 refusals |
| `GET …/score-sheet`, `GET …/corrections`, `GET …/rallies/{rally_id}/media`, `GET …/video` | 401 | 404 | 200 or §3 refusals |

The inventory test must see these 9 routes (BE-QA-01: the inventory walk was empty on FastAPI 0.142; QA owns it).

## 7. Configuration

`MEDIA_URL_TTL_SECONDS` (default 300, max 900) and `S3_PUBLIC_ENDPOINT_URL` (the web origin in dev and in the evidence stack, SRE-MEDIA). No other new setting.

## 8. Not decided here (owners)

| Item | Owner |
|---|---|
| C-02/C-03 resolution choices and which next-game rallies are marked (`@needs-verification`) | pickleball-domain-coach (match-aggregate §8 Q1) |
| Responsible-player side rules for forced errors | pickleball-domain-coach (§8 Q2) |
| Singles preset keyed by (`rules_version`, `format`) (ST-035) | senior-backend-engineer with QA (§8 Q3, BE-D1-05) |
| Sprint 2 screen flows (T-01, S-01, H-01, V-01) as a design file | principal-designer |
| Gaps (FR-047, ST-036) | principal-engineer, only if ST-036 is pulled in (§8 Q5) |
