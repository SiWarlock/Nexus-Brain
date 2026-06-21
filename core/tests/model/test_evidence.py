"""Unit tests for the frozen EvidenceRef contract (ARCHITECTURE.md §10, Appendix A:217).

★ Freeze-before-fork contract. An `EvidenceRef` is a user-visible piece of evidence backing an
answer: `{type, label, resource_ref?, confidence?}`. Per lead decision D-A11 (Option B) the field
SHAPE is frozen here while the externally-owned `EvidenceType` membership is DEFERRED to Phase-4.
This file pins the 4-field shape snapshot but has NO EvidenceType value-set snapshot.
"""

from __future__ import annotations

import json
from typing import Any, get_args

import pytest
from pydantic import ValidationError

from model.evidence import EvidenceRef, EvidenceType

pytestmark = pytest.mark.unit

# The checked-in frozen field SHAPE (snapshot). 4 fields — Appendix-A line 217. Per D-A11
# guardrail 2 this pins field NAMES only, so later EvidenceType narrowing stays additive.
EXPECTED_EVIDENCE_FIELDS = frozenset({"type", "label", "resource_ref", "confidence"})

# The string fields that carry strip+min_length (LESSON 7). resource_ref only when present.
STRIP_FIELDS = ("type", "label", "resource_ref")


def _valid_kwargs() -> dict[str, Any]:
    # Any: heterogeneous kwargs unpacked into the typed EvidenceRef(...); negative tests omit/
    # override fields, so a precise TypedDict would fight the cases.
    """A fully-specified valid evidence payload (all 4 fields)."""
    return {
        "type": "code_chunk",
        "label": "anchor.py — Anchor model",
        "resource_ref": "chunk_01h9z",
        "confidence": 0.82,
    }


def test_evidence_schema_snapshot() -> None:
    # spec(§10): §2.5-seam ★ freeze pin — SHAPE only (field names); drift is a cross-track Finding.
    assert set(EvidenceRef.model_fields) == EXPECTED_EVIDENCE_FIELDS


def test_evidence_valid_construction_full() -> None:
    # spec(§10): the happy path — all 4 fields construct + round-read.
    e = EvidenceRef(**_valid_kwargs())
    assert e.type == "code_chunk"
    assert e.label == "anchor.py — Anchor model"
    assert e.resource_ref == "chunk_01h9z"
    assert e.confidence == 0.82


def test_evidence_valid_construction_minimal() -> None:
    # spec(§10): resource_ref?/confidence? are optional — only type+label is a valid EvidenceRef.
    e = EvidenceRef(type="commit", label="fix: redaction gate")
    assert e.resource_ref is None
    assert e.confidence is None


def test_evidence_rejects_extra_field() -> None:
    # spec(§10): §4 parse-don't-trust — an unknown kwarg raises (extra="forbid").
    kwargs = _valid_kwargs()
    kwargs["resource_kind"] = "x"  # the discriminator IS `type`; no separate kind field
    with pytest.raises(ValidationError):
        EvidenceRef(**kwargs)


def test_evidence_required_fields() -> None:
    # LESSON 3: omit-each on the REQUIRED subset — type/label required; optionals are not.
    optionals = {"resource_ref", "confidence"}
    for required in EXPECTED_EVIDENCE_FIELDS - optionals:
        kwargs = _valid_kwargs()
        del kwargs[required]
        with pytest.raises(ValidationError):
            EvidenceRef(**kwargs)
    for optional in optionals:
        kwargs = _valid_kwargs()
        del kwargs[optional]
        EvidenceRef(**kwargs)  # must NOT raise


def test_evidence_rejects_empty_strings() -> None:
    # LESSON 7: ""/whitespace-only rejected for each strip+min_length string field (resource_ref
    # only matters when present).
    for field in STRIP_FIELDS:
        for bad in ("", "   "):
            kwargs = _valid_kwargs()
            kwargs[field] = bad
            with pytest.raises(ValidationError):
                EvidenceRef(**kwargs)


def test_evidence_strips_whitespace() -> None:
    # LESSON 7: StringConstraints(strip_whitespace=True) — surrounding whitespace stripped.
    kwargs = _valid_kwargs()
    kwargs["type"] = "  code_chunk  "
    kwargs["label"] = "  ev chip  "
    kwargs["resource_ref"] = "\tchunk_01h9z\n"
    e = EvidenceRef(**kwargs)
    assert e.type == "code_chunk"
    assert e.label == "ev chip"
    assert e.resource_ref == "chunk_01h9z"


def test_evidence_optional_fields() -> None:
    # spec(§10): optional-field contract — omitted/None ok; a present value is kept.
    none_kwargs = _valid_kwargs()
    none_kwargs["resource_ref"] = None
    none_kwargs["confidence"] = None
    e = EvidenceRef(**none_kwargs)
    assert e.resource_ref is None
    assert e.confidence is None

    present = EvidenceRef(**_valid_kwargs())
    assert present.resource_ref == "chunk_01h9z"
    assert present.confidence == 0.82


def test_evidence_confidence_range() -> None:
    # spec(§10): confidence (when present) is [0,1]; None is valid; out-of-range raises.
    for bad in (-0.1, 1.1):
        kwargs = _valid_kwargs()
        kwargs["confidence"] = bad
        with pytest.raises(ValidationError):
            EvidenceRef(**kwargs)
    for good in (0.0, 1.0, None):
        kwargs = _valid_kwargs()
        kwargs["confidence"] = good
        assert EvidenceRef(**kwargs).confidence == good


def test_evidence_type_membership_is_deferred() -> None:
    # D-A11 (Option B): EvidenceType membership is intentionally OPEN until the canonical 11 are
    # pinned at Phase-4 grounding (first consumption). EvidenceType is a DEFERRED constrained-str
    # alias (Annotated[str, StringConstraints]) — its base type is str and it is NOT an instantiated
    # enum, so ANY non-empty string is a valid `type`. This test + the module marker ARE the
    # deferral record; there is deliberately NO value-set snapshot (it would lock a deferred set).
    args = get_args(EvidenceType)
    assert args and args[0] is str  # Annotated[str,...]; empty tuple ⇒ wrapper lost (bug, not pass)
    for any_kind in ("code_chunk", "some_future_kind", "commit", "episode_card", "plan_task"):
        assert EvidenceRef(type=any_kind, label="lbl").type == any_kind


def test_evidence_is_frozen() -> None:
    # spec(§10): an evidence record is immutable; a re-scored ref is a new instance.
    e = EvidenceRef(**_valid_kwargs())
    with pytest.raises(ValidationError):
        e.confidence = 0.1


def test_evidence_roundtrip() -> None:
    # spec(§10): python-mode serialization stability.
    e = EvidenceRef(**_valid_kwargs())
    assert EvidenceRef.model_validate(e.model_dump()) == e


def test_evidence_json_roundtrip() -> None:
    # spec(§10): JSON serialization stability — the persist/reload + MCP-egress boundary; the
    # optional None fields survive the JSON round-trip.
    e = EvidenceRef(type="commit", label="minimal")
    dumped = json.loads(e.model_dump_json())
    assert dumped["resource_ref"] is None  # both optionals serialize to JSON null, not absent
    assert dumped["confidence"] is None
    assert EvidenceRef.model_validate_json(e.model_dump_json()) == e
