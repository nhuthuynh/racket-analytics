# 0024. Match participants are per-match nickname slots inside the `Match` aggregate

- **Status:** Accepted
- **Date:** 2026-10-05
- **Deciders:** principal-engineer
- **Consulted:** security-privacy-engineer (data minimisation, third-party data), business-analyst (FR-005, FR-021), principal-designer (Q-03, Q-04)
- **Related:** ST-016; FR-005, FR-021; NFR-037, NFR-052, NFR-063; sprint-01 §5 `Participants`, §7.3, §14.3.4; DoR P4; OQ-15 (opponent scouting is Won't, ADR 0023); api-sprint-01 §5

## Context and problem statement

ST-016 asks the player to name who played: four nicknames (doubles) or two (singles), in sides A and B, with exactly one marked "me" (FR-005). Later stories need the slots: the score sheet names the server (Sprint 2), analytics split "my" rallies (R1), and vision maps tracks to players (R3). The question is what a participant **is** in the model: a value inside one match, or an identity that spans matches. The answer fixes the schema, the BOLA surface and how much personal data about third parties we keep.

## Decision drivers

- FR-005: nicknames only, no contact details; helper text discourages them.
- Data minimisation for third parties (spec §8; threat model: match titles and names are Medium class, NFR-063).
- Opponent profiles are Won't for the MVP (OQ-15, ADR 0023). Nothing may quietly build them.
- One aggregate per consistency boundary (ddd-guidelines); the score sheet and participants change together.
- Simplest design that meets the Sprint 1 to R1 needs [AQS/ENG-04].

## Considered options

1. **Per-match slots inside `Match`** (chosen): a value object `Participants` holding `MatchParticipant(slot, nickname, is_me)` for slots `A1, A2, B1, B2` (doubles) or `A1, B1` (singles). Stored as child rows of the match; no ID of their own.
2. **A cross-match `Player` entity** (an address book): each nickname becomes a `Player` owned by the account and referenced by ID from matches.
3. **Free text on the match** (one `players` string per side), parsed when needed.

## Decision outcome

Chosen option: **1**, because it meets FR-005 and every R1 consumer, keeps third-party data scoped to the one match it describes, and adds no new ID route (so no new BOLA surface).

Rules (enforced by `Participants`, `racket.matches.domain`; pure Python):

| Rule | Error code (api-sprint-01 §5.3) |
|---|---|
| Doubles: exactly `A1, A2, B1, B2`; singles: exactly `A1, B1`. A missing or extra slot on a side fails for that side | `side_needs_two_players` / `side_needs_one_player` (field `participants.side_a` or `participants.side_b`) |
| A slot appears at most once; slots outside the format's set are refused | `invalid_slot` |
| Exactly one participant has `is_me: true` | `choose_one_me` (field `participants.me`) |
| Nickname: NFC-normalised, trimmed, 1-30 characters, no control characters | `nickname_required` / `nickname_too_long` / `nickname_invalid` (field `participants.<slot>.nickname`) |
| Duplicate nicknames are allowed; the slot disambiguates (Q-04 shows "Ivy (Side A)") | — |
| A nickname that looks like an email address or phone number is **accepted**. `Participants.looks_like_contact_details(nickname)` is a pure predicate shared with the client rule in api-sprint-01 §5.4, so the FE shows the warning (§14.3.4) | — |

- Slot sides map to the engine's `Side`: `A1`/`A2` → `Side.A`, `B1`/`B2` → `Side.B`. The `me` slot tells analytics which side is the account holder's.
- Participants are set at match creation (`POST /matches`). Renaming after creation is a later command (`NameParticipants`, canvas); it replaces the whole set, never a single row, so the invariants are checked as one unit.
- Storage: table `match_participants(match_id FK ON DELETE CASCADE, slot, nickname, is_me, PRIMARY KEY (match_id, slot))`, read only through `racket.matches` (context map rule 1). Deleting a match deletes its participants (retention follows the match, ADR 0006).
- No participant has a public ID, a route or a cross-match link. Pre-filling "answers from the last match" (flows Q-03) is a client read of the user's own last match, not a stored relationship.

## Pros and cons of the options

### Option 1
- Good: smallest personal-data footprint; no new ID route; invariants live in one aggregate; trivial to delete with the match.
- Bad: the same friend typed in ten matches is ten unrelated rows; cross-match "partner" analytics need a later explicit linking feature (and its own privacy review).

### Option 2
- Good: stable identities for partner and opponent statistics.
- Bad: builds the opponent-profile store that OQ-15 made Won't, a new BOLA surface (`/players/{id}`), and long-lived third-party records with their own retention and deletion obligations [AQS/SEC-05] (NFR-063). Speculative for R1 [AQS/ENG-04].

### Option 3
- Good: no schema.
- Bad: no slot or "me" invariant; every consumer re-parses text; the error-summary pattern (NFR-037) cannot point to a field.

## Consequences

- Good: ST-016 BE work is small (one value object, one child table, an extended `POST /matches`); IT-01-05 tests it; the BOLA inventory gains no route (IT-01-11 diff stays empty for participants).
- Trade-offs accepted: no cross-match player identity in R1. A future "link players across matches" feature needs a new ADR, a privacy review and the PO's decision (OQ-15).
- Follow-up: the `Match` aggregate design doc (sprint-01 §4, principal-engineer, D6) uses these slots for serving positions and rally records.

## Evidence

| Claim | Evidence | Type |
|---|---|---|
| Nicknames only, exactly one "me", slots A1..B2 | FR-005; sprint-01 §3.1 ST-016 | requirement |
| Opponent profiles are Won't for the MVP | ADR 0023, OQ-15 | PO decision |
| Third-party names are Medium-class personal data | `docs/security/threat-model-v0.md` §1 | repo document |
| Validation messages and the warning-not-error rule | `docs/design/flows-sprint-01.md` Q-03, Q-04; sprint-01 §7.3, §14.3.4 | design |
| No new ID route means no new BOLA matrix entry | api-sprint-00 §7; `backend/tests/regression/bola.py` covers ID routes only | repo document |
| Duplicates allowed; 30-character limit; contact-detail heuristic | (judgment) | judgment |

## Confirmation

- Unit tests on `Participants` (sprint-01 §5, rows 1-3) and IT-01-05 are green.
- `GET /matches/{id}` returns `participants` in slot order; no route takes a participant ID (route inventory test).
