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

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, StringConstraints


class RegistryEntry(BaseModel):
    """One per-project routing entry (immutable, closed)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    db_path: str = Field(min_length=1)  # LanceDB dataset path (identity)
    schema_version: PositiveInt = Field(...)  # per-project STORE schema (mirrors the stamp)
    model_version: str = Field(min_length=1)  # routing model identity (mirrors the stamp)
    codegraph_db_path: str = Field(min_length=1)  # CodeGraph db path (identity)
    last_indexed_sha: str = Field(min_length=1)  # last indexed git SHA (identity)
    policy: str = Field(min_length=1)  # privacy marker (non-empty); fail-closed semantics in 1.5


class Registry(BaseModel):
    """The cross-project routing index (immutable, closed); see the module docstring for the law."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: PositiveInt = Field(...)  # registry-FILE format version (the 1.2d migrator)
    # required, but {} is valid (a fresh machine has no projects); project_id keys are non-empty.
    entries: dict[Annotated[str, StringConstraints(min_length=1)], RegistryEntry] = Field(...)
