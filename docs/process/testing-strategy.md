# Testing Strategy

- **Status:** Accepted (ADR 0001)
- **Date:** 2026-10-03
- **Owner:** senior-qa-engineer
- **Citation prefixes:** see `working-agreement.md` §0.

## 1. Principles

1. **Code without tests is incomplete.** Unit tests gate every merge. Integration and end-to-end tests check that components work together across interfaces. Performance tests run regularly [EP/ENG-20].
2. **TDD by default.** Test-first is required for all deterministic logic.
3. **Tests are the specification.** Gherkin acceptance criteria become executable scenarios [DPA/PROD-01].
4. **Evidence over assertion.** Every "pass" claim includes the command that was run and its output [EP/ENG-24].
5. **Tests are immutable for implementers.** Removing or editing tests to make them pass is unacceptable [EP/ENG-28, DPA/AI-12].
6. **Writer/reviewer split.** Where practical, one agent writes the tests and another writes the code that makes them pass [DPA/AI-08].

## 2. Test pyramid

Martin Fowler's test pyramid and Google's test-size ratios are unverified in our research [EP Gaps, AQS Gaps]. The shape below is therefore **(judgment)**, built on the layered mix in [EP/ENG-20].

```
            /\        E2E (Playwright): a few critical journeys
           /  \       Scenario (Gherkin): one per acceptance criterion
          /----\      Integration: API<->DB, queue, storage, worker, LLM adapter
         /      \     Unit: domain, rules engine, analytics, geometry, event logic
        /--------\
   + Model-quality layer (separate): frozen gold sets, run per sprint and on demand
   + Coaching-LLM eval layer (separate): 20-50 cases, code + model graders
```

| Level | Scope | Tooling | When it runs | Budget |
|---|---|---|---|---|
| Unit | One behaviour of one unit. No I/O, sleeps or network. Arrange/Act/Assert. Third-party dependencies sit behind interfaces [EP/ENG-17] | pytest, Vitest/Jest (judgment) | Every edit (hook) and every PR | Each test runs in milliseconds; the whole suite in seconds [EP/ENG-17] |
| Integration | Real Postgres, S3-compatible store and queue in Docker Compose; never SQLite [AQS/OPS-05]. API tests use the httpx async client with `dependency_overrides` [AQS/STACK-01] | pytest, Testcontainers or Compose (judgment) | Every PR | Under 10 minutes (judgment) |
| Scenario (BDD) | Gherkin acceptance criteria executed against the API or UI | pytest-bdd (judgment) | Every PR | — |
| End-to-end | upload -> analysis (fixture clip) -> score sheet -> plan | Playwright [AQS/STACK-03] | On merge to `main`, nightly | — |
| Accessibility | axe-core automated checks plus a manual keyboard and screen-reader pass [DPA/DESIGN-14] | axe-core | Every UI PR; manual pass each sprint | — |
| Performance | API latency, upload throughput, pipeline minutes per match-minute [DPA/DESIGN-16] | Locust (ADR 0008; k6 rejected as AGPL-3.0) | Each sprint | — |
| Model quality | CV metrics on frozen gold sets (§6) | TrackEval, custom harness | Each sprint, and on any model change | — |
| LLM eval | Coaching plan quality (§7) | Code and model graders | Each sprint from M5, and on any prompt or model change | — |

## 3. TDD rules (red -> green -> refactor)

