"""The EventSource port — the change/notification feed (ARCHITECTURE.md §7).

Behavioral port (LESSON 1): a `@runtime_checkable Protocol` + a faithful deterministic Fake. The
real adapters (the git-hook/watcher feed → Phase-2 sync; the NexusOps-outbox variant → P2) land
where consumed. This slice freezes the interface + the frozen `Event` type + `FakeEventSource`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict

from _types import IdentityStr


class Event(BaseModel):
    """A change/notification event — frozen. Minimal `{kind, source}`; payload deferred."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: IdentityStr  # the event type (e.g. file_changed)
    source: IdentityStr  # the origin (e.g. git_hook / watcher)


@runtime_checkable
class EventSource(Protocol):
    """A feed of `Event`s (§7) — pull (`poll`) + push (`subscribe`)."""

    def poll(self) -> tuple[Event, ...]:
        """Drain and return the events available since the last poll (empty → `()`)."""
        ...

    def subscribe(self, handler: Callable[[Event], None]) -> None:
        """Register a push handler invoked for each event. No unsubscribe handle — the lifecycle
        (deregister / context manager) is a Phase-2 real-adapter concern, not the frozen seam."""
        ...
