"""The frozen global Registry + RegistryEntry contracts (ARCHITECTURE.md §5, Appendix A).

★ Freeze-before-fork contracts. `~/.project-brain/registry` is the cross-project DERIVED routing
index (`project_id → RegistryEntry`), rebuildable by scanning per-project manifests — it is NOT
canonical (the per-project datasets + their git-SHA version tags are), and is read-only to the
federation router (§4 invariant 5).

Two DISTINCT schema_versions (do not conflate): `Registry.schema_version` is the registry-FILE
format version the Phase-1.2d migrator keys on; `RegistryEntry.schema_version` is the per-project
STORE schema version mirrored from that project's stamp/manifest. All keys are snake_case (no
aliasing) — the on-disk JSON keys are the Python field names.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, PositiveInt

from _types import IdentityStr


class RegistryEntry(BaseModel):
    """One per-project routing entry (immutable, closed)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    db_path: IdentityStr  # LanceDB dataset path (identity)
    schema_version: PositiveInt = Field(...)  # per-project STORE schema (mirrors the stamp)
    model_version: IdentityStr  # routing model identity (mirrors the stamp)
    codegraph_db_path: IdentityStr  # CodeGraph db path (identity)
    last_indexed_sha: IdentityStr  # last indexed git SHA (identity)
    policy: IdentityStr  # privacy marker (non-empty); fail-closed semantics in 1.5


class Registry(BaseModel):
    """The cross-project routing index (immutable, closed); see the module docstring for the law."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: PositiveInt = Field(...)  # registry-FILE format version (the 1.2d migrator)
    # required, but {} is valid (a fresh machine has no projects); project_id keys are non-empty.
    # NOTE (1.6b): a dict has no clean frozen form — LESSON-8 deep immutability for `entries` is a
    # known residual (out of the list→tuple scope); revisit if it becomes a mutation hazard.
    entries: dict[IdentityStr, RegistryEntry] = Field(...)
