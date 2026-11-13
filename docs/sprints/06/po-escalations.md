# Sprint 6 PO escalation note (EM-ESC-06)

- **To:** the human product owner (PO). **From:** engineering-manager. **Sent:** 2026-11-13, before the 2026-11-14 send-by date in `docs/sprints/sprint-06.md` §3.6 (Wave 1).
- **Why one note:** working-agreement §8 says the EM escalates with the question, options, recommendation, evidence and deadline. Kickoff PM-5, PE-2, EM-3, PD-3 and SEC-5 (`docs/sprints/06/kickoff.md` §2 and §5) route their PO questions here. Each question is asked **once**, with options, the cost of each option, a default and a need-by date.
- **Status:** team text (ADR 0047). **None of the defaults below is a PO decision.** A default is only what the team does while there is no answer. It never changes a PO decision, spends money, waives a review or accepts a risk on the PO's behalf. Answers count only when they are quoted verbatim in `docs/requirements/po-input-2026-10-05.md`.
- **Until an item is answered**, agents work only on what does not depend on it (working-agreement §8). Human-only items stay "not met: waiting on P-n" rows in `docs/sprints/06/goal-scorecard.md` §5.
- **Not re-asked here:** P8 (GPU budget), P9 (usability testers), P6, P10, P17, P18 and P20 are still open from `docs/sprints/05/po-escalations.md`. Their questions and defaults there are unchanged; answer them there.

## 0. Your instruction of 2026-11-12, as recorded

Quoted verbatim in `docs/requirements/po-input-2026-10-05.md`, addendum "Video analysis (PO 2026-11-12)":

> resume sprint 5, please try to finish the local docker running and start local prototype first, then fix the CI/CD then adding analyse the videos from training, pro matches, ... getting best practices and patterns, then work out any weaknesses and provide or recommend the exercises to fix those weaknesses

For information, no answer needed: the team reads "resume sprint 5" as "close Sprint 5 first", so the 13 open Sprint 5 PRs, VERIFY-05 and RETRO-05 run before any Sprint 6 build ticket (entry condition E1, sprint-06 §3.6; kickoff EM-1). The local stack and prototype run (`make up` + `make demo` verified 2026-11-12). The CI/CD fixes are the open Sprint 5 PRs #230 (CI-FFMPEG) and #232 (CI-NIGHTLY-PERF), first in the drain.

## 1. Summary: what we need from you, by date

The quickest way to reply is one line per item, for example "P21: B; P22: a; Q1: a". The `#` column is the id to answer with.

| # | Question (short) | Recommended | Default if no answer | Need-by |
|---|---|---|---|---|
| P21 | Sprint 6 = video analysis and the Go port in Sprint 7? (conflicts with your 2026-10-06 decision) | B: slice first | B: tag-based slice in S6, Go port in S7; the 2026-10-06 decision is not marked as changed | **2026-11-17** |
| P22 | May the reference library cite published secondary statistics? (A5) | a | a: yes, only when the citation resolves, labelled "published source" | **2026-11-17** |
| D1 | DR-04 on the shipped Sprint 4 screens: hold it or waive it? (carried from EM-ESC-05) | a: hold | not held; PD-DR04-01..03 stay Open | **2026-11-17** |
| Q1 | What does the "..." in "training, pro matches, ..." cover? (A-Q1) | your words | the team adds nothing: training and pro matches only | 2026-11-26 |
| Q4 | Should players ever run Full Tag on their own videos? (A3) | a: no, for R2 planning | a: Full Tag stays labeller-only (FR-150) | 2026-11-26 |
| P15 | Human coach verification of drills and reference patterns | A now, B before any public beta | everything stays `coach-reviewed` with the UI notice | 2026-11-24 |
| P7 | Rulebook, or accept "unofficial scoring" (re-ask) | A, and B as soon as possible | stays unofficial; rule-dependent patterns labelled unverified | 2026-11-24 |
| P19 | Residual-risk ADR 0059 (re-ask) | a: decide row by row | ADR stays Proposed; no deployment beyond localhost | 2026-11-26 |
| P11 | Pro-match footage with rights and consented training footage (re-ask, wider scope) | a | no CV story Ready; reference values stay coach judgment | S8 planning |
| P16 | Legal review, now also covering training-video consent, pose data and derived statistics (re-ask, wider scope) | a: commission now | flags stay off; no real user, no real-person pose spike | before any real user or real-person footage |

