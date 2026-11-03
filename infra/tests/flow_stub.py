"""A local stand-in for the three GitHub REST list endpoints `scripts/measure/flow_metrics.py`
reads (QA-FLOW-METRICS, PRC-5.1-5.5): `pulls?state=...`, `pulls/{n}/commits` and
`actions/runs`. Real HTTP on 127.0.0.1. It pages with `?page=N` (two items a page, an empty
page past the end) and never sends a `Link` header, because the agent proxy refuses the
`repositories/{id}` form GitHub puts in `Link` (HTTP 403, observed 2026-11-03). Every request
is recorded so a test can assert that only REST paths under `/repos/` were read.
"""

from __future__ import annotations

import json
import re
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlsplit

REPO = "nhuthuynh/racket-analytics"


def pr(
    number: int,
    ticket: str | None,
    created_at: str,
    merged_at: str | None = None,
    *,
    state: str = "closed",
    base: str = "main",
    head: str | None = None,
) -> dict[str, Any]:
    """A pull request as `GET /repos/{repo}/pulls` lists it (only the fields the script reads)."""
    title = f"[{ticket}] work" if ticket else "chore: no ticket id"
    return {
        "number": number,
        "title": title,
        "state": state,
        "created_at": created_at,
        "merged_at": merged_at,
        "closed_at": merged_at if state == "closed" else None,
        "base": {"ref": base},
        "head": {"ref": head or f"s05/{(ticket or 'x').lower()}-{number}"},
    }


def commit(author_date: str, sha: str = "a" * 40) -> dict[str, Any]:
    return {"sha": sha, "commit": {"author": {"date": author_date}}}


def run(
    head_branch: str, started: str, updated: str, *, created: str | None = None, run_id: int = 1
) -> dict[str, Any]:
    return {
        "id": run_id,
        "event": "pull_request",
        "status": "completed",
        "head_branch": head_branch,
        "created_at": created or started,
        "run_started_at": started,
        "updated_at": updated,
    }


@dataclass
class FlowStub:
    pulls: list[dict[str, Any]] = field(default_factory=list)
    commits: dict[int, list[dict[str, Any]]] = field(default_factory=dict)
    runs: list[dict[str, Any]] = field(default_factory=list)
    page_size: int = 2
    fail_status: int | None = None  # e.g. 500: every endpoint fails
    requests: list[str] = field(default_factory=list)
    url: str = ""


def _handler(stub: FlowStub) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args: object) -> None:
            pass

        def do_POST(self) -> None:  # GraphQL would be a POST; it is never allowed here
            stub.requests.append(f"POST {self.path}")
            self._send({"message": "GraphQL is not served by this stub"}, 403)

        def do_GET(self) -> None:
            parts = urlsplit(self.path)
            query = parse_qs(parts.query)
            stub.requests.append(self.path)
            if stub.fail_status:
                return self._send({"message": "boom"}, stub.fail_status)
            page = int(query.get("page", ["1"])[0])
            base = f"/repos/{REPO}"
            if parts.path == f"{base}/pulls":
                state = query.get("state", ["open"])[0]
                items = [p for p in stub.pulls if state == "all" or p["state"] == state]
                return self._send(self._page(items, page))
            m = re.fullmatch(rf"{base}/pulls/(\d+)/commits", parts.path)
            if m:
                return self._send(self._page(stub.commits.get(int(m.group(1)), []), page))
            if parts.path == f"{base}/actions/runs":
                chunk = self._page(stub.runs, page)
                return self._send({"total_count": len(stub.runs), "workflow_runs": chunk})
            self._send({"message": "Not Found"}, 404)

        def _page(self, items: list[Any], page: int) -> list[Any]:
            start = (page - 1) * stub.page_size
            return items[start : start + stub.page_size]

        def _send(self, body: object, status: int = 200) -> None:
            data = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    return Handler


@contextmanager
def serve(stub: FlowStub) -> Iterator[FlowStub]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _handler(stub))
    stub.url = f"http://127.0.0.1:{server.server_address[1]}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield stub
    finally:
        server.shutdown()
        server.server_close()
