"""CI-OBJSTORE-STALL experiment (temporary): per store variant and client path, the writes under
1 MB/s; the store namespace's TCP counter deltas; and, for each slow write, the store-internal
sockets that held unsent or unacknowledged data while it ran (ss samples every 0.25 s)."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict

KEYS = (
    "TcpExt.TCPWinProbe", "TcpExt.TCPToZeroWindowAdv", "TcpExt.TCPFromZeroWindowAdv",
    "TcpExt.TCPWantZeroWindowAdv", "TcpExt.TCPZeroWindowDrop", "TcpExt.TCPTimeouts",
    "TcpExt.TCPLossProbes", "TcpExt.TCPRcvQDrop", "TcpExt.TCPBacklogDrop", "TcpExt.PruneCalled",
    "TcpExt.TCPRcvCollapsed", "TcpExt.TCPOFODrop", "TcpExt.DelayedACKs", "TcpExt.TCPDelivered",
    "Tcp.RetransSegs", "TcpExt.TCPSpuriousRTOs", "TcpExt.TCPRcvCoalesce", "TcpExt.TCPMemoryPressures",
)

rows, counters = [], []
for line in open(sys.argv[1]):
    if not line.startswith("{"):
        continue
    d = json.loads(line)
    (counters if "counters" in d else rows).append(d)
slow_its = defaultdict(set)
by = defaultdict(list)
for r in rows:
    by[r["label"]].append(r)
    if r["mbps"] < 1:
        slow_its[r["label"].split("/")[0]].add(r["it"])
for label, rs in sorted(by.items()):
    slow = [r for r in rs if r["mbps"] < 1]
    print(f"path={label} writes={len(rs)} min_MBps={min(r['mbps'] for r in rs):.3f} "
          f"stalls_lt_1MBps={len(slow)} max_s={max(r['total'] for r in rs):.2f}")
for variant in sorted({c["counters"] for c in counters}):
    for kind, pick in (("stalled", True), ("clean", False)):
        total, its = Counter(), 0
        for c in counters:
            if c["counters"] != variant or (c["it"] in slow_its[variant]) != pick:
                continue
            its += 1
            for k in KEYS:
                total[k] += c["after"].get(k, 0) - c["before"].get(k, 0)
        if its:
            print(f"counters variant={variant} {kind} iterations={its}: "
                  + " ".join(f"{k.split('.')[1]}={v}" for k, v in total.items() if v))
samples: list[tuple[float, str, str]] = []
if len(sys.argv) > 2:
    stamp, head = None, ""
    for line in open(sys.argv[2], errors="replace"):
        m = re.match(r"^# t=([0-9.]+)", line)
        if m:
            stamp = float(m.group(1))
        elif stamp is not None and line.strip():
            if line[0] not in " \t":
                head = line.strip()
            else:
                samples.append((stamp, head, line.strip()))
for r in rows:
    if r["mbps"] >= 1:
        continue
    print("SLOW", json.dumps(r))
    shown = 0
    for t, head, info in samples:
        if not (r["start"] <= t <= r["end"]) or shown >= 16:
            continue
        cols = head.split()
        busy = (len(cols) > 2 and (cols[0] != "0" or cols[1] != "0")) or "unacked" in info \
            or "backoff" in info or "probe" in info
        if busy:
            print(f"  t={t - r['start']:6.2f} {head} | {info[:400]}")
            shown += 1
