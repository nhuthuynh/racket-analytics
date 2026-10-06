# 0031. ASVS 6.3.3: residual risk of the single-factor magic link, or passkeys in R1

- **Status:** **Accepted (PO, 2026-10-06): option 1**, with the conditions below and a re-review before any real-user beta opens. Recorded by the engineering-manager from the PO's own answer (`docs/requirements/po-input-2026-10-05.md`, addendum "Sprint 1 close decisions", row P2); no agent decided it.
- **Date:** 2026-10-05
- **Deciders:** human product owner (sole decider: accepting a security risk, ADR README "Risk and cost"; working-agreement escalation rules). Decided 2026-10-06 by the human product owner
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

**Chosen: option 1, accept the single-factor magic-link residual risk for R1** (human product owner, 2026-10-06). Input: security-privacy-engineer (threat model T-ML-13, S1-F1), engineering-manager and product-manager recommendations above.

Conditions (from option 1, binding):

1. No real-user beta opens before the PO re-reviews this ADR (gate **GATE-BETA-ASVS-6.3.3**, `docs/sprints/sprint-02.md`, next to ST-042 and ST-038). At that re-review the PO chooses again between option 1 (with a review date before general availability) and option 2 (passkeys).
2. The ADR 0025 session controls stay as built: single-use link valid 15 min, 30 d absolute / 7 d idle session limits, sign-out.
3. ASVS 6.3.3 stays recorded as not met in `docs/security/asvs-l2-checklist.md`. The security-privacy-engineer (owner of `docs/security/threat-model-sprint-01.md`) changes T-ML-13 / S1-F1 from **O** (open, undecided) to **accepted residual risk (ADR 0031, PO 2026-10-06), until the beta re-review**.

Effect: findings SEC-R4-S1-04 / BLK-ASVS-6.3.3 and QA-R2V-11 are decided (review-rounds.md, Sprint 2 review round 1). Nothing changes for Sprint 2 dev or internal use.

### Dated notes

- **2026-10-05, product-manager (sprint-close review round 2, SEC-R4-S1-04 / BLK-ASVS-6.3.3, QA-R2V-11). Not a decision.** Checked again for a PO answer and found none in the repo. `grep -n '6\.3\.3\|MFA\|passkey' docs/requirements/po-input-2026-10-05.md docs/decisions/0023-*.md` → no matches (rc=1). The only PO input is "accept all recommendations" for `open-questions.md`, which has no ASVS 6.3.3 question, so it cannot be read as an answer here. The product-manager does not record a PO answer the PO has not given, and does not accept the risk on the PO's behalf (Deciders line above). The questions are with the PO through the engineering-manager's single PO decision request, item **P2** (`docs/sprints/01/blockers.md`, row "PO decision request, sprint-close review round 2"). To make answering quick, the PO can reply with one line, which the product-manager will record here verbatim with the date: *"ADR 0031: option 1 for the first real-user beta, review date YYYY-MM-DD"* or *"ADR 0031: option 2 (passkeys before the real-user beta)"*. Until then there is no effect on Sprint 1 dev or internal use, and any real-user beta stays blocked. `python3 scripts/measure/open_defects.py docs/sprints/01/review-rounds.md` counts `SEC-R4-S1-04`/`BLK-ASVS-6.3.3` as one open major (parser fixed in `351488e`, PE-R2-S1-02).

- **2026-10-06, engineering-manager (Sprint 2 review round 1, SEC-R4-S1-04 / QA-R2V-11 / BLK-ASVS-6.3.3). Records the PO's decision.** The PO answered P2 in `docs/requirements/po-input-2026-10-05.md`, addendum "Sprint 1 close decisions (PO decision request P1–P4, blockers.md; answered 2026-10-06)", verbatim: "P2 ADR 0031 (ASVS 6.3.3) | **Option 1: accept the single-factor magic-link residual risk for R1**, with the conditions listed in ADR 0031. Re-review before any real-user beta opens. | ADR 0031 → Accepted (PO)". Status set to Accepted with the PO as decider; the security-privacy-engineer's input is the threat model above.

## Evidence

| Claim | Evidence | Type |
|---|---|---|
| Single factor only | ADR 0025; threat-model-sprint-01.md:41 (T-ML-13) | data |
| PO input does not cover it | `grep -n '6\.3\.3\|MFA\|passkey' docs/decisions/0023-*.md docs/requirements/po-input-2026-10-05.md` → no matches (SEC-R4-S1-04) | data |
| ASVS 6.3.3 is L2, owner security + PO | `docs/security/asvs-l2-checklist.md:196` | data |
| Size of a passkey story | judgment | judgment |
| PO decision, option 1 | `grep -n "P2 ADR 0031" docs/requirements/po-input-2026-10-05.md` → the addendum row quoted in the 2026-10-06 note | data |
