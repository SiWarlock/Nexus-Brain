"""Unit tests for the pure schema-migration engine (ARCHITECTURE.md §5; synthetic chains)."""

from __future__ import annotations

from typing import Any, NoReturn

import pytest

from model.migrations import (
    CURRENT_MANIFEST_SCHEMA_VERSION,
    CURRENT_REGISTRY_SCHEMA_VERSION,
    DowngradeRefused,
    Migration,
    MigrationError,
    MissingMigration,
    migrate,
)

pytestmark = pytest.mark.unit


def _to_v2(d: dict[str, Any]) -> dict[str, Any]:
    return {**d, "order": [*d.get("order", []), "v2"]}


def _to_v3(d: dict[str, Any]) -> dict[str, Any]:
    return {**d, "order": [*d.get("order", []), "v3"]}


def test_migrate_identity_at_current() -> None:
    # spec(§5): from_version == current_version is a no-op — content unchanged, and the engine
    # returns a defensive COPY, never an alias of the caller's input (pure data→data).
    data = {"schemaVersion": 1, "x": "y"}
    result = migrate(data, 1, chain={}, current_version=1)
    assert result == data
    assert result is not data


def test_migrate_forward_single_step() -> None:
    # spec(§5): a registered v1->v2 step applies when current=2.
    chain: dict[int, Migration] = {1: _to_v2}
    assert migrate({}, 1, chain=chain, current_version=2) == {"order": ["v2"]}


def test_migrate_forward_multi_step() -> None:
    # spec(§5): multi-step chains apply in ASCENDING version order.
    chain: dict[int, Migration] = {1: _to_v2, 2: _to_v3}
    assert migrate({}, 1, chain=chain, current_version=3) == {"order": ["v2", "v3"]}


def test_downgrade_refused() -> None:
    # spec(§5): forward-only — a file newer than the code supports is refused, never loaded;
    # the error carries both version numbers for operator diagnostics.
    with pytest.raises(DowngradeRefused, match=r"v3.*v2"):
        migrate({}, 3, chain={}, current_version=2)


def test_missing_migration_raises() -> None:
    # spec(§5): a gap in the chain (v2->v3 unregistered) raises — never silently skip a version.
    chain: dict[int, Migration] = {1: _to_v2}
    with pytest.raises(MissingMigration):
        migrate({}, 1, chain=chain, current_version=3)


def test_missing_migration_empty_chain() -> None:
    # spec(§5): the zero-registration case — a version bumped without registering its step.
    with pytest.raises(MissingMigration):
        migrate({}, 1, chain={}, current_version=2)


def test_engine_does_no_io(monkeypatch: pytest.MonkeyPatch) -> None:
    # spec(§5): §4/§7 — the engine NEVER touches the filesystem; the host owns read/write/backup.
    def _forbidden_open(*args: object, **kwargs: object) -> NoReturn:
        raise AssertionError("migrate must not perform file I/O")

    monkeypatch.setattr("builtins.open", _forbidden_open)
    chain: dict[int, Migration] = {1: _to_v2}
    assert migrate({}, 1, chain=chain, current_version=2) == {"order": ["v2"]}


def test_engine_imports_no_io() -> None:
    # spec(§5): §4/§7 chokepoint BY CONSTRUCTION — the pure engine imports no I/O-capable module
    # (whack-a-mole-proof vs patching individual functions). The host owns all FS access.
    import model.migrations as migrations_mod

    io_modules = {"os", "pathlib", "io", "subprocess", "shutil", "socket"}
    assert not (io_modules & set(migrations_mod.__dict__))


def test_current_baselines_are_v1() -> None:
    # spec(§5): no real migrations yet — both on-disk formats baseline at v1.
    assert CURRENT_MANIFEST_SCHEMA_VERSION == 1
    assert CURRENT_REGISTRY_SCHEMA_VERSION == 1


def test_migrate_does_not_validate() -> None:
    # spec(§5): transform vs validation — migrate returns a raw dict the caller validates, even
    # one a Pydantic model would reject (no model construction inside the engine).
    data = {"not_a_real_field": 123, "another": "x"}
    result = migrate(data, 1, chain={}, current_version=1)
    assert result == data
    assert isinstance(result, dict)


def test_migration_errors_share_base() -> None:
    # spec(§5): typed errors share a common base so a caller can catch all migration failures.
    assert issubclass(DowngradeRefused, MigrationError)
    assert issubclass(MissingMigration, MigrationError)
