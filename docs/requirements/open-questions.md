# Open Questions for the Human Product Owner

- **Status:** Answered 2026-10-05. The human product owner replied "accept all recommendations"; every recommendation below is accepted and recorded in [ADR 0023](../decisions/0023-product-owner-decisions-2026-10-05.md). The PO's later input of the same day ([`po-input-2026-10-05.md`](po-input-2026-10-05.md): US and AU jurisdictions; rulebook later) is folded in. Residual items that need a PO input (rulebook files, budget amount, recruitment, legal review) stay open in the "Still open" column. Answers are recorded as ADRs, either a new ADR or a dated note on the Proposed ADR named in the row [docs/decisions/README.md "Escalations"]. **2026-10-06:** the PO's addenda of that day (Sprint 1 close P1-P5, PR #1 merge order, the Go port in Sprint 6, the private footage bucket, repository visibility) are folded into the ADR 0023 note of 2026-10-06. No OQ answer changes. Still open: OQ-01 rulebook (P7, 2026-11-16), OQ-13 budget amount (P8), OQ-20 recruitment (P9), the OQ-05 legal review before any real-user beta (US and AU), and two new PO items outside the OQ list: P10 (GitHub reports the repository as public; the record says private) and P11 (provider of the private footage bucket). **2026-10-08 (Sprint 3 close):** the PO's addenda of 2026-10-07 are folded into the ADR 0023 note of 2026-10-08: P12 option (b) (human-gated items become sprint-DoD rows), Sprint 3 scope confirmed, PR #2 merged, and the ticket-level PR rule (ADR 0039). The rule's start sprint is the new PO item P13, because the "Sprint 4" date was the agents' text, not the PO's. No OQ answer changes. Still open: OQ-01 (P7), OQ-13 (P8), OQ-20 (P9), the OQ-05 legal review, P6, P10, P11 and P13.
- **Date:** 2026-10-03
- **Author:** business-analyst, consolidating the open-question lists of all four brainstorms (PROD §13, ENG §10, DES §12, QD §11) and the spec's §9. Duplicates are merged.
- **How to answer:** reply with the OQ number and "accept the recommendation" or your alternative. Questions marked **Blocking** stop the named work until answered.

## Summary

| OQ | Question (short) | Blocks | Team recommendation | Status (2026-10-05) | Still open (owner) |
|---|---|---|---|---|---|
| OQ-01 | Supply the 2026 USAP rulebook | R1 "official scoring", 18 FRs | Yes, you supply the PDFs | Accepted; ADR 0009 Accepted | **Rulebook PDFs to be supplied** (PO). Scoring presets stay PROVISIONAL-UNVERIFIED, rows `@needs-verification` |
| OQ-02 | Approve the R1/R2 MVP slicing | Sprint planning | Accept ADR 0002 | Accepted; ADRs 0002, 0007 Accepted | — |
| OQ-03 | Which federations' rules? | Rules presets | USAP only for v1 | Accepted | — |
| OQ-04 | Rally scoring in R1? | FR-043 | No, R2 after verification | Accepted | Rule verification via OQ-01 |
| OQ-05 | Age, minors, jurisdictions, legal review | Real-user beta | 18+, no minors, one jurisdiction, legal pass first | Accepted; jurisdictions named 2026-10-05: **US and AU** (PO chose two; ADR 0023 note) | **Legal review before any real-user beta, covering US (incl. state video/biometric privacy laws) and AU (Privacy Act 1988 / APPs)** (PO, security) |
| OQ-06 | Third-party footage in gold sets; training consent | Gold sets, FR-009, FR-150 | Opt-in consent; legal pass first | Accepted | Legal pass (with OQ-05) |
| OQ-07 | Retention and deletion windows | FR-006/008/024, NFR-066 | Accept ADR 0006 | Accepted; ADR 0006 Accepted (interim) | Legal adequacy (OQ-05 review) |
| OQ-08 | Weakness unit: rallies lost per game | FR-120 | Accept ADR 0003 | Accepted; ADR 0003 Accepted | Coach verifies the rule after OQ-01 |
| OQ-09 | Redefine M2/M3 accuracy targets | R2/R3 gates | Accept ADR 0004 | Accepted; ADR 0004 Accepted | — |
| OQ-10 | Confidence as 3 word bands | FR-090, NFR-008 | Accept | Accepted | — |
| OQ-11 | Calibration: any ≥ 4 points, no drag | FR-082 | Accept | Accepted | — |
| OQ-12 | CV licences: MIT/Apache only vs Ultralytics Enterprise | R2 vision work | MIT/Apache only unless SPIKE-01 shows a gap | Accepted; ADR 0015 Accepted | PE/security reviews of SPIKE-01 evidence |
| OQ-13 | Monthly spend ceiling; quota sizes | FR-160/161, NFR-022 | Set a beta budget; quotas at P75 usage | Accepted | **Budget amount to be named** (PO) by the Sprint 2 review |
| OQ-14 | Monetisation direction to test first | FR-162 | Fake door: freemium (manual free, auto paid) | Accepted | Model chosen after MA-1/MA-2 data |
| OQ-15 | Opponent scouting: v1 promise or later? | E12 | Later, after privacy pass | Accepted (Won't for MVP) | — |
| OQ-16 | Drop "height over the net" | Data model | Yes, drop from v1 | Accepted | — |
| OQ-17 | Reference device; is iOS Safari release-blocking? | NFR-011, NFR-024 | Mid-range Android + iPhone Safari both blocking | Accepted | WebKit/iOS CI runs (SRE, ST-002 carry-over) |
| OQ-18 | Upload copy: "resume on return" or native app earlier | FR-022 | Resume on return; decide native after SPIKE-06 | Accepted | Native wrapper after SPIKE-06 |
| OQ-19 | English only in v1? | Copy, score calls | Yes | Accepted | — |
| OQ-20 | Recruit testers, interviewees and a second coach | NFR-036, R-01, QD-AN-03 | Yes: ≥ 5 testers, ≥ 8 interviews, 1 second coach | Accepted | **Recruitment is a PO action**, by Sprint 3 planning |
| OQ-21 | Product name | Branding only | Keep "racket-analytics" as working name | Accepted | — |
| OQ-22 | Coach multi-player view in v1.x? | E14 | Not in the MVP; revisit after R2 interviews | Accepted (Won't for MVP) | — |

---

## Details

### OQ-01 Supply the 2026 USA Pickleball Official Rulebook and change document (Blocking)
- **Why:** No pickleball rule is verified. usapickleball.org, pickleballcanada.org, the GPF site and Wikipedia were all egress-blocked. QD re-tried on 2026-10-03 and got 403 [DOM G1, DOM Gaps 1; QD §0].
  - 18 FRs are `needs-verification`, 11 of them R1 Musts.
  - Without the rulebook, R1 ships only as "unofficial scoring" (FR-055, NFR-003).
- **Recommendation:** You supply the PDFs [DOM/DOMAIN-01, DOM/DOMAIN-02, both unverified]. The pickleball-domain-coach then records the rule number and wording for R1-R6 in `docs/domain/rules-verified.md`. The engine is parameterised (FR-040), so only config values and test tables change.
- **Answer (2026-10-05, human product owner):** recommendation accepted (ADR 0023); ADR 0009 is Accepted. Still open: **Rulebook PDFs to be supplied** (PO). Scoring presets stay PROVISIONAL-UNVERIFIED, rows `@needs-verification`.
- **Raised by:** PROD Q2, ENG Q4, QD Q1.

### OQ-02 Approve the MVP slicing (Blocking for sprint planning)
- **Why:** The spec delivers a training plan only at M5, after four vision milestones (spec §7). All four brainstorms propose that R1 closes "upload → stats → plan" on manual Quick Tag, with no CV. This changes the M0/M5 scope.
- **Recommendation:** Accept ADR 0002:
  - R1 is the walking skeleton.
  - R2 is first automation plus LLM explanations.
  - R3 is automatic scoring.
  - M6/M7 come later.
- **Answer (2026-10-05, human product owner):** recommendation accepted (ADR 0023); ADRs 0002 and 0007 are Accepted. Still open: nothing.
- **Raised by:** PROD Q1, ENG §0.1.

### OQ-03 Which rulebook editions must v1 support?
- **Why:** Pickleball Canada and the GPF publish their own 2026 documents [DOM/DOMAIN-04, DOM/DOMAIN-05, unverified].
- **Recommendation:** USAP only for v1. Other federations become extra `RulesConfig` presets later, with no engine change.
- **Answer (2026-10-05, human product owner):** recommendation accepted (ADR 0023). The PO will upload the PDFs later ([`po-input-2026-10-05.md`](po-input-2026-10-05.md)). Still open: **rulebook PDFs to be supplied** (PO), need-by Sprint 3 planning, 2026-11-16. Until then presets stay `PROVISIONAL-UNVERIFIED` and rows stay `@needs-verification` (ADR 0009).
- **Raised by:** PROD Q3, QD Q2.

### OQ-04 Should rally scoring be in R1?
- **Why:** Rally scoring is reported as a provisional rule, and its 2026 game-point change and doubles rotation are unverified [DOM G1 R3].
- **Recommendation:** R2. The engine flag exists from R1. No preset ships with a guessed rotation rule (FR-043).
- **Answer (2026-10-05, human product owner):** recommendation accepted (ADR 0023). Still open: Rule verification via OQ-01.
- **Raised by:** QD Q3.

### OQ-05 Minimum age, minors in footage, target jurisdictions and legal review (Blocking for any real-user beta)
- **Why:** Children's-data, biometric and lawful-basis rules are unverified [AQS G3.5, AQS Gaps]. The spec says videos may show minors (spec §8).
- **Recommendation:**
  - Account holders confirm they are 18+ (FR-003).
  - The capture guide asks users not to upload matches with minors.
  - The beta runs in a single jurisdiction that you choose.
  - No real-user beta happens until a verified privacy/legal review is recorded as an ADR (NFR-070).
- **Answer (2026-10-05, human product owner):** recommendation accepted (ADR 0023). Later the same day the PO named the beta jurisdictions: **United States and Australia** ([`po-input-2026-10-05.md`](po-input-2026-10-05.md); ADR 0023 note). The recommendation was one jurisdiction; the PO chose two. Still open: **legal review before any real-user beta** (PO, security). It must cover the US (including state privacy laws relevant to video and biometrics) and AU (Privacy Act 1988 / APPs).
- **Raised by:** PROD Q4, ENG Q4/Q8.

### OQ-06 Third-party footage in gold sets, and training use of user video
- **Why:** Using a user's video to train models is a different purpose from analysing their own match (judgment). Gold sets show third parties. Revoked consent conflicts with frozen gold sets (ENG NFR-PRIV-06).
- **Recommendation:**
  - Training use requires a separate opt-in that is off by default and revocable (FR-009). Full Tag works only on consented matches (FR-150).
  - When consent is revoked, the match leaves all *future* gold-set versions. Frozen historical versions are retired at their next scheduled refresh rather than edited (judgment, which keeps NFR-078).
  - Until the legal pass, build gold sets only from footage the team records with written consent from everyone filmed.
- **Answer (2026-10-05, human product owner):** recommendation accepted (ADR 0023). Still open: Legal pass (with OQ-05).
- **Raised by:** ENG Q6, QD Q4.

### OQ-07 Retention and deletion defaults
- **Why:** The brainstorms disagreed (conflicts K13-K15). Legal adequacy is unverified [AQS G3.5].
- **Recommendation:** Accept ADR 0006:
  - Original video is deleted 30 days after analysis.
  - The review video follows the user's setting, default 90 days.
  - Abandoned uploads are freed after 24 h.
  - A deleted match is hidden within 1 min and purged within 7 days.
  - **Consequence to accept:** re-processing after 30 days uses the 720p review video or is unavailable.
- **Answer (2026-10-05, human product owner):** recommendation accepted (ADR 0023); ADR 0006 is Accepted as interim defaults. Still open: Legal adequacy (OQ-05 review).
- **Raised by:** PROD Q5, ENG Q3.

### OQ-08 Rank weaknesses by "rallies lost per game" instead of "points lost per match"
- **Why:** Under side-out scoring a rally lost on serve concedes no point, so the spec's unit undercounts serving-side errors (QD X1; depends on the unverified [DOM G1 R2]).
- **Recommendation:** Accept ADR 0003.
- **Answer (2026-10-05, human product owner):** recommendation accepted (ADR 0023); ADR 0003 is Accepted. Still open: Coach verifies the rule after OQ-01.
- **Raised by:** QD Q5.

### OQ-09 Redefine the M2 and M3 accuracy targets
- **Why:**
  - "≥ 90% of rallies segmented correctly" leaves "correct" undefined.
  - "≤ 1 correction per game" implies about 96-97% accuracy on every score-affecting field, which conflicts with the spec's own one-camera premise (ENG §5.4).
- **Recommendation:** Accept ADR 0004:
  - M2 becomes rally-segmentation F1 ≥ 90%, with ±1.0 s matching and no merge or split.
  - M3 becomes ≤ 2.0 score-affecting corrections per game plus ≤ 5 confirmations, with unflagged rallies ≥ 95% correct.
  - ≤ 1.0 correction per game stays as a later target.
- **Answer (2026-10-05, human product owner):** recommendation accepted (ADR 0023); ADR 0004 is Accepted. Still open: nothing.
- **Raised by:** PROD C8/C9, ENG Q5, QD X9.

### OQ-10 Show confidence as 3 word bands backed by gold-set accuracy
- **Why:** A raw probability is not a real-world accuracy (DES CD4). HAX asks us to make clear how well the system does what it does [DPA/DESIGN-11] G2. This makes band calibration a model release gate (NFR-008).
- **Recommendation:** Accept "Sure / Likely / Check this", with the raw % in a details view.
- **Answer (2026-10-05, human product owner):** recommendation accepted (ADR 0023). Still open: nothing.
- **Raised by:** DES Q1.

### OQ-11 Replace "confirm 4 corners" with "confirm any 4 or more named court points, no dragging required"
- **Why:**
  - WCAG 2.2 SC 2.5.7 requires a non-drag alternative [DPA/DESIGN-05].
  - Near corners are often out of frame (DES CD2, judgment).
  - More points help a robust fit [DOM G6 H2, partly inferred].
- **Recommendation:** Accept (FR-082).
- **Answer (2026-10-05, human product owner):** recommendation accepted (ADR 0023). Still open: nothing.
- **Raised by:** DES Q3.

### OQ-12 Computer-vision licence posture
- **Why:** Ultralytics YOLO is AGPL-3.0 or a paid Enterprise licence [DOM/CV-05]. BoxMOT is AGPL-3.0 [DOM/CV-07]. MIT/Apache alternatives exist: ByteTrack [DOM/CV-04], supervision [DOM/CV-16], MMPose/RTMPose [DOM/CV-11] and TrackNetV3 [DOM/CV-01].
- **Recommendation:** Use an MIT/Apache-only stack by default. Budget for Enterprise only if ENG SPIKE-01 shows a measured accuracy or cost gap. NFR-062 blocks any AGPL component without an ADR.
- **Answer (2026-10-05, human product owner):** recommendation accepted (ADR 0023); ADR 0015 is Accepted. Still open: PE/security reviews of SPIKE-01 evidence.
- **Raised by:** ENG Q1.

### OQ-13 Monthly spend ceiling for beta (GPU, LLM, storage) and quota sizes
- **Why:** At the ENG design point, GPU is the dominant cost: about 6,000 GPU-h/month for 1,000 MAU at 1.5 GPU-min per match-minute (ENG §4.3, judgment). No verified GPU price source exists (PROD MA-4).
- **Recommendation:**
  - Set a monthly beta budget. Alerts fire at 50/80/100% (NFR-022).
  - The analysed-minutes quota starts at 180 min per month (placeholder) and is reset to the P75 of measured usage after R1 (PROD MA-3).
  - Rate limit: 10 jobs per hour per user.
- **Answer (2026-10-05, human product owner):** recommendation accepted (ADR 0023). Still open: **Budget amount to be named** (PO) by the Sprint 2 review.
- **Raised by:** PROD Q8, ENG Q2.

### OQ-14 Which monetisation model to test first?
- **Why:** The spec leaves this open (spec §9). Free manual tagging is cheap. Automatic analysis carries GPU cost (PROD MA-2).
- **Recommendation:** Test a freemium split through a fake-door pricing page in R1 (FR-162): manual Quick Tag plus the plan are free, automatic analysis is paid. Decide after MA-1/MA-2 data. No payments in the MVP.
- **Answer (2026-10-05, human product owner):** recommendation accepted (ADR 0023). Still open: Model chosen after MA-1/MA-2 data.
- **Raised by:** PROD Q6, spec §9.

### OQ-15 Is opponent scouting a v1 promise or a later upsell?
- **Why:**
  - Opponent profiles are personal data about non-users, and privacy law is unverified [AQS G3.5].
  - Amateurs meet the same opponent rarely, so samples are small (PROD C5).
- **Recommendation:** Later (Won't for this MVP). Gate it on OQ-05/OQ-06 and validate the demand with a fake door (PROD MA-5).
- **Answer (2026-10-05, human product owner):** recommendation accepted (ADR 0023); Won't for this MVP. Still open: nothing.
- **Raised by:** PROD Q7.

### OQ-16 Drop "height over the net" from v1
- **Why:** A homography maps only points on the court plane [DOM/CV-12].
- **Recommendation:** Drop it. Revisit only if a later 3D-trajectory spike succeeds.
- **Answer (2026-10-05, human product owner):** recommendation accepted (ADR 0023). Still open: nothing.
- **Raised by:** ENG Q7, DES CD5.

### OQ-17 Reference device, network and browsers
- **Why:** The performance and compatibility NFRs need a fixed lab profile (NFR-011, NFR-024).
- **Recommendation:**
  - Reference profile: mid-range Android (about 4 GB RAM) on 4G throttled to 9/1.5 Mbps.
  - Release-blocking browsers: iOS Safari and Android Chrome, current and previous major versions. Many amateurs film on iPhones (judgment).
- **Answer (2026-10-05, human product owner):** recommendation accepted (ADR 0023). Still open: WebKit/iOS CI runs (SRE, ST-002 carry-over).
- **Raised by:** DES Q4.

### OQ-18 Upload copy: "resume when you return", or a native wrapper earlier than planned?
- **Why:** A PWA cannot be relied on to keep uploading after the tab closes (DES FR-UX-31, judgment; no verified source either way).
- **Recommendation:** Use honest "resume on return" copy in R1 (FR-022). Decide on a native wrapper after ENG SPIKE-06 measures completion rates on iOS Safari and Android Chrome.
- **Answer (2026-10-05, human product owner):** recommendation accepted (ADR 0023). Still open: Native wrapper after SPIKE-06.
- **Raised by:** DES Q6.

### OQ-19 Is v1 English only?
- **Recommendation:** Yes. Copy length budgets and the score-call format assume English.
- **Answer (2026-10-05, human product owner):** recommendation accepted (ADR 0023). Still open: nothing.
- **Raised by:** DES Q7.

### OQ-20 Recruit participants
- **Why:** Several targets are hypotheses until tested with people:
  - Quick Tag effort (NFR-036);
  - personas (PROD R-01);
  - metric and taxonomy agreement checks (QD-AN-03, QD-TX-03).

  Agents cannot recruit (designer and PM boundaries).
- **Recommendation:**
  - ≥ 5 amateur players for moderated tests at R1 exit and before the R2 review queue ships.
  - ≥ 8 interviews before R2 priorities are fixed.
  - One second qualified coach, or a 4.0+ player, for agreement checks.
- **Answer (2026-10-05, human product owner):** recommendation accepted (ADR 0023). Still open: **Recruitment is a PO action**, by Sprint 3 planning.
- **Raised by:** DES Q5, PROD R-01, QD Q6.

### OQ-21 Product name
- **Recommendation:** Keep "racket-analytics" as the working name. This does not block anything.
- **Answer (2026-10-05, human product owner):** recommendation accepted (ADR 0023). Still open: nothing.
- **Raised by:** spec §9, PROD Q9.

### OQ-22 Coach multi-player view in v1.x
- **Recommendation:** Not in the MVP (Won't). Validate it with 5 coach interviews (PROD MA-6) after R2.
- **Answer (2026-10-05, human product owner):** recommendation accepted (ADR 0023); Won't for this MVP. Still open: nothing.
- **Raised by:** spec §9.
