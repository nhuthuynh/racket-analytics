"""CI-OBJSTORE-STALL experiment (temporary): per-path summary of the probe rows, and every write
under 1 MB/s with the ss samples of its connection during the write."""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict

rows = [json.loads(line) for line in open(sys.argv[1]) if line.startswith("{")]
by = defaultdict(list)
for r in rows:
    by[r["label"]].append(r)
for label, rs in sorted(by.items()):
    slow = [r for r in rs if r["mbps"] < 1]
    print(
        f"path={label} writes={len(rs)} min_MBps={min(r['mbps'] for r in rs):.3f} "
        f"median_MBps={sorted(r['mbps'] for r in rs)[len(rs) // 2]:.2f} stalls_lt_1MBps={len(slow)} "
        f"max_s={max(r['total'] for r in rs):.2f}"
    )
samples: list[tuple[float, str]] = []
if len(sys.argv) > 2:
    stamp = None
    for line in open(sys.argv[2], errors="replace"):
        m = re.match(r"^# t=([0-9.]+)", line)
        if m:
            stamp = float(m.group(1))
        elif stamp is not None:
            samples.append((stamp, line.rstrip()))
for r in rows:
    if r["mbps"] >= 1:
        continue
    print("SLOW", json.dumps(r))
    port = str(r.get("lport"))
    shown = 0
    for i, (t, line) in enumerate(samples):
        if r["start"] - 1 <= t <= r["end"] + 1 and f":{port}" in line and shown < 12:
            nxt = samples[i + 1][1] if i + 1 < len(samples) else ""
            print(f"  ss t={t:.1f} {line.strip()} | {nxt.strip()}")
            shown += 1
