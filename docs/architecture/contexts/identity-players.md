# Canvas: Identity & Players

- **Status:** Accepted (2026-10-03, principal-engineer; reviewed against threat model v0)
- **Code module:** `racket.players` (the dev identity provider lives here, behind `DEV_IDENTITY_ENABLED`)

## Purpose
Know who the user is, keep their session, and hold the player and opponent records they own. Every other context asks this one "who is calling?". The answer is used to scope every resource to its owner.

## Strategic classification
- **Domain:** Generic. Authentication and profiles are not a differentiator.
- **Business model role:** compliance enabler (privacy, minors, third parties).
- **Evolution:** commodity. Sign-in uses passkeys or magic links (FR-001), with no custom crypto.

## Domain roles
Gateway and specification: it publishes `current_account`, the ownership pattern used everywhere (R1).

## Inbound communication
| From | What | Kind |
|---|---|---|
| Player (browser) | `POST /dev/sign-in` (S0), magic link and passkey (S1), `POST /auth/sign-out`, `GET /me` | commands / query |
| Player | `ConfirmAge`, `AcknowledgeFootageNotice` (FR-003), `NameParticipants` (FR-005), `CreateOpponentProfile` | commands |

## Outbound communication
| To | What | Kind |
|---|---|---|
| Every context | `current_account` → `AccountId` or 401; owner-scoped loading pattern | OHS (R1) |
| Dataset & Labelling | `TrainingConsentGranted/Revoked` is raised here and consumed there | event |
| Security log | `auth.sign_in`, `auth.sign_out`, `authz.denied` (no PII) | log [AQS/SEC-04 16.3.1-16.3.2] |

## Ubiquitous language
Account, Session, Player profile, Opponent profile (private to its creator), Nickname, Age confirmation, Footage notice, Dev identity provider (dev/test only).

## Business decisions
- Every resource is private to its owner. Another user gets the same "not found" as for a missing resource (FR-002, NFR-051, NFR-064) [AQS/SEC-09].
- An opponent profile is visible only to its creator [AQS/SEC-03 8.2.2].
- Sessions use opaque random tokens stored hashed. Cookies are `HttpOnly`, `SameSite=Lax`, and `__Host-`/`Secure` outside tests (api-sprint-00 §2).
- The dev identity provider cannot run with `APP_ENV=prod`; startup refuses it (ST-006).
- No face recognition and no inferred attributes (NFR-065).

## Assumptions
- One person per account; no team accounts in R1 (judgment).
- An email address is the only contact data collected (FR-001); nicknames are free text and may be real names (judgment, so they are classed Medium, NFR-063).

## Verification metrics
- BOLA matrix coverage 100% and inventory diff empty (NFR-051).
- 0 prod starts with the dev provider (Settings test).
- 100% of sign-in attempts logged; 0 tokens or emails in logs (NFR-057, NFR-069; IT-00-15).

## Open questions
- Legal basis for minors and third parties (NFR-070, OQ-05): **unverified**, for the PO.
- Session lifetimes for real sign-in (ASVS 7.1.1) are decided in Sprint 1 with the security-privacy-engineer.
