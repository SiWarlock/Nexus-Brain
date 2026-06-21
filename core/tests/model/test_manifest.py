"""Unit tests for the frozen ProjectManifest + ManifestArtifact contracts (§5, Appendix A)."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from model.manifest import ManifestArtifact, ProjectManifest

pytestmark = pytest.mark.unit

# Python snake-case field-name snapshots (the freeze pins).
EXPECTED_MANIFEST_FIELDS = frozenset(
    {
        "schema_version",
        "project_id",
        "source_repo",
        "ingested_from_sha",
        "embedding_model",
        "dimension",
        "chunker_version",
        "doc_format_spec_range",
        "artifacts",
        "staleness_pointer",
        "policy_path",
        "lance_version_tag",
    }
)
EXPECTED_ARTIFACT_FIELDS = frozenset({"path", "content_hash", "doc_type", "producer", "ownership"})
# The on-disk .project-brain/manifest.json key contract (camelCase only for the two
# aliased fields; the rest stay snake_case — per DATA_MODEL.md line 40).
EXPECTED_MANIFEST_JSON_KEYS = frozenset(
    {
        "schemaVersion",
        "project_id",
        "source_repo",
        "ingestedFromSha",
        "embedding_model",
        "dimension",
        "chunker_version",
        "doc_format_spec_range",
        "artifacts",
        "staleness_pointer",
        "policy_path",
        "lance_version_tag",
    }
)
# Identity strings pinned non-empty (min_length=1); free-form strings deferred (Q3/Q4).
# chunker_version is part of the §4-inv-1 reproducibility recipe (parallel to embedding_model).
MANIFEST_IDENTITY_FIELDS = (
    "project_id",
    "source_repo",
    "ingested_from_sha",
    "embedding_model",
    "lance_version_tag",
    "chunker_version",
)
ARTIFACT_IDENTITY_FIELDS = ("path", "content_hash")


def _valid_artifact_kwargs() -> dict[str, Any]:
    # Any: heterogeneous kwargs unpacked into the typed model; negative tests omit/override.
    return {
        "path": "docs/architecture.md",
        "content_hash": "sha256:artabc",
        "doc_type": "architecture",
        "producer": "human",
        "ownership": "owned",
    }


def _valid_manifest_kwargs() -> dict[str, Any]:
    # Any: heterogeneous kwargs unpacked into the typed model; negative tests omit/override.
    return {
        "schema_version": 1,
        "project_id": "proj-abc",
        "source_repo": "git@github.com:acme/repo.git",
        "ingested_from_sha": "deadbeefcafe",
        "embedding_model": "qwen3-embedding-4b",
        "dimension": 2560,
        "chunker_version": "code-hier@1",
        "doc_format_spec_range": ">=1.0,<2.0",
        "artifacts": [ManifestArtifact(**_valid_artifact_kwargs())],
        "staleness_pointer": "HEAD",
        "policy_path": ".project-brain/policy.yaml",
        "lance_version_tag": "deadbeefcafe",
    }


def test_manifest_schema_snapshot() -> None:
    # spec(§5): §2.5-seam freeze pin (Python field names).
    assert set(ProjectManifest.model_fields) == EXPECTED_MANIFEST_FIELDS


def test_artifact_schema_snapshot() -> None:
    # spec(§5): §2.5-seam freeze pin (artifact row).
    assert set(ManifestArtifact.model_fields) == EXPECTED_ARTIFACT_FIELDS


def test_manifest_json_keys_camelcase() -> None:
    # spec(§5): the on-disk .project-brain/manifest.json key contract (camelCase for the two
    # aliased fields, snake for the rest) — the format other tools/versions read.
    m = ProjectManifest(**_valid_manifest_kwargs())
    assert set(m.model_dump(by_alias=True)) == EXPECTED_MANIFEST_JSON_KEYS


def test_manifest_valid_construction() -> None:
    # spec(§5): happy-path shape, incl. nested artifact validation.
    m = ProjectManifest(**_valid_manifest_kwargs())
    assert m.project_id == "proj-abc"
    assert m.schema_version == 1
    assert len(m.artifacts) == 1
    assert m.artifacts[0].path == "docs/architecture.md"
    assert m.artifacts[0].ownership == "owned"


def test_manifest_rejects_extra_field() -> None:
    # spec(§5): §4 parse-don't-trust (extra="forbid").
    kwargs = _valid_manifest_kwargs()
    kwargs["unexpected"] = "x"
    with pytest.raises(ValidationError):
        ProjectManifest(**kwargs)


def test_artifact_rejects_extra_field() -> None:
    # spec(§5): §4 parse-don't-trust (extra="forbid").
    kwargs = _valid_artifact_kwargs()
    kwargs["unexpected"] = "x"
    with pytest.raises(ValidationError):
        ManifestArtifact(**kwargs)


def test_manifest_is_frozen() -> None:
    # spec(§5): a serialized projection is immutable (frozen=True).
    m = ProjectManifest(**_valid_manifest_kwargs())
    with pytest.raises(ValidationError):
        m.project_id = "mutated"


def test_artifact_is_frozen() -> None:
    # spec(§5): immutable artifact row (frozen=True).
    a = ManifestArtifact(**_valid_artifact_kwargs())
    with pytest.raises(ValidationError):
        a.path = "mutated"


def test_manifest_all_required() -> None:
    # spec(§5): every field required (LESSONS §3 omit-each; artifacts required but [] allowed).
    for name in EXPECTED_MANIFEST_FIELDS:
        kwargs = _valid_manifest_kwargs()
        del kwargs[name]
        with pytest.raises(ValidationError):
            ProjectManifest(**kwargs)


def test_artifact_all_required() -> None:
    # spec(§5): every artifact field required (LESSONS §3 omit-each guard).
    for name in EXPECTED_ARTIFACT_FIELDS:
        kwargs = _valid_artifact_kwargs()
        del kwargs[name]
        with pytest.raises(ValidationError):
            ManifestArtifact(**kwargs)


def test_manifest_roundtrip() -> None:
    # spec(§5): on-disk round-trip stability — dump to the camelCase JSON contract, reload.
    m = ProjectManifest(**_valid_manifest_kwargs())
    assert ProjectManifest.model_validate_json(m.model_dump_json(by_alias=True)) == m


def test_manifest_identity_min_length() -> None:
    # spec(§5): terminal identity strings rejected when empty (min_length=1).
    for field in MANIFEST_IDENTITY_FIELDS:
        kwargs = _valid_manifest_kwargs()
        kwargs[field] = ""
        with pytest.raises(ValidationError):
            ProjectManifest(**kwargs)


def test_artifact_identity_min_length() -> None:
    # spec(§5): artifact path + content_hash rejected when empty (min_length=1).
    for field in ARTIFACT_IDENTITY_FIELDS:
        kwargs = _valid_artifact_kwargs()
        kwargs[field] = ""
        with pytest.raises(ValidationError):
            ManifestArtifact(**kwargs)


def test_manifest_accepts_empty_artifacts() -> None:
    # spec(§5): R-PARTIAL — a doc-less repo has zero artifacts; [] coerces to () (valid).
    kwargs = _valid_manifest_kwargs()
    kwargs["artifacts"] = []
    m = ProjectManifest(**kwargs)
    assert m.artifacts == ()


def test_manifest_artifacts_tuple() -> None:
    # LESSON 8 (1.6b): artifacts is an immutable tuple — a list input coerces; .append() raises
    # (a "frozen" manifest's artifact list can't be mutated in place).
    m = ProjectManifest(**_valid_manifest_kwargs())  # _valid passes a list -> must coerce to tuple
    assert isinstance(m.artifacts, tuple)
    assert isinstance(m.artifacts[0], ManifestArtifact)
    with pytest.raises(AttributeError):
        m.artifacts.append(m.artifacts[0])  # type: ignore[attr-defined]  # tuple has no .append


def test_artifact_ownership_closed_set() -> None:
    # spec(§5): closed-set integrity for artifact ownership (Literal owned|foreign|supplemental).
    kwargs = _valid_artifact_kwargs()
    kwargs["ownership"] = "mine"
    with pytest.raises(ValidationError):
        ManifestArtifact(**kwargs)


def test_manifest_validates_by_alias_kwargs() -> None:
    # spec(§5): the writer-from-parsed-camelCase-dict path — construct via the camelCase ALIAS
    # kwarg names; validate_by_alias maps them onto the Python attributes.
    kwargs = _valid_manifest_kwargs()
    kwargs["schemaVersion"] = kwargs.pop("schema_version")
    kwargs["ingestedFromSha"] = kwargs.pop("ingested_from_sha")
    m = ProjectManifest(**kwargs)
    assert m.schema_version == 1
    assert m.ingested_from_sha == "deadbeefcafe"


def test_manifest_lenient_read_accepts_snake_or_camel_aliased_keys() -> None:
    # spec(§5): lenient reader / strict writer. validate_by_name means a manifest.json carrying
    # the snake key ("schema_version") for an aliased field is STILL accepted on read, not only
    # the canonical camelCase. STRICT on-disk key-shape rejection (wrong-key / duplicate-key) is
    # owned by the 1.2d migrator / startup-reconcile loader, NOT this frozen model — documenting
    # the intentional seam.
    kwargs = _valid_manifest_kwargs()
    kwargs["artifacts"] = []  # avoid a nested model instance inside a model_validate dict
    assert ProjectManifest.model_validate(kwargs).schema_version == 1  # snake keys accepted
    camel = dict(kwargs)
    camel["schemaVersion"] = camel.pop("schema_version")
    camel["ingestedFromSha"] = camel.pop("ingested_from_sha")
    assert ProjectManifest.model_validate(camel).schema_version == 1  # camelCase keys accepted
