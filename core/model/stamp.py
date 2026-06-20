"""The frozen store version stamp — the §5 source-of-truth contract (ARCHITECTURE.md §5).

★ Freeze-before-fork contract. One `StoreVersionStamp` per LanceDB dataset.

Source-of-truth law (§5): the store-level stamp is canonical for `{schema, model, dim}`; the
**git-SHA is the LanceDB version tag** (the sole canonical SHA home, set at write-time in
Phase 3.1) — so the stamp deliberately carries NO SHA field (a second SHA home could disagree
with the version tag and break source-of-truth). The `.project-brain/manifest.json` + global
registry are DERIVED projections of this stamp + the version tag, never independent authorities.

The field set is pinned by a spec(§5) schema-snapshot test; a change must ride an atomic
Appendix-A edit (silent drift is a cross-track Finding).
"""

from __future__ import annotations

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, PositiveInt

from _types import IdentityStr


class StoreVersionStamp(BaseModel):
    """The one-per-dataset version stamp (immutable, closed).

    `index_built_at` is REQUIRED with no default — the writer injects it via the `Clock` seam
    (forbidden-rule 4 / LESSONS §1), never inline. `schema_version` is the on-disk store schema
    version the Phase-1.2d forward-only migrator keys on (starts at 1), NOT the chunk/model version.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    embedding_model: IdentityStr  # terminal source-of-truth id (federation gate)
    dimension: PositiveInt = Field(...)
    schema_version: PositiveInt = Field(...)
    index_built_at: AwareDatetime = Field(...)
    source_root_hash: IdentityStr  # terminal source-of-truth id (generation identity)
