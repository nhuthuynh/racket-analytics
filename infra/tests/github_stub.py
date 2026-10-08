"""A local stand-in for the three GitHub REST endpoints `scripts/ci/merge_ready.py` reads
(CI-PR-GATE). It speaks real HTTP on 127.0.0.1, paginates with `Link: rel="next"` like
GitHub, and records the requests, so the script is exercised over a real socket.
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
PR_NUMBER = 7
HEAD_SHA = "c2" * 20
OLD_SHA = "c1" * 20


def check_run(
    name: str,
    conclusion: str | None = "success",
    status: str = "completed",
    run_id: int = 1,
    suite_id: int = 1,
) -> dict[str, Any]:
    return {
        "id": run_id,
        "name": name,
        "status": status,
        "conclusion": conclusion,
        "check_suite": {"id": suite_id},
    }


def review(
    role: str,
    verdict: str,
    sha: str = HEAD_SHA,
    review_id: int = 1,
    submitted_at: str | None = "2026-10-08T10:00:00Z",
    *,
    state: str = "COMMENTED",
    association: str = "OWNER",
) -> dict[str, Any]:
    """A review as GitHub lists it. The repo owner's account posts for every agent role."""
    login = "nhuthuynh" if association == "OWNER" else "outsider"
    return {
        "id": review_id,
        "user": {"login": login},
        "author_association": association,
        "state": state,
        "commit_id": sha,
        "submitted_at": submitted_at,
        "body": f"Verdict: {verdict}\nReviewer: {role}\n\nFindings: none.",
    }


def green_runs() -> list[dict[str, Any]]:
    names = [
        "PR policy (test immutability, size)",
        "Python unit suites (time-budgeted)",
        "Infra, hooks and CI-script tests (ST-001..ST-003)",
        "ci-gate",
    ]
    runs = [check_run(n, run_id=i + 1) for i, n in enumerate(names)]
    runs.append(check_run("Flaky-test report (NFR-074)", conclusion="skipped", run_id=9))
    return runs


def approvals(sha: str = HEAD_SHA) -> list[dict[str, Any]]:
    return [
        review("principal-engineer", "APPROVE", sha, 1),
        review("senior-qa-engineer", "APPROVE", sha, 2),
    ]


@dataclass
class GitHubStub:
    pr: dict[str, Any] = field(
        default_factory=lambda: {
            "number": PR_NUMBER,
            "state": "open",
            "head": {"sha": HEAD_SHA},
            "base": {"ref": "main"},
        }
    )
    check_runs: list[dict[str, Any]] = field(default_factory=green_runs)
    reviews: list[dict[str, Any]] = field(default_factory=approvals)
    page_size: int = 2
    requests: list[tuple[str, str | None]] = field(default_factory=list)
    url: str = ""
    raw_pr: bytes | None = None  # a non-JSON body for the PR endpoint


def _handler(stub: GitHubStub) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args: object) -> None:  # keep test output clean
            pass

        def do_GET(self) -> None:
            parts = urlsplit(self.path)
            stub.requests.append((self.path, self.headers.get("Authorization")))
            page = int(parse_qs(parts.query).get("page", ["1"])[0])
            base = f"/repos/{REPO}"
            if parts.path == f"{base}/pulls/{PR_NUMBER}":
                return self._send_raw(stub.raw_pr) if stub.raw_pr else self._send(stub.pr)
            m = re.fullmatch(rf"{base}/commits/(\w+)/check-runs", parts.path)
            if m:
                runs = [r for r in stub.check_runs if r.get("head_sha", HEAD_SHA) == m.group(1)]
                chunk, more = self._page(runs, page)
                return self._send({"total_count": len(runs), "check_runs": chunk}, more, page)
            if parts.path == f"{base}/pulls/{PR_NUMBER}/reviews":
                chunk, more = self._page(stub.reviews, page)
                return self._send(chunk, more, page)
            self._send({"message": "Not Found"}, status=404)

        def _send_raw(self, data: bytes) -> None:
            self.send_response(200)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _page(self, items: list[Any], page: int) -> tuple[list[Any], bool]:
            start = (page - 1) * stub.page_size
            return items[start : start + stub.page_size], start + stub.page_size < len(items)

        def _send(self, body: object, more: bool = False, page: int = 1, status: int = 200) -> None:
            data = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            if more:
                path = urlsplit(self.path).path
                self.send_header(
                    "Link", f'<{stub.url}{path}?per_page=100&page={page + 1}>; rel="next"'
                )
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    return Handler


@contextmanager
def serve(stub: GitHubStub) -> Iterator[GitHubStub]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _handler(stub))
    stub.url = f"http://127.0.0.1:{server.server_address[1]}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield stub
    finally:
        server.shutdown()
        server.server_close()
