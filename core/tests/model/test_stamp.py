"""Unit tests for the frozen StoreVersionStamp contract (ARCHITECTURE.md §5, Appendix A)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import ValidationError

from model.stamp import StoreVersionStamp

pytestmark = pytest.mark.unit

# The checked-in frozen field set (the snapshot). 5 fields, NO SHA field — the git-SHA is
# the LanceDB version tag (§5-canonical); a stamp SHA field would be a second, divergent home.
EXPECTED_STAMP_FIELDS = frozenset(
    {
        "embedding_model",
        "dimension",
        "schema_version",
        "index_built_at",
        "source_root_hash",
    }
)


def _valid_kwargs() -> dict[str, Any]:
    # Any: heterogeneous kwargs unpacked into the typed StoreVersionStamp(...); negative
    # tests deliberately omit/override fields, so a precise TypedDict would fight the cases.
    """A fully-specified valid stamp payload (literals; no inline now())."""
    return {
        "embedding_model": "qwen3-embedding-4b",
        "dimension": 2560,
        "schema_version": 1,
        "index_built_at": datetime(2026, 1, 1, tzinfo=UTC),
        "source_root_hash": "sha256:rootabcd",
    }


def test_stamp_schema_snapshot() -> None:
    # spec(§5): §2.5-seam freeze pin — drift on this ★ contract is a cross-track Finding.
    assert set(StoreVersionStamp.model_fields) == EXPECTED_STAMP_FIELDS


def test_stamp_valid_construction() -> None:
    # spec(§5): the happy-path contract shape.
    s = StoreVersionStamp(**_valid_kwargs())
    assert s.embedding_model == "qwen3-embedding-4b"
    assert s.dimension == 2560
    assert s.schema_version == 1
    assert s.index_built_at == datetime(2026, 1, 1, tzinfo=UTC)
    assert s.source_root_hash == "sha256:rootabcd"


def test_stamp_rejects_extra_field() -> None:
    # spec(§5): §4 parse-don't-trust — an unknown kwarg raises (extra="forbid").
    kwargs = _valid_kwargs()
    kwargs["completely_unknown"] = "x"
    with pytest.raises(ValidationError):
        StoreVersionStamp(**kwargs)


def test_stamp_rejects_empty_identity_strings() -> None:
    # spec(§5): embedding_model + source_root_hash are TERMINAL source-of-truth identifiers
    # (federation store-gate / generation identity) with no downstream validator — empty is
    # rejected (min_length=1).
    for field in ("embedding_model", "source_root_hash"):
        kwargs = _valid_kwargs()
        kwargs[field] = ""
        with pytest.raises(ValidationError):
            StoreVersionStamp(**kwargs)


def test_stamp_rejects_sha_field() -> None:
    # spec(§5): the SHA is NOT a stamp field — it is the LanceDB version tag (source-of-truth law).
    for sha_field in ("ingested_from_sha", "git_sha", "sha"):
        kwargs = _valid_kwargs()
        kwargs[sha_field] = "deadbeef"
        with pytest.raises(ValidationError):
            StoreVersionStamp(**kwargs)


def test_stamp_is_frozen() -> None:
    # spec(§5): a stamp is immutable; a model/dim change = a new generation, not an in-place edit.
    s = StoreVersionStamp(**_valid_kwargs())
    with pytest.raises(ValidationError):
        s.dimension = 9999


def test_stamp_all_required() -> None:
    # spec(§5): every field is required (LESSONS §3 generic shadow/required-ness guard).
    for name in EXPECTED_STAMP_FIELDS:
        kwargs = _valid_kwargs()
        del kwargs[name]
        with pytest.raises(ValidationError):
            StoreVersionStamp(**kwargs)


def test_stamp_index_built_at_tz_aware() -> None:
    # spec(§5): tz-safe serialization — index_built_at is Clock-injected + AwareDatetime.
    kwargs = _valid_kwargs()
    kwargs["index_built_at"] = datetime(2026, 1, 1)  # naive
    with pytest.raises(ValidationError):
        StoreVersionStamp(**kwargs)


def test_stamp_positive_ints() -> None:
    # spec(§5): a 0/negative embedding dimension or schema version is never valid.
    for field in ("dimension", "schema_version"):
        for bad in (0, -1):
            kwargs = _valid_kwargs()
            kwargs[field] = bad
            with pytest.raises(ValidationError):
                StoreVersionStamp(**kwargs)


def test_stamp_roundtrip() -> None:
    # spec(§5): python-mode serialization stability.
    s = StoreVersionStamp(**_valid_kwargs())
    assert StoreVersionStamp.model_validate(s.model_dump()) == s


def test_stamp_json_roundtrip() -> None:
    # spec(§5): JSON serialization stability — the AwareDatetime ISO-string parse path
    # (the real LanceDB persist→reload boundary).
    s = StoreVersionStamp(**_valid_kwargs())
    assert StoreVersionStamp.model_validate_json(s.model_dump_json()) == s
