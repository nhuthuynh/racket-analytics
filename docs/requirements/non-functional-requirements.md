# Non-Functional Requirements (NFR register)

- **Status:** Baselined draft v1, for product-owner review
- **Date:** 2026-10-03
- **Author:** business-analyst
- **Consulted (via brainstorm files):** product-manager ("PROD"), principal-engineer, sre-devops-engineer, security-privacy-engineer, senior-ml-cv-engineer ("ENG"), principal-designer, senior-frontend-engineer ("DES"), senior-qa-engineer, pickleball-domain-coach ("QD")
- **Companion files:** `functional-requirements.md`, `traceability-matrix.md`, `open-questions.md`, ADRs 0002-0006

## 0. Rules for this register

1. **Every NFR is measurable.** Each row states a metric, a numeric target, how it is tested (test level, from `docs/process/testing-strategy.md` §2) and the release it gates.
2. **Sources.** Research is cited `<file>/<ID>` (EP, AQS, DPA, DOM). A number with no source next to it is **(judgment)**: a starting target to be replaced by spike or production data through a superseding ADR, not evidence.
   - Performance categories (response time, throughput, latency) are verified [DPA/DESIGN-16]. That source gives no percentiles, so **every percentile target here is judgment** [DPA G-REQ-7, DPA Gaps].
   - SLI/SLO/error-budget framing is verified [AQS/REL-01, AQS/REL-02]. The SLO values are judgment.
3. **ISO/IEC 25010 categories are used as headings only.** The standard could not be fetched [AQS G1.5, AQS Gaps; DPA Gaps]. We use its widely known 2011 characteristic names as a filing scheme, which is **(judgment)**:
   - Functional suitability
   - Performance efficiency
   - Compatibility
   - Usability
   - Reliability
   - Security
   - Maintainability
   - Portability

   Two extra groupings are used:
   - **Privacy** is filed as a sub-group of Security (confidentiality).
   - **Cost** is filed under Performance efficiency (resource utilisation).

   Re-check the names and the 2023 edition changes before quoting 25010 externally.
4. **Release gates.** "Gate" means the release cannot ship while the NFR fails. R1 and R2 make up the MVP (ADR 0002).
5. **Test levels:** U unit · I integration · S scenario (Gherkin) · E2E Playwright · A11y (axe-core + manual) · P performance (Locust, ADR 0008) · MQ model-quality layer · LE coaching-LLM eval layer · OPS production SLI/telemetry · R review/checklist.

---

## 1. Functional suitability (correctness)

