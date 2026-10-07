"""The browser specs' expected stats stay the independent reference's (QA-ACC-3, ST-054).

``web/e2e/sprint-03/worked-example.reference.json`` holds the coach's worked example
(metric-dictionary §2) as tags and the stats ``scripts/measure/statslib.py`` computes from it.
E2E-03-01..06 and the timing spec read both from that file, so the browser tags exactly the
rallies the numbers belong to. The file is generated, never edited by hand:

    cd backend && env -u APP_ENV uv run python -c "from tests.support.stats import \
write_e2e_reference; write_e2e_reference()"

A difference here means the reference or the worked example changed and the file was not
regenerated (or was edited by hand); the browser numbers would then check nothing.
"""

from __future__ import annotations

import json

import pytest

from tests.support import stats

pytestmark = [pytest.mark.unit, pytest.mark.analytics]


def test_e2e_reference_file_is_the_generated_reference_byte_for_byte() -> None:
    on_disk = stats.E2E_REFERENCE.read_text(encoding="utf-8")
    assert on_disk == stats.e2e_reference_text(), (
        f"{stats.E2E_REFERENCE} is stale or hand-edited; regenerate it (module docstring)"
    )


def test_e2e_reference_tags_are_the_worked_example_without_times() -> None:
    doc = json.loads(stats.e2e_reference_text())
    assert len(doc["tags"]) == 14
    assert doc["tags"] == [
        {k: t[k] for k in ("winning_side", "ending", "fault_kind", "responsible_player")}
        for t in stats.WORKED_EXAMPLE
    ]


def test_e2e_reference_metrics_are_statslib_rounded_to_4_places() -> None:
    doc = json.loads(stats.e2e_reference_text())
    raw = stats.reference(stats.WORKED_EXAMPLE)
    assert set(doc["metrics"]) == set(stats.METRICS)
    # negative control: a hand edit of one number is caught
    assert doc["metrics"]["AN-01"]["A"]["n"] == raw["AN-01"]["A"]["n"] == 7
    text = stats.e2e_reference_text()
    assert json.loads(text)["metrics"] == stats._rounded(json.loads(json.dumps(raw)))
    edited = text.replace('"n": 7, "value": 0.5714', '"n": 8, "value": 0.5714', 1)
    assert edited != text
    assert json.loads(edited)["metrics"]["AN-01"]["A"]["n"] == 8
