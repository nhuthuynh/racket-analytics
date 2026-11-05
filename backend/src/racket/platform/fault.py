"""The API value of the ADR 0012 fault seam (ST-075d; NFR-041.5 fault path, NFR-041.6).

``RACKET_FAULT_INJECTION=api:5xx_on_header`` makes a request carrying ``X-Racket-Fault: 5xx``
get the generic 500 before routing, so the SLO drill (ST-075c) can burn the error budget.
``FaultMiddleware`` reads only ``Settings.fault_injection``, which ``Settings.from_env`` keeps
only under ``APP_ENV=test``: under dev, staging and prod it is inert by construction (threat
note T5-OB-5). ``create_app`` registers it inside ``HttpMetricsMiddleware`` (every injected
500 is in the availability SLI) and inside ``EdgeMiddleware`` (security headers, request ID).
"""

from __future__ import annotations

from typing import Any

from racket.platform.errors import ErrorMapper
from racket.platform.http import error_response, log_error
from racket.platform.settings import Settings

API_5XX_ON_HEADER = "api:5xx_on_header"
FAULT_HEADER = b"x-racket-fault"
FAULT_VALUE = b"5xx"


class FaultMiddleware:
    def __init__(self, app: Any, settings: Settings, mapper: ErrorMapper | None = None) -> None:
        self.app = app
        self.active = settings.fault_injection == API_5XX_ON_HEADER
        self.mapper = mapper or ErrorMapper()

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if self.active and scope["type"] == "http" and _faulted(scope):
            error = self.mapper.for_status(500)
            log_error(error, None)
            await error_response(error, str(scope["method"]))(scope, receive, send)
            return
        await self.app(scope, receive, send)


def _faulted(scope: Any) -> bool:
    return any(k.lower() == FAULT_HEADER and v == FAULT_VALUE for k, v in scope["headers"])
