# Traceability Matrix

- **Status:** Baselined draft v1
- **Date:** 2026-10-03
- **Author:** business-analyst
- **Chain:** requirement → epic → sprint → story → test level → test file.
  - **Sprint assignments added 2026-10-03 by the engineering-manager** from `docs/sprints/roadmap.md` (ADR 0007). `S0`..`S9` are the sprints in the roadmap calendar; `R3 (S10-S12)` and `Later` are outline only and planned just in time. Story IDs (`ST-nnn`) exist for Sprints 0-2 only (§6). "part a" marks the engine-mechanics part of a rules FR that is Ready now; the preset values wait for OQ-01 (ADR 0009).
  - Test files for Sprints 0-2 are the `tests/features/*.feature` files named in §6; the business-analyst confirms each path when the test lands.
  - The DoD requires this chain to be complete for every merged story [process/definition-of-done.md].
  - Stories and test files are filled in as sprints are planned and executed.
- **Generated from** the `Priority`, `Release` and `Status` lines of `functional-requirements.md` and the tables of `non-functional-requirements.md`. Regenerate after any edit; do not hand-edit the counts.

## 1. Epics

The epics come from PROD §5. E16 is added by the BA (judgment), because many NFRs (CI gates, observability, SLOs, dev/prod parity) belong to no product epic. E13 and E14 have no FRs in the MVP; they are listed as non-goals in `functional-requirements.md` §J.

| Epic | Name | Release | MoSCoW (MVP) |
|---|---|---|---|
| E1 | Account and privacy foundation | R1 | Must |
| E2 | Capture and upload | R1 | Must |
| E3 | Rules engine and score sheet | R1 | Must (blocked on rule verification for "official") |
| E4 | Quick Tag, Full Tag and corrections | R1 | Must |
| E5 | Starter stats dashboard and evidence | R1 | Must |
| E6 | Rules-only general plan and drill library | R1 | Must |
| E7 | Court calibration, player tracking, identity, positioning | R2 | Should |
| E8 | Ball, hit, bounce and rally detection; analysis jobs | R2 | Should |
| E9 | Automatic scoring, review queue, shot classification | R3 (review queue starts in R2) | Could (MVP) |
| E10 | Full analytics and clips | R3 | Could |
| E11 | LLM-written plan explanations and plan efficacy | R2 | Should |
| E12 | Opponent profiles and scouting | Later | Won't |
| E13 | Live mode | Later | Won't |
| E14 | Coach multi-player view | Later | Won't |
| E15 | Cost guardrails and usage quotas | R1 (quotas), R2 (GPU) | Must |
| E16 | Platform, quality gates and operability (BA addition) | R1 onward | Must |

Test-level key: U unit · I integration · S scenario (Gherkin) · E2E Playwright · A11y · P performance · MQ model-quality · LE coaching-LLM eval · OPS production SLI · R review/checklist · CI static check [testing-strategy §2].

## 2. Functional requirements