1. **Red:** write one failing test for the next small behaviour, and confirm it fails for the right reason. Write the negative test before the positive one [EP/ENG-18].
2. **Green:** write the smallest code that makes it pass [EP/ENG-18].
3. **Refactor:** improve the design while all tests stay green. Refactor-only changes go in their own PR [EP/ENG-18, EP/ENG-04].
4. **Bugs:** first write a failing test that reproduces the bug, then fix it [EP/ENG-24].
5. **Commits:** use `test:` for the red commit only if the team chooses to commit red tests on a branch (judgment). `main` is always green.
6. **Design for testability:** parameterize instead of hard-coding, log configuration at startup, propagate correlation IDs [EP/ENG-20]. Keep GPU and model inference behind interfaces so unit tests need no GPU [EP/ENG-17].
7. **Mocks:** use them sparingly. Prefer fakes injected through interfaces or `dependency_overrides` [EP/ENG-17, AQS/STACK-01].
8. **Positive control for every negative or security test (2026-10-05, retro 0 A3a).** A test that asserts something is refused, blocked or absent also shows, in the same file, that the same path accepts or finds the valid case (for example IT-00-10's `api` → `OPEN` control, IT-01-09's valid MP4). Red-first suites are also run once against a throwaway fake and at least one mutant, and the counts go in the decision log. Reason: retro 0 M7, a sandbox test passed for the wrong reason.
9. **Parsers of untrusted input get a property or fuzz test (2026-10-05, retro 0 A3b).** Every parser of a header, body field, file header or query value that comes from a client (for example `Upload-Offset`, `Upload-Length`, `Upload-Checksum`, `Upload-Metadata`, `traceparent`) has a Hypothesis test over arbitrary text and bytes: it returns a typed error or a valid value and never raises an unhandled exception. Negative tests come from the input domain, not only from the contract text. Reason: retro 0 M5.
10. **E2E specs never share mutable seeded state (2026-10-05, retro 0 A3c).** Each Playwright spec signs in as a user that no other spec changes, or creates its own data, so specs pass in any order and with `--repeat-each`. Reason: retro 0 M7 (QA-R1-04).

The pickleball rules engine is pure logic, which makes it the first TDD target. Its tests are table-driven `Scenario Outline`s and property-based tests: serve order, side-out, win-by-2 and rally scoring. These tests stay tagged `@needs-verification` until the domain coach records the rule numbers [DOM G1, EP implications].

## 4. Scenario (Gherkin) rules

These rules follow [DPA/PROD-01, DPA/PROD-02]:

- One `Feature` per capability, and one `Rule:` per business rule.
- Each `Scenario` illustrates one example in about 3-5 steps.
- `Background` is at most about 4 lines.
- Write declaratively. Ask: "Would this wording change if the implementation changed?" If yes, rewrite it.
- `Given` sets state; it does not describe user clicks.
- `Then` asserts outcomes the user can observe, not database rows.
- Tags: `@M0`..`@M7`, `@story-<id>`, `@nfr-<id>`, `@needs-verification`, `@slow` (judgment).

Example of the expected style (illustrative only, not a verified rule):

```gherkin
Feature: Manual match tagging produces a score sheet
  Rule: Only the serving side scores under side-out scoring   # @needs-verification (DOM G1 R2)
    Scenario Outline: Rally won by the receiving side causes no point
      Given a doubles match using side-out scoring at score "<before>"
      When the receiving side wins the rally
      Then the score sheet shows "<after>"
      Examples:
        | before | after |
        | ...    | ...   |
```

## 5. Mandatory regression suites

These come from the security and reliability research. They never get deleted.

| Suite | What it proves | Source |
|---|---|---|
| BOLA matrix | User B gets 404, the same response as for a missing resource, on every one of user A's resources, on every endpoint that takes an ID (FR-002, NFR-051) | [AQS/SEC-09, AQS/SEC-03] |
| Upload validation | Oversize uploads, wrong magic bytes and executable payloads are rejected. Storage names are generated | [AQS/SEC-02] |
| Upload resume | A HEAD then PATCH resumes the upload. An offset mismatch returns 409 and leaves the upload unchanged | [AQS/STACK-06] |
| Worker crash | Killing a worker mid-job requeues the job. The re-run leaves no duplicate Event or Shot rows | [AQS/OPS-02] |
| Fail closed | A failing stage rolls back its partial writes and marks the job failed | [AQS/SEC-12] |
| Trace header | A malformed `traceparent` does not break the request | [AQS/OPS-06] |
| Error bodies | Errors are generic, with no stack traces or secrets | [AQS/SEC-04] |
| LLM output | An unknown drill ID or metric from the LLM is rejected and the plan is not saved | [AQS/SEC-08] |
| Quotas | Rate limits and analysis quotas are enforced | [AQS/SEC-10] |

