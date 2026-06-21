"""Unit tests for the EventSource port (ARCHITECTURE.md §7).

★ Freeze-before-fork behavioral port (LESSON 1): Protocol + deterministic Fake. Real adapters
(git-hook/watcher feed → Phase-2 sync; NexusOps-outbox → P2) land where consumed.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from ports.events import Event, EventSource
from testing.fakes import FakeEventSource

pytestmark = pytest.mark.unit


def _event(kind: str = "file_changed", source: str = "git_hook") -> Event:
    return Event(kind=kind, source=source)


def test_eventsource_conformance() -> None:
    # LESSON 1: the Fake structurally satisfies the port (runtime_checkable).
    assert isinstance(FakeEventSource(), EventSource)


def test_eventsource_poll() -> None:
    # §7: poll() drains the canned queue → tuple[Event, ...]; empty → ().
    assert FakeEventSource().poll() == ()
    e1, e2 = _event(kind="a"), _event(kind="b")
    src = FakeEventSource(events=(e1, e2))
    assert src.poll() == (e1, e2)
    assert src.poll() == ()  # drained


def test_eventsource_subscribe() -> None:
    # §7 (Q1: both poll + subscribe): subscribe fans the canned events to the handler.
    received: list[Event] = []
    FakeEventSource(events=(_event(kind="x"),)).subscribe(received.append)
    assert [e.kind for e in received] == ["x"]
    # empty source → zero handler invocations.
    empty: list[Event] = []
    FakeEventSource().subscribe(empty.append)
    assert empty == []


def test_event_snapshot() -> None:
    # spec(§7): §2.5-seam ★ freeze — Event shape; frozen + extra-forbid; LESSON 7 strip identity.
    assert set(Event.model_fields) == {"kind", "source"}
    bad: dict[str, Any] = {"kind": "a", "source": "b", "extra": 1}
    with pytest.raises(ValidationError):
        Event(**bad)
    e = _event()
    with pytest.raises(ValidationError):
        e.kind = "z"
    for badval in ("", "   "):
        with pytest.raises(ValidationError):
            Event(kind=badval, source="git")
    assert Event(kind="  k  ", source="s").kind == "k"


def test_fake_eventsource_deterministic() -> None:
    # LESSON 1: same canned config → same poll sequence (fresh instances).
    e = _event(kind="c")
    assert FakeEventSource(events=(e,)).poll() == FakeEventSource(events=(e,)).poll()
