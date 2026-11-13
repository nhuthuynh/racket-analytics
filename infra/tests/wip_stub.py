"""A local stand-in for the GitHub REST endpoints `scripts/measure/wip_gate.py` reads
(QA-WIP-GATE, PRC-12.1): `pulls?state=open`, `pulls/{n}/reviews` and
`commits/{sha}/check-runs`. Real HTTP on 127.0.0.1. It pages with `?page=N` (two items a page,
an empty page past the end) and sends no `Link` header, as `flow_stub.py` does, because the
agent proxy refuses the `repositories/{id}` form GitHub puts in `Link`. Every request is
recorded so a test can assert that only REST paths under `/repos/` were read.
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
PE = "principal-engineer"
QA = "senior-qa-engineer"


def ticket_pr(
    number: int,
    *,
    draft: bool = False,
    ticket: str | None = None,
    base: str = "main",
    sha: str | None = None,
) -> dict[str, Any]:
    """An open pull request as `GET /repos/{repo}/pulls` lists it (only the fields read)."""
    tid = ticket if ticket is not None else f"T-{number}"
    return {
        "number": number,
        "title": f"[{tid}] work" if tid else "chore: no ticket id",
        "state": "open",
        "draft": draft,
        "base": {"ref": base},
        "head": {"ref": f"s06/t-{number}", "sha": sha or head_of(number)},
    }


def head_of(number: int) -> str:
    return f"{number:040x}"


_REVIEW_IDS = iter(range(1, 1_000_000))


def review(
    role: str,
    sha: str,
    verdict: str = "APPROVE",
    *,
    submitted_at: str = "2026-11-13T10:00:00Z",
    association: str = "OWNER",
) -> dict[str, Any]:
    """A submitted review whose body is the parseable verdict (working-agreement §6)."""
    return {
        "id": next(_REVIEW_IDS),
        "state": "APPROVED" if verdict == "APPROVE" else "CHANGES_REQUESTED",
        "body": f"Verdict: {verdict}\nReviewer: {role}\n\nHead: {sha}\n",
        "commit_id": sha,
        "submitted_at": submitted_at,
        "author_association": association,
    }


def gate_run(conclusion: str = "success", name: str = "ci-gate") -> dict[str, Any]:
    return {"id": 1, "name": name, "status": "completed", "conclusion": conclusion}


@dataclass
class WipStub:
    pulls: list[dict[str, Any]] = field(default_factory=list)
    reviews: dict[int, list[dict[str, Any]]] = field(default_factory=dict)
    check_runs: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    page_size: int = 2
    fail_status: int | None = None  # e.g. 500: every endpoint fails
    requests: list[str] = field(default_factory=list)
    url: str = ""

    def in_progress(self, number: int) -> None:
        self.pulls.append(ticket_pr(number, draft=True))

    def in_review(self, number: int) -> None:
        self.pulls.append(ticket_pr(number))

    def awaiting_qa(self, number: int) -> None:
        self.pulls.append(ticket_pr(number))
        self.reviews[number] = [review(PE, head_of(number))]

    def awaiting_merge(self, number: int) -> None:
        self.pulls.append(ticket_pr(number))
        self.reviews[number] = [review(PE, head_of(number)), review(QA, head_of(number))]
        self.check_runs[head_of(number)] = [gate_run()]


def _handler(stub: WipStub) -> type[BaseHTTPRequestHandler]:
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
            m = re.fullmatch(rf"{base}/pulls/(\d+)/reviews", parts.path)
            if m:
                return self._send(self._page(stub.reviews.get(int(m.group(1)), []), page))
            m = re.fullmatch(rf"{base}/commits/([0-9a-f]{{40}})/check-runs", parts.path)
            if m:
                runs = stub.check_runs.get(m.group(1), [])
                return self._send({"total_count": len(runs), "check_runs": self._page(runs, page)})
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
def serve(stub: WipStub) -> Iterator[WipStub]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _handler(stub))
    stub.url = f"http://127.0.0.1:{server.server_address[1]}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield stub
    finally:
        server.shutdown()
        server.server_close()
