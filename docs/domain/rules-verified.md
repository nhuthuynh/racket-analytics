# Verified pickleball rules

- **Owner:** pickleball-domain-coach
- **Created:** 2026-10-03 (Sprint 0 task, sprint-00 §4)
- **Edition being verified:** USA Pickleball Official Rulebook 2026 [DOM/DOMAIN-01] and the 2026 change document [DOM/DOMAIN-02]

## Status: NOTHING IS VERIFIED

**As of 2026-10-03, no pickleball rule is verified.** The table in §3 is empty on purpose.

- Every rule in `docs/research/domain-pickleball-cv.md` G1 (R1-R6) is **UNVERIFIED**.
- Every glossary term marked "(needs-verification)" in `docs/process/ddd-guidelines.md` §6 is also unverified.
- So is every row of the QD §2.2 scoring tables (SOD, SOS, F, C, RS).

**Nothing will be marked verified until the human product owner supplies the rulebook (OQ-01)** and the coach records, for each rule, the edition, the rule number and the exact wording, as in §3.

Until then:

- the only rules preset is `PROVISIONAL-UNVERIFIED`. No preset may be named after a federation, such as `USAP-2026` (ADR 0009 rule 4; NFR-003);
- every scenario that relies on a rule is tagged `@needs-verification`. Such scenarios never count toward a Must FR's Definition of Done (QD-QG-P5);
- every score sheet is labelled "unofficial scoring (rules not yet verified)" (FR-055);
- the coach will not supply rule numbers from memory. Background knowledge is not verification [DOM G1].

## 1. Why the rulebook could not be fetched (evidence)

| Date | Who | Attempt | Result |
|---|---|---|---|
| 2026-10-02 | research (DOM) | Fetch DOMAIN-01 / DOMAIN-02 | "egress blocked"; the documents exist per web search results only [DOM/DOMAIN-01, DOM/DOMAIN-02] |
| 2026-10-03 | pickleball-domain-coach | `curl -sS -o /dev/null -w "%{http_code}" --max-time 20 https://usapickleball.org/docs/rules/USAP-Official-Rulebook.pdf` | `curl: (56) CONNECT tunnel failed, response 403`. The agent proxy reports `usapickleball.org:443 — connect_rejected` (organisation egress policy) |
| 2026-10-03 | pickleball-domain-coach | same for `.../USAP-Rulebook-Change-Document.pdf` | same: 403 `connect_rejected` |

The coach does not keep retrying. Unblocking needs the human product owner: **OQ-01, "Supply the 2026 USA Pickleball Official Rulebook and change document (Blocking)"**. Need-by: as early as possible, and at the latest Sprint 3 planning (2026-11-16) for official scoring in R1 (sprint-00 §10). This is recorded in `docs/sprints/00/blockers.md`.

## 2. How a row gets verified (procedure)

1. The PO supplies the PDF(s). The coach records the file name, edition and SHA-256 in §4, so the source is pinned.
2. For each rule the product relies on (the queue in §5), the coach copies the **exact wording**, the **rule number** and the **edition** into §3.
3. If the wording differs from the provisional value in `PROVISIONAL-UNVERIFIED` / QD §2.2, this is a **requirement change**:
   - the senior-qa-engineer changes the test row and adds an ADR note on ADR 0009 [EP/ENG-28];
   - the implementer never makes this change.
4. The coach adds `@rule-<number>` to every scenario row that relies on the rule, and removes `@needs-verification` only when **all** rules that row relies on are verified (QD-TR-07).
5. When every row of a preset is verified, a new preset named for the edition (e.g. `USAP-2026`) may be created (ADR 0009 rule 4). The `PROVISIONAL-UNVERIFIED` preset is kept for matches already scored under it (sprint-01 §7.7, "A match keeps the rules version it was scored under").
6. Where sources conflict, for example USAP against another federation, or the rulebook against the change document, the coach writes an ADR and escalates to the EM and PO (agent definition).

## 3. Verified rules

| Rule (product name) | Edition | Rule number | Exact wording (quoted from the rulebook) | Verified by | Date | Rows / scenarios that rely on it |
|---|---|---|---|---|---|---|
| *(none; see "Status" above)* | | | | | | |

## 4. Source documents on file

| File | Edition | SHA-256 | Supplied by | Date |
|---|---|---|---|---|
| *(none; OQ-01 open)* | | | | |

## 5. Verification queue (what the product needs verified, in priority order)

All entries are **UNVERIFIED**. The "provisional value" column restates what the team assumes today, so that the comparison is quick when the rulebook arrives. It is **not** a claim about the rules.

| Priority | Product need | Provisional value (UNVERIFIED) | Research ref | Blocks |
|---|---|---|---|---|
| 1 | Side-out scoring: only the serving side scores | as stated | DOM G1 R2 | FR-041; SOD rows; AN-01..AN-03 definitions |
| 2 | Game target and margin | 11, win by 2 | DOM G1 R2 | FR-040 preset; SOD-07..SOD-11 |
| 3 | Doubles server number and first-service exception | game starts "0-0-2"; server 1 then server 2; then side-out | DOM G1 R6 | SOD-01..SOD-04, SOD-10; AN-03 "service turn" |
| 4 | Score call format | three numbers in doubles: serving score, receiving score, server number | DOM G1 R6 | FR-048 (Sprint 2, ST-029) |
| 5 | Faults end the rally against the faulting side; subtype does not change the score | as stated | DOM G1 R4-R6; QD-RE-09 | FR-044; F-01..F-06; AN-05, AN-07 |
| 6 | Serving position follows the serving side's score (even = right) | as stated | DOM G1 R6 | "Server changes court" scenario (sprint-01 §7.8) |
| 7 | Singles serving court parity | serve from the right on an even score | DOM G1 R6 (by analogy, judgment) | FR-042 (Sprint 2, ST-035) |
| 8 | Match formats: best of 1 / 3; who serves first in game 2; end switches | inputs today (no rule claim) | — | FR-045 (b) |
| 9 | Rally scoring (provisional rule in 2026): target, rotation, game point | not modelled; option disabled | DOM G1 R3 | FR-043 (R2) |
| 10 | Two-bounce rule; NVZ volley rule; line calls | as stated | DOM G1 R4, R5, R6 | Fault subtype labels; R2 automatic fault detection |
