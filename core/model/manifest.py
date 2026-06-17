"""The frozen ProjectManifest + ManifestArtifact contracts (ARCHITECTURE.md §5, Appendix A).

★ Freeze-before-fork contracts. `.project-brain/manifest.json` is a per-repo DERIVED projection
of the §5 source-of-truth (the LanceDB dataset + the git-SHA version tag) — rebuilt from the
dataset on every commit and reconciled at startup; it is NOT itself canonical. `ingested_from_sha`
records the (derived) generation SHA that mirrors the version tag. The manifest is project-brain-
owned (sibling to the read-only `.scaffolding/manifest.json`, §4 invariant 7).

On-disk JSON contract: keys are snake_case EXCEPT the two camelCase aliases `schemaVersion` and
`ingestedFromSha` (per DATA_MODEL.md). `validate_by_name` + `validate_by_alias` let the writer
construct by Python name while the persisted file keeps its frozen camelCase keys; the field-name
snapshot pins the Python names and the by-alias test pins the JSON keys.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, PositiveInt


class ManifestArtifact(BaseModel):
    """One ingested artifact row in a manifest (immutable, closed)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    path: str = Field(min_length=1)  # repo-relative path (identity)
    content_hash: str = Field(min_length=1)  # of the source unit (identity)
    doc_type: str = Field(...)  # open-ended (classifier may grow)
    producer: str = Field(...)  # open-ended (classifier may grow)
    ownership: Literal["owned", "foreign", "supplemental"] = Field(...)


class ProjectManifest(BaseModel):
    """The per-repo derived projection (immutable, closed); see the module docstring for the law.

    Identity/recipe strings are pinned non-empty (min_length=1); free-form strings
    (doc_format_spec_range, staleness_pointer, policy_path) stay loose and tighten in their
    consuming phases. `artifacts` is required but may be `[]` (R-PARTIAL: a doc-less repo).
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_by_name=True,
        validate_by_alias=True,
    )

    schema_version: PositiveInt = Field(alias="schemaVersion")  # the 1.2d migrator keys on this
    project_id: str = Field(min_length=1)
    source_repo: str = Field(min_length=1)
    ingested_from_sha: str = Field(min_length=1, alias="ingestedFromSha")  # derived (mirrors tag)
    embedding_model: str = Field(min_length=1)  # reproducibility recipe (§4 inv 1)
    dimension: PositiveInt = Field(...)
    chunker_version: str = Field(min_length=1)  # reproducibility recipe (§4 inv 1)
    doc_format_spec_range: str = Field(...)  # free-form version range (tighten in consuming phase)
    artifacts: list[ManifestArtifact] = Field(...)  # required; [] allowed (R-PARTIAL)
    staleness_pointer: str = Field(...)  # free-form freshness ref (tighten in sync phase)
    policy_path: str = Field(...)  # path to policy.yaml (tighten in 1.5)
    lance_version_tag: str = Field(min_length=1)  # the git-SHA LanceDB version tag (identity)
