#!/usr/bin/env python3
"""Measure the private footage bucket (sprint-DoD row S3-DoD-P11; BLK-GOLD-01; PO P12 option b).

    footage_bucket.py --po docs/requirements/po-input-2026-10-05.md [--dod docs/sprints/sprint-03.md]
        [--endpoint URL --bucket NAME]      # live probe; credentials from S3_ACCESS_KEY_ID/SECRET
        [--from-probe probe.json]           # recorded {"exists": bool, "anonymous_status": n}

The row is met only when (1) the PO decision record has a P11 table row naming the provider
("Provider: <name>") and (2) the footage bucket exists (authenticated HEAD) and refuses an
anonymous read (HTTP 401/403). An anonymous 403 alone proves nothing: S3 stores answer 403 for
a missing bucket too. Without a provider the status is "not met: waiting on P11".

Exit 0 met, 1 not met, 2 malformed input or an unexpected answer (fail closed, ADR 0014), 3 the
sprint plan's S3-DoD-P11 status says something other than the measurement.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

DOD_ROW = "S3-DoD-P11"
PROVIDER = re.compile(r"\bprovider\s*:\s*([^.;]*[^\s.;])", re.I)
REFUSED = (401, 403)


def _rows(text: str):
    for line in text.splitlines():
        if line.lstrip().startswith("|"):
            yield [" ".join(c.replace("**", "").split()) for c in line.strip().strip("|").split("|")]


def po_provider(record: str) -> str | None:
    """The provider a P11 decision-table row names ("Provider: <name>"), else None."""
    for cells in _rows(record):
        if re.match(r"P11\b", cells[0]) and len(cells) > 1:
            found = PROVIDER.search(cells[1])
            if found:
                return found.group(1).strip()
    return None


def bucket_state(exists: bool, anonymous_status: int) -> str:
    """'absent', 'public' or 'private' from a probe; ValueError for any other anonymous answer."""
    if anonymous_status not in (200, *REFUSED):
        raise ValueError(f"anonymous read answered HTTP {anonymous_status}, not 200/401/403")
    if not exists:
        return "absent"
    return "public" if anonymous_status == 200 else "private"


def status_text(provider: str | None, state: str | None) -> str:
    """The S3-DoD-P11 status in the plan's words."""
    if provider is None:
        return "not met: waiting on P11"
    if state == "public":
        return "not met: footage bucket is readable without credentials"
    if state == "private":
        return f"met (provider: {provider}; anonymous read refused)"
    return "not met: P11 answered, footage bucket not built (C3-08)"


def measure(provider: str | None, state: str | None) -> dict:
    """The S3-DoD-P11 result for the PO's provider and the probed bucket state (None: no probe)."""
    status = status_text(provider, state)
    return {"provider": provider, "bucket": state, "met": status.startswith("met"), "status": status}


def dod_status(plan: str) -> str:
    """The last cell of the plan's S3-DoD-P11 row, without Markdown emphasis."""
    for cells in _rows(plan):
        if cells[0] == DOD_ROW:
            return cells[-1]
    raise ValueError(f"the sprint plan has no {DOD_ROW} row")


def dod_verdict(status: str) -> str:
    """'met' or 'not met: ...': the status without its parenthesised note."""
    return status.split("(", 1)[0].strip()


def probe(endpoint: str, bucket: str) -> tuple[bool, int]:
    """Live probe: authenticated HEAD for existence, then an anonymous GET of the bucket."""
    import boto3  # noqa: PLC0415 (only the live probe needs it)
    from botocore.client import Config  # noqa: PLC0415
    from botocore.exceptions import ClientError  # noqa: PLC0415

    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=os.environ["S3_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["S3_SECRET_ACCESS_KEY"],
        region_name=os.environ.get("S3_REGION", "us-east-1"),
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )
    try:
        s3.head_bucket(Bucket=bucket)
        exists = True
    except ClientError as exc:
        code = exc.response["ResponseMetadata"]["HTTPStatusCode"]
        if code != 404:
            raise ValueError(f"authenticated HEAD of {bucket!r} answered HTTP {code}") from exc
        exists = False
    url = f"{endpoint.rstrip('/')}/{bucket}"
    if not url.startswith(("http://", "https://")):
        raise ValueError(f"endpoint {endpoint!r} is not http(s)")
    try:
        with urllib.request.urlopen(url, timeout=30) as response:  # noqa: S310 (scheme checked)
            return exists, response.status
    except urllib.error.HTTPError as exc:
        return exists, exc.code


def recorded(path: Path) -> tuple[bool, int]:
    """A recorded probe {"exists": bool, "anonymous_status": n}, so tests need no store."""
    answer = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(answer.get("exists"), bool):
        raise ValueError(f"{path}: 'exists' must be true or false")
    return answer["exists"], int(answer["anonymous_status"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--po", type=Path, required=True, help="the PO decision record")
    parser.add_argument("--dod", type=Path, help="sprint plan whose S3-DoD-P11 row must agree")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--endpoint", help="S3 endpoint URL for the live probe (needs --bucket)")
    source.add_argument("--from-probe", type=Path, help="recorded probe JSON")
    parser.add_argument("--bucket", help="the footage bucket's name")
    args = parser.parse_args(argv)
    if args.endpoint and not args.bucket:
        parser.error("--endpoint needs --bucket")
    try:
        seen = None
        if args.endpoint:
            seen = probe(args.endpoint, args.bucket)
        elif args.from_probe:
            seen = recorded(args.from_probe)
        state = bucket_state(*seen) if seen else None
        result = measure(po_provider(args.po.read_text(encoding="utf-8")), state)
        result["anonymous_status"] = seen[1] if seen else None
        claimed = dod_status(args.dod.read_text(encoding="utf-8")) if args.dod else None
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"footage_bucket: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    if claimed is not None and dod_verdict(claimed) != dod_verdict(result["status"]):
        print(
            f"footage_bucket: {DOD_ROW} says {claimed!r} but the PO record and the bucket say "
            f"{result['status']!r}",
            file=sys.stderr,
        )
        return 3
    return 0 if result["met"] else 1


if __name__ == "__main__":
    sys.exit(main())
