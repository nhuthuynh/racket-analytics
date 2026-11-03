# Retrospective: Sprint <NN> (<YYYY-MM-DD>)

<!--
Copy to docs/retros/<YYYY-MM-DD>-sprint-<NN>.md.
Facilitator: engineering-manager, or a neutral role (business-analyst or the main session) when the retro's focus is the EM-owned process after a difficult period [ASB/RPD-12]. Participants: every agent that worked in the sprint; the human product owner is invited.
Rules [EP/ENG-15]: pick one focus area per retro; rotate the format; every action item has an owner and a
deadline and goes into the backlog, prioritised for completion before the next retro. Blameless: discuss
systems, prompts and process, not individuals (judgment).
Citation prefixes: see docs/process/working-agreement.md §0. Label opinions "(judgment)".
-->

- **Sprint goal:** <copy from docs/sprints/sprint-<NN>.md>
- **Goal met?** Yes / Partly / No. <one line, with evidence>
- **Format used:** Timeline | 5 Whys | Fishbone | Focus | Mad/Sad/Glad [EP/ENG-15]
- **Focus area this retro:** <e.g. review loop, eval stability, estimation>
- **Participants:** <agent names, human>

## 1. Previous action items (review these first)

| # | Action | Owner | Due | Status (done / partly / not done) | Evidence |
|---|---|---|---|---|---|
| | | | | | |

## 2. Sprint facts (data before opinions)

| Measure | This sprint | Last sprint | Source |
|---|---|---|---|
| Stories committed / done | | | `docs/sprints/<NN>/status.json` |
| Change lead time (median) | | | working-agreement §10 [ASB/AGL-02] |
| Deployment frequency | | | working-agreement §10 [ASB/AGL-02] |
| Change fail rate | | | working-agreement §10 [ASB/AGL-02] |
| Failed deployment recovery time | | | working-agreement §10 [ASB/AGL-02] |
| Deployment rework rate | | | working-agreement §10 [ASB/AGL-02] |
| PR time-to-merge (avg) | | | [EP/ENG-19] |
| Cycle time, first commit to merge (median / max) | | | working-agreement §10 (ADR 0056) |
| Throughput (tickets merged) | | | working-agreement §10 (ADR 0056) |
| Work item age of open tickets (max) | | | working-agreement §10 (ADR 0056) |
| WIP limit breaches (count; reasons) | | | working-agreement §3 "Flow and WIP limits" |
| Cost per PR (median; sprint total), tokens and wall time | | | working-agreement §10 (ADR 0056); `decisions/<TICKET-ID>.md` |
| Median PR size (changed lines) | | | [EP/ENG-04] |
| Auto-fix iterations per PR (avg / max) | | | working-agreement §7 |
| Escalations to human | | | working-agreement §8 |
| Test suites: unit / integration / scenario / E2E pass rate | | | test report |
| Flaky / skipped / quarantined tests | | | test report |
| Coverage (changed code) vs target | | | testing-strategy §8 |
| Model eval regression (key metrics vs tolerance) | | | `docs/evals/` |
| Coaching LLM eval pass^k (from M5) | | | testing-strategy §7 |
| GPU-seconds per match-minute | | | spec §8 |
| SLO error budget remaining | | | [AQS/REL-02] |
| Accuracy of size estimates (planned vs actual) | | | [EP/ENG-15] |

## 3. What went well

-

## 4. What went wrong: mistakes and incidents

Each item needs a root cause, not just a symptom.

| # | What happened | Impact | Root cause (5 Whys or Fishbone) | Evidence (PR, log, test, ADR) |
|---|---|---|---|---|
| | | | | |

## 5. Lessons learned

State each lesson as a rule we will follow from now on, and say whether it changes a process doc, an agent prompt, a hook or a test.

| # | Lesson | Change it implies | Where (file) |
|---|---|---|---|
| | | | |

## 6. Agent-team health

- **Prompts and briefs.** Which agent briefs were unclear or overlapped? [EP/ENG-26]
- **Review quality.** Where did reviewers over-flag (causing over-engineering) or under-flag (letting defects escape)? [EP/ENG-24]
- **Transcripts.** Which transcripts were read, and what did they show? [DPA/AI-05]
- **Process rules.** Were any rules bypassed, such as test edits, missing evidence or skipped ADRs?

## 7. Action items

| # | Action | Owner (agent / human) | Due date | Backlog ID | Success measure |
|---|---|---|---|---|---|
| | | | | | |

## 7a. Requirement breakdown

Which FRs or NFRs reached development non-atomic or unmeasurable (see the atomic-breakdown items in `docs/process/definition-of-ready.md`), and what should the DoR change?

| # | FR/NFR ID | What was missing (rule split, negative example, metric, window, open clarification) | Found by (PR, review, test) | DoR change proposed |
|---|---|---|---|---|
| | | | | |

## 7b. Rules to remove

For each process rule added in the last two retros: is it still load-bearing (it prevented a failure this sprint, with evidence), or can it be dropped or moved into a hook, script or CI job? Every harness rule encodes an assumption that can go stale [ASB/ANT-18].

| # | Rule (file, section) | Added in | Prevented a failure this sprint? (evidence) | Keep / drop / move to a check |
|---|---|---|---|---|
| | | | | |

## 8. Decisions taken in this retro

- Process changes are made through a new or superseding ADR: <links>.
