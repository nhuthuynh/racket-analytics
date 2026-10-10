"""CI-OBJSTORE-STALL: how many loopback segments a TCP receive buffer holds.

Inside the object store's container the filer sends each chunk to its volume server over the
loopback device (MTU 65536, MSS 65483 bytes). A default receive buffer of 128 KiB (the CI runner
kernel's ``net.ipv4.tcp_rmem``) holds two such segments; on the runner the queue is then pruned,
segments are dropped and the connection crawls on retransmission timeouts and zero-window
probes (runs 38059526467, 38062207301, 38064153385). The store's namespace gets a buffer of at
least ``MIN_SEGMENTS`` loopback segments."""

from __future__ import annotations

LOOPBACK_MSS = 65_483  # bytes: loopback MTU 65536 - 40 (IPv4 + TCP) - 12 (timestamps option)
MIN_SEGMENTS = 16


def default_rmem(tcp_rmem: str) -> int:
    """The default (middle) value of a ``net.ipv4.tcp_rmem`` triple "min default max"."""
    parts = tcp_rmem.split()
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        raise ValueError(f"tcp_rmem is 'min default max' in bytes, got {tcp_rmem!r}")
    low, default, high = (int(p) for p in parts)
    if not low <= default <= high:
        raise ValueError(f"tcp_rmem needs min <= default <= max, got {tcp_rmem!r}")
    return default


def loopback_segments(rmem: int) -> int:
    """Whole loopback segments a receive buffer of ``rmem`` bytes holds."""
    return rmem // LOOPBACK_MSS