| ID | Requirement | Metric | Target | How tested | Release | Source |
|---|---|---|---|---|---|---|
| NFR-001 | Rules engine matches the golden scoring tables | Table rows passing / rows | 100% of ≥ 46 rows (16 SOD, 6 F, 12 SOS, 8 M, 4 C); ≥ 12 RS rows once rally scoring is verified | U + S (`Scenario Outline`, tagged `@needs-verification` until rule numbers recorded) | R1 gate | QD §2.2; [DPA/PROD-01]; [EP/ENG-17]; [DOM G1] (rules UNVERIFIED) |
| NFR-002 | Rules engine invariants hold, and an independent implementation agrees | (a) property suites P1-P8; (b) disagreements in a differential oracle written by a different agent | (a) ≥ 1,000 random sequences per scoring system per CI run, 0 failures; (b) 100,000 sequences nightly, 0 disagreements | U (property-based); nightly job | R1 gate | QD §2.3, QD-QG-S1; writer/reviewer split [DPA/AI-08] |
| NFR-003 | "Official scoring" correctness (QD's M0b) | Rally-by-rally score calls matching hand-scored real games, scored independently by 2 people | 100% exact on ≥ 10 side-out doubles + ≥ 3 singles games. Until met, the UI shows "unofficial scoring" (FR-055) | S on QD-GD-02 | Gate for any release claiming an official `rules_version` | QD X8, QD-QG-R3; [DOM G1] |
| NFR-004 | Metric definitions computed correctly | Metric values from gold tags vs the coach's hand count | 100% exact for every metric with status ≥ coach-reviewed, on 3 golden matches (R1) and 10 (R2) | S on QD-GD-03 | R1 gate | QD QD-AN-02, QD-AN-03, QD-QG-S5 |
| NFR-005 | Plans obey the hard rules, and the LLM explanations are good | (a) code-grader pass^3: drill exists, metric cited, time/players/equipment fit; (b) model-grader rubric mean; (c) model-grader vs coach agreement | (a) 100% on a ≥ 30-case eval set; (b) ≥ 4.0/5 on relevance and clarity; (c) within ±1 point on ≥ 80% of 10 coach-graded cases per sprint | LE (code + model + human graders); R1 runs (a) on rules-only plans | (a) R1 gate; (b)(c) R2 gate | QD QD-QG-S7, QD-GD-05; 20-50 cases, mixed graders, pass^k [DPA/AI-05]; [AQS/AI-03]; [EP/ENG-27] |
| NFR-006 | Vision accuracy at R2 entry, on a frozen, venue-split gold set | Ball F1 (visible frames, centre within 10 px at 1920×1080); HOTA (4 on-court players); auto-calibration success rate; reprojection error; hit P/R; median and p95 hit-timing error; bounce recall; landing error p80; **rally segmentation F1**, where a rally matches when start and end are each within ±1.0 s and it is neither merged nor split | Ball F1 ≥ 80%; HOTA ≥ 65; calibration ≥ 70% of videos without fallback; reprojection ≤ 15 cm RMS; hit P/R ≥ 85%/85%; timing median ≤ 33 ms, p95 ≤ 100 ms; bounce recall ≥ 70%, landing p80 ≤ 60 cm; **rally F1 ≥ 90%** (spec M2) | MQ per sprint and per model PR; regression tolerances set in an ADR before R2 | R2 gate (rally F1); others R2 entry targets, reviewed at retro | ENG §5.3-5.4 CV-T01..T09; PROD C9; spec M2; [DOM/CV-01]; [DOM/CV-08]; [DOM G8 E1-E4]; ADR 0004 |
| NFR-007 | Automatic scoring accuracy (spec M3, redefined) | (a) score-affecting corrections per game, counted by an oracle user against gold; (b) one-tap confirmations per game; (c) accuracy of unflagged rallies | (a) ≤ 2.0 (≤ 1.0 at a later milestone); (b) ≤ 5; (c) ≥ 95% point estimate **and** 95% CI lower bound ≥ 93%, pooled over all gold games | MQ on QD-GD-04 | R3 gate (post-MVP) | spec M3; ENG §5.4; QD X9; PROD C8; ADR 0004 |
| NFR-008 | Confidence bands are calibrated | Observed accuracy per band on the gold set, per `pipeline_version` | "Sure" ≥ 95%; "Likely" 80-95%; "Check this" < 80%. A model release that violates a band is blocked | MQ | R2 gate | DES NFR-TRUST-01/02, CD4; [DPA/DESIGN-11] G2 |
| NFR-009 | Metrics computed from automatic events agree with gold | Per-match relative error (counts) and absolute error (rates) | Counts within ±10% relative and rates within ±5 pp, on ≥ 80% of gold matches | MQ | R2 (heatmap/positioning metrics); R3 (shot-level) | QD QD-QG-S6 |

## 2. Performance efficiency

### 2.1 Time behaviour

The reference client profile (judgment, needs PO confirmation, OQ-17) is a mid-range Android phone with about 4 GB RAM on 4G throttled to 9 Mbps down / 1.5 Mbps up [DES §6]. Each number in this table is (judgment). The categories come from [DPA/DESIGN-16].

| ID | Requirement | Metric | Target | How tested | Release |
|---|---|---|---|---|---|
| NFR-010 | API read latency: match, score sheet, dashboard, plan | Server-side latency | p95 ≤ 300 ms, p99 ≤ 800 ms at 50 RPS | P (Locust, ADR 0008) each sprint; OPS | R1 gate |
| NFR-011 | Time to an interactive score sheet or dashboard on the client | Lab time-to-interactive on the reference profile | p95 ≤ 2.0 s warm, ≤ 3.5 s cold | P (Playwright/Lighthouse lab) | R1 gate |
| NFR-012 | Tag or correction feedback | (a) tap/key → updated score visible (optimistic); (b) any tap/key on tagging screens → visual feedback | (a) p95 ≤ 200 ms; (b) p95 ≤ 100 ms | E2E timing | R1 gate |
| NFR-013 | Correction confirmed by the server (rules replay + metrics recomputed) | Command → confirmed state, 3-game match | p95 ≤ 1.5 s | I + P | R1 gate |
| NFR-014 | Seek from a rally row or evidence link to playing video | Click → first frame playing | p95 ≤ 1.5 s on the reference profile | E2E timing | R1 |
| NFR-015 | JavaScript budget for the first route | Gzipped JS for the first route | ≤ 200 KB; chart and video libraries lazy-loaded | CI bundle-size check | R1 gate |
| NFR-016 | Upload throughput | (a) client throughput / measured uplink; (b) sustained server ingest per upload | (a) ≥ 90%, with chunk size adapting between 5 and 50 MB; (b) ≥ 50 Mbps | P with network throttling | R1 |
| NFR-017 | Results after manual tagging | Last tag saved → score sheet and stats current | p95 ≤ 5 s | I + E2E | R1 gate |
| NFR-018 | Results after automatic analysis | Upload complete → stats available, as a multiple of match duration; plus accuracy of the "Analysing" estimate | **Gate:** p90 ≤ 2.0x. **Target:** p50 ≤ 0.5x and p90 ≤ 1.0x, once ENG SPIKE-03/04 show it is affordable. Estimate within ±30% for 80% of jobs | OPS job metrics; P on fixture matches | R2 gate (2.0x) |
| NFR-019 | Plan generation time | Request → plan shown | Rules-only p95 ≤ 5 s (R1); with LLM p95 ≤ 60 s, async with notification (R2) | I + P | R1 / R2 |

Sources: PROD NFR-PERF-01..03; ENG NFR-PERF-01..06; DES NFR-UXP-01..07; conflicts K16, K17 in `functional-requirements.md` §1.

### 2.2 Resource utilisation and cost

| ID | Requirement | Metric | Target | How tested | Release | Source |
|---|---|---|---|---|---|---|
| NFR-020 | GPU cost of automatic analysis | GPU-seconds per match-minute (`full` level), recorded per stage run and as a telemetry metric | ≤ 120 GPU-s (2 GPU-min) per match-minute at R2 entry; ≤ 90 GPU-s by R2 release; alert at 120 | OPS + MQ throughput run per model PR | R2 gate | spec §8 (1-2 GPU-min); ENG NFR-COST-01/02, CV-T12; [AQS/SEC-10]; [AQS/OPS-07] |
| NFR-021 | LLM usage per plan | Tokens per plan | ≤ 30k input + 4k output; input is aggregated stats only | LE + OPS | R2 gate | ENG NFR-COST-03 (judgment) |
| NFR-022 | Spend guardrails | Alerts configured on each paid provider; $ per analysed match-minute reported | Billing alerts at 50/80/100% of the monthly budget on the LLM provider and object storage (R1) and the GPU provider (R2). Fully loaded $/match-minute on a dashboard every sprint from R2 | R (config review) + OPS | R1 / R2 gate | PROD US-1502; ENG NFR-COST-04/06; [AQS/SEC-10] |
| NFR-023 | Quotas and rate limits enforced | Requests beyond a limit that are accepted | 0. Covers job creation (10/h/user), per-user storage quota, monthly analysed minutes (FR-160/161) and pagination limits | I (quota regression suite) | R1 gate | [AQS/SEC-10]; [AQS/SEC-07] 2.4.1; [AQS/SEC-02] 5.2.4; testing-strategy §5 |

## 3. Compatibility

| ID | Requirement | Metric | Target | How tested | Release | Source |
|---|---|---|---|---|---|---|
| NFR-024 | Supported clients | Critical E2E journeys passing per browser | 100% on current and previous major versions of iOS Safari and Android Chrome (phones), plus desktop Chrome. Whether iOS Safari is release-blocking is OQ-17 | E2E matrix | R1 gate | DES OQ 4 (judgment) |
| NFR-025 | Phone video formats | Share of sample files from ≥ 5 phone models (R-05) that probe, play and (R2) normalise correctly, including VFR | 100% of MP4/MOV with H.264/HEVC | I with fixture files | R1 (probe) / R2 (normalise) | ENG §1.2, RISK-14; PROD R-05 |
| NFR-026 | Resumable-upload protocol conformance | tus 1.0.0 behaviours passing: HEAD offset discovery, PATCH from offset, 409 on offset mismatch with the upload unchanged, checksum and expiration extensions | 100% | I (upload-resume regression suite) | R1 gate | [AQS/STACK-06]; testing-strategy §5 |

## 4. Usability (includes accessibility and human-AI interaction)

| ID | Requirement | Metric | Target | How tested | Release | Source |
|---|---|---|---|---|---|---|
| NFR-027 | WCAG 2.2 Level AA conformance | (a) serious/critical axe-core violations; (b) manual keyboard and screen-reader (VoiceOver iOS, TalkBack Android) checklist on changed screens | (a) 0 on every PR; (b) 100% complete each sprint | A11y (CI + manual) | R1 gate | [DPA/DESIGN-01]; [DPA/DESIGN-14] |
| NFR-028 | Target size | Interactive targets under size | 0 below 24×24 CSS px; 0 primary or tagging touch controls below 48×48 CSS px | E2E custom size check + R | R1 gate | [DPA/DESIGN-02]; [DPA/DESIGN-10] |
| NFR-029 | Contrast | Contrast ratios | Text ≥ 4.5:1 (≥ 3:1 large), including text over video (with a scrim). UI components, focus indicators, chart marks, heatmap cells and court overlays ≥ 3:1 against adjacent colours, checked on 3 reference frames (sunny, shaded, indoor) | A11y + design-token check | R1 gate | [DPA/DESIGN-03]; [DPA/DESIGN-04] |
| NFR-030 | No dragging required | Flows that cannot be completed with taps/keys only | 0, including calibration, seeking, trimming and reordering | E2E taps-and-keys-only journeys | R1 gate (R2 for calibration) | [DPA/DESIGN-05] |
| NFR-031 | Focus not obscured | Focused elements whose box is fully hidden by sticky video, tag bar, banners or sheets | 0 when tabbing through every screen at 360×640 | E2E | R1 gate | [DPA/DESIGN-07] |
| NFR-032 | Accessible authentication | Authentication steps needing a cognitive function test | 0 | E2E + R | R1 gate | [DPA/DESIGN-06] |
| NFR-033 | Media alternatives | Tutorial videos with captions on by default and a text alternative; matches with a complete text score sheet | 100% | R (content checklist) | R1 gate | [DPA/DESIGN-08]; [DPA/DESIGN-09]; DES CD12 (judgment that the score sheet is the match video's alternative) |
| NFR-034 | Keyboard, colour, reflow, announcements | Flows passing a keyboard-only E2E run; status cues conveyed by colour alone (greyscale screenshot test); two-direction scrolling at 320 CSS px (except video); score and upload changes announced politely | 100%; 0; 0; 100% | E2E viewport matrix 320/360/768/1280; A11y manual | R1 gate | **(judgment: SC 2.1.1, 1.4.1, 1.4.10, 4.1.3 were not fetched [DES §0.2])**; QA must check the W3C text before these become gates |
| NFR-035 | Content descriptions | axe accessible-name failures; duplicate names within lists | 0; 0. Decorative overlays hidden from assistive technology | A11y + R | R1 | [DPA/DESIGN-10] |
| NFR-036 | Effort to get value | (a) Quick Tag median seconds per rally; (b) mis-tags per 20 rallies; (c) median total user effort, upload → plan, for a 3-game match; (d) taps or keys to fix any call from where it is seen | (a) ≤ 5 s; (b) ≤ 1; (c) ≤ 15 min (R1); (d) ≤ 2 | Moderated usability test, ≥ 5 players on their own phones; E2E for (d) | R1 gate | PROD US-401, J1; DES §2 principle 3, §9 (all judgment); R2 exit: Quick Tag effort −50% (PROD §11) |
| NFR-037 | Forms and errors follow the patterns | Setup pages violating one-question-per-page / Back link / Continue / "(optional)"; validation errors not shown in the error-summary form | 0; 0 | R + E2E | R1 gate | [DPA/DESIGN-12]; [DPA/DESIGN-13] |
| NFR-038 | Every insight is explained by evidence | (a) metrics, tendencies and drill "why"s without a working evidence link (crawler over dashboard and plan); (b) displayed metrics without n | 0; 0 | E2E crawl; U on view-models | R1 gate | spec §5, §6; DES NFR-TRUST-03/04; [DPA/DESIGN-11] G2, G10, G11 |
| NFR-039 | Layout stability | Visible content shift when scores or stats load | 0 in visual-regression snapshots | E2E visual regression | R1 | DES NFR-UXP-08 (judgment) |
| NFR-040 | Review effort with automatic scoring | Median "Needs your eyes" items per game; median review time per match | ≤ 15; ≤ 5 min | OPS product analytics in beta | R3 | DES NFR-TRUST-07; PROD J1 (judgment) |

## 5. Reliability

SLIs are good events / valid events, with a numeric SLO and an error budget of 100% − SLO [AQS/REL-01, AQS/REL-02]. The windows are monthly. SLO values are judgment. They are deliberately below "three nines" for a pre-PMF product, because we should not engineer reliability beyond what we can sustain [AQS/REL-01]. Planned maintenance counts against the budget unless the PO explicitly accepts it [AQS/REL-02].

| ID | Requirement | SLI | Target | How tested | Release | Source |
|---|---|---|---|---|---|---|
| NFR-041 | API availability | Non-5xx responses / all responses, excluding 429 | SLO 99.5% (budget ≈ 3.6 h/month) | OPS SLI dashboard; burn-rate alerts | R1 | ENG NFR-REL-01; PROD NFR-REL-01 |
| NFR-042 | Upload completion | Uploads reaching full length / uploads started and resumed by a live client | SLO 99.0% | OPS | R1 | ENG NFR-REL-02 |
| NFR-043 | Analysis success | Jobs reaching `full` or an explicit degraded level / jobs that passed the quality gate | SLO 97% | OPS | R2 | ENG NFR-REL-03 |
| NFR-044 | Analysis freshness | Jobs finished within the NFR-018 p90 / all jobs | SLO 90% | OPS | R2 | ENG NFR-REL-04 |
| NFR-045 | Durability and recovery | RPO and RTO for the database; loss of confirmed corrections; restore drill | RPO ≤ 24 h (daily backup + WAL), RTO ≤ 4 h measured in a quarterly restore drill; 0 confirmed corrections lost | Restore drill (R); I | R1 (before beta) | ENG NFR-REL-05 (judgment) |
| NFR-046 | Idempotent, disposable workers | (a) duplicate Event/Shot/Rally rows after killing a worker mid-stage and re-running; (b) time to requeue after SIGTERM; (c) API drain time | (a) 0; (b) ≤ 10 s; (c) ≤ 30 s | I (worker-crash regression suite) | R1 (queue exists in M0) gate | [AQS/OPS-02]; ENG §4.2; testing-strategy §5 |
| NFR-047 | Fail closed | Partial writes left after a failed stage or command | 0; the job is marked failed or degraded explicitly | I (fail-closed regression suite) | R1 gate | [AQS/SEC-12]; testing-strategy §5 |
| NFR-048 | Bounded retries | Attempts per stage before a terminal, user-visible `failed` state plus an alert | ≤ 3, with exponential backoff | I | R2 | ENG §4.2 (judgment; retry guidance unverified [AQS Gaps]) |
| NFR-049 | Error-budget policy | Sprints after a budget exhaustion that start with reliability work | 100% | R at sprint planning | R1 | applies [AQS/REL-02] (policy wording is judgment; SRE workbook unverified [AQS Gaps]) |

## 6. Security (target: OWASP ASVS 5.0 Level 2)

ASVS numbers come from a summarising fetch. Spot-check them against the raw ASVS markdown before quoting them in a story [AQS caveats; ENG §4.5 note].

| ID | Requirement | Metric | Target | How tested | Release | Source |
|---|---|---|---|---|---|---|
| NFR-050 | ASVS 5.0 L2 for API and client | Applicable L2 requirements passing or covered by an accepted-risk ADR | 100% at each release review | R (security-privacy-engineer checklist) | R1 gate | [AQS/SEC-01] |
| NFR-051 | Object-level authorisation (BOLA) | Endpoints taking a resource ID that are covered by the parametrised BOLA matrix; responses other than 404 for user B | 100% (an endpoint-inventory diff fails CI on any new uncovered route); 0 | I (BOLA regression suite) | R1 gate | [AQS/SEC-09]; [AQS/SEC-03] 8.2.2; [AQS/SEC-08] API9 inventory |
| NFR-052 | Field-level authorisation and deny-by-default | Responses not built from explicit allowlist schemas; write requests with unknown fields that are accepted; routes without an authz dependency | 0; 0; 0 | U + I | R1 gate | [AQS/SEC-03] 8.2.1, 8.2.3, 8.3.1; [AQS/SEC-08] API3 |
| NFR-053 | Upload safety | Invalid files accepted: wrong magic bytes or codec, > 10 GB, > 150 min. Storage keys derived from user input. Downloads without `Content-Disposition` | 0 for each (caps provisional pending R-05) | I (upload-validation regression suite) | R1 gate | [AQS/SEC-02] 5.2.1, 5.2.2, 5.3.1, 5.3.2, 5.4.1-5.4.2; conflict K12 |
| NFR-054 | Media-processing sandbox | Network destinations reachable from FFmpeg/worker sandboxes other than storage; jobs without CPU, memory and time limits; user filenames passed to tools | 0; 0; 0 | I + R (infra config) | R1 gate | [AQS/SEC-06] 13.2.4; [AQS/SEC-10]; ENG NFR-SEC-05 |
| NFR-055 | Media URLs | Signed URL TTL; long-lived tokens or session tokens in URLs | ≤ 15 min (judgment); 0 | I | R1 gate | [AQS/SEC-05] 14.2.1 |
| NFR-056 | Secrets and service identities | Secrets in repo or build artefacts (secret scan); default credentials; services sharing one credential | 0; 0; 0. Separate least-privilege identities for the API, CPU worker and GPU worker; GPU workers have no broad DB credentials | CI secret scan + R | R1 gate | [AQS/SEC-06] 13.2.1-13.2.3, 13.3.1-13.3.2; [AQS/OPS-01]; ENG §1.1 |
| NFR-057 | Security logging | Auth attempts and authz failures logged with when/where/who/what in UTC; credentials in logs; log-injection test cases passing; logs shipped off-host | 100%; 0; 100%; yes | I + R | R1 gate | [AQS/SEC-04] 16.2.1, 16.2.2, 16.2.5, 16.3.1-16.3.4, 16.4.1-16.4.3 |
| NFR-058 | Generic errors | Error responses containing stack traces, queries, secrets or internal IDs (other than a short support reference) | 0; a central handler plus a global fallback handler | I (error-body regression suite) | R1 gate | [AQS/SEC-04] 16.5.1; [AQS/SEC-12] |
| NFR-059 | LLM output and prompt-injection containment | Adversarial recorded responses that persist a plan (unknown drill, unknown metric, missing citation, constraint breach, injected instructions in user free text) | 0. User text sent inside delimited data tags; LLM tools limited to read-only drill/metric lookup | U + I (LLM-output regression suite) + LE | R2 gate (R1 has no LLM) | [AQS/SEC-08] API10; QD QD-TR-06; ENG NFR-SEC-11, NFR-SEC-15 (tool minimalism applying [AQS/AI-02] is judgment) |
| NFR-060 | Business-flow order | Analysis started before upload is complete and checksum-verified; corrections accepted on matches not in a scorable state | 0; 0 | I | R1 gate | [AQS/SEC-07] 2.3.1; [AQS/STACK-06] |
| NFR-061 | Hardening and client security headers | Production debug mode on; VCS metadata or directory listings exposed; responses missing CSP, `nosniff`, `X-Frame-Options: DENY` | 0; 0; 0 | I + automated header scan | R1 gate | [AQS/SEC-06] 13.4.1-13.4.3; [AQS/STACK-04] |
| NFR-062 | Supply chain and licences | Unpinned dependencies; builds without SBOM; open critical dependency findings; AGPL/non-commercial components, weights or datasets used in the product without an ADR | 0; 0; 0; 0 | CI scans + licence check + R | R1 gate | [AQS/SEC-11] A03 (controls are judgment [AQS G2.14]); [DOM/CV-05]; [DOM/CV-07]; [DOM/CV-09] |

### 6.1 Security: privacy (confidentiality)

Privacy **law** is unverified [AQS G3.5]. These NFRs are technical controls. They do not claim legal compliance.

| ID | Requirement | Metric | Target | How tested | Release | Source |
|---|---|---|---|---|---|---|
| NFR-063 | Data classification and per-class rules | Data classes documented with encryption, retention and access rules | High (videos, clips, thumbnails, pose/frame artefacts), Medium (nicknames, notes), Low (aggregated metrics): 100% of stored data types mapped before beta | R | R1 gate (before beta) | [AQS/SEC-05] 14.1.1, 14.1.2; ENG NFR-PRIV-01 |
| NFR-064 | Private by default | Endpoints or UI that expose a user's media or records to anyone but the owner | 0 in the MVP; no share links exist | I (BOLA suite) + R | R1 gate | spec §8; DES FR-UX-100; [AQS/SEC-03] |
| NFR-065 | No face recognition or inferred attributes | Face-recognition features, biometric templates, or inferred identity/age/attributes stored or shown | 0. Re-id features are within-match only and are deleted with frame artefacts | R (design and code review checklist) | R1 gate, permanent | spec §8; ENG NFR-PRIV-03; DES NFR-TRUST-08 (mapping to [DPA/DESIGN-11] G6 is judgment) |
| NFR-066 | Deletion and retention execution | (a) match hidden after delete; (b) all objects and rows purged after delete; (c) scheduled retention jobs completing on time; (d) abandoned uploads freed | (a) ≤ 1 min; (b) ≤ 7 days; (c) 100%, run daily; (d) ≤ 24 h after expiry | I (delete → assert storage and DB empty) + OPS | R1 gate | [AQS/SEC-05] 14.2.7; ADR 0006; conflicts K13-K15 |
| NFR-067 | Client-side data hygiene | Sensitive responses without `Cache-Control: no-store`; authenticated data left in client storage or service-worker caches after logout; media cached by the service worker | 0; 0; 0 | I + E2E | R1 gate | [AQS/SEC-05] 14.3.1-14.3.3; [AQS/STACK-04] |
| NFR-068 | Minimal data to the LLM | Prompts containing names, nicknames, notes, video, frames or raw events | 0 (pseudonymous labels and aggregates only) | U on the prompt builder + LE transcript review | R2 gate | ENG NFR-PRIV-07 (judgment) |
| NFR-069 | Pseudonymous logs | Log lines containing emails, names or signed media URLs | 0 | I (log scanner on test runs) | R1 gate | [AQS/SEC-04] 16.2.5; ENG NFR-PRIV-08 |
| NFR-070 | Legal gate before real users | A verified privacy/legal review (lawful basis, third-party footage, minors, retention, training use, jurisdictions) recorded as an ADR | Exists and accepted by the PO before any real-user beta | R | Gate for any real-user beta | [AQS G3.5, AQS Gaps]; ENG §4.6 blocker; OQ-05, OQ-06 |

## 7. Maintainability

| ID | Requirement | Metric | Target | How tested | Release | Source |
|---|---|---|---|---|---|---|
| NFR-071 | Coverage floors (a floor, not a goal) | Line/branch coverage on changed code | Rules engine and aggregates ≥ 95% line / ≥ 90% branch; analytics and coaching ≥ 90%; API ≥ 85%; worker deterministic code ≥ 85%; frontend ≥ 80% | CI coverage gate | R1 gate | testing-strategy §8 (judgment); QD QD-QG-P2 |
| NFR-072 | Rules-engine test strength | Mutation score on `sports/pickleball/rules` | ≥ 85% per sprint | Mutation run (tool is judgment) | R1 | QD QD-QG-S2 (judgment) |
| NFR-073 | Fast tests | Rules + domain unit suite; whole backend unit suite; integration suite | < 10 s; ≤ 60 s; < 10 min | CI timing | R1 gate | [EP/ENG-17] ("milliseconds… seconds"); budgets are judgment (QD QD-QG-P3; ENG NFR-PERF-07; testing-strategy §2) |
| NFR-074 | Flaky tests contained | Flaky rate over the sprint; time to quarantine | < 1% of runs; ≤ 1 day, with owner and fix-by date | CI analytics | R1 | testing-strategy §9; QD QD-QG-S3 (judgment) |
| NFR-075 | Reproducible outputs | Stored outputs missing `rules_version`, `pipeline_version`, `metric_def_version`, `library_version` or `prompt_version`; golden replay of stored rallies reproducing the stored score sheet byte for byte | 0; 100% | U + I | R1 gate | ENG §4.8; QD QD-TR-04, QD-TR-11; ddd-guidelines §4.7 |
| NFR-076 | Observability | (a) one trace per journey upload → analysis → plan, propagated through the queue; (b) structured JSON logs to stdout with UTC timestamp, trace_id, request_id, pseudonymous user_id, match_id and job_id; (c) malformed `traceparent` breaking a request; (d) required metrics emitted (ENG §4.7 list); (e) workers log model versions, weight hashes and thresholds at startup | (a) 100% of sampled journeys; (b) 100% of log lines; (c) 0; (d) 100%; (e) yes | I (trace-header regression suite) + OPS | R1 gate | [AQS/OPS-03]; [AQS/OPS-06]; [AQS/OPS-07]; [AQS/SEC-04]; [EP/ENG-20] |
| NFR-077 | Code standards and change size | Ruff lint and format errors; type errors in `scoring`, `analytics`, `coaching`; median PR size; PRs > 400 changed lines without an EM waiver | 0; 0 (strict mode); ~100 lines; 0 | CI + R | R1 | [AQS/STACK-05]; [EP/ENG-04]; 400-line ceiling is judgment (ADR 0001) |
| NFR-078 | Gold-set and test immutability | Gold files whose sha256 differs from the manifest; tests edited or deleted without QA approval | 0; 0 | CI manifest check + hooks | R1 gate | [EP/ENG-27]; [EP/ENG-28]; [DPA/AI-12]; QD QD-QG-P1 |
| NFR-079 | Rules and court facts are configuration | Rule constants or court dimensions as literals outside `RulesConfig` / `CourtModel` | 0 (lint/grep rule) | CI static check | R1 | QD §0 design principle, §3.2 note (judgment) |

## 8. Portability (flexibility)

| ID | Requirement | Metric | Target | How tested | Release | Source |
|---|---|---|---|---|---|---|
| NFR-080 | Dev/prod parity | Backing services in dev that differ from prod (DB, object store, queue) | 0: Postgres, S3-compatible store and the same queue via Docker Compose; no SQLite | R + I runs on Compose | R1 gate | [AQS/OPS-05]; [AQS/STACK-03] |
| NFR-081 | Stateless, env-configured processes | Process state kept between requests or jobs outside backing services; config constants in code | 0; 0 | R + I (kill/restart test) | R1 gate | [AQS/OPS-04]; [AQS/OPS-01] |
| NFR-082 | Sport plug-in extensibility | Files changed outside `sports/<sport>/` and a registration point to add a stub second sport (court model, rules, taxonomy, metrics, drills) | 0, proven by a stub-sport contract test | U/I contract test | R2 | spec §3 plug-in interface; ddd-guidelines §3 Published Language (judgment) |

---

## 9. Counts

| ISO/IEC 25010 heading (judgment filing) | NFRs |
|---|---|
| Functional suitability | 9 (NFR-001..009) |
| Performance efficiency: time behaviour | 10 (NFR-010..019) |
| Performance efficiency: resource use and cost | 4 (NFR-020..023) |
| Compatibility | 3 (NFR-024..026) |
| Usability (incl. accessibility, human-AI) | 14 (NFR-027..040) |
| Reliability | 9 (NFR-041..049) |
| Security | 13 (NFR-050..062) |
| Security: privacy | 8 (NFR-063..070) |
| Maintainability | 9 (NFR-071..079) |
| Portability | 3 (NFR-080..082) |
| **Total** | **82** |

By earliest release:

- R1: 66
- R2: 12
- R3: 2 (NFR-007, NFR-040)
- milestone gates not tied to one release: 2 (NFR-003 "official scoring" and NFR-070 "real-user beta")

See `traceability-matrix.md` §4 for the per-ID mapping.
