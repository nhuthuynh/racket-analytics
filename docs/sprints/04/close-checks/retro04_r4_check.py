#!/usr/bin/env python3
"""RETRO-04 fourth-close checklist (fail closed; docs-only ticket, stands in for the red test).

Usage: python3 docs/sprints/04/close-checks/retro04_r4_check.py [REPO_DIR]
Committed (not kept in scratch) so a reviewer can re-run the red/green evidence (QA-RETRO04R3-02).
"""

import json
import re
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
fails = []


def need(cond, msg):
    if not cond:
        fails.append(msg)


def read(p):
    f = root / p
    return f.read_text() if f.exists() else ""


def sh(*a):
    return subprocess.run(a, cwd=root, capture_output=True, text=True, check=False)  # noqa: S603


G = [f"G04-{i:02d}" for i in range(1, 13)]
rep = read("docs/sprints/04/sprint-report.md")
retro = read("docs/retros/2026-12-11-sprint-04.md")

# 1. VERIFY-04-r5 folded in unchanged
br = "origin/s04/verify-04-r5-sprint-4-goal-verification-round-5"
need(
    sh("git", "merge-base", "--is-ancestor", br, "HEAD").returncode == 0,
    f"{br} is not an ancestor of HEAD",
)
need(
    sh(
        "git", "diff", "--quiet", br, "HEAD", "--", "docs/sprints/04/decisions/VERIFY-04-r5.md"
    ).returncode
    == 0,
    "decisions/VERIFY-04-r5.md differs from the verifier's branch",
)

# 2. report: goal + scorecard first, of record VERIFY-04-r5, 12 of 12
head = rep.split("## 1. Goal")[0]
need(
    "VERIFY-04-r5" in head and "4095937" in head,
    "report head does not name VERIFY-04-r5 at 4095937",
)
need(
    "12 of 12" in head and "fourth close" in head.lower(),
    "report head lacks the fourth-close paragraph (12 of 12)",
)
m1 = re.search(
    r"^## 1\. Goal.*?(?=^### 1\.0 Measurement of record: VERIFY-04-r4)", rep, re.M | re.S
)
sec1 = m1.group(0) if m1 else ""
need(
    re.search(r"^### 1\.0 Measurement of record: VERIFY-04-r5", sec1, re.M),
    "report §1 lacks '### 1.0 Measurement of record: VERIFY-04-r5' before the r4 section",
)
need("goal is met" in sec1.lower(), "report §1 does not state that the goal is met")
for g in G:
    need(
        re.search(rf"^\| {g} \|[^\n]*\| \*\*yes\*\* \|", sec1, re.M),
        f"report §1 VERIFY-04-r5 table lacks a met row for {g}",
    )
for p in ["P15", "P16", "P7", "P8", "P6", "P10", "P11"]:
    need(f"waiting on {p}" in sec1, f"report §1 (r5) lacks 'waiting on {p}'")
need(re.search(r"^## 14\. Fourth close", rep, re.M), "report lacks §14 Fourth close")
for n in [139, 180, 181]:
    need(f"#{n}" in rep.split("## 14. Fourth close")[-1], f"report §14 does not name PR #{n}")
need("Carry-over after the fourth close" in rep, "report lacks the fourth-close carry-over")
need(
    "QA-VERIFY04R5-01" in rep, "report does not name the make-demo flag-on finding QA-VERIFY04R5-01"
)
need(
    "this close's count of #175/#176" not in rep,
    "report still explains 71 -> 73 with #175/#176 (QA-RETRO04R3-01, PE-RETRO04R3-01)",
)
r4 = re.search(r"^### 1\.0 Measurement of record: VERIFY-04-r4.*?(?=^### 1\.1 )", rep, re.M | re.S)
g12 = [ln for ln in (r4.group(0) if r4 else "").splitlines() if ln.startswith("| G04-12 |")]
need(g12 and "#139" in g12[0], "r4 §1.0 G04-12 row does not name #139 as the missing PR")
need(g12 and "M13" in g12[0], "r4 §1.0 G04-12 row lacks the pointer to retro M13 (PE-RETRO04R3-02)")

# 3. ledger
led = read("docs/sprints/04/review-rounds.md")
need(
    re.search(r"^## .*fourth close", led, re.M | re.I),
    "review-rounds lacks the fourth-close section",
)
for m in ["QA-RETRO04R3-01", "QA-RETRO04R3-02", "PE-RETRO04R3-01", "PE-RETRO04R3-02"]:
    need(
        re.search(rf"^\| {m} \| (minor|nit) \| \*\*Fixed\*\*", led, re.M), f"{m} lacks a Fixed row"
    )
