# 0032. Account identity is the normalised address, not the HMAC `email_key` (amends ADR 0025)

- **Status:** Proposed (principal-engineer). Needs the security-privacy-engineer's sign-off on the privacy part (storing the address for the life of the account) before it becomes Accepted. **Gate:** the implementation story below must be done before any non-dev deployment (staging, beta, prod).
- **Date:** 2026-10-05
- **Deciders:** principal-engineer, security-privacy-engineer
- **Consulted:** senior-backend-engineer (implementation), engineering-manager (routing)
- **Related:** findings SEC-R3-S1-01, SEC-R4-S1-01 (sprint-01 review rounds 3 and 4, carried to sprint-close review round 1); retro 1 action A4; ADR 0025 (magic link); ADR 0027 (mail worker); decision-log row 2026-10-05 "accounts store only `email_key`"; threat model `docs/security/threat-model-sprint-01.md` §1; api-sprint-01 §8

## Context and problem statement

ADR 0025 defines `email_key` as a **log pseudonym and rate-limit key**: the first 16 hex characters (64 bits) of HMAC-SHA256(`AUTH_EMAIL_KEY`, normalised address). The ST-013 code also uses it as the **account identity**:

- `backend/src/racket/players/domain.py:46-48`: `return hmac.new(secret, email.encode(), hashlib.sha256).hexdigest()[:16]`.
- `backend/src/racket/players/service.py` `_account_for` (lines 291-304 at `17c850d`) inserts `accounts(email_key=key)` with `ON CONFLICT (email_key) DO NOTHING` and otherwise selects by `email_key`.
- Migration `0005_magic_link_sign_in.py:24-25` adds `accounts.email_key` with `uq_accounts_email_key`. `players/models.py:15`: `# HMAC, never the address`. The account stores no address.

Consequences of the code as it is:

