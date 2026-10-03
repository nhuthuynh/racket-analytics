#!/usr/bin/env python3
"""Contrast proof for docs/design/tokens.json (NFR-029; WCAG 2.2 SC 1.4.3 and 1.4.11).

Owner: principal-designer. This is documentation tooling, not product code: it proves that every
foreground/background pair declared in ``tokens.json`` -> ``contrastPairs`` meets its minimum ratio,
and prints the Markdown table embedded in ``docs/design/tokens.md``.

Usage:
    python3 docs/design/tools/contrast_check.py [path/to/tokens.json] [--markdown]

Exit codes: 0 every pair passes; 1 at least one pair fails; 2 the tokens file is malformed.

Formula: WCAG 2.x relative luminance and contrast ratio (L1 + 0.05) / (L2 + 0.05), sRGB channel
linearisation with the 0.04045 threshold. Alpha colours (``#RRGGBBAA``) are composited over the
pair's declared ``over`` colour (worst case for a video scrim) before measuring.
Standard library only; no I/O beyond reading the tokens file.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

MINIMUMS = {"text": 4.5, "large-text": 3.0, "non-text": 3.0}


def _hex_to_rgba(value: str) -> tuple[float, float, float, float]:
    v = value.strip().lstrip("#")
    if len(v) not in (6, 8):
        raise ValueError(f"not a #RRGGBB or #RRGGBBAA colour: {value!r}")
    r, g, b = (int(v[i : i + 2], 16) for i in (0, 2, 4))
    a = int(v[6:8], 16) / 255 if len(v) == 8 else 1.0
    return r / 255, g / 255, b / 255, a


def _composite(fg: str, over: str) -> tuple[float, float, float]:
    r, g, b, a = _hex_to_rgba(fg)
    br, bg, bb, _ = _hex_to_rgba(over)
    return (r * a + br * (1 - a), g * a + bg * (1 - a), b * a + bb * (1 - a))


def _lin(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(rgb: tuple[float, float, float]) -> float:
    r, g, b = (_lin(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(fg: tuple[float, float, float], bg: tuple[float, float, float]) -> float:
    l1, l2 = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def resolve(tokens: dict, ref: str) -> str:
    """Resolve 'color.light.text' style references to a hex value."""
    node: object = tokens
    for part in ref.split("."):
        if not isinstance(node, dict) or part not in node:
            raise KeyError(f"unknown token reference {ref!r}")
        node = node[part]
    if isinstance(node, dict):
        node = node.get("value")
    if not isinstance(node, str) or not node.startswith("#"):
        raise KeyError(f"token {ref!r} is not a colour")
    return node


def check(tokens: dict) -> list[dict]:
    rows = []
    for pair in tokens.get("contrastPairs", []):
        kind = pair["kind"]
        if kind not in MINIMUMS:
            raise ValueError(f"unknown pair kind {kind!r}")
        bg_hex = resolve(tokens, pair["bg"])
        if len(bg_hex.lstrip("#")) == 8:
            bg_rgb = _composite(bg_hex, resolve(tokens, pair["over"]))
        else:
            bg_rgb = _composite(bg_hex, "#000000")
        fg_hex = resolve(tokens, pair["fg"])
        opaque_fg = len(fg_hex.lstrip("#")) == 6
        fg_rgb = _composite(fg_hex, "#000000") if opaque_fg else _composite(fg_hex, bg_hex)
        r = ratio(fg_rgb, bg_rgb)
        over_note = f" over `{resolve(tokens, pair['over'])}`" if "over" in pair else ""
        need = MINIMUMS[kind]
        rows.append(
            {
                "theme": pair.get("theme", ""),
                "use": pair["use"],
                "fg": f"{pair['fg']} `{fg_hex}`",
                "bg": f"{pair['bg']} `{bg_hex}`" + over_note,
                "kind": kind,
                "need": need,
                "ratio": r,
                "pass": round(r, 2) >= need and r >= need,
            }
        )
    return rows


def markdown(rows: list[dict]) -> str:
    out = [
        "| Theme | Use | Foreground | Background | Kind | Minimum | Ratio | Result |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        out.append(
            f"| {r['theme']} | {r['use']} | {r['fg']} | {r['bg']} | {r['kind']} | {r['need']}:1 | "
            f"{r['ratio']:.2f}:1 | {'PASS' if r['pass'] else 'FAIL'} |"
        )
    return "\n".join(out)


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    path = Path(args[0]) if args else Path(__file__).resolve().parent.parent / "tokens.json"
    try:
        tokens = json.loads(path.read_text(encoding="utf-8"))
        rows = check(tokens)
    except (OSError, ValueError, KeyError) as exc:
        print(f"MALFORMED: {exc}", file=sys.stderr)
        return 2
    if "--markdown" in argv:
        print(markdown(rows))
    failures = [r for r in rows if not r["pass"]]
    for r in failures:
        print(f"FAIL {r['theme']} {r['use']}: {r['ratio']:.2f}:1 < {r['need']}:1", file=sys.stderr)
    print(f"{len(rows) - len(failures)}/{len(rows)} pairs pass", file=sys.stderr)
    return 1 if failures or not rows else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
