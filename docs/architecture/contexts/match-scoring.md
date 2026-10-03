# Canvas: Match & Scoring

- **Status:** Accepted (2026-10-03, principal-engineer). Includes Review & Correction (C4).
- **Code modules:** `racket.matches` (aggregate, commands, corrections, API), `racket.scoring` (application service around the rules engine)
- **Aggregates:** `Match` (root; owns `Rally` and `Shot`)

## Purpose
Keep the authoritative record of a match and its score under a specific rules edition, including every correction the player makes.

## Strategic classification
- **Domain:** Core. A trustworthy, correctable score sheet is the first promise (spec §1).
- **Business model role:** the trust anchor for everything downstream.
- **Evolution:** custom-built.

## Domain roles
Specification and audit: it guards score consistency per `rules_version`, and every correction is audited.

## Inbound communication
| From | What | Kind |
|---|---|---|
| Player | `CreateMatch(title, format)` (S0), `NameParticipants`, `ConfirmRallyOutcome`, `CorrectScore`, `CorrectShot` | commands |
| Capture & Media | `MatchUploaded`; `media_summary` for the read model | C/S (R2) |
| Vision Analysis | `EventTrack` through the **ACL** → `Rally` / `Shot` | R4 |
| Sport Plug-in | rules state machine and `RulesConfig` | Published Language (R5) |

## Outbound communication
| To | What | Kind |
|---|---|---|
| Analytics | `RallyScored`, `ScoreCorrected`, `ShotCorrected`, `MatchScored` (after commit, idempotent) | C/S events (R6) |
| Dataset & Labelling | corrections, only with consent | R9 |
| Player | read model "match detail" (`status`, `media`, score sheet) | API §5 |

## Ubiquitous language
Match, Game, Rally, Shot, Side, Rules version, Correction, `corrected_by_user`, Score sheet, Match status (`awaiting_upload`, `uploading`, `video_received`, `probe_failed`). The full glossary is in ddd-guidelines §6.

## Business decisions
- A new match starts in `awaiting_upload`. `mark_uploaded(media_asset_id)` is allowed once. `can_be_read_by(other)` is false (sprint-00 §5).
- The API `status` is a **read model**: Match lifecycle plus `video_ingest.media_summary`. The aggregate does not track upload bytes.
- Sprint 0 exception: `mark_uploaded` commits with upload completion (ADR 0011; hotspot H3).
- User corrections win over re-processing (ddd-guidelines §4.8). Corrections are audited.
- Scoring is a pure function: (state, rally outcome, `RulesConfig`) → new state (ADR 0009; NFR-079).

## Assumptions
- Doubles first, singles supported (spec §2).
- Every rule is **needs-verification** until the coach confirms it [DOM G1] (eventstorming H2).

## Verification metrics
- IT-00-01/02 and BOLA matrix green.
- Rules-engine coverage of 95% line and 90% branch, and mutation score of 85% or more (NFR-071, NFR-072).
- Golden replay is byte-identical (NFR-075).

## Open questions
- Rally scoring status in 2026 (DOM G1 R3).
- Official scoring claims (NFR-003; OQ-01).
