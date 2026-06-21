"""The ObservabilitySink port — instrumented-but-silent telemetry (ARCHITECTURE.md §7, §19).

Behavioral port (LESSON 1). The real OTel sink is OFF-BY-DEFAULT + LOCAL-ONLY and NEVER phones home
(Key safety rule #6 / D-22) — Phase-2. This slice freezes the interface + the frozen `ObsEvent` +
`FakeObservabilitySink` (records locally, never network).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict

from _types import IdentityStr


class ObsEvent(BaseModel):
    """An observability event — frozen. `{name, attributes}` where attributes is a tuple of
    `(key, value)` pairs (LESSON 8 tuple collection). The KEY is a strip+non-empty identity
    (LESSON 7); the VALUE is a plain str (an OTel attribute value may legitimately be empty). The
    OTel span/metric/log mapping is the Phase-2 real-sink concern.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: IdentityStr
    attributes: tuple[tuple[IdentityStr, str], ...]


@runtime_checkable
class ObservabilitySink(Protocol):
    """A telemetry sink (§7) — `emit` is instrumented-but-silent."""

    def emit(self, event: ObsEvent) -> None:
        """Emit an observability event (off-by-default + local-only in the real sink)."""
        ...
