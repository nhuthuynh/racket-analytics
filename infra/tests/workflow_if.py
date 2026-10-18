"""Evaluate a GitHub Actions job `if:` for a given event (CI-DRAFT-SKIP).

Covers the subset ci.yml uses: dotted `github.*` contexts, string literals, `==`, `!=`, `!`,
`&&`, `||`, parentheses and `always()`. A missing context is null, as on GitHub (a push has
no `github.event.pull_request`, so `!github.event.pull_request.draft` is true there). Anything
else raises, so a new construct in ci.yml cannot be silently misread.
"""

from __future__ import annotations

import re
from typing import Any

_TOKEN = re.compile(
    r"\s*(?:(?P<str>'[^']*')|(?P<op>==|!=|&&|\|\||!|\(|\))|(?P<call>always\(\))"
    r"|(?P<ctx>github(?:\.[A-Za-z_][A-Za-z0-9_-]*)+))"
)
_PY = {"==": "==", "!=": "!=", "&&": " and ", "||": " or ", "!": " not ", "(": "(", ")": ")"}

DRAFT_PR = {"github.event_name": "pull_request", "github.event.pull_request.draft": True}
READY_PR = {"github.event_name": "pull_request", "github.event.pull_request.draft": False}
PUSH = {"github.event_name": "push"}
SCHEDULE = {"github.event_name": "schedule"}
DISPATCH = {"github.event_name": "workflow_dispatch"}


def evaluate(expr: str | None, context: dict[str, Any]) -> bool:
    """True when a job with this `if:` runs for the event in `context` (no `if:` = runs)."""
    if expr is None:
        return True
    source, values, pos = [], {}, 0
    expr = expr.strip()
    while pos < len(expr):
        m = _TOKEN.match(expr, pos)
        if not m or m.end() == pos:
            raise ValueError(f"unsupported expression at {pos}: {expr[pos:]!r}")
        pos = m.end()
        if m["str"]:
            source.append(repr(m["str"][1:-1]))
        elif m["op"]:
            source.append(_PY[m["op"]])
        elif m["call"]:
            source.append("True")
        else:
            key = f"v{len(values)}"
            values[key] = context.get(m["ctx"])
            source.append(key)
    return bool(eval("".join(source), {"__builtins__": {}}, values))  # noqa: S307 - own tokens
