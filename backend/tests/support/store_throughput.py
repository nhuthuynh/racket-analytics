"""Write throughput of the test object store (CI-OBJSTORE-SLOW).

CI runs 37764445816 and 37961668800: minutes into the integration job, the store took the
1.72 MB clip at about 64 KiB/s and upload tests timed out. ``measure`` writes a payload the way
``UploadService.write_chunk`` stores a two-PATCH clip (the first half staged with PutObject, then
the whole clip as multipart part 1, then complete) from parallel writers, and ``verdict`` says
whether the store is fast enough for the suites. Keys are under ``test-own/`` and removed.
"""

from __future__ import annotations

import statistics
import time
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from racket.platform.storage import ObjectStore

MB = 1_000_000
FLOOR_MEDIAN = 5 * MB  # bytes/s: the ticket's floor for the clip, on the median write
FLOOR_SLOWEST = 1 * MB  # bytes/s: no single write may stall (the CI stall was 65,536 B/s)


@dataclass(frozen=True)
class Throughput:
    rates: tuple[float, ...]  # bytes per second, one per clip write

    @property
    def median(self) -> float:
        return statistics.median(self.rates)

    @property
    def slowest(self) -> float:
        return min(self.rates)


def verdict(result: Throughput) -> str | None:
    """None when the store is fast enough; otherwise why it is not, in MB/s."""
    if not result.rates:
        return "no write was measured"
    problems = []
    if result.median < FLOOR_MEDIAN:
        problems.append(f"median {result.median / MB:.2f} MB/s < {FLOOR_MEDIAN / MB:g} MB/s")
    if result.slowest < FLOOR_SLOWEST:
        problems.append(f"slowest {result.slowest / MB:.3f} MB/s < {FLOOR_SLOWEST / MB:g} MB/s")
    if not problems:
        return None
    return f"object store too slow for the clip ({len(result.rates)} writes): " + "; ".join(
        problems
    )


def _write_once(store: ObjectStore, data: bytes) -> float:
    key = f"test-own/objstore-throughput/{uuid.uuid4().hex}"
    stage = key + ".stage"
    started = time.perf_counter()
    store.put_bytes(stage, data[: len(data) // 2])
    upload_id = store.create_multipart(key)
    etag = store.upload_part(key, upload_id, 1, data)
    store.complete_multipart(key, upload_id, [(1, etag)])
    elapsed = time.perf_counter() - started
    store.delete(key)
    store.delete(stage)
    return (len(data) + len(data) // 2) / elapsed


def measure(
    make_store: Callable[[], ObjectStore], data: bytes, *, writers: int, rounds: int
) -> Throughput:
    """``writers`` threads, each with its own client, write ``data`` ``rounds`` times."""

    def writer(_: int) -> list[float]:
        store = make_store()
        return [_write_once(store, data) for _ in range(rounds)]

    with ThreadPoolExecutor(max_workers=writers) as pool:
        per_writer = list(pool.map(writer, range(writers)))
    return Throughput(tuple(rate for rates in per_writer for rate in rates))
