# Definition of Ready

- **Status:** Accepted (ADR 0001)
- **Date:** 2026-10-03
- **Basis:** Stories should be designed and ready before sprint planning [EP/ENG-15]. The checklist items below are (judgment) unless a citation is given. INVEST is unverified in our research [DPA Gaps], so it is not cited. Citation prefixes are explained in `working-agreement.md` §0.

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

## Domain truth
- [ ] Every pickleball rule or coaching fact in the story is verified by the domain coach, with its rulebook edition and rule number. Otherwise the story is **not Ready** [DOM G1, DOM Gaps].
- [ ] Terms are taken from the glossary in `ddd-guidelines.md`. New terms have been added.

## Design
- [ ] The bounded context(s) and aggregate(s) touched are identified [EP/ENG-12].
- [ ] For a new component, contract or cross-context change, a design doc or ADR is reviewed and approved [DPA/DESIGN-15].
- [ ] For UI, the flow and all states are specified by the principal-designer, with the HAX and WCAG checklists done [DPA/DESIGN-11, DPA/DESIGN-01].
- [ ] For security-relevant work (uploads, auth, personal data, LLM), the threat-model notes from security-privacy-engineer are attached.

## Delivery
- [ ] It is sized relatively, and is small enough to land in PRs of about 100 lines each [EP/ENG-15, EP/ENG-04].
- [ ] Dependencies are available: other stories, data, gold sets, credentials and licences. Any licence choice, such as AGPL components, is decided in an ADR [DOM/CV-05].
- [ ] It names its files, interfaces and end-to-end verification step [DPA/AI-08].
