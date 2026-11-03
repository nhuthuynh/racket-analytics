# Definition of Done

- **Status:** Accepted (ADR 0001)
- **Date:** 2026-10-03
- **Basis:** The three-level DoD (story, sprint, release) from the Microsoft Code-With Engineering Playbook [EP/ENG-16], extended for this product. Citation prefixes are explained in `working-agreement.md` §0.

Evidence means the exact command and its output, or a link to the CI run, report or file. "It works" is not evidence [EP/ENG-24].

## Story level

A story is done only when every box is checked and the evidence is attached to the PR.

**Requirements**
- [ ] All Gherkin acceptance criteria pass as executable tests [EP/ENG-16, DPA/PROD-01].
- [ ] Traceability is updated, linking requirement -> story -> scenario -> test.

**Tests and TDD**
- [ ] New or changed logic was developed test-first (red -> green -> refactor), with negative cases included [EP/ENG-18].
- [ ] Unit tests are written and passing. They are fast and isolated, with no network or disk [EP/ENG-17].
- [ ] Integration tests cover each touched boundary (API <-> DB, queue, storage, worker) [EP/ENG-20].
- [ ] No existing test was edited or deleted to make it pass [EP/ENG-28]. Any test change is approved by the senior-qa-engineer and explained.
- [ ] Coverage targets in `testing-strategy.md` are met for changed code.

**Build and code quality**
- [ ] The build has no errors. Lint (Ruff/ESLint) and type checks are clean [EP/ENG-16, AQS/STACK-05].
- [ ] The PR is one concern, aims for about 100 production lines, and passes `check_pr_size.py`: 400 production lines or fewer, or the EM `size-waiver` decided while the PR is a draft. The size unit is defined in working-agreement §5 (ADR 0054, ADR 0052). Refactors are separate [EP/ENG-04].
- [ ] Conventional Commit message and a complete PR description (what, why, trade-offs, evidence) [EP/ENG-08, EP/ENG-07].

**Security and privacy (when applicable)**
- [ ] BOLA tests cover each new endpoint that takes a resource ID [AQS/SEC-09].
- [ ] Upload, secret, logging and error-body rules hold [AQS/SEC-02, AQS/SEC-06, AQS/SEC-04].
- [ ] LLM output is validated before it is used [AQS/SEC-08].

**Operability**
- [ ] Structured logs with correlation IDs, plus traces and metrics, exist for new operations [AQS/OPS-03, AQS/OPS-06, EP/ENG-20].

**UI (when applicable)**
- [ ] WCAG 2.2 AA checks pass: axe-core plus a keyboard smoke test [DPA/DESIGN-01, DPA/DESIGN-14].
- [ ] All states are built: empty, loading, error, low-confidence and low-sample.
- [ ] Each automatic call shows its confidence and can be corrected [DPA/DESIGN-11].

**Domain (when applicable)**
- [ ] Every pickleball rule used is verified with its edition and rule number by the domain coach [DOM G1].

**Vision and ML (when applicable)**
- [ ] The eval report is committed.
- [ ] No regression beyond tolerance on the frozen gold sets.
- [ ] The GPU cost metric is recorded [DOM/CV-08, DOM/CV-01].

**Review, decisions and merge**
- [ ] `scripts/ci/merge_ready.py` exits 0 on the PR head SHA, and the gated merge step merges the PR into `main`. The script checks `ci-gate` and every check run on that SHA (PO rule "CI first", 2026-10-08) and the latest principal-engineer and senior-* verdicts on it (PO decision 2026-10-07: "Merge only when both latest verdicts approve the current head SHA"). Who must review is set in working-agreement §6 [EP/ENG-03, EP/ENG-16].
- [ ] For code PRs (tier 1 and 2), the senior-qa-engineer has tested the PR head: ran the suites and checked each acceptance criterion against the sprint goal, and posted the result as its review verdict. In tier 1 that verdict fills the senior slot (PO 2026-11-03, ADR 0056; PO instruction 2026-10-31 quoted in `docs/requirements/po-input-2026-10-05.md`). `merge_ready.py` does not enforce the tiers yet.
- [ ] Each significant decision is an ADR with evidence and the alternatives considered. Smaller decisions go in `docs/sprints/<nn>/decisions/<TICKET-ID>.md`.

## Sprint level

- [ ] Every story in the sprint meets the story-level DoD [EP/ENG-16].
- [ ] A ticket that misses any story-level item is not reported as done or partly done and is not demoed. It returns to the backlog with its open items listed [ASB/AGL-01, a mirror of the Scrum Guide 2020]. An item that only a human can supply is reported as "not met: waiting on P-n" (PO decision P12).
- [ ] Functional, integration, performance and end-to-end suites pass on `main` [EP/ENG-16].
- [ ] Model and coaching regression eval suites pass, where relevant [EP/ENG-27].
- [ ] The sprint goal is demonstrated against its bullet list [EP/ENG-15].
- [ ] The test report, `status.json` and `progress.md` are up to date [EP/ENG-28].
- [ ] DORA metrics and PR time-to-merge are recorded [EP/ENG-21, EP/ENG-19].
- [ ] The retrospective is written with owned, dated action items, and the previous actions have been reviewed [EP/ENG-15].
- [ ] No untriaged Blocking security findings remain.

## Release level

- [ ] The sprint goals for the release are met [EP/ENG-16].
- [ ] The milestone's "Done when" criterion from spec §7 is shown with evidence. Example: M2 needs rally-segmentation F1 ≥ 90% on the frozen gold set, with the matching rule in NFR-006 (ADR 0004).
- [ ] SLOs and alerts are defined for the new user journeys [AQS/REL-01].
- [ ] Cost guardrails are active: quotas and billing alerts [AQS/SEC-10].
- [ ] Release notes are written and a rollback path is documented.
- [ ] **The human product owner marks the release ready for production** [EP/ENG-16].
