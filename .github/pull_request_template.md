<!-- Conventional Commit title, e.g. "feat(matches): reject unknown match format (ST-006)" [EP/ENG-08].
     One concern, about 100 changed lines; > 400 needs the EM's `size-waiver` label [EP/ENG-04].
     Evidence = the exact command and its output, or a CI link. "It works" is not evidence [EP/ENG-24]. -->

## What and why

- **Story / requirement:** ST-___ · FR-___ / NFR-___
- **What changed:**
- **Why:**
- **Trade-offs and alternatives:**
- **ADR(s):** <!-- docs/decisions/NNNN-... for any significant decision, or "none" -->

## Evidence

<!-- Paste commands and outputs: red run first (TDD), then green. -->

```text
$ <command that failed first>
<output>

$ <command that passes now>
<output>
```

## Definition of Done (story level, docs/process/definition-of-done.md)

**Requirements**
- [ ] All Gherkin acceptance criteria for this story pass as executable tests
- [ ] Traceability updated (requirement -> story -> scenario -> test)

**Tests and TDD**
- [ ] Developed test-first (red -> green -> refactor), negative cases included [EP/ENG-18]
- [ ] Unit tests fast and isolated: no network or disk [EP/ENG-17]
- [ ] Integration tests cover each touched boundary (API <-> DB, queue, storage, worker) [EP/ENG-20]
- [ ] No existing test edited or deleted to make it pass; any test change approved by QA (`qa-approved-test-change`) [EP/ENG-28]
- [ ] Coverage targets met for changed code (testing-strategy §8)

**Build and code quality**
- [ ] Lint (Ruff/ESLint) and type checks clean [AQS/STACK-05]
- [ ] One concern, ~100 changed lines; refactors in a separate PR [EP/ENG-04]
- [ ] Conventional Commit message; this description is complete [EP/ENG-08, EP/ENG-07]

**Security and privacy** (when applicable; tick or write N/A)
- [ ] BOLA tests for each new endpoint that takes a resource ID [AQS/SEC-09]
- [ ] Upload, secret, logging and error-body rules hold [AQS/SEC-02, AQS/SEC-06, AQS/SEC-04]
- [ ] LLM output validated before use [AQS/SEC-08]

**Operability**
- [ ] Structured logs with correlation IDs, traces and metrics for new operations [AQS/OPS-03, AQS/OPS-06]

**UI** (when applicable)
- [ ] WCAG 2.2 AA: axe-core clean plus keyboard smoke test [DPA/DESIGN-01, DPA/DESIGN-14]
- [ ] Empty, loading, error, low-confidence and low-sample states built
- [ ] Each automatic call shows its confidence and can be corrected [DPA/DESIGN-11]

**Domain** (when applicable)
- [ ] Every pickleball rule used is verified with edition and rule number by the domain coach [DOM G1]

**Vision and ML** (when applicable)
- [ ] Eval report committed; no regression beyond tolerance on frozen gold sets; GPU cost metric recorded

**Review, decisions and merge**
- [ ] Required reviewers (working-agreement §6) have reviewed; no open Blocking findings [EP/ENG-03]
- [ ] Significant decisions recorded as ADRs with evidence and alternatives
- [ ] `ci-gate` is green

## Reviewers

<!-- Per working-agreement §6, e.g. QA + principal-engineer + security-privacy-engineer -->
