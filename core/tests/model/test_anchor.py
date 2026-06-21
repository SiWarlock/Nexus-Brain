"""Unit tests for the frozen Anchor trust contract (ARCHITECTURE.md §10, Appendix A).

★ Freeze-before-fork contract (§10 north-star). The Anchor is the typed file:line[-range]
edge from a prose/answer span to a code target, carrying its revalidation `state`,
`last_resolved_sha`, and `confidence`. The 11-field set + the 5-value `AnchorState` alphabet
are pinned by spec(§10) snapshots; drift is a cross-track Finding.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from pydantic import ValidationError

from model.anchor import Anchor, AnchorState

pytestmark = pytest.mark.unit

# The checked-in frozen field set (the snapshot). 11 fields — Appendix-A line 216.
EXPECTED_ANCHOR_FIELDS = frozenset(
    {
        "anchor_id",
        "project_id",
        "source_file",
        "source_span",
        "target_path",
        "target_line_start",
        "target_line_end",
        "target_symbol",
        "state",
        "last_resolved_sha",
        "confidence",
    }
)

# The 6 REQUIRED strip+min_length identity/path string fields (target_symbol is optional —
# covered separately in test_anchor_target_symbol_optional).
REQUIRED_STRIP_FIELDS = (
    "anchor_id",
    "project_id",
    "source_file",
    "source_span",
    "target_path",
    "last_resolved_sha",
)


def _valid_kwargs() -> dict[str, Any]:
    # Any: heterogeneous kwargs unpacked into the typed Anchor(...); negative tests deliberately
    # omit/override fields, so a precise TypedDict would fight the cases.
    """A fully-specified valid anchor payload (literals; ids caller-injected upstream)."""
    return {
        "anchor_id": "anc_01h9z",
        "project_id": "proj_nexus",
        "source_file": "docs/answers/q42.md",
        "source_span": "12-18",
        "target_path": "core/model/anchor.py",
        "target_line_start": 20,
        "target_line_end": 35,
        "target_symbol": "Anchor",
        "state": AnchorState.LIVE,
        "last_resolved_sha": "sha256:deadbeefcafe",
        "confidence": 0.95,
    }


def test_anchor_schema_snapshot() -> None:
    # spec(§10): §2.5-seam ★ freeze pin — drift on this contract is a cross-track Finding.
    assert set(Anchor.model_fields) == EXPECTED_ANCHOR_FIELDS


def test_anchor_state_values() -> None:
    # spec(§10): the state alphabet is itself a frozen contract (Appendix-A line 216); `deleted`
    # is record-lifecycle removal, NOT a `state` value, so it is absent here.
    assert {s.value for s in AnchorState} == {"live", "stale", "moved", "unknown", "orphaned"}


def test_anchor_rejects_invalid_state() -> None:
    # spec(§10): the grounding gate keys on `state == live`; an unrecognized/legacy state from a
    # deserialized on-disk or MCP anchor must be rejected at the boundary (§4 parse-don't-trust),
    # never silently admitted. `deleted` is record-lifecycle, NOT an accepted state (Q1).
    bogus = _valid_kwargs()
    bogus["state"] = "bogus"
    with pytest.raises(ValidationError):
        Anchor(**bogus)

    # the on-disk / MCP-egress deserialization path (JSON) must reject a non-member too.
    payload = Anchor(**_valid_kwargs()).model_dump(mode="json")
    payload["state"] = "deleted"
    with pytest.raises(ValidationError):
        Anchor.model_validate_json(json.dumps(payload))


def test_anchor_valid_construction() -> None:
    # spec(§10): the happy-path contract shape round-reads its fields.
    a = Anchor(**_valid_kwargs())
    assert a.anchor_id == "anc_01h9z"
    assert a.project_id == "proj_nexus"
    assert a.source_file == "docs/answers/q42.md"
    assert a.source_span == "12-18"
    assert a.target_path == "core/model/anchor.py"
    assert a.target_line_start == 20
    assert a.target_line_end == 35
    assert a.target_symbol == "Anchor"
    assert a.state is AnchorState.LIVE
    assert a.last_resolved_sha == "sha256:deadbeefcafe"
    assert a.confidence == 0.95


def test_anchor_rejects_extra_field() -> None:
    # spec(§10): §4 parse-don't-trust — an unknown kwarg raises (extra="forbid").
    kwargs = _valid_kwargs()
    kwargs["completely_unknown"] = "x"
    with pytest.raises(ValidationError):
        Anchor(**kwargs)


def test_anchor_all_required() -> None:
    # spec(§10): every field except the optional target_symbol is required (LESSONS §3 guard).
    for name in EXPECTED_ANCHOR_FIELDS - {"target_symbol"}:
        kwargs = _valid_kwargs()
        del kwargs[name]
        with pytest.raises(ValidationError):
            Anchor(**kwargs)


def test_anchor_rejects_empty_identity_strings() -> None:
    # spec(§10): before-fork whitespace sweep — a whitespace-loose identity in a frozen
    # cross-track contract is a Finding; "" and whitespace-only are rejected (min_length=1).
    for field in REQUIRED_STRIP_FIELDS:
        for bad in ("", "   "):
            kwargs = _valid_kwargs()
            kwargs[field] = bad
            with pytest.raises(ValidationError):
                Anchor(**kwargs)


def test_anchor_strips_surrounding_whitespace() -> None:
    # spec(§10): StringConstraints(strip_whitespace=True) behavior pin — surrounding ws stripped.
    kwargs = _valid_kwargs()
    kwargs["anchor_id"] = "  anc_01h9z  "
    kwargs["target_path"] = "\tcore/model/anchor.py\n"
    a = Anchor(**kwargs)
    assert a.anchor_id == "anc_01h9z"
    assert a.target_path == "core/model/anchor.py"


def test_anchor_span_ordering() -> None:
    # spec(§10): a backwards span is never valid; single-line ⇒ start == end is valid.
    kwargs = _valid_kwargs()
    kwargs["target_line_start"] = 35
    kwargs["target_line_end"] = 20
    with pytest.raises(ValidationError):
        Anchor(**kwargs)

    single = _valid_kwargs()
    single["target_line_start"] = 42
    single["target_line_end"] = 42
    a = Anchor(**single)
    assert a.target_line_start == a.target_line_end == 42


def test_anchor_positive_lines() -> None:
    # spec(§10): line numbers are 1-based positive (PositiveInt) — 0/negative rejected. Setting
    # ONLY the field under test isolates its bound: PositiveInt fails at field-validation, before
    # the after-validator span-order check ever runs, so the other line stays valid.
    for field in ("target_line_start", "target_line_end"):
        for bad in (0, -1):
            kwargs = _valid_kwargs()
            kwargs[field] = bad
            with pytest.raises(ValidationError):
                Anchor(**kwargs)


def test_anchor_confidence_range() -> None:
    # spec(§10): confidence is a [0.0, 1.0] probability — out-of-range rejected, bounds inclusive.
    for bad in (-0.1, 1.1):
        kwargs = _valid_kwargs()
        kwargs["confidence"] = bad
        with pytest.raises(ValidationError):
            Anchor(**kwargs)
    for good in (0.0, 1.0):
        kwargs = _valid_kwargs()
        kwargs["confidence"] = good
        assert Anchor(**kwargs).confidence == good


def test_anchor_target_symbol_optional() -> None:
    # spec(§10): a line-range anchor needn't name a symbol — omit/None constructs; a present
    # value is kept; whitespace-only is rejected (strip+min_length=1 when present).
    omitted = _valid_kwargs()
    del omitted["target_symbol"]
    assert Anchor(**omitted).target_symbol is None

    none_kwargs = _valid_kwargs()
    none_kwargs["target_symbol"] = None
    assert Anchor(**none_kwargs).target_symbol is None

    present = _valid_kwargs()
    present["target_symbol"] = "  resolve_anchor  "
    assert Anchor(**present).target_symbol == "resolve_anchor"

    for bad in ("", "   "):
        kwargs = _valid_kwargs()
        kwargs["target_symbol"] = bad
        with pytest.raises(ValidationError):
            Anchor(**kwargs)


def test_anchor_is_frozen() -> None:
    # spec(§10): an anchor is an immutable record; revalidation produces a new instance.
    a = Anchor(**_valid_kwargs())
    with pytest.raises(ValidationError):
        a.confidence = 0.1


def test_anchor_roundtrip() -> None:
    # spec(§10): python-mode serialization stability (enum member preserved).
    a = Anchor(**_valid_kwargs())
    assert Anchor.model_validate(a.model_dump()) == a


def test_anchor_json_roundtrip() -> None:
    # spec(§10): JSON serialization stability — AnchorState serializes to its lowercase string
    # value (the persist/reload + MCP-egress boundary), not "LIVE" or an enum repr.
    a = Anchor(**_valid_kwargs())
    assert json.loads(a.model_dump_json())["state"] == "live"
    assert Anchor.model_validate_json(a.model_dump_json()) == a