## 6. CV model evaluation sets as tests

The model-quality layer treats evaluation like tests [EP/ENG-27, DOM G8]:

- **Gold sets:**
  - The sets are versioned and frozen per sprint, built from M0 manual tags and labelled frames.
  - The split covers courts, lighting and camera heights (judgment).
  - **Nobody edits a gold set to improve a score.** Changes to a set need an ADR.
- **Metrics:**

| Stage | Metric | Source |
|---|---|---|
| Player tracking | HOTA (DetA, AssA), MOTA, IDF1, ID switches per match | TrackEval reference implementation [DOM/CV-08] |
| Ball tracking | Accuracy, precision, recall, F1 and FPS, visibility-aware, with a documented pixel threshold | [DOM/CV-01] (threshold is judgment) |
| Hit timing | Mean and p95 error in ms against labelled hits; audio and video fused | (judgment) |
| Court calibration | Reprojection error of known court lines, in pixels, below a documented threshold | (judgment from DOM G6) |
| Rally segmentation | F1 ≥ 90%; a rally matches when start and end are each within ±1.0 s and it is neither merged nor split (NFR-006) | spec M2 as made measurable by ADR 0004 (Proposed; OQ-09) |
| Auto scoring | (a) score-affecting corrections per game by an oracle user against gold, ≤ 2.0 (≤ 1.0 later); (b) ≤ 5 confirmations per game; (c) unflagged rallies ≥ 95% correct with pooled 95% CI lower bound ≥ 93% (NFR-007) | spec M3 as made measurable by ADR 0004 (Proposed; OQ-09) |
| Cost | GPU-seconds per match-minute, target about 1-2 GPU-min | spec §8 |

- **Two suites** [EP/ENG-27]:
  - *Regression evals* should pass at about 100% and gate merges. A metric may not drop by more than its tolerance. Tolerances are set in an ADR.
  - *Capability evals* track progress towards targets and do not gate merges.
- **Dataset licences:** SportsMOT is CC BY-NC, so it is used for evaluation only [DOM/CV-09].
- **Small fixtures:** unit and integration tests use short fixture clips with known expected events and ID switches, so CI stays fast.

## 7. Coaching LLM evals

These start before M5 [DPA/AI-05]:

- 20-50 player profiles drawn from real tagged matches [DPA/AI-05, AQS/AI-03].
- **Code graders:**
  - every drill ID exists in the library;
  - every drill cites a metric;
  - the plan fits the time the player has available.
- **Model grader:** scores relevance and clarity against a rubric. The rubric is calibrated by the domain coach against human grades [DPA/AI-05].
- **Consistency:** report pass^k for consistency and pass@k for exploratory changes. Read the transcripts [DPA/AI-05].

## 8. Coverage targets (judgment)

No verified source prescribes coverage numbers, so these are the team's own choices and are reviewed at retros:

| Area | Line coverage | Branch coverage |
|---|---|---|
| Rules engine and domain aggregates | ≥ 95% | ≥ 90% |
| Analytics and coaching services | ≥ 90% | — |
| API routers and services | ≥ 85% | — |
| Worker deterministic code (geometry, events, segmentation) | ≥ 85% | — |
| Frontend components and hooks | ≥ 80% | — |

- Coverage of model weights and notebooks is not measured. The eval sets cover them instead.
- Coverage is a floor, not a goal. Reviewers check that tests are meaningful [AQS/ENG-04].

## 9. Flaky and skipped tests

- A flaky test is quarantined within one day. It gets an owner, an issue and a fix-by date, and quarantine must not exceed one sprint (judgment).
- A skipped test needs a linked issue and a reason. Skipped tests are listed in the sprint test report.
