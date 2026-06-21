"""Unit tests for the ObservabilitySink port (ARCHITECTURE.md §7, §19 never-phone-home).

★ Freeze-before-fork behavioral port. The real OTel sink is off-by-default + local-only and never
phones home (Phase-2, D-22); this slice freezes the interface + ObsEvent + the recording Fake.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from ports.observability import ObservabilitySink, ObsEvent
from testing.fakes import FakeObservabilitySink

pytestmark = pytest.mark.unit


def test_obssink_conformance() -> None:
    # LESSON 1: the Fake structurally satisfies the port (runtime_checkable).
    assert isinstance(FakeObservabilitySink(), ObservabilitySink)


def test_obssink_emit() -> None:
    # §7: emit(event) -> None; the Fake records it locally (assertable), never touches the network.
    sink = FakeObservabilitySink()
    ev = ObsEvent(name="ingest.chunk", attributes=(("project", "nexus"),))
    sink.emit(ev)  # -> None (instrumented-but-silent); records locally for the assertion below
    assert sink.emitted == [ev]


def test_obsevent_snapshot() -> None:
    # spec(§7): §2.5-seam ★ freeze — ObsEvent shape; attributes is a tuple (LESSON 8); frozen.
    # extra-forbid + empty attrs allowed; LESSON 7 strip on name.
    assert set(ObsEvent.model_fields) == {"name", "attributes"}
    ev = ObsEvent(name="n", attributes=(("k", "v"),))
    assert isinstance(ev.attributes, tuple)
    bad: dict[str, Any] = {"name": "n", "attributes": (), "extra": 1}
    with pytest.raises(ValidationError):
        ObsEvent(**bad)
    with pytest.raises(ValidationError):
        ev.name = "z"
    assert ObsEvent(name="n", attributes=()).attributes == ()
    for badval in ("", "   "):
        with pytest.raises(ValidationError):
            ObsEvent(name=badval, attributes=())
    assert ObsEvent(name="  n  ", attributes=()).name == "n"
    # LESSON 7: the attribute KEY is a strip+non-empty identity; the VALUE may be empty.
    for bad_key in ("", "  "):
        with pytest.raises(ValidationError):
            ObsEvent(name="n", attributes=((bad_key, "v"),))
    assert ObsEvent(name="n", attributes=(("  k  ", ""),)).attributes == (("k", ""),)
