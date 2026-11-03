# Definition of Ready

- **Status:** Accepted (ADR 0001)
- **Date:** 2026-10-03
- **Basis:** Stories should be designed and ready before sprint planning [EP/ENG-15]. The checklist items below are (judgment) unless a citation is given. Stories meet INVEST: Independent, Negotiable, Valuable, Estimable, Small ("hours to a couple days") and Testable. DORA's small-batches capability recommends INVEST [ASB/AGL-04]; Bill Wake's original article could not be fetched, so it is not cited. Citation prefixes are explained in `working-agreement.md` §0.

Only a story that meets every item below may be pulled into a sprint. The business-analyst prepares it. The EM checks it at planning.

## Value and scope
- [ ] It has a story ID, a user value statement ("As a <player>, I want ..., so that ...") and a PM-assigned priority.
- [ ] It is linked to the FR/NFR IDs it implements, and to its spec milestone (M0-M7).
- [ ] Out-of-scope items are listed explicitly [DPA/AI-08].

## Acceptance criteria
- [ ] Acceptance criteria are written in declarative Gherkin. Scenarios are about 3-5 steps, and each `Then` asserts an observable outcome [DPA/PROD-01, DPA/PROD-02].
- [ ] Negative and edge cases are included. Data variations use `Scenario Outline` [DPA/PROD-01].
- [ ] NFRs that apply are measurable, covering security, performance, accessibility, reliability and cost [DPA/DESIGN-16, AQS/SEC-01, DPA/DESIGN-01, AQS/REL-01].
- [ ] The senior-qa-engineer agrees every criterion is testable, and has named the test level for each one.

### Atomic breakdown (stories pulled from Sprint 5 on)
These three items apply to stories pulled into Sprint 5 and later. The existing FR and NFR registers are not rewritten to meet them.
- [ ] Each FR the story implements is broken into atomic rules: one Gherkin `Rule:` per obligation, numbered `FR-nnn.R1`, `FR-nnn.R2`, ..., under the FR's existing ID (no new register rows). Each rule has at least one happy-path and one negative `Example` [ASB/REQ-01]. Writing the rule line as one When/While/If-then sentence (EARS style) is optional guidance (judgment).
- [ ] Each NFR that applies names one quality characteristic, a metric with its unit, how it is measured (tool, load, measuring point), the target, and a sample size or time window. An NFR with sub-targets is split into one item per target [ASB/REQ-12, ASB/REQ-19].
- [ ] No `[NEEDS CLARIFICATION: ...]` marker remains on scope, security or a domain rule, and every choice the business-analyst defaulted is listed under **Assumptions** in the story for PM and PO review [ASB/REQ-07].

## Domain truth
- [ ] Every pickleball rule or coaching fact in the story is verified by the domain coach, with its rulebook edition and rule number. Otherwise the story is **not Ready** [DOM G1, DOM Gaps].
- [ ] Terms are taken from the glossary in `ddd-guidelines.md`. New terms have been added.

## Design
- [ ] The bounded context(s) and aggregate(s) touched are identified [EP/ENG-12].
- [ ] For a new component, contract or cross-context change, a design doc or ADR is reviewed and approved [DPA/DESIGN-15].
- [ ] For UI, the flow and all states are specified by the principal-designer, with the HAX and WCAG checklists done [DPA/DESIGN-11, DPA/DESIGN-01].
- [ ] For security-relevant work (uploads, auth, personal data, LLM), the threat-model notes from security-privacy-engineer are attached.

## Delivery
- [ ] It is sized relatively and meets INVEST (see Basis): in particular Small (it lands in ticket PRs of about 100 production lines each, within the size unit of working-agreement §5) and Testable, with an independent test that shows its value on its own [EP/ENG-15, EP/ENG-04, ASB/AGL-04].
- [ ] Dependencies are available: other stories, data, gold sets, credentials and licences. Any licence choice, such as AGPL components, is decided in an ADR [DOM/CV-05].
- [ ] It names its files, interfaces and end-to-end verification step [DPA/AI-08].