| FR | Title | Priority | Release | Status | Epic | Sprint | Test levels |
|---|---|---|---|---|---|---|---|
| FR-001 | Passwordless sign-in | Must | R1 | ready-candidate | E1 | S1 (ST-013) | U, I, E2E, A11y |
| FR-002 | Only the owner can access their resources | Must | R1 | ready-candidate | E1 | S0 (ST-006, match); extended every sprint | I (BOLA suite), S |
| FR-003 | Age confirmation and footage notice | Must (gate for any real-user beta) | R1 | needs-PO-decision (OQ-05) | E1 | S4 | U, S, E2E |
| FR-004 | First-run promise | Should | R1 | ready-candidate | E1 | S1 (ST-015) | U, S, E2E |
| FR-005 | Match participants by nickname | Must | R1 | ready-candidate | E1 | S1 (ST-016) | U, S, E2E |
| FR-006 | Delete a match and everything derived from it | Must | R1 | ready-candidate (windows needs-PO-decision, OQ-07) | E1 | S3 | I (deletion), S, E2E |
| FR-007 | Delete my account | Must | R1 | ready-candidate | E1 | S3 | I (deletion), S, E2E |
| FR-008 | Video retention setting | Should | R1 | needs-PO-decision (OQ-07) | E1 | S4 | I, S |
| FR-009 | Training-data consent | Should | R1 | needs-PO-decision (OQ-06) | E1 | S4 | U, I, S |
| FR-010 | Export my data | Could | R2 | ready-candidate | E1 | S9 | I, S |
| FR-011 | Sign out clears local data | Must | R1 | ready-candidate | E1 | S1 (ST-014) | E2E |
| FR-012 | Opponent profiles linked across matches | Won't (this MVP) | Later | deferred (privacy gate, OQ-15) | E12 | Later | I (BOLA), S |
| FR-020 | Capture guide | Must | R1 | ready-candidate | E2 | S1 (ST-015) | E2E, A11y, S |
| FR-021 | Match setup flow | Must | R1 | ready-candidate | E2 | S1 (ST-016) | E2E, A11y, S |
| FR-022 | Resumable upload | Must | R1 | ready-candidate | E2 | S0 (ST-008, core); S1 (ST-017) | I (upload-resume suite), E2E |
| FR-023 | Upload validation | Must | R1 | ready-candidate (caps confirmed by R-05) | E2 | S1 (ST-018, ST-025) | I (upload-validation suite), S, E2E |
| FR-024 | Abandoned uploads expire | Must | R1 | ready-candidate | E2 | S2 (ST-038) | I |
| FR-025 | Footage quality report | Should | R1 (fps, resolution, duration); R2 (court visibility) | ready-candidate | E2 | S0 (ST-009, facts); S1 (ST-019, stretch); S6 (court visibility) | I, S, E2E |
| FR-026 | Analysis level is explicit | Should | R2 | ready-candidate | E8 | S7 | I (fail-closed), S |
| FR-027 | Jump to the video moment | Must | R1 | ready-candidate | E5 | S2 (ST-037) | E2E, P |
| FR-029 | Analysis-ready notification | Should | R2 | ready-candidate | E8 | S7 | I, E2E |
| FR-030 | Extracted clips | Could | R3 | ready-candidate | E10 | R3 (S10-S12) | I, E2E |
| FR-031 | Framing check before the match | Could | R2 | ready-candidate | E7 | S6 (Could) | I, MQ |
| FR-040 | Versioned, parameterised rules engine | Must | R1 | needs-verification (preset values) | E3 | S1 (ST-020, part a); preset after OQ-01 | U (table-driven + property), S |
| FR-041 | Side-out doubles scoring | Must | R1 | needs-verification | E3 | S1 (ST-020, ST-023, part a); preset after OQ-01 | U (table-driven + property), S @needs-verification |
| FR-042 | Side-out singles scoring | Should | R1 | needs-verification | E3 | S2 (ST-035, ST-041, part a) | U (table-driven + property), S @needs-verification |
| FR-043 | Rally scoring option | Should | R2 | needs-verification (blocked) | E3 | S9 (only if verified) | U (table-driven + property), S @needs-verification |
| FR-044 | Faults end the rally against the faulting side | Must | R1 | needs-verification | E3 | S1 (ST-020, ST-023, part a) | U (table-driven + property), S @needs-verification |
| FR-045 | Match structure | Must | R1 | needs-verification | E3 | S1 (ST-021, part a) | U (table-driven + property), S @needs-verification |
| FR-046 | Start the score sheet mid-game | Must | R1 | needs-verification | E3 | S2 (ST-034, ST-041, part a) | U (table-driven + property), S @needs-verification |
| FR-047 | Gaps and resync | Should | R1 | ready-candidate | E3 | S2 (ST-036, stretch); else S3 | U, S |
| FR-048 | Score call and announcement | Must | R1 | needs-verification (call format) | E3 | S2 (ST-029) | U (snapshot), E2E, A11y |
| FR-049 | Score sheet | Must | R1 | ready-candidate (rule data needs-verification) | E3 | S2 (ST-026, ST-030) | U, S, E2E, A11y |
| FR-050 | Quick Tag a rally | Must | R1 | ready-candidate | E4 | S2 (ST-027) | S, E2E, A11y |
| FR-051 | Keyboard tagging | Must | R1 | ready-candidate | E4 | S2 (ST-028) | S, E2E, A11y |
| FR-052 | Undo and correction audit | Must | R1 | ready-candidate | E4 | S2 (ST-031) | U, I, S |
| FR-053 | Corrections replay the score and keep conflicting rallies | Must | R1 | needs-verification (game-end rule) | E4 | S2 (ST-032, ST-041, part a) | U (C-01..C-04), S |
| FR-054 | Show the consequences of a correction | Should | R1 | ready-candidate | E4 | S2 (ST-033, stretch); else S3 | S, E2E |
| FR-055 | "Unofficial scoring" label | Must | R1 | ready-candidate | E3 | S2 (ST-030) | S, E2E |
| FR-056 | User corrections survive re-processing | Must | R2 | ready-candidate | E9 | S8 | I, S |
| FR-057 | "Needs your eyes" review queue | Should | R2 (rally-level calls); Must in R3 | ready-candidate | E9 | S8 | S, E2E, A11y |
| FR-058 | Automatic scoring with confidence | Could (MVP); Must for R3 | R3 | ready-candidate (targets per ADR 0004) | E9 | R3 (S10-S12) | MQ, S |
| FR-059 | "Who is who" identity assignment | Should | R2 | ready-candidate | E7 | S6 | S, E2E, MQ (identity errors) |
| FR-060 | Correction reason | Could | R2 | ready-candidate | E9 | S8 (Could) | S |
| FR-061 | Full rally timeline with shots | Could | R3 | ready-candidate | E9 | R3 (S10-S12) | E2E, A11y |
| FR-080 | Analysis job lifecycle | Should | R2 (the queue itself exists in R1 for media probing) | ready-candidate | E8 | S0 (ST-007, queue base); S6 (lifecycle) | I (worker-crash, fail-closed suites), S |
| FR-081 | Media probe and normalisation | Must (probe, R1); Should (normalise, R2) | R1/R2 | ready-candidate | E2 | S0 (ST-009, probe); S6 (normalise) | I (fixture files) |
| FR-082 | Court calibration without dragging | Should | R2 | ready-candidate | E7 | S6 | MQ, E2E (no-drag), A11y, S |
| FR-083 | Player detection and tracking | Should | R2 | ready-candidate (licence decision ENG SPIKE-01, OQ-12) | E7 | S6 | MQ (HOTA), I (fixture clips) |
| FR-084 | Ball tracking with visibility | Should | R2 | ready-candidate | E8 | S7 | MQ, U (deterministic logic), I (fixture clips) |
| FR-085 | Hit detection from video and audio | Should | R2 | ready-candidate | E8 | S7 | MQ, U (deterministic logic), I (fixture clips) |
| FR-086 | Bounce detection and landing position | Should | R2 | ready-candidate | E8 | S7 | MQ, U (deterministic logic), I (fixture clips) |
| FR-087 | Automatic rally segmentation | Should | R2 | ready-candidate | E8 | S8 | MQ, U (deterministic logic), I (fixture clips) |
| FR-088 | Shot classification (faceted) | Could | R3 | needs-verification (definitions [DOM G2]) | E9 | R3 (S10-S12) | MQ (per-facet F1), S |
| FR-089 | Re-processing on a new pipeline version | Should | R2 | ready-candidate (depends on video retention, OQ-07) | E9 | S8 | I, S |
| FR-090 | Confidence on every automatic value | Should | R2 | needs-PO-decision (OQ-10) | E8 | S7-S8 | MQ (band calibration), I, S |
| FR-100 | Starter stats from Quick Tag | Must | R1 | needs-verification (definitions, coach review) | E5 | S3 | U, S (golden matches) |
| FR-101 | Sample size and uncertainty on every metric | Must | R1 | ready-candidate | E5 | S3 | U, S |
| FR-102 | Versioned metric dictionary | Must | R1 | ready-candidate | E5 | S3 | U, S |
| FR-103 | "Show me" evidence for every metric | Must | R1 | ready-candidate | E5 | S3 | E2E (evidence crawl) |
| FR-104 | Trends across matches | Should | R2 | ready-candidate | E5 | S9 | U, S |
| FR-105 | Team-relative court frame | Should | R2 | needs-verification (end switching) | E7 | S6 | U (frame test), MQ |
| FR-106 | Player heatmaps and partner spacing | Should | R2 | needs-verification (AN-16 definition) | E7 | S6 | U, MQ, A11y |
| FR-107 | Shot-level analytics | Could | R3 | needs-verification (definitions [DOM G2]) | E10 | R3 (S10-S12) | U, S, MQ |
| FR-108 | Pattern n-grams | Could | R3 | needs-verification | E10 | R3 (S10-S12) | U, S, MQ |
| FR-109 | Attribution conservation | Must | R1 | ready-candidate | E5 | S3 | U (invariant) |
| FR-110 | Opponent scouting report | Won't (this MVP) | Later | deferred | E12 | Later | U, S |
| FR-120 | Rank weaknesses by rallies lost | Must | R1 | needs-PO-decision (OQ-08); needs-verification (side-out rule) | E6 | S4 | U, S |
| FR-121 | Rules-only general training plan | Must | R1 | ready-candidate (needs FR-141 content) | E6 | S4 | U, S, LE (code graders) |
| FR-122 | Every drill explains why | Must | R1 | ready-candidate | E6 | S4 | U, S, E2E |
| FR-123 | Plan built on limited data says so | Must | R1 | ready-candidate | E6 | S4 | U, S, E2E |
| FR-124 | Mark sessions done and swap drills | Should | R1 | ready-candidate | E6 | S4 | S, E2E |
| FR-125 | LLM-written ordering and explanation, validated | Should | R2 | ready-candidate (eval set first) | E11 | S9 | U, I (LLM-output suite), LE |
| FR-126 | AI-text label and global control | Should | R2 | ready-candidate | E11 | S9 | S, E2E |
| FR-127 | Plan efficacy without over-claiming | Should | R2 | ready-candidate | E11 | S9 | U, S |
| FR-128 | Opponent-specific plan | Won't (this MVP) | Later | deferred | E12 | Later | S, LE |
| FR-140 | Drill schema, lint and immutability | Must | R1 | ready-candidate | E6 | S3 | CI lint, U, S |
| FR-141 | Starter drill library by coverage | Must | R1 | needs-verification (drill content [DOM G2]) | E6 | S4 | CI coverage check, R (coach) |
| FR-150 | Full Tag labelling tool (internal) | Must | R1 | ready-candidate (consent: OQ-06) | E4 | S3 | S, E2E |
| FR-151 | Frozen, versioned gold sets | Must | R1 | ready-candidate | E4 | S0 (ST-011, manifest check); S2 (ST-040, schema); S3 | CI manifest check |
| FR-160 | Upload and job rate limits | Must | R1 | needs-PO-decision (OQ-13) | E15 | S4 | I (quota suite), S |
| FR-161 | Monthly analysis quota | Must | R2 | needs-PO-decision (OQ-13, OQ-14) | E15 | S9 | I (quota suite), S |
| FR-162 | Pricing fake door | Could | R1 | needs-PO-decision (OQ-14) | E15 | S5 (Could, stretch) | E2E |

