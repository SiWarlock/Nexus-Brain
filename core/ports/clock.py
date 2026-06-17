"""The `Clock` determinism-seam port + its real adapter (ARCHITECTURE.md §7, C-15).

`Clock` is one of the two deterministic test seams frozen in Phase 1. Time is read
through this port everywhere (manifest timestamps, anchor revalidation, freshness
deltas, backoff budgets) — never via `datetime.now()` / `time.monotonic()` inline.
Inject `SystemClock` in production; inject `testing.fakes.FakeClock` under test.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Protocol, runtime_checkable


@runtime_checkable
class Clock(Protocol):
    """A source of time. Real + fake adapters are DI-substitutable (§7)."""

    def now(self) -> datetime:
        """Return the current instant as a timezone-aware UTC `datetime`."""
        ...

    def monotonic(self) -> float:
        """Return non-decreasing seconds from an arbitrary epoch (duration source)."""
        ...


class SystemClock:
    """Real `Clock` — the OS wall clock (UTC) and monotonic clock."""

    def now(self) -> datetime:
        return datetime.now(UTC)

    def monotonic(self) -> float:
        return time.monotonic()
