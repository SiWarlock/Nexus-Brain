"""Unit tests for the frozen Chunk data contract (ARCHITECTURE.md §5, Appendix A)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import ValidationError

from model.chunk import Chunk

pytestmark = pytest.mark.unit

# The checked-in frozen field set (the snapshot). Adjudicated union of Appendix-A
# (Chunk row) + DATA_MODEL.md §①, with BM25/FTS excluded (native LanceDB index).
EXPECTED_CHUNK_FIELDS = frozenset(
    {
        "chunk_id",
        "project_id",
        "source_path",
        "doc_or_code",
        "producer",
        "doc_type",
        "ownership",
        "register",
        "text",
        "vector",
        "anchor",
        "content_hash",
        "last_resolved_sha",
        "ingested_from_sha",
        "embedding_model_version",
        "context_blurb",
        "generation",
        "tombstone",
        "created_at",
    }
)


def _valid_kwargs() -> dict[str, Any]:
    # Any: heterogeneous kwargs unpacked into the typed Chunk(...); negative tests
    # deliberately omit/override fields, so a precise TypedDict would fight the cases.
    """A fully-specified valid Chunk payload (literals; no inline now()/uuid4)."""
    return {
        "chunk_id": "chunk-0001",
        "project_id": "proj-abc",
        "source_path": "src/app.py",
        "doc_or_code": "code",
        "producer": "human",
        "doc_type": "guide",
        "ownership": "owned",
        "register": "plain",
        "text": "def f() -> int: ...",
        "vector": [0.1, 0.2, 0.3],
        "anchor": "src/app.py:10-20",
        "content_hash": "sha256:abcd",
        "last_resolved_sha": "deadbeefcafe",
        "ingested_from_sha": "deadbeefcafe",
        "embedding_model_version": "qwen3-embedding-4b@1",
        "context_blurb": "A small helper function.",
        "generation": 1,
        "tombstone": False,
        "created_at": datetime(2026, 1, 1, tzinfo=UTC),
    }


def test_chunk_schema_snapshot() -> None:
    # spec(§5): §2.5-seam freeze pin — any field add/remove/rename on this ★ contract
    # fails here, forcing the atomic Appendix-A edit (a silent drift is a cross-track Finding).
    assert set(Chunk.model_fields) == EXPECTED_CHUNK_FIELDS


def test_chunk_valid_construction() -> None:
    # spec(§5): the happy-path contract shape — a fully-specified Chunk validates.
    c = Chunk(**_valid_kwargs())
    assert c.chunk_id == "chunk-0001"
    assert c.doc_or_code == "code"
    assert c.vector == [0.1, 0.2, 0.3]
    assert c.created_at == datetime(2026, 1, 1, tzinfo=UTC)


def test_chunk_rejects_extra_field() -> None:
    # spec(§5): §4 parse-don't-trust at the contract boundary (extra="forbid").
    kwargs = _valid_kwargs()
    kwargs["unexpected_field"] = "x"
    with pytest.raises(ValidationError):
        Chunk(**kwargs)


def test_chunk_is_frozen() -> None:
    # spec(§5): a persisted row is immutable; mutation = a new generation, not in-place.
    c = Chunk(**_valid_kwargs())
    with pytest.raises(ValidationError):
        c.text = "mutated"


def test_chunk_requires_chunk_id_and_created_at() -> None:
    # spec(§5): forbidden-rule 4 — ids/timestamps are caller-injected via IdGen/Clock,
    # never minted inline (no default_factory). A missing required field raises.
    for field in ("chunk_id", "created_at"):
        kwargs = _valid_kwargs()
        del kwargs[field]
        with pytest.raises(ValidationError):
            Chunk(**kwargs)


def test_chunk_created_at_must_be_tz_aware() -> None:
    # spec(§5): tz-safe serialization (mirrors the Clock.now() contract from 1.1).
    kwargs = _valid_kwargs()
    kwargs["created_at"] = datetime(2026, 1, 1)  # naive
    with pytest.raises(ValidationError):
        Chunk(**kwargs)


def test_chunk_closed_set_fields_reject_unknown() -> None:
    # spec(§5): closed-set integrity for the Literal/Enum fields.
    for field, bad in (
        ("doc_or_code", "image"),
        ("ownership", "mine"),
        ("register", "loud"),
    ):
        kwargs = _valid_kwargs()
        kwargs[field] = bad
        with pytest.raises(ValidationError):
            Chunk(**kwargs)


def test_chunk_roundtrip() -> None:
    # spec(§5): serialization stability for the LanceDB row.
    c = Chunk(**_valid_kwargs())
    assert Chunk.model_validate(c.model_dump()) == c


def test_chunk_all_non_optional_fields_required() -> None:
    # spec(§5): every field except context_blurb is required (no default). Generalizes the
    # freeze pin and catches the metaclass-attribute-shadow default trap (e.g. `register`
    # silently picking up ABCMeta.register as its default).
    optional = {"context_blurb"}
    for name in EXPECTED_CHUNK_FIELDS - optional:
        kwargs = _valid_kwargs()
        del kwargs[name]
        with pytest.raises(ValidationError):
            Chunk(**kwargs)


def test_chunk_json_roundtrip() -> None:
    # spec(§5): JSON serialization stability — pins the AwareDatetime ISO-string parse path
    # (the real LanceDB persist→reload boundary), which python-mode dump/validate skips.
    c = Chunk(**_valid_kwargs())
    assert Chunk.model_validate_json(c.model_dump_json()) == c


def test_chunk_identity_fields_hardened() -> None:
    # 1.6a: the §5 gap — chunk identity fields were BARE `str` (pre-LESSON-7, zero validation). Now
    # the shared IdentityStr: every identity field rejects empty / whitespace-only / control / NUL,
    # and strips surrounding whitespace.
    identity_fields = (
        "chunk_id",
        "project_id",
        "source_path",
        "producer",
        "doc_type",
        "anchor",
        "content_hash",
        "last_resolved_sha",
        "ingested_from_sha",
        "embedding_model_version",
    )
    for field in identity_fields:
        for bad in ("", "   ", "x\x00y"):
            kwargs = _valid_kwargs()
            kwargs[field] = bad
            with pytest.raises(ValidationError):
                Chunk(**kwargs)
    kwargs = _valid_kwargs()
    kwargs["chunk_id"] = "  chunk-0001  "
    assert Chunk(**kwargs).chunk_id == "chunk-0001"  # strip


def test_chunk_content_fields_use_textstr() -> None:
    # 1.6a: content fields (text, context_blurb) use TextStr — inline newline is legitimate, but NUL
    # and empty are rejected (was bare `str`, which admitted both).
    kwargs = _valid_kwargs()
    kwargs["text"] = "line1\nline2"
    assert "\n" in Chunk(**kwargs).text  # inline newline is legitimate for content
    for field in ("text", "context_blurb"):
        for bad in ("", "a\x00b"):
            kwargs = _valid_kwargs()
            kwargs[field] = bad
            with pytest.raises(ValidationError):
                Chunk(**kwargs)


def test_chunk_tombstone_strict() -> None:
    # §5 lifecycle (1.6c): tombstone is StrictBool — a lax 1/"yes"/"true"/"on" can't coerce to True
    # (parse-don't-trust on the persisted lifecycle flag); a real bool is accepted.
    for lax in (1, 0, "yes", "true", "on", "false"):
        kwargs = _valid_kwargs()
        kwargs["tombstone"] = lax
        with pytest.raises(ValidationError):
            Chunk(**kwargs)
    kwargs = _valid_kwargs()
    kwargs["tombstone"] = True
    assert Chunk(**kwargs).tombstone is True
