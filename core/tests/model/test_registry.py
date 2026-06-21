"""Unit tests for the frozen Registry + RegistryEntry contracts (ARCHITECTURE.md §5, Appendix A)."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from model.registry import Registry, RegistryEntry

pytestmark = pytest.mark.unit

EXPECTED_ENTRY_FIELDS = frozenset(
    {
        "db_path",
        "schema_version",
        "model_version",
        "codegraph_db_path",
        "last_indexed_sha",
        "policy",
    }
)
EXPECTED_REGISTRY_FIELDS = frozenset({"schema_version", "entries"})
# Entry identity strings pinned non-empty (min_length=1). policy is included: an empty privacy
# marker on a routing entry is a fail-open shape (fail-closed SEMANTICS are owned by the 1.5 model).
ENTRY_IDENTITY_FIELDS = (
    "db_path",
    "model_version",
    "codegraph_db_path",
    "last_indexed_sha",
    "policy",
)


def _valid_entry_kwargs() -> dict[str, Any]:
    # Any: heterogeneous kwargs unpacked into the typed model; negative tests omit/override.
    return {
        "db_path": "~/.project-brain/proj-abc/lancedb",
        "schema_version": 1,
        "model_version": "qwen3-embedding-4b@1",
        "codegraph_db_path": "/repo/.codegraph/codegraph.db",
        "last_indexed_sha": "deadbeefcafe",
        "policy": "local",
    }


def _valid_registry_kwargs() -> dict[str, Any]:
    # Any: heterogeneous kwargs unpacked into the typed model; negative tests omit/override.
    return {
        "schema_version": 1,
        "entries": {"proj-abc": RegistryEntry(**_valid_entry_kwargs())},
    }


def test_registry_entry_schema_snapshot() -> None:
    # spec(§5): §2.5-seam freeze pin (entry row).
    assert set(RegistryEntry.model_fields) == EXPECTED_ENTRY_FIELDS


def test_registry_schema_snapshot() -> None:
    # spec(§5): §2.5-seam freeze pin (registry wrapper).
    assert set(Registry.model_fields) == EXPECTED_REGISTRY_FIELDS


def test_registry_on_disk_keys_are_field_names() -> None:
    # spec(§5): LESSON §4 (trivially) — the registry is all-snake, so the on-disk JSON keys ARE
    # the Python field names (no aliasing); the field-name snapshot doubles as the on-disk pin.
    reg = Registry(**_valid_registry_kwargs())
    assert set(reg.model_dump(by_alias=True)) == EXPECTED_REGISTRY_FIELDS
    entry = reg.entries["proj-abc"]
    assert set(entry.model_dump(by_alias=True)) == EXPECTED_ENTRY_FIELDS


def test_registry_entry_valid_construction() -> None:
    # spec(§5): happy-path entry shape.
    e = RegistryEntry(**_valid_entry_kwargs())
    assert e.db_path == "~/.project-brain/proj-abc/lancedb"
    assert e.schema_version == 1
    assert e.policy == "local"


def test_registry_valid_construction() -> None:
    # spec(§5): happy-path registry shape with ≥1 entry in the map.
    reg = Registry(**_valid_registry_kwargs())
    assert reg.schema_version == 1
    assert reg.entries["proj-abc"].model_version == "qwen3-embedding-4b@1"


def test_registry_entry_rejects_extra() -> None:
    # spec(§5): §4 parse-don't-trust (extra="forbid").
    kwargs = _valid_entry_kwargs()
    kwargs["unexpected"] = "x"
    with pytest.raises(ValidationError):
        RegistryEntry(**kwargs)


def test_registry_rejects_extra() -> None:
    # spec(§5): §4 parse-don't-trust (extra="forbid").
    kwargs = _valid_registry_kwargs()
    kwargs["unexpected"] = "x"
    with pytest.raises(ValidationError):
        Registry(**kwargs)


def test_registry_entry_is_frozen() -> None:
    # spec(§5): immutable entry (frozen=True).
    e = RegistryEntry(**_valid_entry_kwargs())
    with pytest.raises(ValidationError):
        e.db_path = "mutated"


def test_registry_is_frozen() -> None:
    # spec(§5): immutable registry (frozen=True).
    reg = Registry(**_valid_registry_kwargs())
    with pytest.raises(ValidationError):
        reg.schema_version = 9


def test_registry_entry_all_required() -> None:
    # spec(§5): every entry field required (LESSONS §3 omit-each guard).
    for name in EXPECTED_ENTRY_FIELDS:
        kwargs = _valid_entry_kwargs()
        del kwargs[name]
        with pytest.raises(ValidationError):
            RegistryEntry(**kwargs)


def test_registry_all_required() -> None:
    # spec(§5): both wrapper fields required (entries required but {} allowed).
    for name in EXPECTED_REGISTRY_FIELDS:
        kwargs = _valid_registry_kwargs()
        del kwargs[name]
        with pytest.raises(ValidationError):
            Registry(**kwargs)


def test_registry_accepts_empty() -> None:
    # spec(§5): a fresh machine has zero projects — an empty registry ({}) is valid.
    reg = Registry(schema_version=1, entries={})
    assert reg.entries == {}


def test_registry_entry_identity_min_length() -> None:
    # spec(§5): terminal identity strings (incl. policy) rejected when empty (min_length=1).
    for field in ENTRY_IDENTITY_FIELDS:
        kwargs = _valid_entry_kwargs()
        kwargs[field] = ""
        with pytest.raises(ValidationError):
            RegistryEntry(**kwargs)


def test_registry_rejects_empty_project_id_key() -> None:
    # spec(§5): project_id map keys are identity — an empty-string key is rejected (min_length=1),
    # on BOTH the constructor and the model_validate ingress path (file-load / MCP-ingress).
    entry = RegistryEntry(**_valid_entry_kwargs())
    with pytest.raises(ValidationError):
        Registry(schema_version=1, entries={"": entry})
    with pytest.raises(ValidationError):
        Registry.model_validate({"schema_version": 1, "entries": {"": _valid_entry_kwargs()}})


def test_registry_roundtrip() -> None:
    # spec(§5): on-disk round-trip stability (all-snake JSON; nested entries preserved).
    reg = Registry(**_valid_registry_kwargs())
    assert Registry.model_validate_json(reg.model_dump_json()) == reg


def test_registry_roundtrip_multi_entry() -> None:
    # spec(§5): round-trip with ≥2 distinct project_ids carrying different store schema_versions.
    reg = Registry(
        schema_version=1,
        entries={
            "proj-a": RegistryEntry(**_valid_entry_kwargs()),
            "proj-b": RegistryEntry(**{**_valid_entry_kwargs(), "schema_version": 3}),
        },
    )
    assert len(reg.entries) == 2
    assert Registry.model_validate_json(reg.model_dump_json()) == reg


def test_registry_two_schema_versions_distinct() -> None:
    # spec(§5): Registry.schema_version (registry-FILE format) is INDEPENDENT of
    # RegistryEntry.schema_version (per-project STORE schema) — a file-format bump ≠ a store bump.
    entry = RegistryEntry(**{**_valid_entry_kwargs(), "schema_version": 5})
    reg = Registry(schema_version=2, entries={"proj-a": entry})
    # independent values — a single merged field could not represent both at once:
    assert reg.schema_version != reg.entries["proj-a"].schema_version
    assert reg.schema_version == 2
    assert reg.entries["proj-a"].schema_version == 5
    # structural distinctness — they are fields on two different models:
    assert Registry.model_fields is not RegistryEntry.model_fields
