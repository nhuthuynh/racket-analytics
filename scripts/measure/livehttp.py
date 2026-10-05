"""Minimal HTTP(S) client and magic-link sign-in for the live measurement scripts.

Standard library only. One ``Client`` holds one keep-alive connection, so use one per thread.
The pure parts (token and cookie parsing, tus headers) are in measurelib and unit-tested.
"""

from __future__ import annotations

import http.client
import json
import ssl
import time
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from typing import Any

from measurelib import session_cookie, token_from


@dataclass
class Reply:
    status: int
    headers: http.client.HTTPMessage
    body: bytes
    ms: float

    def json(self) -> Any:
        return json.loads(self.body or b"null")


def ssl_context(cacert: str | None, insecure_loopback: bool) -> ssl.SSLContext:
    ctx = ssl.create_default_context(cafile=cacert) if cacert else ssl.create_default_context()
    if insecure_loopback:  # loopback dev stack only, like Playwright (ADR 0029)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


class Client:
    def __init__(self, base: str, origin: str, ctx: ssl.SSLContext, timeout: float = 60) -> None:
        url = urllib.parse.urlsplit(base)
        if url.scheme == "https" and url.hostname not in ("localhost", "127.0.0.1", "::1"):
            ctx = ssl.create_default_context()  # never relax TLS beyond loopback
        self.scheme, self.host, self.port = url.scheme, url.hostname or "", url.port
        self.prefix = url.path.rstrip("/")
        self.origin, self.ctx, self.timeout = origin, ctx, timeout
        self.cookie: str | None = None
        self.conn: http.client.HTTPConnection | None = None

    def _connect(self) -> http.client.HTTPConnection:
        if self.conn is None:
            if self.scheme == "https":
                self.conn = http.client.HTTPSConnection(
                    self.host, self.port, timeout=self.timeout, context=self.ctx
                )
            else:
                self.conn = http.client.HTTPConnection(self.host, self.port, timeout=self.timeout)
        return self.conn

    def close(self) -> None:
        if self.conn is not None:
            self.conn.close()
            self.conn = None

    def path(self, p: str) -> str:
        """API paths are relative to the prefix; a Location that already has it is kept."""
        return p if self.prefix and p.startswith(self.prefix + "/") else self.prefix + p

    def request(
        self,
        method: str,
        p: str,
        *,
        body: bytes | None = None,
        json_body: Any = None,
        headers: dict[str, str] | None = None,
    ) -> Reply:
        hdrs = {"Origin": self.origin, **(headers or {})}
        if json_body is not None:
            body = json.dumps(json_body).encode()
            hdrs["Content-Type"] = "application/json"
        if self.cookie:
            hdrs["Cookie"] = self.cookie
        for attempt in (1, 2):
            conn = self._connect()
            start = time.perf_counter()
            try:
                conn.request(method, self.path(p), body=body, headers=hdrs)
                resp = conn.getresponse()
                data = resp.read()
            except (http.client.HTTPException, OSError):
                self.close()
                if attempt == 2:
                    raise
                continue
            ms = (time.perf_counter() - start) * 1000
            cookie = session_cookie(resp.headers.get_all("Set-Cookie") or [])
            if cookie:
                self.cookie = cookie
            if resp.headers.get("Connection", "").lower() == "close":
                self.close()
            return Reply(resp.status, resp.headers, data, ms)
        raise RuntimeError("unreachable")


def mailpit_token(mailpit: str, address: str, timeout_s: float = 30.0) -> str | None:
    """The sign-in token from the newest email to ``address`` in Mailpit, or None."""
    deadline = time.monotonic() + timeout_s
    query = urllib.parse.urlencode({"query": f'to:"{address}"'})
    while time.monotonic() < deadline:
        with urllib.request.urlopen(f"{mailpit}/api/v1/search?{query}", timeout=10) as r:  # noqa: S310
            messages = json.load(r).get("messages") or []
        if messages:
            with urllib.request.urlopen(  # noqa: S310
                f"{mailpit}/api/v1/message/{messages[0]['ID']}", timeout=10
            ) as r:
                msg = json.load(r)
            return token_from(f"{msg.get('Text', '')}\n{msg.get('HTML', '')}")
        time.sleep(0.2)
    return None


def sign_in(client: Client, mailpit: str) -> dict[str, Any]:
    """Magic-link sign-in as a fresh account (testing-strategy rule c: no shared state)."""
    address = f"goal-{uuid.uuid4().hex[:12]}@example.com"
    t0 = time.perf_counter()
    link = client.request("POST", "/auth/links", json_body={"email": address})
    token = mailpit_token(mailpit, address) if link.status == 202 else None
    t_mail = time.perf_counter()
    exchange = (
        client.request("POST", "/auth/exchange", json_body={"token": token}) if token else None
    )
    t1 = time.perf_counter()
    ok = bool(exchange and exchange.status == 200 and client.cookie)
    return {
        "ok": ok,
        "address": address,
        "link_status": link.status,
        "exchange_status": exchange.status if exchange else None,
        "email_s": round(t_mail - t0, 3),
        "sign_in_s": round(t1 - t0, 3),
    }
