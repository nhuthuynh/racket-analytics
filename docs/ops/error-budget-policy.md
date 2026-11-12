# Error-budget policy for R1 (NFR-049.1) — DRAFT

**Status: Draft, waiting on the human product owner (P17, due 2026-11-12).** Written by the
sre-devops-engineer (ST-075c) from the outline in ADR 0057 §4. Nothing here is a PO decision;
the policy applies only after the PO accepts it, in the PO's own words, in a `po-input-*.md`.

SLOs and alerts: [`slo.md`](slo.md). Error budget = 100 % − SLO over a 30-day rolling window
[AQS/REL-01, AQS/REL-02]: 0.5 % for API availability, 1.0 % for upload completion. Planned
maintenance spends budget unless the PO accepts the window in advance [AQS/REL-02].

## Triggers

| Id | Trigger | Measured by |
|---|---|---|
| EB-1 | A 30-day error budget is fully spent at sprint planning | the `sli-metrics.md` query over `[30d]`, read by the sre-devops-engineer for the planning brief |
| EB-2 | A `severity="page"` SLO alert (`ApiAvailabilityFastBurn`, `UploadCompletionFastBurn`) is firing for more than 1 h | Prometheus `/api/v1/alerts` or the `ALERTS` series |
| EB-3 | More than half of a budget spent in one 7-day period (early warning, no freeze) | as EB-1 over `[7d]` |

## Actions

| Trigger | Action | Owner |
|---|---|---|
| EB-1 | The next sprint starts with reliability work on the cause before any new feature ticket (CI FIRST still comes first). Release-candidate sign-off waits until the budget is positive again or the PO accepts the risk in writing | engineering-manager at planning |
| EB-2 | Treat as an incident: a blameless postmortem with a cause and a test-first fix ticket; the ticket enters the current sprint ahead of feature work | sre-devops-engineer (incident lead), engineering-manager (ticket) |
| EB-3 | Raise it in the next daily sync; no freeze | sre-devops-engineer |

## Owners and data

- engineering-manager: applies the policy at sprint planning and records it in the sprint plan.
- sre-devops-engineer: the budget numbers, the alert history and the postmortems.
- Human product owner: accepts the policy and the SLO targets (P17), and decides any exception.

## Exceptions

A fault injected on purpose (the G05-02 drill, `slo.md` "Drill") runs only on a local test-mode
stack and never spends a real budget. An outage caused by a dependency outside our control still
spends budget; the PO may waive EB-1 for it in writing.

## Sources

The policy shape (trigger, action, owner) follows ADR 0057 §4 [AQS/REL-02 applied]. The SRE
workbook's error-budget policy is unverified (a Blocked source, `docs/research/architecture-quality-security.md`
gaps table); the wording above is judgment.
