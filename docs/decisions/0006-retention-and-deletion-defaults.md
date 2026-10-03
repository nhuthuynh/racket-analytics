# 0006. Interim retention, expiry and deletion defaults (pending legal review)

- **Status:** Proposed. This is an escalation to the human product owner (OQ-07). The legal adequacy of every window is unverified.
- **Date:** 2026-10-03
- **Deciders:** business-analyst (proposer); security-privacy-engineer (reviewer); human product owner (approver)
- **Consulted:** product-manager (PROD US-103, US-104, US-202), principal-engineer, sre-devops-engineer, security-privacy-engineer (ENG §4.6, §6.1, ENG-FR-01), principal-designer (DES FR-UX-31, FR-UX-90)
- **Related:** FR-006, FR-007, FR-008, FR-024, FR-089; NFR-063, NFR-066, NFR-070; conflicts K13, K14, K15

## Context and problem statement

The spec requires private-by-default videos, explicit sharing and retention controls (spec §8). The brainstorms proposed conflicting windows:

| Item | PROD | ENG |
|---|---|---|
| Abandoned uploads | 7 days | 24 h |
| Match deletion | hidden in 1 min, unrecoverable in 30 days | all rows and objects gone in 7 days |
| Video retention | user choice of 30/90/365 days or until deleted, default 90 | originals deleted 30 days after analysis; 720p proxy kept while the match exists |

Storage is a major cost: about 31 TB rolling if originals are kept 30 days at the ENG design point (ENG §4.3, judgment). Privacy law is unverified [AQS G3.5].

## Decision drivers

- Scheduled deletion of unneeded sensitive data [AQS/SEC-05] 14.2.7, and classification with per-class retention [AQS/SEC-05] 14.1.1-14.1.2.
- Data minimisation: take the stricter window where both are workable (judgment).
- User control over their footage (spec §8).
- Re-processing needs source video (ENG-FR-08, FR-089).

## Considered options

1. **PROD's values.**
2. **ENG's values.**
3. **A layered combination:**
   - Original and mezzanine video are deleted 30 days after analysis completes (a system rule).
   - The user's retention setting (30/90/365 days or until deleted, default 90) applies to the 720p review video and clips.
   - Abandoned uploads are freed after 24 h.
   - A deleted match is hidden in ≤ 1 min and purged in ≤ 7 days.
4. **Do nothing:** keep everything until the user deletes it.

## Decision outcome

Chosen option: **Option 3, as an interim default until the legal review (NFR-070).**

- It takes the stricter value wherever both proposals are workable: 24 h and 7 days.
- It keeps user choice where the user sees the effect, on the review video.
- It removes the largest objects (originals) on a fixed schedule.

## Pros and cons of the options

### Option 1: PROD
- Good: generous resume window and user choice.
- Bad: keeps up to 10 GB partial uploads for 7 days. The 30-day deletion tail is longer than needed.

### Option 2: ENG
- Good: lowest storage and exposure.
- Bad: no user control over review video. That weakens the spec §8 "retention controls".

### Option 3: layered
- Good: both concerns are met, and the windows are configurable.
- Bad: re-processing a match more than 30 days old must use the 720p proxy (lower accuracy) or is unavailable. The PO must accept this. A user returning after 24 h cannot resume a partial upload.

### Option 4: keep everything
- Bad: contradicts [AQS/SEC-05] 14.2.7 and the cost model.

## Consequences

- FR-006/008/024 and NFR-066 carry these windows as configuration.
- The retention job is integration-tested: delete, then assert that storage and DB are empty.
- The legal review may supersede any value.

## Evidence

| Claim | Evidence | Type |
|---|---|---|
| Scheduled automatic deletion of unneeded sensitive data | [AQS/SEC-05] 14.2.7 | verified source |
| Classify data and document retention per class | [AQS/SEC-05] 14.1.1, 14.1.2 | verified source |
| tus expiration extension for abandoned uploads | [AQS/STACK-06] | verified source |
| Privacy law (GDPR, minors, storage limitation) | [AQS G3.5], unverified | gap; escalated |
| Storage volume estimate (~31 TB rolling) | ENG §4.3 | judgment |
| The specific windows (24 h, 1 min, 7 d, 30 d, 90 d) | — | judgment |

## Confirmation

- NFR-066 integration tests pass.
- The PO answers OQ-07.
- The legal-review ADR (NFR-070) confirms or supersedes this decision.

## Notes