need(
    re.search(r"^\| QA-VERIFY04R5-01 \| minor \| Open", led, re.M),
    "QA-VERIFY04R5-01 (make demo on a flag-on stack) lacks its Open minor row",
)
r = sh(
    "python3",
    "scripts/measure/open_defects.py",
    "docs/sprints/03/review-rounds.md",
    "docs/sprints/04/review-rounds.md",
)
need(r.returncode == 0, f"open_defects rc {r.returncode}: {r.stdout.strip()[-80:]}")

# 4. status.json
try:
    st = json.loads(read("docs/sprints/04/status.json"))
    need("fourth_close" in st, "status.json lacks fourth_close")
    need(st.get("goal_met") is True, "status.json goal_met is not true")
    prs = [m.get("pr") for m in st["ticket_prs"]["map"]]
    need(180 in prs, "status.json map lacks PR #180")
    need(len(prs) == len(set(prs)), "status.json map has a duplicate PR")
    need(st["ticket_prs"]["merged"] == 74, f"status.json merged {st['ticket_prs']['merged']} != 74")
    need(st["ci"]["main_head"].startswith("4095937"), "status.json ci.main_head is not 4095937")
    need(st["open_defects"]["count"] == 0, "status.json open_defects.count != 0")
    gm = st["goal_metrics"]
    need(
        all(gm[g]["verified"].startswith("VERIFY-04-r5") for g in G),
        "status.json goal_metrics not all VERIFY-04-r5",
    )
    need(sum(1 for g in G if gm[g].get("met") is True) == 12, "status.json goal_metrics met != 12")
except Exception as e:  # noqa: BLE001 - any parse error fails closed
    fails.append(f"status.json: {type(e).__name__} {e}")

# 5. retro §12
r12 = retro.split("## 12. Fourth close")[1] if "## 12. Fourth close" in retro else ""
need(r12, "retro lacks §12 Fourth close")
for e in ["E1", "E2", "E3", "E4", "E5"]:
    need(re.search(rf"^\| {e} \|", r12, re.M), f"retro §12 does not review {e}")
need("root cause" in r12.lower(), "retro §12 lacks root causes")
need("Lessons" in r12, "retro §12 lacks lessons")
acts = re.findall(r"^\| (F\d) \| [^|]+ \| ([^|]+) \| (2026-\d\d-\d\d) \|", r12, re.M)
need(1 <= len(acts) <= 5, f"retro §12 has {len(acts)} owned dated F-actions (need 1-5)")
need("Process changes" in r12, "retro §12 lacks process changes")

# 6. decision log, decisions file, blockers, progress
dl = read("docs/sprints/04/decision-log.md")
for f in sorted((root / "docs/sprints/04/decisions").glob("*.md")):
    need(f"(decisions/{f.name})" in dl, f"decision-log index lacks {f.name}")
need(re.search(r"^## 5\. .*fourth close", dl, re.M | re.I), "decision-log lacks §5 fourth close")
dec = read("docs/sprints/04/decisions/RETRO-04.md")
need(
    "## Fourth close" in dec and "retro04_r4_check.py" in dec,
    "decisions/RETRO-04.md lacks the fourth-close section naming the check",
)
bl = read("docs/sprints/04/blockers.md")
need("fourth close" in bl.lower(), "blockers lacks a fourth-close row")
fl = [ln for ln in bl.splitlines() if "The flag-on stack cannot be started with `make up`" in ln]
need(
    fl and not fl[0].rstrip().endswith("| Open |"),
    "blockers row 'flag-on stack cannot be started' is still Open",
)
pg = read("docs/sprints/04/progress.md")
need(
    "4095937" in pg and "fourth close" in pg.lower(),
    "progress.md lacks the fourth-close status at 4095937",
)

# 7. traceability + roadmap
need(
    "fourth close" in read("docs/requirements/traceability-matrix.md").lower(),
    "traceability matrix lacks the fourth-close note",
)
need(
    "fourth close" in read("docs/sprints/roadmap.md").lower(),
    "roadmap lacks the S4 fourth-close actuals row",
)

if fails:
    for f in fails:
        print("FAIL", f)
    print(f"retro-04-r4-check: not met ({len(fails)} failures)")
    sys.exit(1)
print("retro-04-r4-check: met")
sys.exit(0)
