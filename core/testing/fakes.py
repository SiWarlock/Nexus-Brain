"""Deterministic test doubles for the determinism-seam ports (ARCHITECTURE.md §7, C-15).

The canonical `Fake*` home for the whole engine — 1.4 extends this file with the
provider / CodeGraph fakes + cassette record/replay. Each fake satisfies its port
structurally (DI-substitutable) and is fully reproducible so golden-set tests are stable.
"""

from __future__ import annotations

import hashlib
import random
from collections.abc import Iterable
from datetime import datetime, timedelta

from ports.host import HostAction, HostCapability, HostDenied, HostIntent, HostResult


class FakeClock:
    """Deterministic `Clock` — time only moves when you `advance()` it forward.

    Enforces the same contract the real `SystemClock` upholds (parse-don't-trust):
    `start` must be timezone-aware (a naive datetime is rejected), and `advance`
    is forward-only so `now()`/`monotonic()` stay non-decreasing.
    """

    def __init__(self, start: datetime) -> None:
        if start.utcoffset() is None:
            raise ValueError("FakeClock start must be timezone-aware (UTC), not naive")
        self._now = start
        self._monotonic = 0.0

    def now(self) -> datetime:
        return self._now

    def monotonic(self) -> float:
        return self._monotonic

    def advance(self, delta: timedelta) -> None:
        """Move both the wall and monotonic clocks forward by `delta` (must be >= 0)."""
        if delta < timedelta(0):
            raise ValueError("FakeClock.advance delta must be non-negative (forward-only)")
        self._now += delta
        self._monotonic += delta.total_seconds()


class FakeIdGen:
    """Deterministic `IdGen` — reproducible per-kind sequence, distinct kinds never collide.

    Ids are opaque: `kind` separates the internal counters but is not recoverable from
    the emitted token (honors the opaque-id convention).
    """

    def __init__(self) -> None:
        self._counters: dict[str, int] = {}

    def new_id(self, kind: str) -> str:
        n = self._counters.get(kind, 0)
        self._counters[kind] = n + 1
        digest = hashlib.sha256(f"{kind}\x00{n}".encode()).hexdigest()
        return f"fakeid-{digest[:24]}"


class FakeSeed:
    """Deterministic `Seed` — the same seed yields the same draw sequence."""

    def __init__(self, seed: int) -> None:
        self._seed = seed

    def rng(self) -> random.Random:
        """Return a FRESH seeded `random.Random` at position 0 (parallel to `SystemSeed`).

        Hold the returned generator and draw from it repeatedly within a context;
        each `rng()` call restarts the same sequence, so don't call `rng()` expecting
        a continuing stream.
        """
        return random.Random(self._seed)


class FakeHost:
    """Deterministic, fail-closed `HostPort` double — the safety-seam fake every track injects.

    Upholds the SAME fail-closed allowlist contract a real host must (LESSON 1 fidelity — no looser
    fake on a safety seam, Key safety rule #4): `authorize` denies any capability outside the
    configured allowlist with `HostDenied`; `perform` executes ONLY an authorized action AND
    re-validates the capability allowlist (so a forged `authorized=True` for a non-allowlisted
    capability is still denied), recording performed actions for test assertions.
    """

    def __init__(self, capabilities: Iterable[HostCapability] = ()) -> None:
        self._capabilities = frozenset(capabilities)
        self.performed: list[HostAction] = []

    def capabilities(self) -> frozenset[HostCapability]:
        return self._capabilities

    def authorize(self, intent: HostIntent) -> HostAction:
        if intent.capability not in self._capabilities:
            raise HostDenied(f"capability {intent.capability.value!r} not in host allowlist")
        return HostAction(capability=intent.capability, summary=intent.summary, authorized=True)

    def perform(self, action: HostAction) -> HostResult:
        if not action.authorized:
            raise HostDenied("perform requires an action produced by authorize (forged rejected)")
        # defense in depth: never run a non-allowlisted capability even if `authorized` is forged.
        if action.capability not in self._capabilities:
            raise HostDenied(f"capability {action.capability.value!r} not in host allowlist")
        self.performed.append(action)
        return HostResult(ok=True, detail=f"performed {action.capability.value}")
