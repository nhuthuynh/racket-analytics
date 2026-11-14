# Sources register (domain citations)

- **Owner:** pickleball-domain-coach. **Written:** 2026-11-13 (COACH-6a, Sprint 6). **Used by:** `docs/domain/pattern-catalogue.md`, the reference set v1 (COACH-6c, `content/references/` (planned)), the reference lint `racket-reference-lint` (ST-170a, planned) and the doc check extension CI-DOC-CHECK-06 (planned), which checks that every `SRC-nnnn` a reference entry or catalogue line cites is a row of this table.
- **Requirements:** FR-170.R1 ("a source id that resolves"), FR-170.R5 (provenance label), PO question P22 / assumption A5 (`docs/sprints/06/po-escalations.md`): an entry may carry a published value only when its citation resolves here. P22 is open; its default is option (a).
- **What "resolve" means here:** someone on the team opened the document and checked that it says what we cite it for. Search results, snippets or a title alone do not count.

## 1. Rules

1. **Ids.** `SRC-` plus four digits, never reused, never renumbered. A withdrawn source keeps its row with status `unresolved` and a note.
2. **Resolve status**, one of:
   - `resolved`: opened and checked; the evidence column says by whom, when and how. For an in-repo document the evidence is its path at `origin/main`. For an external source already verified in the research register, the evidence is that register's "Verified: yes" row.
   - `exists-unfetched`: search results show the document exists, but nobody has read it (egress blocked or not supplied). Nothing may be cited from it as a fact.
   - `unresolved`: not reached, or no locator on file. Nothing may be cited from it.
3. **Claim kind** says what a row may back. `definition` (how a pattern is counted), `rule` (a rulebook rule), `method` (a statistical or engineering method), `statistic` (a number about how people play). **Only a `resolved` row of kind `statistic` may back a `published` reference value** (FR-170.R1, P22 (a)). A reference value without one is `source_type: judgment` and shows "coach judgment, not measured from pro matches" (FR-170.R5).
4. **No invented locators.** A URL appears only when it is already on file in a research register row; otherwise the locator column says "none on file".
5. **Changing a row:** a status change carries new evidence (command and result, or the reviewer and date). Rows are append-only apart from the status and evidence columns.

## 2. Register

