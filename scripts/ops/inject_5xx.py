#!/usr/bin/env python3
"""G05-02 SLO drill: burn the API error budget through the ST-075d fault seam (ST-075c).

Sends GET requests to ``--base-url`` + ``--path`` at ``--rps``; ``--rate`` % of them carry
``X-Racket-Fault: 5xx``, spread evenly. A drill stack (APP_ENV=test plus
infra/compose.fault-drill.yaml) answers those with 500; any other stack ignores the header
(NFR-041.6). The script changes nothing else: no stack setting, no Compose call.

Expectations (any combination; exit 1 names each one that fails):
  --expect-alert NAME   NAME is firing in Prometheus (``--prom``) before the run ends; the run
                        stops as soon as it fires and records seconds_to_firing
  --expect-no-alert     no alert is firing in Prometheus at any poll of the run
  --expect-no-5xx       no response has a 5xx status

Usage (docs/ops/slo.md "Drill"; ADR 0057: at least 5 requests/s, no load in the previous hour):
  inject_5xx.py --base-url https://localhost:3000 --rate 10 --minutes 10 \
    --expect-alert ApiAvailabilityFastBurn --prom http://localhost:9090 \
    --json reports/slo-drill.json

Exit codes: 0 every expectation met, 1 an expectation failed, 2 usage error or the API or
Prometheus could not be reached (fails closed, ADR 0014). Standard library only.
"""

from __future__ import annotations

import argparse
import json
import math
import ssl
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

FAULT_HEADER = "X-Racket-Fault"
FAULT_VALUE = "5xx"
DEFAULT_CA = Path(".local/demo/root.crt")  # copied by `make demo` from the stack's web-tls
TIMEOUT_S = 10


class Unreachable(Exception):
    """The API or Prometheus did not answer: the run is not evidence either way."""


def faulted(i: int, rate: float) -> bool:
    """Whether request ``i`` (from 0) carries the header: exactly rate % of any prefix, spread."""
    return math.floor((i + 1) * rate / 100) > math.floor(i * rate / 100)


def _rate(text: str) -> float:
    try:
        value = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError("--rate must be a number from 0 to 100") from None
    if not 0 <= value <= 100:
        raise argparse.ArgumentTypeError("--rate must be a number from 0 to 100")
    return value


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--base-url", required=True, help="the stack's web origin or API base")
    p.add_argument("--path", default="/api/healthz", help="request path (default the API health)")
    p.add_argument("--rate", type=_rate, required=True, help="percent of requests to fault, 0-100")
    span = p.add_mutually_exclusive_group(required=True)
    span.add_argument("--minutes", type=float, help="how long to send requests")
    span.add_argument("--requests", type=int, help="how many requests to send")
    p.add_argument("--rps", type=float, default=10.0, help="requests a second (default 10)")
    p.add_argument("--prom", help="Prometheus base URL, e.g. http://localhost:9090")
    p.add_argument("--expect-alert", metavar="NAME")
    p.add_argument("--expect-no-alert", action="store_true")
    p.add_argument("--expect-no-5xx", action="store_true")
    p.add_argument("--poll-s", type=float, default=15.0, help="Prometheus poll interval")
    p.add_argument("--cacert", type=Path, help=f"TLS root for https (default {DEFAULT_CA})")
    p.add_argument("--json", type=Path, help="write the run report here")
    args = p.parse_args(argv)
    if (args.expect_alert or args.expect_no_alert) and not args.prom:
        p.error("--expect-alert and --expect-no-alert need --prom")
    if args.rps <= 0 or (args.requests is not None and args.requests < 1):
        p.error("--rps and --requests must be positive")
    return args


def _ssl_context(base_url: str, cacert: Path | None) -> ssl.SSLContext | None:
    if not base_url.startswith("https://"):
        return None
    ca = cacert or DEFAULT_CA
    return ssl.create_default_context(cafile=str(ca)) if ca.is_file() else None


