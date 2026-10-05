# Sprint 1 decision log

Small decisions, one dated row each (who, decision, evidence, reasoning). Append only; do not rewrite other rows.
Significant decisions go to `docs/decisions/` as ADRs.

| Date | Who | Decision | Evidence | Reasoning |
|---|---|---|---|---|
| 2026-10-05 | product-manager | Sprint 1 DoR item P1 closed: every committed story (ST-013..ST-018, ST-020..ST-025, SPIKE-06) is priority P1 for this sprint; ST-019 stays stretch. MoSCoW comes from the FRs (all Must, except FR-004 inside ST-015, which is Should) | sprint-01 §14.1 "Priority / milestone" lines; §14.5 P1 row | No PO answer changed scope ("accept all recommendations", ADR 0023), so the BA's FR-derived priorities stand. FR-004 stays inside ST-015 because the first-run screen and the guide share one flow (judgment) |
| 2026-10-05 | product-manager | Sprint 1 starts on 2026-10-05 instead of the planned 2026-10-19, because the PO said "start sprint 1". Planned dates in sprint-01.md are kept as the review/retro reference; `status.json` records `work_started` | PO message 2026-10-05 (ADR 0023 Evidence) | Same pattern as Sprint 0 (sprint-report §7: ran before its planned dates) |
