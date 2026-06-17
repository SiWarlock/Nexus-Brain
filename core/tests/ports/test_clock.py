"""Unit tests for the Clock determinism-seam port (ARCHITECTURE.md §7, C-15)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from ports.clock import Clock, SystemClock
from testing.fakes import FakeClock

pytestmark = pytest.mark.unit


def test_system_clock_now_is_tz_aware_utc() -> None:
    # spec(§7): §5/§10 timestamps + anchor revalidation must be tz-aware UTC to serialize.
    now = SystemClock().now()
    assert now.tzinfo is not None
    assert now.utcoffset() == timedelta(0)


def test_system_clock_now_nondecreasing() -> None:
    # spec(§7): wall-clock sanity for freshness deltas.
    clock = SystemClock()
    first = clock.now()
    second = clock.now()
    assert second >= first


def test_system_clock_monotonic_nondecreasing() -> None:
    # spec(§7): wall-clock-independent duration source for backoff/timeout budgets.
    clock = SystemClock()
    first = clock.monotonic()
    second = clock.monotonic()
    assert second >= first


def test_fake_clock_returns_set_time() -> None:
    # spec(§7): C-15 determinism seam — reproducible time under test.
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    assert FakeClock(t0).now() == t0


def test_fake_clock_rejects_naive_start() -> None:
    # spec(§7): parse-don't-trust — the fake enforces the same tz-aware-UTC contract
    # the real clock upholds; a naive start must not silently mask tz bugs downstream.
    naive = datetime(2026, 1, 1)  # no tzinfo
    with pytest.raises(ValueError):
        FakeClock(naive)


def test_fake_clock_advance_rejects_negative_delta() -> None:
    # spec(§7): now()/monotonic() must stay non-decreasing — the seam never
    # synthesizes backward time.
    clock = FakeClock(datetime(2026, 1, 1, tzinfo=UTC))
    with pytest.raises(ValueError):
        clock.advance(timedelta(seconds=-1))


def test_fake_clock_advance() -> None:
    # spec(§7): controllable time for anchor-revalidation/drift tests downstream.
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    clock = FakeClock(t0)
    clock.advance(timedelta(seconds=30))
    assert clock.now() == t0 + timedelta(seconds=30)


def test_fake_clock_now_is_stable_without_advance() -> None:
    # spec(§7): time doesn't move unless advanced — repeated reads are identical
    # (the core determinism guarantee golden-set reproducibility depends on).
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    clock = FakeClock(t0)
    assert clock.now() == clock.now()


def test_clock_real_and_fake_conform() -> None:
    # spec(§7): one port, real adapter + named fake double, DI-substitutable.
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    assert isinstance(SystemClock(), Clock)
    assert isinstance(FakeClock(t0), Clock)
