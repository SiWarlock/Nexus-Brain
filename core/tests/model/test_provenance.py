"""Unit tests for the frozen ProvenancePacket contract (ARCHITECTURE.md §10, Appendix A:217).

★ Freeze-before-fork contract. A `ProvenancePacket` is the evidence + freshness + confidence record
attached to every answer (the audit of trust). 10 fields, frozen, composing the 1.3c `EvidenceRef`
by value. Completes Phase 1.3. The 10-field set is pinned by a spec(§10) snapshot.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from pydantic import ValidationError

from model.evidence import EvidenceRef
from model.provenance import ProvenancePacket

pytestmark = pytest.mark.unit

# The checked-in frozen field set (the snapshot). 10 fields — Appendix-A line 217 (reconciled to
# include the additive evidence[] aggregation the DOMAIN_MODEL ER map mandates).
EXPECTED_PROVENANCE_FIELDS = frozenset(
    {
        "project_ids",
        "source_ids",
        "citations",
        "commit_shas",
        "session_ids",
        "recorded_sha",
        "index_freshness",
        "confidence",
        "drift_markers",
        "evidence",
    }
)

# The string-list fields whose ELEMENTS carry strip+min_length (LESSON 7).
STRING_LIST_FIELDS = (
    "project_ids",
    "source_ids",
    "citations",
    "commit_shas",
    "session_ids",
    "drift_markers",
)


def _evidence() -> EvidenceRef:
    """A valid nested EvidenceRef for the packet's evidence[] list."""
    return EvidenceRef(type="code_chunk", label="anchor.py — Anchor", resource_ref="chunk_1")


def _valid_kwargs() -> dict[str, Any]:
    # Any: heterogeneous kwargs unpacked into the typed ProvenancePacket(...); negative tests
    # omit/override fields, so a precise TypedDict would fight the cases.
    """A fully-specified valid provenance payload (all 10 fields, one nested EvidenceRef)."""
    return {
        "project_ids": ["proj_nexus"],
        "source_ids": ["src_docs"],
        "citations": ["core/model/anchor.py:20-35"],
        "commit_shas": ["sha256:deadbeef"],
        "session_ids": ["sess_01h9z"],
        "recorded_sha": "sha256:cafef00d",
        "index_freshness": "fresh",
        "confidence": 0.91,
        "drift_markers": ["none"],
        "evidence": [_evidence()],
    }


def test_provenance_schema_snapshot() -> None:
    # spec(§10): §2.5-seam ★ freeze pin — drift on this contract is a cross-track Finding.
    assert set(ProvenancePacket.model_fields) == EXPECTED_PROVENANCE_FIELDS


def test_provenance_valid_construction_full() -> None:
    # spec(§10): the happy path — all 10 fields (incl. a nested EvidenceRef) round-read.
    p = ProvenancePacket(**_valid_kwargs())
    assert p.project_ids == ["proj_nexus"]
    assert p.citations == ["core/model/anchor.py:20-35"]
    assert p.commit_shas == ["sha256:deadbeef"]
    assert p.recorded_sha == "sha256:cafef00d"
    assert p.index_freshness == "fresh"
    assert p.confidence == 0.91
    assert p.drift_markers == ["none"]
    assert len(p.evidence) == 1
    assert p.evidence[0].type == "code_chunk"


def test_provenance_rejects_extra_field() -> None:
    # spec(§10): §4 parse-don't-trust — an unknown kwarg raises (extra="forbid").
    kwargs = _valid_kwargs()
    kwargs["low_confidence_links"] = []  # Q3: NOT a packet field
    with pytest.raises(ValidationError):
        ProvenancePacket(**kwargs)


def test_provenance_required_fields() -> None:
    # LESSON 3: omit-each on the REQUIRED subset — only recorded_sha is optional.
    for required in EXPECTED_PROVENANCE_FIELDS - {"recorded_sha"}:
        kwargs = _valid_kwargs()
        del kwargs[required]
        with pytest.raises(ValidationError):
            ProvenancePacket(**kwargs)
    omitted = _valid_kwargs()
    del omitted["recorded_sha"]
    ProvenancePacket(**omitted)  # must NOT raise


def test_provenance_empty_lists_allowed() -> None:
    # spec(§10): an ungrounded/flagged answer carries empty citation/evidence lists.
    kwargs = _valid_kwargs()
    for field in (*STRING_LIST_FIELDS, "evidence"):
        kwargs[field] = []
    p = ProvenancePacket(**kwargs)
    assert p.citations == []
    assert p.evidence == []


