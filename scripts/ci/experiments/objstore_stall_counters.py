"""/proc/net/netstat + /proc/net/snmp (header line, value line per group) on stdin -> JSON."""

import json
import sys

lines = sys.stdin.read().splitlines()
out = {}
for head, vals in zip(lines[::2], lines[1::2], strict=False):
    group, names = head.split(":", 1)
    _, values = vals.split(":", 1)
    for name, value in zip(names.split(), values.split(), strict=False):
        out[f"{group}.{name}"] = int(value)
print(json.dumps(out))
