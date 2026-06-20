"""The frozen per-project policy.yaml contract (ARCHITECTURE.md §16, Appendix A).

★ Freeze-before-fork contract — the privacy/safety posture every later phase reads (Phase-2 ingest:
privacy + .brainignore · Phase-6 federation visibility · Phase-8 MCP boundary · Phase-9 session
consent · Phase-10 provider selection). Its defaults are FAIL-CLOSED: an absent/minimal policy
parses to the MOST-RESTRICTIVE posture — `privacy=local`, every opt-in (`mcp.expose`,
`federation.visible`, `sessions.consent`) OFF, no provider override, no `.brainignore` entries.

This is a STRICT parser (parse-don't-trust, §4): a bad enum value or an unknown key raises rather
than being silently coerced — a silently-accepted bad privacy marker is exactly the fail-open we
reject. The fail-SOFT "malformed policy → most-restrictive instead of crash" fallback is the
Phase-2/3 LOADER's job (startup-reconcile), NOT this frozen schema (mirrors the manifest/registry
lenient-read-at-loader / strict-schema split, LESSON 4).

On-disk keys are snake_case throughout (a user-edited YAML file — no camelCase aliases, unlike the
Brain-written manifest.json). The Phase-2/3 loader keys the forward migrator off `schema_version`
(the pure `migrate()` in migrations.py takes `from_version` as an int arg, not a fixed key name).

Provider CATALOG membership + the privacy↔provider (local|cloud) consistency validator are
Phase-10-deferred (D-A11 — the catalog doesn't exist until the bake-off): the shape is frozen now,
ids are opaque (LESSON 2), membership lands additively at first consumption.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, PositiveInt

from _types import IdentityStr

# Policy on-disk format baseline — parallels CURRENT_MANIFEST/REGISTRY_SCHEMA_VERSION (migrations.py
# both baseline at v1). The Phase-2/3 loader keys the forward migrator off this.
CURRENT_POLICY_SCHEMA_VERSION = 1


class Privacy(StrEnum):
    """The closed per-project privacy alphabet (§16 — "explicit user choice local|cloud").

    A NAMED domain alphabet (read across providers/federation/egress seams), hence a StrEnum with a
    membership snapshot (LESSON 6), not an inline Literal.
    """

    LOCAL = "local"
    CLOUD = "cloud"


class ProviderPolicy(BaseModel):
    """Per-role provider SELECTION (§16) — opaque optional ids; absent ⇒ the host default.

    Shape-only freeze: the provider CATALOG + the privacy↔provider consistency validator are
    Phase-10-deferred (D-A11). Ids are opaque (LESSON 2) — accepted as-is, only min-length-checked
    when present, never parsed for structure or checked against a catalog here.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    embedding: IdentityStr | None = None
    reranker: IdentityStr | None = None
    context: IdentityStr | None = None
    model: IdentityStr | None = None


class McpPolicy(BaseModel):
    """MCP-boundary exposure (§14/§16) — fail-CLOSED: not exposed unless explicitly opted in.

    Minimal Phase-1 shape; the richer boundary-filter fields land at Phase 8 (additive).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    expose: bool = False


class FederationPolicy(BaseModel):
    """Cross-repo federation visibility (§16) — fail-CLOSED: hidden unless explicitly opted in."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    visible: bool = False


class SessionPolicy(BaseModel):
    """Session-capture consent (§16) — fail-CLOSED: no consent unless explicitly opted in."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    consent: bool = False


class ProjectPolicy(BaseModel):
    """The frozen per-project policy.yaml schema (§16) — fail-CLOSED by default (see module doc).

    Every section is optional with a most-restrictive default, so an empty `policy.yaml` (or `{}`)
    parses to the least-permissive posture. Nested sub-models coerce from `dict` (the YAML/MCP
    boundary path) and are deep-frozen (LESSON 8); collections are immutable tuples (LESSON 8) with
    strip+min_length elements (LESSON 7).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: PositiveInt = CURRENT_POLICY_SCHEMA_VERSION
    privacy: Privacy = Privacy.LOCAL
    providers: ProviderPolicy = Field(default_factory=ProviderPolicy)
    mcp: McpPolicy = Field(default_factory=McpPolicy)
    federation: FederationPolicy = Field(default_factory=FederationPolicy)
    sessions: SessionPolicy = Field(default_factory=SessionPolicy)
    brainignore: tuple[IdentityStr, ...] = ()
