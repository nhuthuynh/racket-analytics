# Interim wording register, Sprint 4

- **Owner:** product-manager (ticket PM-4; ADR 0051 rule 4: "The user-facing texts are owned by the product-manager and marked 'interim, pending legal review (NFR-070)' in the wording register").
- **Date:** 2026-10-17
- **Used by:** ST-068b (A-01, upload notice), ST-071 (R-01), ST-072b (Q-01), ST-063a (P-01). PD-4 flows place each string; this file decides its words. A front-end PR that changes a string changes it here first, in the same PR, with the product-manager as reviewer (sprint-04 §5 "interim wording review in FE PRs").
- **Not a PO decision.** The values in these texts are the PO's accepted answers of 2026-10-05 (ADR 0023: OQ-05, OQ-06, OQ-07, OQ-08, OQ-13). Only the words are interim. Nothing here records, changes or re-asks a PO decision (ADR 0047 rule 5).

## 1. Rules for every string

1. **Marker.** Every row's marker starts with `interim, pending` and names the open item it waits on: the NFR-070 legal review (US + AU, **P16**) for FR-003, FR-008 and FR-009; the OQ-13 budget and quota size (**P8**) for FR-160; the side-out rule check (OQ-01, **P7**) for the weakness split; a human coach (**P15**) for the drill notice. When an item closes, its owner removes `interim` from the row (scorecard S4-DoD-P16, S4-DoD-P8).
2. **Values come from config, never from the text.** `{age_minimum}` (18), `{retention_days}` (30, 90, 365), `{original_days}` (30), `{match_limit}` (10), `{limit_gb}` (20, (judgment) until P8) and every date, time and count are placeholders filled from `Settings` (ST-067) or the API response. A string with a digit outside a placeholder fails the check, so a changed setting cannot leave stale words (as flows-sprint-01 D-5 did for the upload caps).
3. **Plain language** (judgment; see §8 on the requirement id). With placeholders replaced by a short word, each string must: (a) keep every sentence at 20 words or fewer; (b) score Flesch-Kincaid grade 8.0 or lower when it has 8 words or more; (c) use none of the banned terms in the check (`retention`, `quota`, `consent`, `minor`, `processing`, `label set`, `dataset`, `rate limit`, `revoke`, `opt in`, and similar). Shorter alternatives: "keep", "storage", "agree", "under {age_minimum}", "training sets", "turn off".
4. **Honest scope** (HAX G1, G2 [DPA/DESIGN-11]). No string promises legal compliance, names a law, or claims more than the API does (for example ST-068a stores no birth date, so no string asks for one).

## 2. FR-003 Age question, under-18 reason and footage notice (A-01, upload page)

| ID | Kind | Where | Text | Marker |
|---|---|---|---|---|

## 3. FR-008 How long videos are kept (R-01, match page)

| ID | Kind | Where | Text | Marker |
|---|---|---|---|---|

## 4. FR-009 Training use (R-01)

| ID | Kind | Where | Text | Marker |
|---|---|---|---|---|

## 5. FR-160 Over-limit and storage (Q-01)

| ID | Kind | Where | Text | Marker |
|---|---|---|---|---|

## 6. Weakness unit (FR-120) and human-coach notice (FR-141) (P-01)

| ID | Kind | Where | Text | Marker |
|---|---|---|---|---|

## 7. The check

Run from the repository root (standard library only; rc 0 pass, rc 1 fail):

```sh
f=$(mktemp) && sed -n '/^```python check$/,/^```$/p' docs/requirements/interim-wording-sprint-04.md | sed '1d;$d' > "$f"
python3 -I "$f" docs/requirements/interim-wording-sprint-04.md
```

```python check
import re, sys
REQUIRED = {"age-question", "under-18-reason", "footage-notice", "retention", "consent",
            "over-limit", "quota", "weakness-unit", "human-coach-notice"}
BANNED = ["retention", "quota", "consent", "minor", "processing", "processed", "label set", "dataset",
          "rate limit", "revoke", "opt in", "opt-in", "purge", "lawful", "jurisdiction", "biometric",
          "pursuant", "hereby", "analytics", "algorithm", "normalised", "invalid"]
def syllables(word):
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 0
    n = len(re.findall(r"[aeiouy]+", w))
    if w.endswith("e") and not w.endswith(("le", "ee")) and n > 1:
        n -= 1
    return max(n, 1)
def problems(text):
    out = []
    if re.search(r"\d", re.sub(r"\{[a-z_]+\}", "", text)):
        out.append("digit outside a placeholder")
    plain = re.sub(r"\{[a-z_]+\}", "ten", text)
    low = plain.lower()
    out += [f"banned term '{b}'" for b in BANNED if re.search(r"\b" + re.escape(b) + r"\b", low)]
    sentences = [s for s in re.split(r"[.!?]+(?:\s|$)", plain) if s.strip()]
    words = re.findall(r"[A-Za-z']+", plain)
    out += [f"sentence over 20 words ({len(s.split())})" for s in sentences if len(s.split()) > 20]
    if len(words) >= 8:
        grade = 0.39 * len(words) / len(sentences) + 11.8 * sum(map(syllables, words)) / len(words) - 15.59
        if grade > 8.0:
            out.append(f"grade {grade:.1f} > 8.0")
    return out
rows, failures = [], []
for line in open(sys.argv[1], encoding="utf-8"):
    if line.startswith("| W-"):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        rid, kind, text, marker = cells[0], cells[1], cells[3].strip("`"), cells[4]
        rows.append(kind)
        if not re.match(r"interim, pending .*\b(OQ-\d\d|P\d+)\b", marker):
            failures.append(f"{rid}: marker must start 'interim, pending' and name OQ-nn or P-n")
        failures += [f"{rid}: {p}" for p in problems(text)]
missing = REQUIRED - set(rows)
if missing:
    failures.append("missing kinds: " + ", ".join(sorted(missing)))
print(f"strings {len(rows)}, failures {len(failures)}")
print("\n".join(failures))
sys.exit(1 if failures else 0)
```

## 8. Notes

- **Requirement id of the plain-language check.** The PM-4 card names "the plain-language reading level check (NFR-028)", but NFR-028 in `non-functional-requirements.md` is "Target size" (24×24 and 48×48 CSS px). No NFR defines a reading level today, so §1 rule 3 and §7 are the check (judgment) until the business-analyst adds one (decision row in `docs/sprints/04/decisions/PM-4.md`).
