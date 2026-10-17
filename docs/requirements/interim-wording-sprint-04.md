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
| W-A01 | age-question | A-01 heading | `Are you {age_minimum} or over?` | interim, pending legal review (OQ-05 accepted; NFR-070, P16) |
| W-A02 | age-question | A-01 hint | `You need to be {age_minimum} or over to have an account. We only ask once and we do not store your birth date.` | interim, pending legal review (OQ-05 accepted; NFR-070, P16) |
| W-A03 | age-question | A-01 choice | `Yes, I am {age_minimum} or over` | interim, pending legal review (OQ-05 accepted; NFR-070, P16) |
| W-A04 | age-question | A-01 choice | `No, I am under {age_minimum}` | interim, pending legal review (OQ-05 accepted; NFR-070, P16) |
| W-A05 | age-question | A-01 error, nothing chosen | `Choose yes or no` | interim, pending legal review (OQ-05 accepted; NFR-070, P16) |
| W-A06 | under-18-reason | A-01 under-18 heading | `You can't have an account yet` | interim, pending legal review (OQ-05 accepted; NFR-070, P16) |
| W-A07 | under-18-reason | A-01 under-18 why | `You need to be {age_minimum} or over to use this app. We did not make an account for you.` | interim, pending legal review (OQ-05 accepted; NFR-070, P16) |
| W-A08 | under-18-reason | A-01 under-18 what to do | `You are welcome back when you turn {age_minimum}. If you chose the wrong answer, sign in again to answer again.` | interim, pending legal review (OQ-05 accepted; NFR-070, P16) |
| W-A09 | footage-notice | upload page and first-run screen | `Don't upload matches with anyone under {age_minimum}. Film only people who agree to be filmed.` | interim, pending legal review (OQ-05 accepted; NFR-070, P16) |

## 3. FR-008 How long videos are kept (R-01, match page)

| ID | Kind | Where | Text | Marker |
|---|---|---|---|---|
| W-R01 | retention | R-01 heading | `How long we keep your videos` | interim, pending legal review (OQ-07 accepted; NFR-070, P16) |
| W-R02 | retention | R-01 intro | `You choose how long we keep the video you watch and tag. Your score sheet, stats and plan stay until you delete the match.` | interim, pending legal review (OQ-07 accepted; NFR-070, P16) |
| W-R03 | retention | R-01 system rule | `We delete the file you uploaded {original_days} days after it is ready. The copy you watch is kept for the time you choose here.` | interim, pending legal review (OQ-07 accepted; NFR-070, P16) |
| W-R04 | retention | R-01 choice, one per setting value | `{retention_days} days` | interim, pending legal review (OQ-07 accepted; NFR-070, P16) |
| W-R05 | retention | R-01 default tag on the default choice | `(default)` | interim, pending legal review (OQ-07 accepted; NFR-070, P16) |
| W-R06 | retention | R-01 choice | `Until I delete it` | interim, pending legal review (OQ-07 accepted; NFR-070, P16) |
| W-R07 | retention | R-01 date list, per match | `Video will be deleted on {date}` | interim, pending legal review (OQ-07 accepted; NFR-070, P16) |
| W-R08 | retention | R-01 date list, kept | `Video kept until you delete it` | interim, pending legal review (OQ-07 accepted; NFR-070, P16) |
| W-R09 | retention | match page, video gone | `This video was deleted on {date}, as you chose. Your score sheet and stats are still here.` | interim, pending legal review (OQ-07 accepted; NFR-070, P16) |
| W-R10 | retention | R-01 saved | `Saved. The new deletion dates are shown below.` | interim, pending legal review (OQ-07 accepted; NFR-070, P16) |
| W-R11 | retention | R-01 save failed | `We couldn't save your choice. Your old setting still applies. Try again.` | interim, pending legal review (OQ-07 accepted; NFR-070, P16) |

## 4. FR-009 Training use (R-01)

| ID | Kind | Where | Text | Marker |
|---|---|---|---|---|
| W-C01 | consent | R-01 heading | `Help improve the app` | interim, pending legal review (OQ-06 accepted; NFR-070, P16) |
| W-C02 | consent | R-01 switch label | `Use my matches to improve the app` | interim, pending legal review (OQ-06 accepted; NFR-070, P16) |
| W-C03 | consent | R-01 explanation | `If you turn this on, we may use your matches and tags to train and test our video tools. It stays off unless you turn it on.` | interim, pending legal review (OQ-06 accepted; NFR-070, P16) |
| W-C04 | consent | R-01 turning off | `You can turn it off at any time. Then your matches go into no new training sets. Older training sets are not changed, and they are replaced at their next planned update.` | interim, pending legal review (OQ-06 accepted; NFR-070, P16) |
| W-C05 | consent | R-01 saved, on | `Turned on. You can turn it off here at any time.` | interim, pending legal review (OQ-06 accepted; NFR-070, P16) |
| W-C06 | consent | R-01 saved, off | `Turned off. Your matches will not be in any new training set.` | interim, pending legal review (OQ-06 accepted; NFR-070, P16) |
| W-C07 | consent | R-01 save failed | `We couldn't save your choice. Your old setting still applies. Try again.` | interim, pending legal review (OQ-06 accepted; NFR-070, P16) |

## 5. FR-160 Over-limit and storage (Q-01)

| ID | Kind | Where | Text | Marker |
|---|---|---|---|---|
| W-Q01 | over-limit | match setup, too many matches | `You have started {match_limit} matches in the last hour. You can start a new match at {time}.` | interim, pending the OQ-13 budget review (10 per hour accepted; P8) |
| W-Q02 | over-limit | match setup, no time in the reply | `You have started a lot of matches in the last hour. You can start a new match within the hour.` | interim, pending the OQ-13 budget review (10 per hour accepted; P8) |
| W-Q03 | quota | upload page, video too big for space left | `This video won't fit in your storage. You have used {used_gb} of {limit_gb} GB.` | interim, pending the OQ-13 quota size (20 GB is (judgment); P8) |
| W-Q04 | quota | upload page, what to do | `Delete a match you no longer need, then try again.` | interim, pending the OQ-13 quota size (20 GB is (judgment); P8) |
| W-Q05 | quota | upload page, usage line | `Storage: {used_gb} of {limit_gb} GB used` | interim, pending the OQ-13 quota size (20 GB is (judgment); P8) |

## 6. Weakness unit (FR-120) and human-coach notice (FR-141) (P-01)

| ID | Kind | Where | Text | Marker |
|---|---|---|---|---|
| W-P01 | weakness-unit | P-01 weakness unit label | `Rallies lost per game` | interim, pending the side-out rule check (OQ-08 accepted; OQ-01, P7) |
| W-P02 | weakness-unit | P-01 split under each weakness | `On your serve: {serve_count} per game. On their serve: {receive_count} per game.` | interim, pending the side-out rule check (OQ-08 accepted; OQ-01, P7) |
| W-P03 | weakness-unit | P-01 notice, once before the first card | `Unofficial scoring (rules not yet verified). The split between your serve and theirs may change when the rules are checked.` | interim, pending the side-out rule check (OQ-08 accepted; OQ-01, P7) |
| W-H01 | human-coach-notice | P-01 notice, under the unofficial notice | `A human coach has not checked these drills yet. Use them as a starting point and stop any drill that hurts.` | interim, pending a human coach's drill review (P15) |

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
