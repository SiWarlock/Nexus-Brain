"""The `IdGen` + `Seed` determinism-seam ports + real adapters (ARCHITECTURE.md §7, C-15).

`IdGen` mints unique ids; `Seed` yields seeded RNGs. Both are deterministic test seams
frozen in Phase 1: id minting and any sampling/jitter go through these ports — never via
`uuid.uuid4()` / `random.*` inline. Inject `UuidGen` / `SystemSeed` in production;
inject `testing.fakes.FakeIdGen` / `FakeSeed` under test.

Minted ids are OPAQUE: `kind` is a minting hint, never recoverable from the id. Typed
model fields carry kind; no consumer parses it back out of an id string.
"""

from __future__ import annotations

import random
import uuid
from typing import Protocol, runtime_checkable


@runtime_checkable
class IdGen(Protocol):
    """Mints unique, opaque string ids. Real + fake are DI-substitutable (§7)."""

    def new_id(self, kind: str) -> str:
        """Mint a unique id. `kind` is a minting hint, not encoded into the id."""
        ...


@runtime_checkable
class Seed(Protocol):
    """Yields a seeded `random.Random`. Real + fake are DI-substitutable (§7)."""

    def rng(self) -> random.Random:
        """Return a `random.Random` instance to draw from."""
        ...


class UuidGen:
    """Real `IdGen` — globally unique ids via `uuid4` (kind is an opaque hint)."""

    def new_id(self, kind: str) -> str:
        # `kind` is an opaque minting hint only; uuid4 uniqueness is kind-agnostic.
        return str(uuid.uuid4())


class SystemSeed:
    """Real `Seed` — an OS-entropy-seeded RNG (non-deterministic by design)."""

    def rng(self) -> random.Random:
        return random.Random()
