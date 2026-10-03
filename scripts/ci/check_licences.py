#!/usr/bin/env python3
"""Licence gate over a CycloneDX JSON SBOM of the *shipped* dependency graph (NFR-062).

Fails on AGPL and non-commercial licences, plus source-available licences that restrict
commercial use (SSPL, BUSL, Commons Clause, PolyForm Noncommercial; judgment, ADR 0014).
LGPL is allowed as an unmodified library (ADR 0008; security-privacy-engineer confirms).
Components with no licence data are listed for review but do not fail the gate.

Exceptions need an ADR: --allow file {"exceptions": [{"name": "...", "reason": "ADR nnnn ..."}]}
Exit: 0 pass, 1 denied licence found, 2 unreadable input (fails closed).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

DENY = re.compile(
    r"AGPL|Affero|SSPL|Server Side Public|BUSL|Business Source|Commons[- ]Clause|"
    r"CC-BY-NC|Non-?Commercial|PolyForm-Noncommercial",
    re.IGNORECASE,
)


def licence_strings(component: dict) -> list[str]:
    out: list[str] = []
    for entry in component.get("licenses") or []:
        if "expression" in entry:
            out.append(str(entry["expression"]))
        lic = entry.get("license") or {}
        for key in ("id", "name"):
            if lic.get(key):
                out.append(str(lic[key]))
    return out


def load_allow(path: str | None) -> dict[str, str]:
    if not path:
        return {}
    data = json.loads(Path(path).read_text())
    allowed: dict[str, str] = {}
    for item in data.get("exceptions", []):
        if not item.get("name") or not str(item.get("reason", "")).strip():
            raise ValueError(f"allowlist entry needs name and reason (an ADR): {item}")
        allowed[item["name"]] = item["reason"]
    return allowed


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sbom", required=True, action="append", help="CycloneDX JSON; repeatable")
    ap.add_argument("--allow", help="JSON file of ADR-backed exceptions")
    args = ap.parse_args(argv)
    try:
        allowed = load_allow(args.allow)
        components: list[dict] = []
        for path in args.sbom:
            components.extend(json.loads(Path(path).read_text()).get("components") or [])
    except (OSError, ValueError) as exc:
        print(f"licences: cannot read input ({exc}); failing closed")
        return 2
    if not components:
        print("licences: SBOM has no components; failing closed (wrong scan target?)")
        return 2

    denied, excepted, unknown = [], [], []
    for c in components:
        ident = f"{c.get('name')}@{c.get('version', '?')}"
        lics = licence_strings(c)
        if not lics:
            unknown.append(ident)
            continue
        bad = [lic for lic in lics if DENY.search(lic)]
        if not bad:
            continue
        if c.get("name") in allowed:
            excepted.append(f"{ident}: {', '.join(bad)} (exception: {allowed[c['name']]})")
        else:
            denied.append(f"{ident}: {', '.join(bad)}")

    print(f"licences: checked {len(components)} components")
    for line in excepted:
        print(f"  allowed by exception: {line}")
    if unknown:
        print(f"  unknown licence (review manually, not failing): {len(unknown)}")
        for ident in sorted(set(unknown)):
            print(f"    - {ident}")
    if denied:
        print("licences: DENIED licences in the shipped graph (NFR-062):")
        for line in denied:
            print(f"  - {line}")
        return 1
    print("licences: no AGPL or non-commercial licence in the shipped graph")
    return 0


if __name__ == "__main__":
    sys.exit(main())