| Id | Source | Locator | Claim kind | Used for | Resolve status | Evidence |
|---|---|---|---|---|---|---|
| SRC-0001 | QD §3.2 shot-level metric table (AN-08..AN-16) | `docs/requirements/brainstorm-quality-domain.md` §3.2 | definition | starting formulas of AN-08..AN-13 and AN-16; min_n of the QD table | `resolved` | read at `origin/main` 842b33b6 on 2026-11-13 (coach) |
| SRC-0002 | Sprint 6 atomic rules FR-171.R1-R7, FR-172.R1, assumptions A2 and A6 | `docs/sprints/06/requirements-breakdown.md` §1 and §6 | definition | the counted rules this catalogue makes operational | `resolved` | read at 842b33b6 on 2026-11-13 (coach) |
| SRC-0003 | Full Tag labels v1 (events, facets, `court_xy_m`, outcome) | `docs/data/gold-label-schema.md` §4; `backend/src/racket/dataset/labels.py` | definition | the vocabulary every FT pattern counts over; the worked examples validate against it | `resolved` | every worked example passes `validate_labels` (COACH-6a PR evidence) |
| SRC-0004 | Metric dictionary v0.1 rules 0.1-0.6 (exclusions, attribution, uncertainty, scope) | `docs/domain/metric-dictionary.md` §0 | definition | attribution of errors and faults (rule 0.2); per-side scope (rule 0.4) | `resolved` | read at 842b33b6 on 2026-11-13 (coach) |
| SRC-0005 | ADR 0005 low-sample and efficacy claim rules (Wilson 95 % interval, minimum n) | `docs/decisions/0005-low-sample-and-efficacy-claim-rules.md` | method | `interval_method: wilson`, low-sample flag | `resolved` | read at 842b33b6 on 2026-11-13 (coach) |
| SRC-0006 | Wilson interval implementation `wilson(k, n)` | `backend/src/racket/analytics/uncertainty.py` | method | every Wilson figure in the worked examples is recomputed with it | `resolved` | figures recomputed with it (COACH-6a PR evidence) |
| SRC-0007 | Distribution-free order-statistic interval for the median, as stated in FR-171.R4, and its numeric check (n = 10 gives l = 2; n = 6 gives l = 1) | `docs/sprints/06/review-rounds.md` row PE-PLAN06-03 (Fixed) | method | `interval_method: order_statistic_median` (AN-13) | `resolved` | review row read at 842b33b6; l recomputed for n = 6..12 in the COACH-6a PR evidence. The method is standard statistics (judgment); no textbook is on file |
| SRC-0008 | 2026 USA Pickleball Official Rulebook [DOM/DOMAIN-01] | https://usapickleball.org/docs/rules/USAP-Official-Rulebook.pdf | rule | two-bounce rule, NVZ rules, court dimensions, line calls (catalogue §0.9) | `exists-unfetched` | `curl -sS -o /dev/null -w "%{http_code}" --max-time 15 <locator>` on 2026-11-13 → `curl: (56) CONNECT tunnel failed, response 403` (proxy `connect_rejected`); same since 2026-10-03 (`docs/domain/rules-verified.md` §1). P7 open |
| SRC-0009 | 2026 USA Pickleball Rulebook Change Document [DOM/DOMAIN-02] | https://usapickleball.org/docs/rules/USAP-Rulebook-Change-Document.pdf | rule | whether any 2026 change touches a pattern's rule dependence | `exists-unfetched` | blocked as SRC-0008 (`rules-verified.md` §1). P7 open |
| SRC-0010 | Coaching snippets on the third-shot drop, the transition zone and the dink [DOM G2 C1] | `docs/research/domain-pickleball-cv.md` G2 C1 (the underlying blogs were never fetched) | definition | the plain-language sense of drop, transition and dink (catalogue AN-09, AN-12, AN-13) | `unresolved` | DOM G2 marks C1 "UNVERIFIED, search snippets from coaching blogs, none fetched"; no blog locator on file |
| SRC-0011 | PB Vision third-shot categories "drop, hybrid, drive or lob" [DOM/DOMAIN-06, DOM/DOMAIN-07] | https://pb.vision/ | definition | the candidate `hybrid` third-shot value (catalogue §10 Q4) | `unresolved` | DOM register: "no: egress blocked. Search snippets only" |
| SRC-0012 | Coaching sites named in DOM "Gaps" item 2 (PPR, betterpickleball.com, selkirk.com, thedinkpickleball.com) | none on file | statistic | candidate published statistics for reference values (P22) | `unresolved` | DOM "Gaps / unverified" item 2: "not fetched or were blocked" |
| SRC-0013 | OpenCV homography tutorial: a homography maps points on one plane only [DOM/CV-12] | https://github.com/opencv/opencv/blob/4.x/doc/tutorials/features2d/homography/homography.markdown | method | only bounce and foot points are placed on the court (catalogue §0.7) | `resolved` | DOM register row CV-12, "Verified: yes" (canonical source fetched by research) |
| SRC-0014 | CoachAI / ShuttleSet stroke-level, attribute-wise annotation [DOM/CV-18] | https://github.com/wywyWang/CoachAI-Projects | method | patterns count facets of single shots, not a one-label shot class (catalogue §0.1) | `resolved` | DOM register row CV-18, "Verified: yes" |
| SRC-0015 | Rules verification queue and rule ids | `docs/domain/rules-verified.md` §5 | rule | mapping of pattern rule dependence to queue rows (catalogue §0.9) | `resolved` | read at 842b33b6 on 2026-11-13 (coach) |
| SRC-0016 | ADR 0003 weakness ranking by rallies lost | `docs/decisions/0003-weakness-ranking-by-rallies-lost.md` | definition | tie-break link of pattern gaps to rallies lost (FR-172.R4) | `resolved` | read at 842b33b6 on 2026-11-13 (coach) |
| SRC-0017 | Metric dictionary v0.1 definitions of AN-05 serve fault % and AN-07 rally-ending mix (`coach-reviewed` 2026-10-07) | `docs/domain/metric-dictionary.md` §1 (AN-05, AN-07) | definition | the quantity each AN-05 and AN-07 reference band is set against (reference set v1, COACH-6c) | `resolved` | read at `origin/main` 0774fa90 on 2026-11-13 (coach) |
| SRC-0018 | Pattern catalogue v0.1 definitions of AN-09 third-shot drop share and AN-13 dink tolerance | `docs/domain/pattern-catalogue.md` §2 and §5 | definition | the quantity each AN-09 and AN-13 reference band is set against (reference set v1, COACH-6c) | `resolved` | read at `origin/main` 0774fa90 on 2026-11-13 (coach) |

## 3. What this means for the reference set v1 (COACH-6c)

- No row of kind `statistic` is `resolved` on 2026-11-13. So **every reference value in v1 is `source_type: judgment`** unless a statistic is resolved first, whatever P22 answers. No v1 value may say "pro" (FR-170.R5; sprint-06 §3.3 ST-170 acceptance).
- To add a published statistic: add a row here with its locator, open the document, record the evidence, set `resolved`; then the reference entry may cite it with `source_type: published`.
- Measured values need licensed footage with a provenance record (FR-170.R3; P11) and cite a footage id, not a row of this register.

## Changelog

| Date | Who | Change |
|---|---|---|
| 2026-11-13 | pickleball-domain-coach | v0.1 written with COACH-6a: rules, 16 rows, consequences for COACH-6c |
| 2026-11-13 | pickleball-domain-coach | COACH-6c: rows SRC-0017 and SRC-0018 (the definitions the reference set v1 bands are set against); no status of an existing row changed |