def _get(url: str, headers: dict[str, str], context: ssl.SSLContext | None) -> int:
    request = urllib.request.Request(url, headers=headers)  # noqa: S310 - operator-given URL
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S, context=context) as response:  # noqa: S310
            response.read()
            return response.status
    except urllib.error.HTTPError as err:
        err.read()
        return err.code
    except (urllib.error.URLError, OSError) as err:
        raise Unreachable(f"{url}: {err}") from None


def firing_alerts(prom: str) -> list[str]:
    """Names of the alerts Prometheus reports in state ``firing``."""
    try:
        with urllib.request.urlopen(f"{prom.rstrip('/')}/api/v1/alerts", timeout=TIMEOUT_S) as r:  # noqa: S310
            doc = json.load(r)
    except (urllib.error.URLError, OSError, ValueError) as err:
        raise Unreachable(f"prometheus {prom}: {err}") from None
    alerts = doc.get("data", {}).get("alerts", [])
    return sorted({a["labels"]["alertname"] for a in alerts if a.get("state") == "firing"})


def drill(args: argparse.Namespace) -> dict[str, Any]:
    url = args.base_url.rstrip("/") + args.path
    context = _ssl_context(args.base_url, args.cacert)
    total = args.requests if args.requests is not None else math.ceil(args.minutes * 60 * args.rps)
    statuses: Counter[str] = Counter()
    sent_faults = 0
    seen_firing: set[str] = set()
    seconds_to_firing: float | None = None
    start = time.monotonic()
    next_poll = start
    started_at = datetime.now(UTC).isoformat(timespec="seconds")
    for i in range(total):
        due = start + i / args.rps
        if (pause := due - time.monotonic()) > 0:
            time.sleep(pause)
        fault = faulted(i, args.rate)
        sent_faults += fault
        statuses[str(_get(url, {FAULT_HEADER: FAULT_VALUE} if fault else {}, context))] += 1
        if args.prom and time.monotonic() >= next_poll:
            next_poll = time.monotonic() + args.poll_s
            seen_firing.update(firing_alerts(args.prom))
            if args.expect_alert in seen_firing and seconds_to_firing is None:
                seconds_to_firing = round(time.monotonic() - start, 1)
                break
    if args.prom and seconds_to_firing is None:
        seen_firing.update(firing_alerts(args.prom))
        if args.expect_alert in seen_firing:
            seconds_to_firing = round(time.monotonic() - start, 1)
    server_errors = sum(n for code, n in statuses.items() if code.startswith("5"))
    problems = []
    if args.expect_alert and seconds_to_firing is None:
        problems.append(f"{args.expect_alert} was not firing before the run ended")
    if args.expect_no_alert and seen_firing:
        problems.append(f"alerts firing during a clean run: {', '.join(sorted(seen_firing))}")
    if args.expect_no_5xx and server_errors:
        codes = ", ".join(f"{c}: {n}" for c, n in sorted(statuses.items()) if c.startswith("5"))
        problems.append(f"{server_errors} responses with a 5xx status ({codes}); expected none")
    return {
        "base_url": args.base_url,
        "path": args.path,
        "rate_percent": args.rate,
        "rps": args.rps,
        "started_at": started_at,
        "elapsed_s": round(time.monotonic() - start, 1),
        "requests": sum(statuses.values()),
        "faulted_requests": sent_faults,
        "status_counts": dict(sorted(statuses.items())),
        "server_errors": server_errors,
        "alerts_seen_firing": sorted(seen_firing),
        "alert": {
            "name": args.expect_alert,
            "firing": seconds_to_firing is not None,
            "seconds_to_firing": seconds_to_firing,
        },
        "problems": problems,
        "result": "fail" if problems else "pass",
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = drill(args)
    except Unreachable as err:
        print(f"inject_5xx: unreachable, not evidence: {err}", file=sys.stderr)
        return 2
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    summary = {k: report[k] for k in ("requests", "faulted_requests", "status_counts", "alert")}
    print(f"inject_5xx: {report['result']} {json.dumps(summary)}")
    for problem in report["problems"]:
        print(f"inject_5xx: FAIL {problem}", file=sys.stderr)
    return 1 if report["problems"] else 0


if __name__ == "__main__":
    sys.exit(main())
