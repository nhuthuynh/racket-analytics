"""IT-05-08 gap F2 (ST-078e-F2, ticket ST-078g; NFR-050.7; G05-07): the media route on the web
origin (``infra/tls/Caddyfile``, ``/{$S3_BUCKET_MEDIA}/*``) carries CSP with
``frame-ancestors 'none'``, ``nosniff`` and ``X-Frame-Options: DENY`` on every answer.

Both branches of the route are probed without an upload (live on the ST-078e head ``ada9c50a``):
a GET with a signature parameter reaches the store, which refuses the bogus signature (403) and
the edge adds ``default-src 'none'; sandbox`` and ``nosniff`` but no frame denial; a GET without
one is stopped by the edge's ``respond 403`` with none of the three headers. The fix is the
SRE's (``infra/tls/Caddyfile``). Until then these rows are red and listed, not gated (ADR 0046
backend twin); when the fix lands, the stale-marker check fails and QA lifts the marker with a
TCR row. G05-07's header line is not met while these rows are red (ST-078e decisions D4).
"""

from __future__ import annotations

import os

import httpx
import pytest

from tests.integration.test_it_05_security_headers import _missing, web  # noqa: F401 (fixture)

pytestmark = [pytest.mark.red_until(story="ST-078g")]

BUCKET = os.environ.get("S3_BUCKET_MEDIA", "racket-media")
PROBE = f"/{BUCKET}/it-05-08-probe"


@pytest.mark.parametrize(
    ("query", "what"),
    [("?X-Amz-Signature=0", "presigned branch (store refuses)"), ("", "unsigned branch (edge)")],
)
def test_every_media_route_answer_has_csp_nosniff_and_frame_denial(
    web: httpx.Client,  # noqa: F811
    query: str,
    what: str,
) -> None:
    response = web.get(PROBE + query)
    # Positive control: the media route answered (a 403 refusal), not the web app's 404 page.
    assert response.status_code == 403, f"{what} {PROBE}{query}: {response.status_code}"
    assert _missing(response) == []