def test_provenance_rejects_empty_string_elements() -> None:
    # LESSON 7: ""/whitespace-only rejected as a list element AND as a scalar string field.
    for field in STRING_LIST_FIELDS:
        for bad in ("", "   "):
            kwargs = _valid_kwargs()
            kwargs[field] = [bad]
            with pytest.raises(ValidationError):
                ProvenancePacket(**kwargs)
    for field in ("recorded_sha", "index_freshness"):
        for bad in ("", "   "):
            kwargs = _valid_kwargs()
            kwargs[field] = bad
            with pytest.raises(ValidationError):
                ProvenancePacket(**kwargs)


def test_provenance_strips_whitespace() -> None:
    # LESSON 7: StringConstraints(strip_whitespace=True) — element + scalar surrounding ws stripped.
    kwargs = _valid_kwargs()
    kwargs["citations"] = ["  core/x.py:1  "]
    kwargs["index_freshness"] = "  fresh  "
    p = ProvenancePacket(**kwargs)
    assert p.citations == ["core/x.py:1"]
    assert p.index_freshness == "fresh"


def test_provenance_confidence_range() -> None:
    # spec(§10): the answer's overall confidence is a [0,1] probability — out-of-range rejected.
    for bad in (-0.1, 1.1):
        kwargs = _valid_kwargs()
        kwargs["confidence"] = bad
        with pytest.raises(ValidationError):
            ProvenancePacket(**kwargs)
    for good in (0.0, 1.0):
        kwargs = _valid_kwargs()
        kwargs["confidence"] = good
        assert ProvenancePacket(**kwargs).confidence == good


def test_provenance_recorded_sha_optional() -> None:
    # spec(§10): recorded-Citations SHA is optional — omitted/None ok; present kept (stripped).
    omitted = _valid_kwargs()
    del omitted["recorded_sha"]
    assert ProvenancePacket(**omitted).recorded_sha is None

    none_kwargs = _valid_kwargs()
    none_kwargs["recorded_sha"] = None
    assert ProvenancePacket(**none_kwargs).recorded_sha is None

    present = _valid_kwargs()
    present["recorded_sha"] = "  sha256:abc  "
    assert ProvenancePacket(**present).recorded_sha == "sha256:abc"


def test_provenance_evidence_typed() -> None:
    # spec(§10): evidence is list[EvidenceRef] (Q1 additive composition) — instances accepted,
    # empty allowed, a non-EvidenceRef/malformed element rejected (parse-don't-trust on the nested).
    p = ProvenancePacket(**_valid_kwargs())
    assert isinstance(p.evidence[0], EvidenceRef)

    empty = _valid_kwargs()
    empty["evidence"] = []
    assert ProvenancePacket(**empty).evidence == []

    # a well-formed dict COERCES to a validated EvidenceRef (the JSON/MCP-egress path) — accepted
    # because it still passes EvidenceRef's full validation; parse-don't-trust holds.
    coerced = _valid_kwargs()
    coerced["evidence"] = [{"type": "commit", "label": "fix"}]
    e0 = ProvenancePacket(**coerced).evidence[0]
    assert isinstance(e0, EvidenceRef)
    assert e0.label == "fix"

    for bad in (42, {"type": "code_chunk"}):  # int; dict missing required 'label' → both rejected
        kwargs = _valid_kwargs()
        kwargs["evidence"] = [bad]
        with pytest.raises(ValidationError):
            ProvenancePacket(**kwargs)


def test_provenance_is_frozen() -> None:
    # spec(§10): a packet is immutable (a re-grounded answer mints a new packet) — and DEEPLY so:
    # the nested EvidenceRef is frozen too, so a trust record can't be edited element-wise.
    p = ProvenancePacket(**_valid_kwargs())
    with pytest.raises(ValidationError):
        p.confidence = 0.1
    with pytest.raises(ValidationError):
        p.evidence[0].label = "x"


def test_provenance_roundtrip() -> None:
    # spec(§10): python-mode serialization stability (incl. the nested EvidenceRef).
    p = ProvenancePacket(**_valid_kwargs())
    assert ProvenancePacket.model_validate(p.model_dump()) == p


def test_provenance_json_roundtrip() -> None:
    # spec(§10): JSON serialization stability — nested EvidenceRef serializes + None recorded_sha
    # survives as null (the persist/reload + MCP-egress boundary with a nested model).
    kwargs = _valid_kwargs()
    kwargs["recorded_sha"] = None
    p = ProvenancePacket(**kwargs)
    dumped = json.loads(p.model_dump_json())
    assert dumped["recorded_sha"] is None
    assert dumped["evidence"][0]["type"] == "code_chunk"
    assert ProvenancePacket.model_validate_json(p.model_dump_json()) == p