P21 has the most effect: it decides whether Sprint 6 or Sprint 7 holds the Go port. P22 and D1 come next, because COACH-6a and the Sprint 6 design work wait on them.

## 2. Decisions that change this sprint's scope or order

### P21. Sprint 6 = video analysis, Go port in Sprint 7? (A-Q2)

- **Question:** your decision "Port the product to Go (PO decision 2026-10-06)" sets the timing as "Sprint 6, directly after the R1 release candidate (Sprint 5), before any computer-vision work." Your instruction of 2026-11-12 orders the work as local stack, then CI/CD, then video analysis. The orchestrator proposed, and the team confirmed at kickoff, "Sprint 6 becomes the first video-analysis sprint as the PO's order requires, and the Go port moves to Sprint 7". That is **not your decision** (`docs/requirements/po-input-2026-10-05.md`, "Orchestrator note (2026-11-12) … not a PO decision"). Which order do you want?
- **Options** (the principal-engineer's three options, kickoff PE-2 and §5 item 1; the cost figures are measured by the EM from `origin/main` and listed in the evidence line):

| Option | What happens | Cost |
|---|---|---|
| **A. Port first** | Sprint 6 is the Go port (after the Sprint 5 close). The video-analysis slice moves to Sprint 7. | Video analysis starts one sprint later than your 2026-11-12 order. The Sprint 6 plan (45 tickets) is re-planned. The port covers today's Python: 20,357 lines of backend product code, 50,736 lines of backend tests, 11,278 lines of scripts and 1,725 lines of docs tools (≈ 84,000 lines, 918 files). No Python growth before the port. Your port definition of done says to split it (strangler) up front if parity cannot be reached in one sprint; at this size that split is likely (judgment, to be settled by the port ADR). |
| **B. Slice first, then port (recommended, default)** | Sprint 6 builds the tag-based video-analysis slice (reference patterns, player-vs-reference gaps, exercises), with no computer-vision code in the product and no new framework. The Go port is Sprint 7. R2 CV sprints move back one sprint (roadmap §6: S8-S10). | Python grows before the port. Upper bound: 16 backend and ML code tickets × the 400-line production limit (ADR 0054) = 6,400 production lines; for scale, Sprint 5 so far added 317 backend production lines, 3,427 backend test lines and 3,324 tooling lines. The new code is pure domain functions and JSON content (kickoff PE-5), so it ports as plain functions. It follows your 2026-11-12 order. It departs from the 2026-10-06 timing in the sprint number only: no computer-vision work enters the product in Sprint 6. |
| **C. Strangler port alongside** | Sprint 6 writes the new slice in Go from the start, while the rest stays Python and is ported context by context. | A port ADR, a Go toolchain and a Go CI job are needed before the first slice ticket (principal-engineer, SRE), so the slice starts later and is smaller: Sprint 6 is already planned at 26.5 of 30.6 units, with 25 % reserved for the Sprint 5 drain. Main runs two languages for several sprints; your definition of done allows that only when the plan says so up front ("never ship a half-ported main"). Almost no Python growth. |

- **Recommendation:** B. It is the only option that ends Sprint 6 with the demo you asked for (`make up` + `make demo`) without breaking roadmap §7.1, and most of it survives either answer (sprint-06 §0.6, option A of the brainstorm).
- **Default if no answer:** B. The team proceeds with the tag-based slice and plans the Go port at S7 planning. The 2026-10-06 decision is **not** recorded as changed; roadmap S7 keeps "if P21 confirms the re-plan", and row S6-P21 stays "not met: waiting on P21".
- **Evidence:** `docs/requirements/po-input-2026-10-05.md` addenda "Port the product to Go (PO decision 2026-10-06)" and "Video analysis (PO 2026-11-12)"; `docs/sprints/roadmap.md` §6 rows S6-S8; `docs/sprints/sprint-06.md` §2 and §10 row 1. Sizes: `git ls-files 'backend/*.py' | grep -v '/tests\?/' | xargs cat | wc -l` → 20357; the same with `grep '/tests\?/'` → 50736; `git ls-files 'scripts/*.py' | xargs cat | wc -l` → 11278; `git ls-files 'docs/*.py' | xargs cat | wc -l` → 1725; `git ls-files '*.py' | wc -l` → 918 (all at `origin/main` `91a58c78`). Sprint 5 growth: `git diff --numstat 49b76cb3 origin/main` over the same paths (PLAN-05 commit to now).
- **Need-by:** 2026-11-17, the Wave 1 merge-by date, before any Sprint 6 build ticket starts.

### P22. May the reference library cite published secondary statistics? (A5)

- **Question:** the reference pattern set (COACH-6a) needs values for pro play, for example how often pros hit a third-shot drop rather than a drive. We hold no pro-match footage with rights (P11), so no value can be measured by us. May an entry cite a statistic that someone else published (an article, a coaching book, a published analysis), with the source named?
- **Options:**

| Option | What happens | Cost |
|---|---|---|
| **a. Yes, when the citation resolves (recommended, default)** | An entry may carry a published value only when its source resolves in `docs/domain/sources.md` (planned), labelled "published source", never "measured". Numbers are cited with attribution, never copied in bulk. | No extra work beyond the sources register already planned. Risk: a published number may be wrong or from a different level of play; the level bands and the "published source" label show that. |
| b. No | Entries carry only coach judgment, labelled "coach judgment, not measured from pro matches", until P11 footage exists. | Fewer entries with a number; more gaps show as "no reference yet". COACH-6a re-labels any cited value. |
| c. Yes, but only after the legal review (P16) | As (a), but no published value is shown before P16 is answered. | Same as (b) until P16 is answered. |

- **Recommendation:** (a).
- **Default if no answer:** (a). If you later answer (b) or (c), entries are re-labelled (scorecard row S6-P22).
- **Evidence:** `docs/sprints/06/requirements-breakdown.md` §6 row A5; `docs/sprints/sprint-06.md` §0.4; kickoff §5 item 3.
- **Need-by:** 2026-11-17, before COACH-6a merges.

### D1. DR-04 never held: hold it now or waive it (carried from EM-ESC-05)

Asked first in `docs/sprints/05/po-escalations.md` D1 (deadline 2026-11-05). No answer is recorded, so the default applied: DR-04 is still "not held" (`docs/design/flows-sprint-04.md` §14.7, 2026-11-12). The question and options are unchanged; the cost line is new.

| Option | What happens | Cost |
|---|---|---|
| **a. Hold (recommended)** | The orchestrator invokes the five decider roles with the §14.4 brief; each commits its own cell; every reject becomes a ledger row. | Five short agent reviews, inside the Wave 1 dates. |
| b. Waive | You record a waiver for the shipped Sprint 4 screens. PD-DR04-01 (major: no confirmation before a shorter retention period deletes videos), PD-DR04-02 and PD-DR04-03 stay Open with owners. | No review time. The major gap stays open until its ticket is built; `feature_retention_setting` stays off until then. |
| c. Wait | Nothing until after Sprint 6. | Repeats retro-04 M5 for a third sprint. |

- **Recommendation:** (a).
- **Default if no answer:** DR-04 stays "not held"; no waiver is assumed; the three gaps stay Open (row S6-D1).
- **Evidence:** `docs/design/flows-sprint-04.md` §14.5 and §14.7; `docs/sprints/05/review-rounds.md` rows PD-DR04-01..03; kickoff PD-3.
- **Need-by:** 2026-11-17.

## 3. Scope questions about video analysis

### Q1. What does the "..." in your list cover? (A-Q1)

- **Question:** your instruction says "analyse the videos from training, pro matches, ...". The team does not expand the "..." (`docs/requirements/po-input-2026-10-05.md`). What else, if anything, did you mean? The options below are examples to make answering quick, not the team's reading.

| Option | What happens | Cost |
|---|---|---|
| **a. Nothing more for now** (default) | Training and pro matches only. | None. |
| b. The player's own recreational or league matches | Already in R1: the player uploads a match and Quick Tags it; the slice ranks those measures against the reference. | None new; confirms the current scope. |
| c. Opponents' matches (scouting) | A new requirement; out of scope in sprint-06 §1. | A new FR, third-party personal data (P16), footage rights (P11); R2 at the earliest. |
| d. Solo or ball-machine practice video | A new capture type with no rally structure. | A new FR and CV work under roadmap §7.1; R2 at the earliest. |
| e. Something else | Your words, recorded verbatim. | Planned at the next sprint planning. |

- **Recommendation:** none; only you know what you meant.
- **Default if no answer:** (a). The team adds nothing.
- **Evidence:** `docs/sprints/06/requirements-breakdown.md` §6 row A-Q1; kickoff §5 item 2.
- **Need-by:** 2026-11-26, so S7 planning has it.

### Q4. Full Tag for players? (A3)

- **Question:** FR-150 makes Full Tag an internal tool for the labeller role. Some patterns (third-shot drop vs drive, dink tolerance, return depth) need Full Tag data. In Sprint 6 the demo player's Full Tag matches are team-made fixtures. Should players ever Full Tag their own videos?

| Option | What happens | Cost |
|---|---|---|
| **a. No (default)** | Full Tag stays labeller-only. Players get Full Tag patterns only when CV can produce them (R2, after P11). | Real players see only Quick Tag patterns until then. |
| b. Yes, a player-facing Full Tag in R2 | A new FR, flows and a design review. | Tagging effort per match rises well above Quick Tag (judgment), which works against the ≤ 15-minute effort goal (NFR-036); a usability check with players (P9). |
| c. A short "pattern tag" for players | Players tag only the 2-3 fields the patterns need. A new FR in R2. | Smaller than (b), but still a new FR, flows and a usability check. |

- **Recommendation:** (a) for now; revisit at R2 planning with the P9 results.
- **Default if no answer:** (a).
- **Evidence:** `docs/requirements/functional-requirements.md` FR-150; `docs/sprints/06/requirements-breakdown.md` §6 row A3; sprint-06 §0.6 ("Parked").
- **Need-by:** 2026-11-26.

## 4. Human inputs re-asked (each a `goal-scorecard.md` §5 row)

### P15. Human coach verification of drills and reference patterns (re-ask)

Asked first in EM-ESC-05 (deadline 2026-11-10); no answer is recorded, so its default applies. The scope is wider now: the new reference pattern entries need the same check.

| Option | What happens | Cost |
|---|---|---|
| **A. Accept the fallback** | Drills and reference entries stay `coach-reviewed` (agent role) with the UI notice and safety notes. | Drill and reference quality is the agent's judgment. |
| B. Name a human coach | Reviewed items move to `verified`. | About 5 minutes per drill (judgment, `docs/domain/po-fallback-p7-p15.md`); 32 drills are `coach-reviewed` today, plus the new pattern entries. |
| C. Hide drills and references until verified | The plan and weakness view show no content. | The Sprint 6 demo and the Product Goal fail. |

- **Recommendation:** A now, and B before any public beta (the coach's recommendation, unchanged).
- **Default if no answer:** A is **not** recorded as accepted; everything stays `coach-reviewed` with the notice, and row S6-P15 stays not met.
- **Evidence:** `docs/domain/po-fallback-p7-p15.md`; `find content/drills -name '*.json' -exec grep -h '"review_status"' {} +` → 32 `coach-reviewed`, 5 `draft`, 0 `verified`.
- **Need-by:** 2026-11-24.

### P7. Rulebook (OQ-01) (re-ask)

Asked first in EM-ESC-05 (deadline 2026-11-10); no answer is recorded. New in Sprint 6: COACH-6a maps the patterns that depend on rules (serve, return, kitchen) to rule ids.

| Option | What happens | Cost |
|---|---|---|
| **A. Accept the fallback** | "Unofficial scoring" stays, and rule-dependent patterns say "rules not yet verified". | Not usable for official scoring, which was never promised. |
| B. Supply the 2026 rulebook PDF | The coach verifies the queue in `docs/domain/rules-verified.md` and the pattern rule ids. | Any row that differs from the provisional value is a requirement change. |
| C. No decision | Unchanged state. | The release notes and patterns carry no PO statement on scoring. |

- **Recommendation:** A, and B as soon as possible (the coach's, unchanged).
- **Default if no answer:** the product stays labelled unofficial, and row S6-P7 stays not met. That is not an acceptance on your behalf.
- **Evidence:** `docs/domain/po-fallback-p7-p15.md`; `docs/domain/rules-verified.md` §1.
- **Need-by:** 2026-11-24.

### P19. Residual-risk ADR 0059 (re-ask)

Asked first in EM-ESC-05 (deadline 2026-11-12); no answer is recorded.

| Option | What happens | Cost |
|---|---|---|
| **a. Decide row by row** | Rows you accept close; rows you reject become fix tickets. | Your time to read the ADR; any rejected row costs a ticket. |
| b. Accept none until P16 | All rows stay open. | No deployment beyond localhost and no real users. |

- **Recommendation:** (a).
- **Default if no answer:** ADR 0059 stays Proposed, every row stays an open risk, and nothing is deployed beyond localhost (kickoff SEC-5; row S6-P19).
- **Evidence:** `docs/decisions/0059-asvs-l2-release-review-residual-risks-for-r1.md` (Status: Proposed).
- **Need-by:** 2026-11-26.

### P11. Pro-match footage with rights and consented training footage (OQ-06; re-ask, wider scope)

Asked first in EM-ESC-05 as the footage bucket (deadline: S7 planning). Your 2026-11-12 instruction needs pro-match and training video, so the question is now about the footage itself. We use pro-match video only where we hold the rights, never scraped broadcast or YouTube content, and training video only with the players' consent.

| Option | What happens | Cost |
|---|---|---|
| **a. Supply both, and choose a private bucket provider** | Licensed pro-match footage and consented training footage go through the provenance and licence gates (ST-175a, ST-175b). The CV spikes run on CPU (ST-176b plans). | A licence fee for pro footage (unknown); bucket storage (P8); labelling time. |
| b. Consented training footage only | Player-side spikes can run; reference values stay coach judgment or published sources (P22). | Bucket storage (P8); no measured pro values. |
| c. Defer | No CV story is Ready (roadmap §7.1, NFR-006). | Video analysis stays tag-based, and reference values are never measured from pro matches. |

- **Recommendation:** (a).
- **Default if no answer:** (c) in effect. The team prepares the provenance gate, the licence gate, the eval harness, the spike plans, and the footage spec with a rights and consent checklist (row S6-P11).
- **Evidence:** `docs/requirements/open-questions.md` OQ-06; `docs/sprints/sprint-06.md` §0.1 row "Footage" (no video with people on `origin/main`).
- **Need-by:** S8 planning (CV spikes), asked now so the gates are ready when footage arrives.

### P16. Legal review (NFR-070, US + AU; re-ask, wider scope)

Asked first in EM-ESC-05; no answer is recorded. Sprint 6 adds three topics: consent for training video, pose or body tracking (personal data), and statistics derived from licensed footage. SEC-6 writes the question list.

| Option | What happens | Cost |
|---|---|---|
| **a. Commission it now, with the three new topics** | Flags can turn on for real users once it is done. | A legal adviser's fee (unknown). |
| b. Defer | No real users, no real-person training footage, no pose spike on real people. | Video analysis stays on team-made fixtures. |

- **Recommendation:** (a). The team cannot judge the law.
- **Default if no answer:** flags stay off; pose work stays at spike-plan level (row S6-P16).
- **Evidence:** `docs/sprints/sprint-06.md` §0.4; `docs/sprints/05/po-escalations.md` P16.
- **Need-by:** before any real user, and before any footage of real people is processed.

## 5. How answers are recorded

1. Answer in any form, for example "P21: B".
2. The orchestrator quotes your words verbatim in a new addendum of `docs/requirements/po-input-2026-10-05.md`. No agent writes a PO decision (ADR 0047).
3. The ticket that owns each item applies the answer: the roadmap (product-manager, P21), COACH-6a (P22, P7, P15), the principal-designer (D1), BA-6 (Q1, Q4), and the scorecard §5 rows (RETRO-06).
4. At each status step the EM checks this table against the addenda. An item past its need-by date with no answer is reported with its default in the EM status record.
