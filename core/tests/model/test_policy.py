"""Unit tests for the frozen policy.yaml contract (ARCHITECTURE.md §16, Appendix A).

★ Freeze-before-fork contract. The per-project `policy.yaml` schema: a `Privacy` alphabet + a
frozen `ProjectPolicy` whose defaults are FAIL-CLOSED (absent → most-restrictive local-only; every
opt-in defaults off). Parse-don't-trust (§4) rejects bad enum values + unknown keys; the fail-SOFT
"malformed policy → most-restrictive instead of crash" fallback is the Phase-2/3 LOADER's job, not
this schema. Serialized-file dual snapshot (LESSON 4). The provider CATALOG + privacy↔provider
consistency are Phase-10-deferred (D-A11 shape-now-membership-later).
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from model.policy import (
    CURRENT_POLICY_SCHEMA_VERSION,
    FederationPolicy,
    McpPolicy,
    Privacy,
    ProjectPolicy,
    ProviderPolicy,
    SessionPolicy,
)

pytestmark = pytest.mark.unit

# Python field-name snapshot (the §2.5-seam freeze pin).
EXPECTED_POLICY_FIELDS = frozenset(
    {"schema_version", "privacy", "providers", "mcp", "federation", "sessions", "brainignore"}
)
# On-disk policy.yaml key contract — an INDEPENDENT literal (NOT derived from the field-name set),
# per LESSON 4: the on-disk key set is a SEPARATE contract. Today it coincides with the Python names
# (snake_case throughout — a user-edited YAML file, no camelCase aliases); defining it standalone
# means a future alias divergence fails this snapshot loudly instead of silently tracking a rename.
EXPECTED_POLICY_ONDISK_KEYS = frozenset(
    {"schema_version", "privacy", "providers", "mcp", "federation", "sessions", "brainignore"}
)
EXPECTED_PROVIDER_FIELDS = frozenset({"embedding", "reranker", "context", "model"})


def test_privacy_values() -> None:
    # spec(§16): the closed per-project privacy alphabet (§16 "explicit user choice local|cloud"),
    # LESSON 6 membership snapshot — drift here is a cross-track Finding.
    assert {p.value for p in Privacy} == {"local", "cloud"}


def test_policy_field_names_snapshot() -> None:
    # spec(§16): §2.5-seam freeze pin (top-level Python field names).
    assert set(ProjectPolicy.model_fields) == EXPECTED_POLICY_FIELDS


def test_policy_ondisk_key_snapshot() -> None:
    # spec(§16): the on-disk policy.yaml key contract (LESSON 4 — names==aliases today, pinned so a
    # future alias divergence fails loudly).
    assert set(ProjectPolicy().model_dump(by_alias=True)) == EXPECTED_POLICY_ONDISK_KEYS


def test_fail_closed_defaults() -> None:
    # THE safety pin (carry-forward; §16 most-restrictive default): an empty/minimal policy parses
    # to the LEAST-permissive posture — local-only, every opt-in OFF. Both the no-arg and {} paths.
    for p in (ProjectPolicy(), ProjectPolicy.model_validate({})):
        assert p.privacy is Privacy.LOCAL
        assert p.mcp.expose is False
        assert p.federation.visible is False
        assert p.sessions.consent is False
        assert p.brainignore == ()
        assert p.providers == ProviderPolicy()  # all four provider overrides default None


def test_unrecognized_privacy_rejected() -> None:
    # spec(§16): parse-don't-trust (§4) — an unknown/empty privacy value RAISES, never silently
    # coerced (a silently-coerced privacy marker is exactly the fail-open we're avoiding).
    for bad in ("public", "", "Local", "LOCAL"):
        with pytest.raises(ValidationError):
            ProjectPolicy.model_validate({"privacy": bad})


def test_frozen_and_extra_forbid() -> None:
    # frozen contract + extra="forbid" at every level (top-level AND nested sub-model).
    p = ProjectPolicy()
    with pytest.raises(ValidationError):
        p.privacy = Privacy.CLOUD  # frozen
    with pytest.raises(ValidationError):
        ProjectPolicy.model_validate({"unknown_key": "x"})  # unknown top-level key
    with pytest.raises(ValidationError):
        ProjectPolicy.model_validate({"mcp": {"expose": True, "bad": 1}})  # unknown sub-model key


def test_brainignore_is_tuple_immutable() -> None:
    # LESSON 8: a frozen-contract collection is a tuple (immutable container); LESSON 7: elements
    # strip + reject empty/whitespace-only; default is the immutable () (no mutable-default leak).
    p = ProjectPolicy.model_validate({"brainignore": ["  *.log  ", "node_modules/"]})
    assert isinstance(p.brainignore, tuple)
    assert p.brainignore == ("*.log", "node_modules/")  # element strip
    assert ProjectPolicy().brainignore == ()
    for bad in ("", "   "):
        with pytest.raises(ValidationError):
            ProjectPolicy.model_validate({"brainignore": [bad]})


def test_provider_ids_opaque_optional() -> None:
    # LESSON 2 (opaque ids: accepted as-is, never parsed) + D-A11 (catalog deferred to Phase 10 —
    # any string id is accepted now, no membership check). Optional/defaulted None; LESSON 7 strip +
    # min_length when present.
    assert set(ProviderPolicy.model_fields) == EXPECTED_PROVIDER_FIELDS
    empty = ProviderPolicy()
    assert (empty.embedding, empty.reranker, empty.context, empty.model) == (None, None, None, None)
    # an arbitrary (catalog-unknown) id is accepted now — membership lands at Phase 10.
    assert ProviderPolicy(model="some-future-model@9").model == "some-future-model@9"
    assert ProviderPolicy(embedding="  qwen3  ").embedding == "qwen3"  # strip
    for field in EXPECTED_PROVIDER_FIELDS:
        with pytest.raises(ValidationError):
            ProviderPolicy(**{field: ""})  # min_length when present


def test_nested_coercion_and_deep_frozen() -> None:
    # LESSON 8: nested sub-models coerce from dict (the YAML/MCP boundary path); deep immutability;
    # dict round-trip preserves equality.
    p = ProjectPolicy.model_validate(
        {
            "privacy": "cloud",
            "providers": {"embedding": "e", "model": "m"},
            "mcp": {"expose": True},
            "federation": {"visible": True},
            "sessions": {"consent": True},
            "brainignore": ["*.env"],
        }
    )
    assert isinstance(p.providers, ProviderPolicy)
    assert p.providers.embedding == "e" and p.mcp.expose is True
    with pytest.raises(ValidationError):
        p.providers.embedding = "x"  # deep-frozen nested element
    with pytest.raises(ValidationError):
        p.mcp.expose = False
    assert ProjectPolicy.model_validate(p.model_dump()) == p  # round-trip equality


def test_schema_version() -> None:
    # spec(§16): §5 forward-only migration consistency with manifest/registry — schema_version is a
    # PositiveInt defaulting to the current baseline; the on-disk key is snake_case `schema_version`
    # (Q4 — the pure migrate() runner takes from_version as an arg, not keyed on a name/case).
    assert ProjectPolicy().schema_version == CURRENT_POLICY_SCHEMA_VERSION
    assert "schema_version" in ProjectPolicy().model_dump(by_alias=True)
    for bad in (0, -1):
        with pytest.raises(ValidationError):
            ProjectPolicy(schema_version=bad)


def test_subpolicy_defaults_and_extra_forbid() -> None:
    # The boolean opt-in sub-models each default OFF + forbid extras (the fail-CLOSED posture per
    # section). Pins their single-field shape so an accidental field add fails here.
    assert McpPolicy().expose is False
    assert FederationPolicy().visible is False
    assert SessionPolicy().consent is False
    bad_extra: dict[str, Any] = {"x": 1}  # an unknown key — each sub-model is extra="forbid"
    with pytest.raises(ValidationError):
        McpPolicy(expose=True, **bad_extra)
    with pytest.raises(ValidationError):
        FederationPolicy(visible=True, **bad_extra)
    with pytest.raises(ValidationError):
        SessionPolicy(consent=True, **bad_extra)


def test_explicit_values_preserved() -> None:
    # Happy-path complement to the fail-CLOSED pin (ADD @Step-2.5): opt-ins actually opt IN and the
    # user's privacy CHOICE is stored. A buggy schema that ignored input and always returned the
    # fail-closed defaults would pass every other (default-state) test but FAIL here. Pinned across
    # a model_dump()→model_validate() round-trip so persistence preserves the explicit posture too.
    p = ProjectPolicy.model_validate(
        {
            "privacy": "cloud",
            "providers": {
                "embedding": "qwen3",
                "reranker": "bge",
                "context": "ctx-v1",
                "model": "gpt",
            },
            "mcp": {"expose": True},
            "federation": {"visible": True},
            "sessions": {"consent": True},
            "brainignore": ["build/"],
            "schema_version": CURRENT_POLICY_SCHEMA_VERSION,
        }
    )
    assert p.privacy is Privacy.CLOUD
    assert p.mcp.expose is True
    assert p.federation.visible is True
    assert p.sessions.consent is True
    assert p.brainignore == ("build/",)
    assert (p.providers.embedding, p.providers.reranker) == ("qwen3", "bge")
    assert (p.providers.context, p.providers.model) == ("ctx-v1", "gpt")
    assert ProjectPolicy.model_validate(p.model_dump()) == p  # explicit values survive round-trip
    # JSON-string round-trip — the real on-disk persistence path; exercises the serializer the dict
    # path skips (e.g. brainignore tuple → JSON array → tuple coercion), mirroring test_manifest.
    assert ProjectPolicy.model_validate_json(p.model_dump_json()) == p
