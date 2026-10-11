"""The PR's labels as they are when a PR-policy check runs (CI-POLICY-LIVE-LABELS).

`github.event.pull_request.labels` is frozen when the event fires: a run started by a push made
before `size-waiver` was applied, or a re-run of it, never sees the label (PR #71, CI runs
38094831495 and 38096137380). `live_labels` reads GET /repos/{repo}/issues/{pr}/labels instead.
It returns None when it cannot (no token, PR number or repo, or the API fails); the caller then
uses the event payload, exactly as before. Either way it logs which source was used.

Env: GITHUB_TOKEN or GH_TOKEN, GITHUB_REPOSITORY, PR_NUMBER, GITHUB_API_URL (default GitHub).
"""

from __future__ import annotations

import json
import re
import urllib.request
from collections.abc import Mapping

MAX_PAGES = 10  # GitHub allows 100 labels per issue; never follow `next` forever
_NEXT = re.compile(r'<([^>]+)>;\s*rel="next"')


def _fetch(url: str, token: str) -> list[str]:
    names: list[str] = []
    for _ in range(MAX_PAGES):
        req = urllib.request.Request(  # noqa: S310 (https, or the local test stub)
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
            body = json.load(resp)
            link = _NEXT.search(resp.headers.get("Link") or "")
        if not isinstance(body, list) or not all(isinstance(x.get("name"), str) for x in body):
            raise ValueError("labels response is not a list of labels")
        names += [x["name"] for x in body]
        if not link:
            return names
        url = link.group(1)
    raise ValueError(f"more than {MAX_PAGES} pages of labels")


def live_labels(env: Mapping[str, str], who: str) -> list[str] | None:
    """The PR's current label names, or None to keep the event payload. `who` prefixes the log."""
    need = {
        "GITHUB_TOKEN": env.get("GITHUB_TOKEN") or env.get("GH_TOKEN"),
        "PR_NUMBER": env.get("PR_NUMBER"),
        "GITHUB_REPOSITORY": env.get("GITHUB_REPOSITORY"),
    }
    missing = [k for k, v in need.items() if not v]
    if missing:
        print(f"{who}: labels from the event payload (no {', '.join(missing)})")
        return None
    api = (env.get("GITHUB_API_URL") or "https://api.github.com").rstrip("/")
    url = f"{api}/repos/{need['GITHUB_REPOSITORY']}/issues/{need['PR_NUMBER']}/labels?per_page=100"
    try:
        names = _fetch(url, str(need["GITHUB_TOKEN"]))
    except (OSError, ValueError, AttributeError) as exc:  # URLError/HTTPError/timeout are OSError
        print(f"{who}: labels from the event payload (GitHub API failed: {exc})")
        return None
    print(f"{who}: labels from the GitHub API: {', '.join(names) or '(none)'}")
    return names
