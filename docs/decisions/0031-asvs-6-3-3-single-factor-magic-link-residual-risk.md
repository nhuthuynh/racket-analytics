# 0031. ASVS 6.3.3: residual risk of the single-factor magic link, or passkeys in R1

- **Status:** Proposed. **Awaiting the human product owner.** No agent may mark this Accepted; only the PO's own answer, recorded here as a dated note, decides it.
- **Date:** 2026-10-05
- **Deciders:** human product owner (sole decider: accepting a security risk, ADR README "Risk and cost"; working-agreement escalation rules)
- **Escalated by:** engineering-manager (review finding SEC-R4-S1-04, sprint-close review round 1)
- **Consulted:** security-privacy-engineer (threat-model-sprint-01 T-ML-13, S1-F1), principal-engineer (ADR 0025)
- **Related:** ADR 0025 (magic-link sign-in design); ADR 0023 and `docs/requirements/po-input-2026-10-05.md` (do not cover this question: `grep -n '6\.3\.3\|MFA\|passkey'` → no matches); `docs/sprints/01/blockers.md` row 1; `sprint-report.md` §6 decision D3; FR for sign-in (`functional-requirements.md`: "passkey or an email magic link")

## Context and problem statement

ASVS 5.0 requirement 6.3.3 (level 2) asks for multi-factor authentication, or a combination of single-factor mechanisms (`docs/security/asvs-l2-checklist.md:196`, owner "security + PO"). Sprint 1 ships one factor: an emailed, single-use magic link (ADR 0025). Passkeys are in the backlog, not in R1. The threat model records this as open residual risk T-ML-13 and finding S1-F1: "PO must accept or reject before any real-user beta". The PO input of 2026-10-05 ("accept all recommendations") folded into ADR 0023 does not mention MFA or passkeys, so this risk has no decision.

It does **not** block Sprint 1 development or internal use. It **blocks any real-user beta** until decided.

## Decision drivers

- An account holds match videos of the player and others, plus their email address (judgment: moderate impact of takeover).
- Email-inbox takeover is the single point of failure for a magic link (T-ML-13).
- Passwordless sign-in without a cognitive test is a product requirement (FR sign-in, NFR-A11Y-08); a passkey keeps that property.
- Cost: passkeys add a WebAuthn ceremony, recovery flow and device tests on iOS Safari and Android Chrome (judgment: about one M story plus device runs).

## Considered options

1. **Accept the residual risk for R1** in this ADR, with conditions: no real-user beta before the PO signs, session controls of ADR 0025 kept (single-use 15-min link, 30 d / 7 d session limits, sign-out), and a review date before general availability.
2. **Pull passkeys into R1** as an optional second sign-in path (passkey or link), with an ASVS 6.3.3 re-assessment after it ships.
3. **Do nothing** (leave undecided). Not acceptable under ADR 0030: the finding needs a disposition, and the beta stays blocked.

## Pros and cons

### Option 1
- Good: no added R1 scope; Sprint 1 design stays as built.
- Bad: ASVS L2 6.3.3 stays unmet; account security equals inbox security.

### Option 2
- Good: meets the intent of 6.3.3 for users who enrol a passkey; phishing-resistant.
- Bad: R1 scope grows (judgment: about one M story); needs real-device runs the sandbox cannot do (blockers.md SPIKE-06 row).

### Option 3
- Good: none.
- Bad: blocks the beta silently; repeats the Sprint 1 "no disposition" problem (ADR 0030).

## Recommendation (engineering-manager, judgment; not a decision)

Option 1 for development and internal use now, as `sprint-report.md` §6 D3 proposes, **and** the PO decides between options 1 and 2 before the real-user beta is planned. The EM does not decide this: accepting a security risk belongs to the PO.

## Recommendation (product-manager, judgment; not a decision)

Added 2026-10-05 in sprint-close review round 1 (finding BLK-ASVS-6.3.3). The product-manager is the PO's proxy but does not accept security risk (role file: "escalate ... anything legal/privacy" to the human PO; this ADR's Deciders line).

- **Now (dev and internal use):** option 1, same as the EM. Nothing in Sprint 1 reaches real users.
- **Before a real-user beta:** option 2 (passkeys as an optional second sign-in path), because the sign-in FR already names "a passkey or an email magic link" (`functional-requirements.md:80`, FR-UX-01, NFR-A11Y-08), so option 2 finishes an existing requirement rather than adding scope, and the accounts hold match videos of the player and others (judgment).
- **Fallback if the PO wants the beta before passkeys ship:** option 1 with the listed conditions, limited to an invite-only beta, and a review date before general availability.

Questions for the PO: (a) option 1 or option 2 for the first real-user beta; (b) if option 1, the review date.

## Decision outcome

**Pending.** The PO's answer goes here as a dated note naming the PO as decider. Until then T-ML-13 / S1-F1 stay **O** (open) and `blockers.md` row 1 stays Open.

## Evidence

| Claim | Evidence | Type |
|---|---|---|
| Single factor only | ADR 0025; threat-model-sprint-01.md:41 (T-ML-13) | data |
| PO input does not cover it | `grep -n '6\.3\.3\|MFA\|passkey' docs/decisions/0023-*.md docs/requirements/po-input-2026-10-05.md` → no matches (SEC-R4-S1-04) | data |
| ASVS 6.3.3 is L2, owner security + PO | `docs/security/asvs-l2-checklist.md:196` | data |
| Size of a passkey story | judgment | judgment |
