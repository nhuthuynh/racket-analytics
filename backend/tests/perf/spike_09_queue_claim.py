"""SPIKE-09: claim throughput and lock contention of the Postgres job queue (ST-007; ADR 0008 B).

Not a pytest module (no ``test_`` prefix): a measurement script run by hand against a real
Postgres, never SQLite. It drives the production code path (``JobQueue.claim`` + commit, then
``lock_running`` + ``complete`` + commit, exactly as ``racket.worker.runner`` does), with
N worker processes over M pre-enqueued jobs, and reports:

* throughput (jobs/s) and claim latency percentiles;
* jobs per worker, empty claims while work remained (SKIP LOCKED skips), lock waits sampled
  from ``pg_stat_activity``;
* correctness: every job done exactly once, attempts == 1, no job left behind.

    cd backend && eval "$(../scripts/dev-postgres.sh start)" && \
      uv run python -m tests.perf.spike_09_queue_claim --workers 4 --jobs 1000 [--work-ms 5]
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import statistics
import threading
import time
import uuid
from datetime import timedelta
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Session

from racket.analysis_jobs.domain import JobKey
from racket.analysis_jobs.queue import JobQueue, jobs
from racket.platform.db import engine_for, session_factory, upgrade_to_head

STAGE = "spike09"


def _worker(url: str, worker_id: str, work_ms: float, start: Any, out: Any) -> None:
    engine = engine_for(url)
    factory = session_factory(engine)
    lease = timedelta(seconds=30)
    latencies: list[float] = []
    empty_while_remaining = 0
    done = 0
    start.wait()
    t0 = time.perf_counter()
    while True:
        c0 = time.perf_counter()
        with factory() as session:
            job = JobQueue(session, lease).claim(worker_id, stages=(STAGE,))
            if job is None:
                session.rollback()
                remaining = session.execute(
                    sa.select(sa.func.count())
                    .select_from(jobs)
                    .where(jobs.c.stage == STAGE, jobs.c.status == "queued")
                ).scalar_one()
                if remaining:
                    empty_while_remaining += 1
                    continue
                break
            job_id = job.id
            session.commit()
        latencies.append(time.perf_counter() - c0)
        if work_ms:
            time.sleep(work_ms / 1000)
        with factory() as session:
            running = JobQueue(session, lease).lock_running(job_id, worker_id)
            assert running is not None, "lost a job"
            running.complete()
            session.commit()
        done += 1
    out.put(
        {
            "worker": worker_id,
            "done": done,
            "elapsed_s": time.perf_counter() - t0,
            "latencies": latencies,
            "empty_while_remaining": empty_while_remaining,
        }
    )
    engine.dispose()


def _sample_lock_waits(
    url: str, stop: threading.Event, samples: list[int], events: dict[str, int]
) -> None:
    engine = sa.create_engine(engine_for(url).url)
    with engine.connect() as conn:
        while not stop.is_set():
            waiting = (
                conn.execute(
                    sa.text(
                        "SELECT wait_event FROM pg_stat_activity "
                        "WHERE wait_event_type = 'Lock' AND datname = current_database()"
                    )
                )
                .scalars()
                .all()
            )
            samples.append(len(waiting))
            for event in waiting:
                events[str(event)] = events.get(str(event), 0) + 1
            conn.commit()
            time.sleep(0.005)
    engine.dispose()


def run(url: str, workers: int, n_jobs: int, work_ms: float) -> dict[str, Any]:
    upgrade_to_head(url)
    engine = engine_for(url)
    with engine.begin() as conn:
        conn.execute(sa.delete(jobs).where(jobs.c.stage == STAGE))
    with Session(engine) as session:
        queue = JobQueue(session)
        for _ in range(n_jobs):
            queue.enqueue(JobKey(match_id=uuid.uuid4(), pipeline_version="spike", stage=STAGE), {})
        session.commit()
    engine.dispose()

    ctx = mp.get_context("spawn")
    start, out = ctx.Event(), ctx.Queue()
    procs = [
        ctx.Process(target=_worker, args=(url, f"bench-{i}", work_ms, start, out))
        for i in range(workers)
    ]
    for p in procs:
        p.start()
    time.sleep(1.0)  # let every process import and connect before the clock starts
    stop = threading.Event()
    lock_samples: list[int] = []
    lock_events: dict[str, int] = {}
    sampler = threading.Thread(
        target=_sample_lock_waits, args=(url, stop, lock_samples, lock_events)
    )
    sampler.start()
    t0 = time.perf_counter()
    start.set()
    results = [out.get(timeout=600) for _ in procs]
    wall = time.perf_counter() - t0
    for p in procs:
        p.join(timeout=30)
    stop.set()
    sampler.join()

    engine = engine_for(url)
    with engine.connect() as conn:
        rows = conn.execute(
            sa.select(jobs.c.status, jobs.c.attempts, sa.func.count())
            .where(jobs.c.stage == STAGE)
            .group_by(jobs.c.status, jobs.c.attempts)
        ).all()
        server = conn.execute(sa.text("SHOW server_version")).scalar_one()
    with engine.begin() as conn:
        conn.execute(sa.delete(jobs).where(jobs.c.stage == STAGE))

    latencies: list[float] = sorted(x for r in results for x in r["latencies"])

    def pct(q: float) -> float:
        return float(round(latencies[min(len(latencies) - 1, int(q * len(latencies)))] * 1000, 2))

    return {
        "postgres": server,
        "workers": workers,
        "jobs": n_jobs,
        "work_ms": work_ms,
        "wall_s": round(wall, 3),
        "throughput_jobs_per_s": round(n_jobs / wall, 1),
        "claim_ms": {
            "p50": pct(0.50),
            "p95": pct(0.95),
            "p99": pct(0.99),
            "max": round(latencies[-1] * 1000, 2),
            "mean": round(statistics.fmean(latencies) * 1000, 2),
        },
        "jobs_per_worker": {r["worker"]: r["done"] for r in results},
        "empty_claims_while_work_remained": sum(r["empty_while_remaining"] for r in results),
        "lock_wait_samples": {
            "n": len(lock_samples),
            "max_waiting": max(lock_samples or [0]),
            "nonzero": sum(1 for n in lock_samples if n > 0),
            "by_wait_event": lock_events,
        },
        "final_states": [list(map(str, r)) for r in rows],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--jobs", type=int, default=1000)
    parser.add_argument("--work-ms", type=float, default=0.0)
    args = parser.parse_args()
    url = os.environ["DATABASE_URL"]
    print(json.dumps(run(url, args.workers, args.jobs, args.work_ms), indent=2))


if __name__ == "__main__":
    main()
