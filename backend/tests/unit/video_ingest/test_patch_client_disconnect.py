"""C-14 (SRE-G2-02): a client that disconnects while a PATCH body streams is a client-side
refusal (4xx, logged at INFO), never a 500: the availability SLI (NFR-041) counts 5xx only.
No I/O: the body reader is driven with a stand-in request.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from starlette.requests import ClientDisconnect

from racket.platform.errors import AppError, ErrorMapper
from racket.video_ingest.api import _read_exactly

pytestmark = pytest.mark.unit


class _Dropped:
    """A request whose client goes away after the first 4 bytes."""

    async def stream(self) -> AsyncIterator[bytes]:
        yield b"abcd"
        raise ClientDisconnect()


async def test_a_disconnect_mid_body_is_a_4xx_app_error() -> None:
    with pytest.raises(AppError) as exc:
        await _read_exactly(_Dropped(), 10)  # type: ignore[arg-type]
    error = ErrorMapper().map(exc.value)
    assert 400 <= error.status < 500
    assert error.code == "client_closed_request"
