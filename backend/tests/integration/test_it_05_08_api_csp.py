"""IT-05-08 gap F1 (ST-078e-F1, ticket ST-078f; NFR-050.7; G05-07): the same-origin ``/api/*``
answers on the web origin carry CSP with ``frame-ancestors 'none'``, ``nosniff`` and
``X-Frame-Options: DENY``.

Next 15 adds no ``headers()`` value to an external rewrite's answer, so ``/api/healthz`` through
the web origin carries the API's own ``nosniff`` and ``DENY`` and no CSP (live on the ST-078e head
``ada9c50a``). The fix is the API's: senior-backend-engineer adds the CSP to ``SECURITY_HEADERS``
in ``backend/src/racket/platform/http.py``. Until then this row is red and listed, not gated
(ADR 0046 backend twin, ``scripts/ci/red_until_report.py``); when the fix lands, the stale-marker
check fails and QA lifts the marker with a TCR row, so the row joins the gate.
G05-07's header line is not met while this row is red (docs/sprints/05/decisions/ST-078e.md D3).
"""

from __future__ import annotations

import httpx
import pytest

from tests.integration.test_it_05_security_headers import _missing, web  # noqa: F401 (fixture)

pytestmark = [pytest.mark.red_until(story="ST-078f")]


def test_the_same_origin_api_answer_has_csp_nosniff_and_frame_denial(web: httpx.Client) -> None:  # noqa: F811
    response = web.get("/api/healthz")
    # Positive control: the API answers through the web origin's rewrite.
    assert response.status_code == 200, f"/api/healthz: {response.status_code}"
    assert _missing(response) == []