## 3. Counts (computed)

| Priority | FRs |
|---|---|
| Must | 42 |
| Should | 28 |
| Could | 10 |
| Won't | 3 |
| **Total** | **83** |

| Epic | FRs |
|---|---|
| E1 | 11 |
| E2 | 7 |
| E3 | 11 |
| E4 | 7 |
| E5 | 7 |
| E6 | 7 |
| E7 | 6 |
| E8 | 8 |
| E9 | 7 |
| E10 | 3 |
| E11 | 3 |
| E12 | 3 |
| E15 | 3 |

## 4. Non-functional requirements

| NFR | Requirement | Release | Epic | Sprint | Test levels |
|---|---|---|---|---|---|
| NFR-001 | Rules engine matches the golden scoring tables | R1 gate | E3 | S1 (ST-023); S2 (ST-041) | U + S (`Scenario Outline`, tagged `@needs-verification` until rule numbers recorded) |
| NFR-002 | Rules engine invariants hold, and an independent implementation agrees | R1 gate | E3 | S1 (ST-022, ST-024) | U (property-based); nightly job |
| NFR-003 | "Official scoring" correctness (QD's M0b) | Gate for any release claiming an official `rules_version` | E3 | After OQ-01 (any sprint) | S on QD-GD-02 |
| NFR-004 | Metric definitions computed correctly | R1 gate | E5 | S3 | S on QD-GD-03 |
| NFR-005 | Plans obey the hard rules, and the LLM explanations are good | (a) R1 gate; (b)(c) R2 gate | E6/E11 | S4 (a); S9 (b, c) | LE (code + model + human graders); R1 runs (a) on rules-only plans |
| NFR-006 | Vision accuracy at R2 entry, on a frozen, venue-split gold set | R2 gate (rally F1); others R2 entry targets, reviewed at retro | E7/E8 | S6-S8 (rally F1 gate S8) | MQ per sprint and per model PR; regression tolerances set in an ADR before R2 |
| NFR-007 | Automatic scoring accuracy (spec M3, redefined) | R3 gate (post-MVP) | E9 | R3 | MQ on QD-GD-04 |
| NFR-008 | Confidence bands are calibrated | R2 gate | E8 | S7-S8 | MQ |
| NFR-009 | Metrics computed from automatic events agree with gold | R2 (heatmap/positioning metrics); R3 (shot-level) | E7/E10 | S6 (positioning); R3 (shot-level) | MQ |
| NFR-010 | API read latency: match, score sheet, dashboard, plan | R1 gate | E16 | S2 (ST-039, baseline); S5 (gate) | P (Locust, ADR 0008) each sprint; OPS |
| NFR-011 | Time to an interactive score sheet or dashboard on the client | R1 gate | E5 | S2 (ST-030); S3 | P (Playwright/Lighthouse lab) |
| NFR-012 | Tag or correction feedback | R1 gate | E4 | S2 (ST-027, ST-039) | E2E timing |
| NFR-013 | Correction confirmed by the server (rules replay + metrics recomputed) | R1 gate | E4 | S2 (ST-032, ST-039) | I + P |
| NFR-014 | Seek from a rally row or evidence link to playing video | R1 | E5 | S2 (ST-037) | E2E timing |
| NFR-015 | JavaScript budget for the first route | R1 gate | E16 | S0 (ST-002, ST-010) | CI bundle-size check |
| NFR-016 | Upload throughput | R1 | E2 | S1 (ST-017) | P with network throttling |
| NFR-017 | Results after manual tagging | R1 gate | E4 | S2 (ST-039, baseline); S5 | I + E2E |
| NFR-018 | Results after automatic analysis | R2 gate (2.0x) | E8 | S7 | OPS job metrics; P on fixture matches |
| NFR-019 | Plan generation time | R1 / R2 | E6/E11 | S4 (rules-only); S9 (LLM) | I + P |
| NFR-020 | GPU cost of automatic analysis | R2 gate | E15 | S4-S5 (SPIKE-03); S7 (gate) | OPS + MQ throughput run per model PR |
| NFR-021 | LLM usage per plan | R2 gate | E15 | S9 | LE + OPS |
| NFR-022 | Spend guardrails | R1 / R2 gate | E15 | S4 (R1 alerts); S7 (GPU) | R (config review) + OPS |
| NFR-023 | Quotas and rate limits enforced | R1 gate | E15 | S4; S9 (analysis quota) | I (quota regression suite) |
| NFR-024 | Supported clients | R1 gate | E16 | S0 (ST-002, skeleton); S5 (gate) | E2E matrix |
| NFR-025 | Phone video formats | R1 (probe) / R2 (normalise) | E2 | S0 (ST-009); S1 (ST-025); S6 (normalise) | I with fixture files |
| NFR-026 | Resumable-upload protocol conformance | R1 gate | E2 | S0 (ST-008, core); S1 (ST-017) | I (upload-resume regression suite) |
| NFR-027 | WCAG 2.2 Level AA conformance | R1 gate | E16 (all UI epics) | S0 (ST-002, ST-010) onward | A11y (CI + manual) |
| NFR-028 | Target size | R1 gate | E16 (all UI epics) | S1 (ST-016) onward | E2E custom size check + R |
| NFR-029 | Contrast | R1 gate | E16 (all UI epics) | S0 (ST-010, tokens) onward | A11y + design-token check |
| NFR-030 | No dragging required | R1 gate (R2 for calibration) | E16 (all UI epics) | S1 onward; S6 (calibration) | E2E taps-and-keys-only journeys |
| NFR-031 | Focus not obscured | R1 gate | E16 (all UI epics) | S1 (ST-016) | E2E |
| NFR-032 | Accessible authentication | R1 gate | E16 (all UI epics) | S1 (ST-013) | E2E + R |
| NFR-033 | Media alternatives | R1 gate | E16 (all UI epics) | S1 (ST-015); S2 (ST-030) | R (content checklist) |
| NFR-034 | Keyboard, colour, reflow, announcements | R1 gate | E16 (all UI epics) | S1 (ST-016); S2 (ST-028, ST-030) | E2E viewport matrix 320/360/768/1280; A11y manual |
| NFR-035 | Content descriptions | R1 | E16 (all UI epics) | S1 (ST-015) | A11y + R |
| NFR-036 | Effort to get value | R1 gate | E4 | S2 (E2E part d); S5 (usability test) | Moderated usability test, ≥ 5 players on their own phones; E2E for (d) |
| NFR-037 | Forms and errors follow the patterns | R1 gate | E2 | S1 (ST-016) | R + E2E |
| NFR-038 | Every insight is explained by evidence | R1 gate | E5/E6 | S3 | E2E crawl; U on view-models |
| NFR-039 | Layout stability | R1 | E16 | S3 | E2E visual regression |
| NFR-040 | Review effort with automatic scoring | R3 | E9 | R3 | OPS product analytics in beta |
| NFR-041 | API availability | R1 | E16 | S1 (ST-024, SLI); S5 (SLO, alerts) | OPS SLI dashboard; burn-rate alerts |
| NFR-042 | Upload completion | R1 | E2 | S1 (ST-017, ST-024, SLI); S5 (SLO, alerts) | OPS |
| NFR-043 | Analysis success | R2 | E8 | S7 | OPS |
| NFR-044 | Analysis freshness | R2 | E8 | S7 | OPS |
| NFR-045 | Durability and recovery | R1 (before beta) | E16 | S5 | Restore drill (R); I |
| NFR-046 | Idempotent, disposable workers | R1 (queue exists in M0) gate | E8 | S0 (ST-007) | I (worker-crash regression suite) |
| NFR-047 | Fail closed | R1 gate | E8 | S0 (ST-007) | I (fail-closed regression suite) |
| NFR-048 | Bounded retries | R2 | E8 | S7 | I |
| NFR-049 | Error-budget policy | R1 | E16 | S5 | R at sprint planning |
| NFR-050 | ASVS 5.0 L2 for API and client | R1 gate | E1 | S0 (checklist); S5 (release review) | R (security-privacy-engineer checklist) |
| NFR-051 | Object-level authorisation (BOLA) | R1 gate | E1 | S0 (ST-006) onward | I (BOLA regression suite) |
| NFR-052 | Field-level authorisation and deny-by-default | R1 gate | E1 | S0 (ST-006) | U + I |
| NFR-053 | Upload safety | R1 gate | E2 | S0 (ST-008, keys); S1 (ST-018) | I (upload-validation regression suite) |
| NFR-054 | Media-processing sandbox | R1 gate | E2 | S0 (ST-009); S1 (ST-018) | I + R (infra config) |
| NFR-055 | Media URLs | R1 gate | E2 | S1 (ST-013); S2 (ST-037) | I |
| NFR-056 | Secrets and service identities | R1 gate | E16 | S0 (ST-002) | CI secret scan + R |
| NFR-057 | Security logging | R1 gate | E1 | S0 (ST-006); S1 (ST-013) | I + R |
| NFR-058 | Generic errors | R1 gate | E16 | S0 (ST-005) | I (error-body regression suite) |
| NFR-059 | LLM output and prompt-injection containment | R2 gate (R1 has no LLM) | E11 | S9 | U + I (LLM-output regression suite) + LE |
| NFR-060 | Business-flow order | R1 gate | E8 | S0 (ST-008); S1 (ST-018) | I |
| NFR-061 | Hardening and client security headers | R1 gate | E16 | S0 (ST-005, ST-010) | I + automated header scan |
| NFR-062 | Supply chain and licences | R1 gate | E16 | S0 (ST-002, SPIKE-01); S6 (CV licences) | CI scans + licence check + R |
| NFR-063 | Data classification and per-class rules | R1 gate (before beta) | E1 | S5 | R |
| NFR-064 | Private by default | R1 gate | E1 | S0 (ST-006) | I (BOLA suite) + R |
| NFR-065 | No face recognition or inferred attributes | R1 gate, permanent | E1 | S0 (review checklist), permanent | R (design and code review checklist) |
| NFR-066 | Deletion and retention execution | R1 gate | E1 | S2 (d); S3 (a, b); S4 (c) | I (delete → assert storage and DB empty) + OPS |
| NFR-067 | Client-side data hygiene | R1 gate | E1 | S0 (ST-005, ST-010); S1 (ST-014) | I + E2E |
| NFR-068 | Minimal data to the LLM | R2 gate | E11 | S9 | U on the prompt builder + LE transcript review |
| NFR-069 | Pseudonymous logs | R1 gate | E16 | S0 (ST-005) | I (log scanner on test runs) |
| NFR-070 | Legal gate before real users | Gate for any real-user beta | E1 | S5 (human gate before any real-user beta) | R |
| NFR-071 | Coverage floors (a floor, not a goal) | R1 gate | E16 | S0 (ST-002) | CI coverage gate |
| NFR-072 | Rules-engine test strength | R1 | E3 | S1 (ST-022, baseline); S2 (gate) | Mutation run (tool is judgment) |
| NFR-073 | Fast tests | R1 gate | E16 | S0 (ST-002, ST-004) | CI timing |
| NFR-074 | Flaky tests contained | R1 | E16 | S0 (ST-002) | CI analytics |
| NFR-075 | Reproducible outputs | R1 gate | E16 | S0 (ST-004, harness); S2 (ST-026) | U + I |
| NFR-076 | Observability | R1 gate | E16 | S0 (ST-005, ST-007) | I (trace-header regression suite) + OPS |
| NFR-077 | Code standards and change size | R1 | E16 | S0 (ST-002) | CI + R |
| NFR-078 | Gold-set and test immutability | R1 gate | E4 | S0 (ST-003, ST-011); S3 (gold sets) | CI manifest check + hooks |
| NFR-079 | Rules and court facts are configuration | R1 | E3 | S1 (ST-020) | CI static check |
| NFR-080 | Dev/prod parity | R1 gate | E16 | S0 (ST-001) | R + I runs on Compose |
| NFR-081 | Stateless, env-configured processes | R1 gate | E16 | S0 (ST-001, ST-005) | R + I (kill/restart test) |
| NFR-082 | Sport plug-in extensibility | R2 | E3 | S9 | U/I contract test |

**NFR total:** 82

## 5. Gaps this matrix exposes (for sprint planning)

1. **18 FRs are `needs-verification`.** Eleven are R1 Musts, and every scoring scenario is tagged `@needs-verification`. The matrix will show these as "not Ready" until the domain coach records rule numbers (OQ-01).
2. **Story IDs exist for Sprints 0-2 only** (`ST-001`..`ST-041`, §6). PROD US-* IDs remain candidates for later sprints. The BA will write `docs/requirements/stories/<id>.md` per story at sprint planning.
3. **Model-quality and LLM-eval levels need data that does not exist yet:**
   - QD-GD-02 needs rule verification first.
   - QD-GD-04 needs the R2 gold set.
   - QD-GD-05 needs 30 coaching cases from real tagged matches.

   These are dependencies for the DoR, not test gaps.

## 6. Stories for Sprints 0-2 (engineering-manager, 2026-10-03)

Source: `docs/sprints/sprint-00.md`, `sprint-01.md`, `sprint-02.md`. Feature files live at the repository root under `tests/features/` (`backend/pyproject.toml`: `bdd_features_base_dir = "../tests/features"`); their step modules are in `backend/tests/features/`, and browser journeys are in `web/e2e/`. "—" means the story is verified by unit, integration or CI checks only.

**Update, business-analyst, 2026-10-03:**

- Paths corrected to `tests/features/`.
- Feature files that **exist** in the repo are marked ✔. These seven exist: `dev_environment`, `errors_and_tracing`, `gold_set_integrity`, `job_resilience`, `object_level_authorisation`, `upload_resume_core`, `walking_skeleton`.
- New Sprint 1 feature files come from sprint-01 §14.3.
- The ADR 0009 (b) parts are added as backlog rows ST-020b and ST-021b.
- The design and domain artefacts that Sprint 1 stories depend on are listed in §7.

| Story | Sprint | FR | NFR | Feature file(s) | Other test levels |
|---|---|---|---|---|---|
| ST-001 | S0 | — | NFR-080, 081 | `dev_environment.feature` ✔ | I (IT-00-16) |
| ST-002 | S0 | — | NFR-015, 024, 027, 056, 062, 071, 073, 074, 077 | — | CI |
| ST-003 | S0 | — | NFR-078 | — | CI, hooks |
| ST-004 | S0 | — | NFR-073, 075 | — | U (builders) |
| ST-005 | S0 | — | NFR-058, 061, 069, 076, 081 | `errors_and_tracing.feature` ✔ | U, I (IT-00-11..15) |
| ST-006 | S0 | FR-002 | NFR-051, 052, 057, 064 | `object_level_authorisation.feature` ✔ | U, I (IT-00-01, 02) |
| ST-007 | S0 | FR-080 | NFR-046, 047, 076 | `job_resilience.feature` ✔ | U, I (IT-00-03..05) |
| ST-008 | S0 | FR-022 | NFR-026, 053, 060 | `upload_resume_core.feature` ✔, `walking_skeleton.feature` ✔ | U, I (IT-00-06..08) |
| ST-009 | S0 | FR-081, FR-025 | NFR-025, 054 | `walking_skeleton.feature` ✔ | U, I (IT-00-09, 10) |
| ST-010 | S0 | — | NFR-015, 027, 029, 061, 067 | `walking_skeleton.feature` ✔ | E2E-00-01, A11y |
| ST-011 | S0 | FR-151 | NFR-078 | `gold_set_integrity.feature` ✔ | U, CI |
| ST-012 | S0 | (suites for FR-002, FR-022, FR-080) | testing-strategy §5 suites | all S0 features | I |
| ST-013 | S1 | FR-001 | NFR-032, 055, 057 | `sign_in.feature` ✔ | U, I (IT-01-01..03), E2E |
| ST-014 | S1 | FR-011 | NFR-067 | `sign_out.feature` ✔ | I (IT-01-04), E2E |
| ST-015 | S1 | FR-004, FR-020 | NFR-033, 035 | `first_run_and_capture_guide.feature` ✔ | E2E, A11y |
| ST-016 | S1 | FR-021, FR-005 | NFR-028, 031, 034, 037 | `match_setup.feature` ✔ | U, I (IT-01-05), E2E, A11y |
| ST-017 | S1 | FR-022 | NFR-016, 026, 042 | `resumable_upload.feature` ✔ | U, I (IT-01-06..08), E2E |
| ST-018 | S1 | FR-023 | NFR-053, 054, 060 | `upload_validation.feature` ✔ | U, I (IT-01-09, 10) |
| ST-019 (stretch) | S1 | FR-025 | — | `footage_quality_report.feature` ✔ | E2E |
| ST-020 | S1 | FR-040, 041, 044 (part a) | NFR-079 | `scoring_engine_mechanics.feature` ✔ | U, CI (IT-01-12, 13) |
| ST-021 | S1 | FR-045 (part a) | — | `match_structure.feature` ✔ | U |
| ST-022 | S1 | — | NFR-002, 072 | `property_and_oracle.feature` ✔ (sprint-01 §14.3.7) | U (property), nightly oracle, mutation |
| ST-023 | S1 | FR-041, FR-044 (provisional rows); FR-045 (M-01..M-08, part a) | NFR-001 | `side_out_doubles_provisional.feature` ✔, `faults_provisional.feature` ✔ (`@needs-verification`); `match_structure.feature` ✔ (M rows) | U |
| ST-024 | S1 | — | NFR-002, 041, 042, 072 | `nightly_quality.feature` ✔ (sprint-01 §14.3.8) | OPS, CI |
| ST-025 | S1 | FR-023 (caps) | NFR-025 | `phone_fixtures.feature` ✔ (sprint-01 §14.3.9) | I (fixtures) |
| ST-020b (backlog) | after OQ-01 | FR-040, 041, 044 (part b: preset values) | NFR-001, NFR-003 | rows of `side_out_doubles_provisional.feature` ✔, `faults_provisional.feature` ✔ gain `@rule-<n>` | U, S. Status `needs-verification` (ADR 0009) |
| ST-021b (backlog) | after OQ-01 | FR-045 (part b: rulebook defaults, if any) | — | `match_structure.feature` ✔ | U. Status `needs-verification` |
| ST-026 | S2 | FR-049 | NFR-075 | `score_sheet.feature` | U, I (IT-02-01) |
| ST-027 | S2 | FR-050 | NFR-012, 028, 030 | `quick_tag.feature` | U, I (IT-02-04), E2E, A11y |
| ST-028 | S2 | FR-051 | NFR-034 | `keyboard_tagging.feature` | E2E-02-02 |
| ST-029 | S2 | FR-048 | — | `score_call.feature` (`@needs-verification`) | U, E2E-02-03 |
| ST-030 | S2 | FR-049, FR-055 | NFR-011, 029, 033, 034 | `score_sheet.feature` | E2E, A11y |
| ST-031 | S2 | FR-052 | — | `undo_and_audit.feature` | U, I (IT-02-03, 09) |
| ST-032 | S2 | FR-053 (part a) | NFR-013 | `corrections_replay.feature` | U, I (IT-02-02, 08) |
| ST-033 (stretch) | S2 | FR-054 | — | `correction_consequences.feature` | E2E |
| ST-034 | S2 | FR-046 (part a) | — | `mid_game_start.feature` (`@needs-verification`) | U |
| ST-035 | S2 | FR-042 (part a) | — | `side_out_singles_provisional.feature` (`@needs-verification`) | U |
| ST-036 (stretch) | S2 | FR-047 | — | `gaps_and_resync.feature` | U |
| ST-037 | S2 | FR-027 | NFR-014, 055 | `evidence_deep_link.feature` | I (IT-02-06), E2E-02-04 |
| ST-038 | S2 | FR-024 | NFR-066 | `abandoned_upload_expiry.feature` | U, I (IT-02-07) |
| ST-039 | S2 | (journey over FR-022, FR-050, FR-049) | NFR-010, 012, 013, 017 | — | E2E-02-01, P (Locust) |
| ST-040 | S2 | FR-151 | — | — | CI (manifest) |
| ST-041 | S2 | FR-042, 046, 053 (provisional rows) | NFR-001 | rows inside the ST-034, ST-035 and ST-032 features | U |

## 7. Design and domain artefacts for Sprint 1 (business-analyst, 2026-10-03)

| Artefact | Owner | Status | Stories | Requirements |
|---|---|---|---|---|
| `docs/design/tokens.json`, `tokens.md` (contrast proof 55/55 pass) | principal-designer | draft v0.1 | ST-010, ST-013..ST-019 | NFR-028, NFR-029, NFR-031, NFR-034 |
| `docs/design/component-accessibility-checklist.md` | principal-designer | draft v0.1 | all UI stories | NFR-027..NFR-035, NFR-037 |
| `docs/design/flows-sprint-01.md` | principal-designer | draft v0.1; design review scheduled 2026-10-06, not held at Sprint 1 close (DoR P7) | ST-013..ST-019 | FR-001, 004, 005, 011, 020..023, 025, 043, 055 |
| `docs/domain/capture-guide-wording.md` | pickleball-domain-coach | draft; coach sign-off still missing at Sprint 1 close although ST-015 shipped (PD-R1-05) | ST-015 | FR-020, NFR-033, NFR-035 |
| `docs/domain/rules-verified.md` | pickleball-domain-coach | empty: nothing verified (OQ-01) | ST-020b, ST-021b, ST-023, all `@needs-verification` rows | FR-040..FR-048, NFR-001, NFR-003 |
| `docs/domain/metric-dictionary.md` AN-01..AN-07 | pickleball-domain-coach | draft | Sprint 3 stats stories | FR-100..FR-103, NFR-004, NFR-038 |

## 8. Sprint 0 test files per story (engineering-manager, 2026-10-03)

The test files as they landed in the repo (backend paths are relative to `backend/tests/`). Every row was green in the EM re-run on 2026-10-03: `cd backend && env -u APP_ENV uv run pytest -q -rs` → `439 passed, 5 skipped` (the skips are IT-00-10, which needs Compose; it passes on Compose, 12 passed in review round 3); `cd infra && uv run pytest -q` → `197 passed`; `cd web && pnpm exec vitest run` → `132 passed`; Playwright Chromium `7 passed` (round 3). Status per story: `docs/sprints/00/status.json`.

| Story | Unit | Integration / regression | Scenario (step module → feature) | E2E / other |
|---|---|---|---|---|
| ST-001 | — | `infra/tests/test_compose.py`, `test_compose_round1.py`, `test_dev_postgres.py`, `test_object_store_parity.py`; `integration/test_it_00_16_object_store_parity.py` | `features/test_dev_environment.py` → `dev_environment.feature` | — |
| ST-002 | — | `infra/tests/test_workflows.py`, `test_workflows_round1.py`, `test_workflows_round2.py`, `test_ci_scripts.py`, `test_web_dockerfile_round2.py` | — | `actionlint` (CI never run on GitHub) |
| ST-003 | — | `infra/tests/test_hook_pre_tool_use.py`, `test_hook_post_tool_use.py`, `test_hook_stop.py`, `test_claude_settings.py`, `test_test_immutability_guard.py`, `test_test_unit_script.py` | — | hook demo (decision-log) |
| ST-004 | `unit/test_architecture.py`, `unit/test_architecture_context_imports.py` | `integration/harness/test_db_fixture.py`; `tools/test_scenario_report.py`, `tools/test_logscan.py`, `tools/test_format.py`, `tools/test_bola_inventory.py` | — | `web/e2e/helpers/axe.ts` |
| ST-005 | `unit/platform/test_settings.py`, `test_error_mapper.py`, `test_tracing.py` | `regression/test_error_bodies.py`, `regression/test_trace_header.py`; `integration/test_it_00_11_trace_propagation.py`, `test_it_00_14_security_headers.py`, `test_it_00_15_log_scan.py`, `integration/platform/test_readiness.py` | `features/test_errors_and_tracing.py` → `errors_and_tracing.feature` | `web/e2e/security-headers.spec.ts` |
| ST-006 | `unit/matches/test_match_domain.py` | `regression/test_bola_matrix.py` (+ `bola.py`); `integration/test_it_00_01_matches_api.py`, `test_dev_user_without_matches.py`, `test_media_not_probed_contract.py` | `features/test_object_level_authorisation.py` → `object_level_authorisation.feature` | `web/e2e/object-level-authorisation.spec.ts` |
| ST-007 | `unit/analysis_jobs/test_job_domain.py`, `unit/test_worker_db_backoff.py` | `integration/test_it_00_03_queue.py`, `test_worker_db_resilience.py`; `regression/test_worker_crash.py`, `regression/test_fail_closed.py` | `features/test_job_resilience.py` → `job_resilience.feature` | `perf/spike_09_queue_claim.py` (SPIKE-09, not collected) |
| ST-008 | `unit/video_ingest/test_upload_domain.py`, `test_upload_domain_round1.py`, `test_tus_header_numbers.py` | `integration/test_it_00_06_tus_upload.py`, `test_it_00_08_probe_after_final_byte.py`; `integration/video_ingest/test_tus_edges.py`, `test_tus_round1.py`, `test_tus_header_numbers_round2.py`; `regression/test_upload_resume.py` | `features/test_upload_resume_core.py` → `upload_resume_core.feature`; `features/test_walking_skeleton.py` → `walking_skeleton.feature` | E2E-00-01 |
| ST-009 | `unit/video_ingest/test_media_facts.py`, `test_probe_sandbox_policy.py`, `test_probe_input_format_policy.py` | `integration/test_it_00_09_probe_stage.py`, `test_it_00_10_worker_sandbox.py`, `test_it_00_10_worker_sandbox_strict.py`; `integration/video_ingest/test_probe_sandbox.py`, `test_probe_input_formats.py`; `infra/tests/test_worker_sandbox.py` | `walking_skeleton.feature` | — |
| ST-010 | `web/tests/unit/*.test.ts(x)` (17 files, 132 tests) | — | `walking_skeleton.feature` | `web/e2e/walking-skeleton.spec.ts` (E2E-00-01, axe); WebKit not run |
| ST-011 | `unit/dataset/test_manifest_check.py`, `test_manifest_check_properties.py` | `integration/dataset/test_manifest_check_cli.py`, `test_committed_fixture_sets.py` | `features/test_gold_set_integrity.py` → `gold_set_integrity.feature` | `scripts/ci/check_fixtures.sh` |
| ST-012 | (owns the red-first suites above) | all `regression/*` and IT-00-* files | all 7 `tests/features/*.feature` | `web/e2e/*` |
| SPIKE-01 | — | — | — | ADR 0015 (document review) |

Open test items: 6 test-change rows waiting for QA approval (`docs/sprints/00/test-change-requests.md`); stale `red_until` markers (QA-R3-08); the weak IT-00-10 probe is to be retired (QA-R3-07).

## 9. Sprint 1 test files per story (engineering-manager, 2026-10-05, sprint close)

The test files as they landed (backend paths relative to `backend/tests/`; feature files under `tests/features/`; browser specs under `web/e2e/sprint-01/`). Evidence for the whole table is the EM's isolated re-run at `cf8cd19`: `cd backend && env -u APP_ENV uv run pytest -q -p no:cacheprovider -rfEs` → `3 failed, 1060 passed, 6 skipped`; `cd web && pnpm exec vitest run` → `251 passed`; `cd infra && uv run pytest -q` → `245 passed`. Browser: QA review round 2 (Chromium, `961648e`) → `44 passed, 6 skipped`. **No story is DoD-done**: no CI run includes these files, and WebKit is unverified (`docs/sprints/01/sprint-report.md`). "Gap" names an acceptance criterion or threat control with no executable test.

| Story | Unit | Integration / regression | Scenario (step module → feature) | E2E / other | Gap at close |
|---|---|---|---|---|---|
| ST-013 | `unit/players/test_magic_link_domain.py`, `test_session_cookie_policy.py`; `unit/platform/test_settings_sprint01.py`; `unit/test_worker_stage_selection.py`; web `auth-api`, `auth-callback`, `sign-in-form`, `sign-in-copy`, `dev-tls` | `integration/test_it_01_01_magic_link.py` (IT-01-01..03, T-ML-12), `integration/platform/test_rate_limiter.py`; `infra/tests/test_compose_sprint01.py`, `test_compose_tls.py` | `features/test_sign_in.py` → `sign_in.feature` | `sign-in.spec.ts` (E2E-01-01) | T-ML-5 prefetch test; idle-timeout and 10-session-cap tests (SEC-R3-S1-02/03) |
| ST-014 | web `account-menu`, `clear-client-data` | `integration/test_it_01_04_no_store.py` | `sign_out.feature` (browser-bound) | `sign-out.spec.ts` | WebKit upload-in-progress dialog (PD-R1-04) |
| ST-015 | web `first-run-and-guide` | — | `first_run_and_capture_guide.feature` (browser-bound) | `first-run-and-guide.spec.ts` | WebKit captions and fallback (PD-R1-02); coach sign-off |
| ST-016 | `unit/matches/test_participants.py`; web `setup-flow`, `match-setup`, `contact-details`, `api-sprint-01-match`, `error-summary` | `integration/test_it_01_05_participants.py` | `features/test_match_setup.py` → `match_setup.feature` | `match-setup.spec.ts` (E2E-01-03, reflow, axe) | T-UV-10 nickname render test; target size on the Q-03 error state (PD-R1-03) |
| ST-017 | `unit/video_ingest/test_upload_extensions.py`; web `tus-transfer`, `match-upload`, `upload-estimate`, `upload-policy-sprint-01`, `upload-files` | `integration/test_it_01_06_tus_extensions.py` (IT-01-06..08), `video_ingest/test_upload_policy_route.py`, `video_ingest/test_tus_resumable_everywhere.py` | `features/test_resumable_upload.py` → `resumable_upload.feature` (depends on Pending TCR row 32) | `resumable-upload.spec.ts` (E2E-01-02) | T-UV-9 file-name log scan; T-UV-10 file-name render; repeated-failure focus (PD-R3-01) |
| ST-018 | `unit/video_ingest/test_upload_policy.py`, `unit/matches/test_match_rejection.py`; web `format-caps` | `integration/test_it_01_09_upload_validation.py` (IT-01-09/10), `test_queue_enqueue_again.py`, `video_ingest/test_upload_create_review_round1.py` | `features/test_upload_validation.py` → `upload_validation.feature` | `upload-validation.spec.ts` | Probe delete-before-commit fault test (PE-R3-02) |
| ST-019 (stretch) | web `quality-report` | — | `footage_quality_report.feature` (browser-bound, `073d3f3`) | `footage-quality-report.spec.ts` | — |
| ST-020 | `unit/sports/pickleball/test_rules_config.py`, `test_rules_engine.py`, `test_rules_outcome.py`, `test_rules_state.py`, `test_rules_server_position.py`, `test_rules_static.py` (IT-01-12/13) | — | `features/test_scoring_engine_mechanics.py` → `scoring_engine_mechanics.feature` | — | — |
| ST-021 | `unit/matches/test_match_state.py` | — | `features/test_match_structure.py` → `match_structure.feature` (M-01..M-08) | — | — |
| ST-022 | `unit/sports/pickleball/test_rules_properties.py` (P1, P2, P4-P8; P3 skipped, OQ-01) | `oracle/test_oracle.py`, `oracle/differential.py` (P9) | `features/test_property_and_oracle.py` → `property_and_oracle.feature` (`@nightly` 100k) | nightly workflow (never run on GitHub) | Mutation baseline |
| ST-023 | — | — | `features/test_side_out_doubles_provisional.py`, `test_faults_provisional.py` → `side_out_doubles_provisional.feature`, `faults_provisional.feature` (26 `@needs-verification` cases) | — | Rule numbers `@rule-<n>` (OQ-01) |
| ST-024 | `unit/platform/test_slis.py`, `test_sli_wiring.py` | `infra/tests/test_nightly_quality.py`, `test_workflows_ci_run1.py`, `test_workflows_ci_run2.py` | `features/test_nightly_quality.py` → `nightly_quality.feature` (1 scenario red until a nightly run) | — | — |
| ST-025 | `unit/dataset/test_manifest_consent.py`, `test_phone_set.py` | `integration/dataset/test_phone_manifest_tool.py` | `features/test_phone_fixtures.py` → `phone_fixtures.feature` (2 scenarios red until real clips) | — | Real phone clips (PO) |
| SPIKE-06 | — | — | — | ADR 0028 (proxy data) | Real-device runs |


## 10. Sprint 1 outcome per requirement (engineering-manager, 2026-10-05, final close)

This section shows the state of each Sprint 1 requirement at the final close. Evidence is goal-scorecard verification round 3 at `e76fb96` (`docs/sprints/01/goal-scorecard.md` §8) and the open findings in `docs/sprints/01/sprint-report.md` §1.2. "Live" means the requirement was shown on an isolated https Compose stack. **No requirement is release-verified**: no green CI run includes these tests, and WebKit is unverified. The test files per story are in §9.

| Requirement | Story | Shown live (goal metric) | Open at close |
|---|---|---|---|
| FR-001 Passwordless sign-in | ST-013 | Yes (G01-01, G01-06a 1.058 s) | NUL address 500 (SEC-R6-S1-01); identity key (ST-013b); ASVS 6.3.3 (ADR 0031) |
| FR-004 First-run promise | ST-015 | Yes (G01-03, demo step 2) | — |
| FR-005 Match participants by nickname | ST-016 | Yes (G01-01 step 3, G01-03) | NUL title 500 (SEC-R6-S1-01) |
| FR-011 Sign out clears local data | ST-014 | Yes, Chromium (G01-01 step 9, demo step 8) | WebKit sign-out dialog |
| FR-020 Capture guide | ST-015 | Yes, Chromium (G01-03, G01-10) | WebKit captions/fallback; consent line (PD-R2R-03) |
| FR-021 Match setup flow | ST-016 | Yes (G01-03 incl. E2E-01-03, G01-10) | Design review P7 |
| FR-022 Resumable upload | ST-017 | Yes (G01-01 drop and resume, G01-05 541.8 Mbit/s but run invalid on disk) | Quota race (PE-R3R-01); server-error recovery (PD-R3V-01) |
| FR-023 Upload validation | ST-018 | Yes (G01-01 460/413/415, demo step 5) | Caps provisional until ST-025 (real phone clips) |
| FR-025 Footage quality report (stretch) | ST-019 | Yes (G01-01 facts, demo step 4) | Design review |
| FR-040, FR-041, FR-044, FR-045 (part a) | ST-020, ST-021, ST-023 | Yes (G01-07: 204/205, 26/26 `@needs-verification`) | Presets PROVISIONAL-UNVERIFIED until OQ-01 |
| NFR-001 / NFR-002 golden tables, invariants, oracle | ST-022, ST-023, ST-024 | Yes, locally (G01-07, G01-08: 0/100,000) | Nightly run on GitHub (P1) |
| NFR-010 / NFR-041 latency and availability | ST-024 | Yes (G01-04: p95 12.79 ms, 100%) | — |
| NFR-016 Upload throughput | ST-017 | Measured 541.8 Mbit/s; evidence invalid (G01-05, disk) | Rerun at ≥ 12 GB free (PO P5) |
| NFR-025 Phone video formats | ST-025 | No | Real phone clips (PO P3) |
| NFR-026 / NFR-053 upload regression suites | ST-017, ST-018 | Yes (G01-02: 41/41) | — |
| NFR-027b Manual screen-reader pass | — | No | QA-R3-GATE-01 (sprint-02 C-06) |
| NFR-028, NFR-030, NFR-031, NFR-034, NFR-037 a11y | ST-016 | Yes, Chromium (G01-10: 0 violations, 0 targets < 24×24) | WebKit |
| NFR-072 Rules-engine test strength | ST-022 | Baseline 0.8654 (G01-08) | Gate from Sprint 2 |
| NFR-073 Fast tests | — | Yes (G01-12: 7.4 s / 8.3 s) | — |
| NFR-074 Flaky rate | — | 0 flaky ×3 on `e2e/sprint-01` (G01-03) | Root specs not repeated; known flake (QA-R3-E2E-01) |
