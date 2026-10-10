"""CI-OBJSTORE-STALL experiment (temporary; removed before merge): the 4x3 throughput-floor
write shape with per-request timings and the client's local port, one JSON row per write.

    python objstore_stall_probe.py LABEL ENDPOINT   (S3_* credentials from the environment)
"""

from __future__ import annotations

import dataclasses
import json
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

from racket.platform.storage import ObjectStore, S3Config
from tests.support.paths import SYNTHETIC_CLIP

DATA = SYNTHETIC_CLIP.read_bytes()
WRITERS, ROUNDS = 4, 3


def _port(store: ObjectStore) -> int | None:
    for p in store._client._endpoint.http_session._manager.pools._container.values():  # noqa: SLF001
        conns = list(p.pool.queue) if p.pool is not None else []
        for c in conns:
            if c is not None and c.sock is not None:
                return int(c.sock.getsockname()[1])
    return None


def writer(label: str, endpoint: str, w: int) -> list[dict[str, object]]:
    store = ObjectStore(dataclasses.replace(S3Config.from_env(), endpoint_url=endpoint))
    rows = []
    for r in range(ROUNDS):
        key = f"test-own/objstore-stall/{uuid.uuid4().hex}"
        t = [time.time()]
        store.put_bytes(key + ".stage", DATA[: len(DATA) // 2])
        t.append(time.time())
        upload = store.create_multipart(key)
        t.append(time.time())
        etag = store.upload_part(key, upload, 1, DATA)
        t.append(time.time())
        store.complete_multipart(key, upload, [(1, etag)])
        t.append(time.time())
        store.delete(key)
        store.delete(key + ".stage")
        total = t[-1] - t[0]
        rows.append(
            {
                "label": label,
                "w": w,
                "r": r,
                "start": round(t[0], 3),
                "end": round(t[-1], 3),
                "total": round(total, 3),
                "steps": [round(b - a, 3) for a, b in zip(t, t[1:], strict=False)],
                "mbps": round((len(DATA) + len(DATA) // 2) / total / 1e6, 3),
                "lport": _safe_port(store),
            }
        )
    return rows


def _safe_port(store: ObjectStore) -> int | None:
    try:
        return _port(store)
    except Exception:  # diagnostics only
        return None


def main() -> None:
    label, endpoint = sys.argv[1], sys.argv[2]
    with ThreadPoolExecutor(WRITERS) as pool:
        for rows in pool.map(lambda w: writer(label, endpoint, w), range(WRITERS)):
            for row in rows:
                print(json.dumps(row), flush=True)


if __name__ == "__main__":
    main()
