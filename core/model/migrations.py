"""Pure schema-migration engine for the §5 serialized files (ARCHITECTURE.md §5; D-26/C-12).

A forward-only `schemaVersion` runner with downgrade-refuse + missing-migration detection, for the
on-disk manifest + registry file formats. The engine is PURE (data→data): it performs NO file I/O.

The host owns the I/O (Phase 2+, via `HostPort.perform`): read the file → `migrate(...)` → BACK UP
the original → write the migrated result → re-validate with the Pydantic model. Raw filesystem
access here would violate the §4/§7 single-mutation chokepoint (and `HostPort` isn't built until
1.4). There are no real migrations yet — both formats baseline at v1 — so this freezes the
FRAMEWORK + the downgrade-refuse safety rule, exercised with synthetic chains.

The engine transforms keys/values only; the caller re-validates the result against its model
(separation of concerns: transform vs validation).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

# Current on-disk format versions. No migrations are registered yet → baseline 1 for both.
CURRENT_MANIFEST_SCHEMA_VERSION = 1
CURRENT_REGISTRY_SCHEMA_VERSION = 1

# A single `vN -> vN+1` transform over the raw (pre-validation) on-disk dict.
# Any: on-disk JSON content is heterogeneous and not yet model-validated (transform, not validate).
Migration = Callable[[dict[str, Any]], dict[str, Any]]


class MigrationError(Exception):
    """Base class for schema-migration failures (catch-all for callers)."""


class DowngradeRefused(MigrationError):
    """The file's version is newer than the code supports — forward-only, never downgrade."""


class MissingMigration(MigrationError):
    """The forward chain has no registered step for a version it must cross."""


def migrate(
    data: dict[str, Any],
    from_version: int,
    *,
    chain: Mapping[int, Migration],
    current_version: int,
) -> dict[str, Any]:
    """Apply the registered forward chain from `from_version` up to `current_version`.

    Pure data→data: performs no file I/O and returns the raw migrated dict (the caller validates).
    `from_version == current_version` is a no-op (the loop body never runs). Raises
    `DowngradeRefused` if `from_version > current_version`, or `MissingMigration` on a chain gap.
    """
    if from_version > current_version:
        raise DowngradeRefused(
            f"on-disk schema v{from_version} is newer than supported v{current_version}"
        )
    result = dict(data)  # defensive copy — never return an alias of the caller's input (pure)
    version = from_version
    while version < current_version:
        step = chain.get(version)
        if step is None:
            raise MissingMigration(f"no migration registered for v{version} -> v{version + 1}")
        result = step(result)
        version += 1
    return result