1. **Key rotation or loss orphans every account.** After `AUTH_EMAIL_KEY` changes, the next exchange computes a new key, finds no account and creates an empty one. The old matches stay owned by an account nobody can sign in to.
2. **A truncation collision merges two people.** Two addresses whose 64-bit prefixes collide sign in to one account (birthday bound about 2^32 addresses; unlikely at our scale, but a merge of two people's data is a privacy breach, not a glitch) (judgment).
3. **The docs say the opposite.** The threat model (§1) says the address is stored in `accounts.email` and that rotating `AUTH_EMAIL_KEY` "resets rate-limit keys only"; api-sprint-01 §8 says the key is for "rate limits, logs". Both are false for the code at `17c850d`.

A sign-in-by-email system cannot avoid knowing the address: the address *is* the credential's delivery channel and the only thing that ties a person to their account. The question is only where the identity lives.

## Decision drivers

- An account must survive rotation of any secret (a secret that must never rotate is a liability; ASVS 11.x key-management spirit) (judgment).
- No two people may ever share an account (privacy; flows D-4 still holds: no existence oracle).
- Data minimisation: store the address only where it is needed, never log it (NFR-057, NFR-069; T-ML-9).
- Simplest option that meets the requirement [AQS/ENG-04]; no new key-management machinery in Sprint 2.
- Later stories need the address anyway: account deletion confirmation (Sprint 3, FR-006/007) and any account-level email (decision-log row 2026-10-05 says such stories need a new decision; this is it).

## Considered options

1. **Store the normalised address on the account and key identity on it** (`accounts.email`, unique). `email_key` stays a pseudonym for logs and rate limits only, as ADR 0025 says. (chosen)
2. **Keep a keyed hash as the identity, but full 256-bit and versioned** (`accounts.email_hmac`, `key_version`; on rotation, look up by the old version and rewrite to the new one at the next sign-in, with `AUTH_EMAIL_KEY_PREVIOUS` configured).
3. **A separate, never-rotating identity key** (`ACCOUNT_IDENTITY_KEY`) with a full 256-bit HMAC.
4. **Keep the code; document the behaviour** ("never rotate `AUTH_EMAIL_KEY`").

## Decision outcome

Chosen option: **1**.

- **Schema (new migration, next free number):** `accounts.email VARCHAR(254) NULL UNIQUE` holding the address exactly as `normalise_email` returns it (trimmed, lower-cased). `accounts.email_key` stays (nullable, **no longer unique**) as the log pseudonym; drop `uq_accounts_email_key`.
- **Carrying the address to the exchange:** accounts are still created at the first successful exchange (ADR 0025, no accounts for typos). The `send_sign_in_link` job (ADR 0027) copies the address from its `sign_in_requests` outbox row onto the new `sign_in_links` row (`email VARCHAR(254) NULL`) in the transaction that stores the token hash, then deletes the outbox row as today. The exchange reads `email` from the link row it locks, sets `sign_in_links.email = NULL` in the same transaction that marks it used, and finds or creates the account **by `email`**. Expired unused links keep the address until the expiry sweep (ST-038 job, ≤ 24 h; judgment) deletes them; until that sweep exists, the exchange path also nulls `email` on any expired row it refuses.
- **Lookup:** `INSERT … ON CONFLICT (email) DO NOTHING RETURNING`, else `SELECT … WHERE email = :email`, the same race-free shape as today.
- **Legacy dev accounts** (created before the migration, `email IS NULL`): at an exchange that finds no account by address, claim the one legacy account whose `email_key` equals the current 16-hex key and whose `email IS NULL`, and set its `email`. Remove this fallback one release after the migration (judgment; dev data only, no non-dev deployment exists).
- **`AUTH_EMAIL_KEY` after this change:** pseudonym for `racket.security` logs, `mail.sent` logs and rate-limit keys only. Rotating it resets the per-address rate-limit windows and breaks correlation of log lines across the rotation; it never touches an account. Truncation stays at 64 bits for those uses (a collision there only shares a rate-limit bucket or a log pseudonym).
- **Never logged, never returned:** the address appears in no log line, no API response except the signed-in user's own `GET /me` if a later story adds it, and no error body (T-ML-9 unchanged).
- **Retention:** the address lives as long as the account; account deletion (Sprint 3, ASVS 7.4.2 follow-up in ADR 0025) deletes it with the account row. Legal obligations for US and AU remain unverified (NFR-070).

### Implementation story (routed, not built in this ADR)

`ST-013b` (senior-backend-engineer; QA owns the tests; security-privacy-engineer reviews), Sprint 2, before any non-dev deployment. Red tests first, negative cases first:

1. Rotation: sign in as `ivy@example.test` under key K1, restart with `AUTH_EMAIL_KEY=K2`, sign in again → **same** `account_id`, same matches visible. (Fails on `17c850d`: a new account is created.)
2. Collision: patch `email_key` to return a constant; two different addresses sign in → **two** accounts. (Fails on `17c850d`: one account.)
3. The used link row has `email IS NULL`; a refused expired link row has `email IS NULL`.
4. IT-01-03 log scan still finds no `@` in any log line.
5. A legacy account (`email IS NULL`, matching `email_key`) is claimed once and gets its `email`.

## Pros and cons of the options

### Option 1
- Good: identity can never be lost by a key operation and can never collide; one unique index; the docs (threat model §1) become true; matches what every later account feature needs.
- Bad: the address is stored for the life of the account (Medium-High asset, threat model §1) and briefly on the link row; a database dump now holds addresses. Mitigated by encryption at rest of the managed Postgres volume and backups (Sprint 4 infra ADR) and by never logging it (judgment).

### Option 2
- Good: no address at rest on the account.
- Bad: needs key versioning, a previous-key setting, a re-key on sign-in, and accounts whose owner never signs in during a rotation window are still orphaned when the old key is retired; losing the key still orphans everyone. The address must still be stored somewhere to send account-level email later. More machinery, weaker guarantee [AQS/ENG-04].

### Option 3
- Good: rotation of the log key no longer affects accounts.
- Bad: just moves the problem to a key that can never rotate and must never be lost; a full HMAC of an address under a known-once-leaked key is reversible by dictionary for common addresses, so the privacy gain over option 1 is small (judgment).

### Option 4
- Good: no work.
- Bad: leaves the collision merge; makes a secret unrotatable; contradicts ADR 0025. Rejected.

## Consequences

- ADR 0025's "Accounts" and "Logging" bullets stay as written for logs and rate limits; this ADR replaces the identity behaviour that the code added without an ADR. ADR 0025 carries a pointer to this ADR.
- The threat model §1 rows for "Account email address" and `AUTH_EMAIL_KEY` are corrected to say what the code does **today** and what changes with ST-013b (done in this change).
- Until ST-013b ships: **do not rotate `AUTH_EMAIL_KEY` in any environment that holds accounts you want to keep**, and no non-dev deployment (blockers.md row).
- security-privacy-engineer: confirm or change the retention and the "address on the link row until use or expiry" choice; record the sign-off by moving this ADR to Accepted.

## Evidence

| Claim | Evidence | Type |
|---|---|---|
| Identity is the 64-bit HMAC today | `domain.py:46-48`; `service.py` `_account_for`; migration 0005 lines 24-25 | code |
| The account holds no address | `players/models.py:9-17` (no `email` column on `accounts`); decision-log row 2026-10-05 senior-backend-engineer | code, decision |
| Docs claim the opposite | `threat-model-sprint-01.md` §1 rows "Account email address" and "`AUTH_EMAIL_KEY`" (before this change); `api-sprint-01.md` §8 `AUTH_EMAIL_KEY` row | docs |
| No ADR existed for the identity use | `grep -l 'SEC-R3-S1-01' docs/decisions/*.md` → only this file | search |
| Simplest option that meets the requirement | [AQS/ENG-04] | verified source |
| Birthday bound for 64 bits ≈ 2^32 | standard result (judgment on relevance) | judgment |
