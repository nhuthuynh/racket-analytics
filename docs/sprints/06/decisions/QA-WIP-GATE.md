# QA-WIP-GATE decisions (senior-qa-engineer, 2026-11-13)

Per-ticket decision file (working-agreement §3). Ticket: QA-WIP-GATE, "`scripts/measure/wip_gate.py`: refuses a ticket start at a full stage, from REST counts" (`docs/sprints/sprint-06.md` §3.2). Story PRC-06, atomic item PRC-12.1, goal metric G06-10, ADR 0056 decision 3. Review tier 1 (ADR 0056): principal-engineer plus the senior-qa-engineer test review; this PR is authored by the senior-qa-engineer, so its own APPROVE does not count (`merge_ready.py`) and the test review goes to another senior role.

## 1. Decisions

| Date | Role | Decision | Evidence | Reason |
|---|---|---|---|---|
| 2026-11-13 | senior-qa-engineer | **Stages come from REST only**: open PRs into main whose title starts `[ID]`; draft → in progress; `merge_ready.py` rc 0 on the head → awaiting merge; principal-engineer APPROVE on the head and no senior-qa-engineer verdict on it → awaiting QA; every other ready PR → in review | `infra/tests/test_wip_gate.py` stage tests | Working-agreement §3 stage table; the PRC-12.1 acceptance names draft state, verdicts on the head, QA verdict and merge-ready |
| 2026-11-13 | senior-qa-engineer | **Awaiting merge is `merge_ready.py` exit 0, not an approximation.** The first green build counted "PE + QA APPROVE on the head and a green `ci-gate`"; the live run then said `awaiting merge 8`, while `merge_ready.py` refused all 8 (#239, #238, #235, #232, #230, #224, #220, #218: tier 2 verdicts missing, missing owner rows, own-role APPROVE). A second red/green cycle replaced it | `GH_TOKEN=$(gh auth token) python3 scripts/measure/wip_gate.py --repo nhuthuynh/racket-analytics --stage start` → `In progress 3 · in review 3 · awaiting QA 0 · awaiting merge 8` (first build); `python3 scripts/ci/merge_ready.py --repo … --pr 220 --sha cd224e09…` → `merge-ready: no`, rc 1 | The gate must agree with the merge step; a stage the merge step does not recognise would block starts for the wrong reason |
| 2026-11-13 | senior-qa-engineer | `merge_ready.py` runs only for ready PRs with an APPROVE and no CHANGES REQUESTED on the head; any exit other than 0 or 1 makes the gate exit 2 (fail closed, ADR 0014) | `test_merge_ready_is_asked_only_with_an_approve_and_no_changes_on_the_head`, `test_the_script_fails_closed_when_merge_ready_cannot_answer` | `merge_ready.py` cannot pass without one APPROVE (tier 0 needs any one role), so asking only those PRs saves about eight REST calls per PR without changing the count |
| 2026-11-13 | senior-qa-engineer | **Start rule:** refused when the start would put "in progress" over 4, or when a later stage is full (in review ≥ 3, awaiting QA ≥ 2, awaiting merge ≥ 1); every blocking stage is named | `test_a_fourth_start_is_refused_while_three_prs_are_in_review`, `test_every_full_stage_is_named` | Working-agreement §3: "When a stage is at its limit, no ticket moves into it: the EM starts no new ticket"; sprint-06 §2.1 "full → the next agent turn reviews" |
| 2026-11-13 | senior-qa-engineer | The first output line is the stage-count line `flow_metrics.py` parses (`In progress N · in review N · awaiting QA N · awaiting merge N`), so the orchestrator can paste it into the EM status record | `test_the_stage_line_is_the_one_flow_metrics_parses` | One format for the status record and the G06-10 breach count |
| 2026-11-13 | senior-qa-engineer | "In progress" counts open draft ticket PRs. A ticket whose lane has commits but no draft PR yet is not counted; the orchestrator opens the draft at start (ADR 0052) to make it visible | REST has no ticket record other than the PR | Stated so the EM reads the count correctly |
| 2026-11-13 | senior-qa-engineer | `--merge-ready PATH` (default `scripts/ci/merge_ready.py`) lets the integration tests substitute a fake that exits 0/1 per PR; `merge_ready.py`'s own REST reads stay covered by `test_merge_ready*.py` | `infra/tests/wip_stub.py` `fake_merge_ready()` | Keeps this stub to the two endpoints the gate itself reads |

## 2. Live measurement

`GH_TOKEN=$(gh auth token) python3 scripts/measure/wip_gate.py --repo nhuthuynh/racket-analytics --stage start` on 2026-11-13 →

```
In progress 3 · in review 11 · awaiting QA 0 · awaiting merge 0
wip-gate: start refused: in review 11 of 3 (full)
```

rc 1. This matches the breach recorded at planning (sprint-06 §0.1, "WIP 12 in review vs limit 3"): no Sprint 6 build ticket should start until the drain clears review.

## 3. Cost per PR (ADR 0056 decision 1)

| Round | wall_time_min | total_cost_usd |
|---|---|---|
| Author build | not measured | not measured (the session does not expose per-ticket wall time or cost to the agent) |
