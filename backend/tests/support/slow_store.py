"""A slow object store for tests (CI-IT0213-HANG): a TCP proxy in front of the real S3 endpoint
that lets the bytes sent TO the store through at a fixed rate.

Scheduled CI run 37764445816 (job 113268514073) timed out in IT-02-13 while its arrange step
uploaded videos: the store's log shows each 0.86 MB write taking 13.3 s and each 1.72 MB part
26.7 s, about 64 KiB/s, while reads and small writes stayed fast. ``slow_object_store`` makes
that condition repeatable on a local stack, so a test can prove it does not depend on the
store's write throughput. Responses from the store are not slowed.
"""

from __future__ import annotations

import contextlib
import socket
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from urllib.parse import urlsplit, urlunsplit

CI_WRITE_RATE = 64 * 1024  # bytes per second, measured in run 37764445816 (see the docstring)
_BUFFER = 16 * 1024


class Throttle:
    """Paces a byte stream to ``rate`` bytes per second. Pure: the caller passes the clock."""

    def __init__(self, rate: int, now: float) -> None:
        if rate <= 0:
            raise ValueError("rate must be positive")
        self.rate = rate
        self._start = now
        self._sent = 0

    def delay_after(self, size: int, now: float) -> float:
        """Count ``size`` bytes as sent; the seconds to wait before sending more."""
        self._sent += size
        return max(0.0, self._start + self._sent / self.rate - now)


def _pump(source: socket.socket, sink: socket.socket, pace: Callable[[int], None] | None) -> None:
    try:
        while chunk := source.recv(_BUFFER):
            if pace is not None:
                pace(len(chunk))  # before sending: the last byte leaves at size / rate
            sink.sendall(chunk)
    except OSError:
        pass
    finally:
        for sock in (source, sink):
            with contextlib.suppress(OSError):
                sock.shutdown(socket.SHUT_RDWR)


class ThrottlingProxy:
    """Listens on 127.0.0.1 (a free port) and forwards each connection to ``upstream``
    (``host:port``); client-to-store bytes are paced to ``rate`` per connection."""

    def __init__(self, upstream: tuple[str, int], rate: int) -> None:
        self.upstream, self.rate = upstream, rate
        self._listener = socket.create_server(("127.0.0.1", 0))
        self.port = self._listener.getsockname()[1]
        self._open: list[socket.socket] = []
        self._thread = threading.Thread(target=self._accept, daemon=True)
        self._thread.start()

    def _accept(self) -> None:
        while True:
            try:
                client, _ = self._listener.accept()
            except OSError:
                return
            store = socket.create_connection(self.upstream, timeout=5)
            store.settimeout(None)
            self._open += [client, store]
            throttle = Throttle(self.rate, time.monotonic())

            def pace(size: int, throttle: Throttle = throttle) -> None:
                time.sleep(throttle.delay_after(size, time.monotonic()))

            threading.Thread(target=_pump, args=(client, store, pace), daemon=True).start()
            threading.Thread(target=_pump, args=(store, client, None), daemon=True).start()

    def close(self) -> None:
        self._listener.close()
        for sock in self._open:
            with contextlib.suppress(OSError):
                sock.close()


@contextmanager
def slow_object_store(endpoint_url: str, rate: int = CI_WRITE_RATE) -> Iterator[str]:
    """Yields an endpoint URL that reaches ``endpoint_url`` through a ``ThrottlingProxy``."""
    parts = urlsplit(endpoint_url)
    host, port = parts.hostname or "127.0.0.1", parts.port or 80
    proxy = ThrottlingProxy((host, port), rate)
    try:
        yield urlunsplit((parts.scheme, f"127.0.0.1:{proxy.port}", parts.path, "", ""))
    finally:
        proxy.close()
