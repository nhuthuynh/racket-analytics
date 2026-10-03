"""Scenario report: every Gherkin scenario with its tags and result; scenarios tagged
``@needs-verification`` are listed in their own section (ST-004; QD-QG-P5; DOM G1).

    cd backend && uv run pytest tests/features --junitxml=../.local/scenarios.xml
    uv run python -m tests.tools.scenario_report --junit ../.local/scenarios.xml

Results are matched to pytest-bdd test names (``test_<scenario name in snake case>``).
"""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gherkin.parser import Parser
from pytest_bdd.scenario import make_python_name

from tests.support.paths import FEATURES


@dataclass(frozen=True)
class Row:
    feature_file: str
    feature: str
    scenario: str
    tags: tuple[str, ...]
    result: str

    @property
    def needs_verification(self) -> bool:
        return "needs-verification" in self.tags


def _test_name(scenario: str) -> str:
    """The test function name pytest-bdd generates for a scenario."""
    return "test_" + make_python_name(scenario)


def _tags(node: dict[str, Any]) -> list[str]:
    return [t["name"].lstrip("@") for t in node.get("tags", [])]


def _junit_results(junit: Path | None) -> dict[str, str]:
    if junit is None:
        return {}
    outcomes: dict[str, set[str]] = {}
    for case in ET.parse(junit).getroot().iter("testcase"):  # noqa: S314
        name = case.get("name", "").split("[")[0]
        if case.find("failure") is not None or case.find("error") is not None:
            outcome = "failed"
        elif case.find("skipped") is not None:
            outcome = "skipped"
        else:
            outcome = "passed"
        outcomes.setdefault(name, set()).add(outcome)
    return {
        name: "failed" if "failed" in seen else "skipped" if seen == {"skipped"} else "passed"
        for name, seen in outcomes.items()
    }


def collect(features_dir: Path = FEATURES, junit: Path | None = None) -> list[Row]:
    results = _junit_results(junit)
    rows: list[Row] = []
    for path in sorted(features_dir.glob("*.feature")):
        document = Parser().parse(path.read_text(encoding="utf-8"))
        feature: dict[str, Any] = dict(document["feature"] or {})
        feature_tags = _tags(feature)
        stack: list[tuple[dict[str, Any], list[str]]] = [(feature, feature_tags)]
        while stack:
            node, inherited = stack.pop(0)
            for child in node.get("children", []):
                if "rule" in child:
                    stack.append((child["rule"], inherited + _tags(child["rule"])))
                elif "scenario" in child:
                    scenario = child["scenario"]
                    rows.append(
                        Row(
                            feature_file=path.name,
                            feature=feature["name"],
                            scenario=scenario["name"],
                            tags=tuple(inherited + _tags(scenario)),
                            result=results.get(_test_name(scenario["name"]), "not run"),
                        )
                    )
    return rows


def _tag_text(row: Row) -> str:
    return " ".join("@" + t for t in row.tags)


def render(rows: Sequence[Row]) -> str:
    def table(selected: Sequence[Row]) -> list[str]:
        lines = ["| Feature file | Scenario | Tags | Result |", "|---|---|---|---|"]
        lines += [
            f"| {r.feature_file} | {r.scenario} | {_tag_text(r)} | {r.result} |" for r in selected
        ]
        return lines

    verified = [r for r in rows if not r.needs_verification]
    unverified = [r for r in rows if r.needs_verification]
    counts: dict[str, int] = {}
    for r in rows:
        counts[r.result] = counts.get(r.result, 0) + 1
    summary = ", ".join(f"{v} {k}" for k, v in sorted(counts.items()))
    out = [
        "# Scenario report",
        "",
        f"{len(rows)} scenarios: {summary}",
        "",
        "## Verified rules",
        "",
    ]
    out += table(verified)
    out += ["", "## Needs verification", ""]
    out += table(unverified) if unverified else ["None."]
    return "\n".join(out) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path, default=FEATURES)
    parser.add_argument("--junit", type=Path)
    args = parser.parse_args(argv)
    sys.stdout.write(render(collect(args.features, args.junit)))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
