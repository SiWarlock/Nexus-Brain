"""The §14 MCP tool contract — INGRESS half (ARCHITECTURE.md §14, Appendix A).

★ Freeze-before-fork trust-boundary contract. Slice 1.5c1 freezes the `RetrievalScope` alphabet +
the 5 tool PARAM models (search / get_file / graph / list_projects / status) with positive
allow-list ingress validation (LESSON 10). The result/chip/provenance shapes + the policy-denied
marker + streaming are 1.5c2 (this file extends).

This is the EXTERNAL untrusted-caller boundary (§14 — the loopback token defends against other-uid
processes + browser pages), so ingress is validated by POSITIVE allow-lists, never deny-lists
(LESSON 10): the `get_file` path SHAPE allow-list + bounded `query`/`top_k` via named constants.
Runtime execution is NOT here — the canonicalize-against-the-REAL-project-root CONTAINMENT,
registry-scope authorization, egress redaction, and loopback-token transport are the Phase-8
boundary (8.1 builds the FastMCP tools from these models; 8.2 enforces containment + authz).
The un-allow-listable CodeGraph query/symbol args are argv-hardened at Phase 4.2 (D-A14); here they
are bounded strings (the contract bounds the input shape; runtime execution-containment is later).
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints

# Ingress bounds (LESSON 10 / §14 "bound query/k sizes") — named so a future LOOSENING is a visible,
# test-breaking change (test_bounds_constants pins them). Tightening a frozen bound is breaking;
# loosening is additive — so these start conservative.
MAX_TOP_K = 100
MAX_QUERY_LEN = 4096

# LESSON 7: identity strings strip surrounding whitespace + reject empty/whitespace-only.
# LESSON 2: project_id / graph kind are OPAQUE — carried as min-length strings, never parsed.
_StrippedStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
# §14 bound query (LESSON 10): non-empty (stripped) + capped length.
_BoundedQuery = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_QUERY_LEN)
]

# §14 ingress ALLOW-LIST for the get_file path SHAPE — a STRICT ASCII positive charset (LESSON 10,
# mirroring 1.4c resolve_codegraph_dir). Everything not explicitly permitted is rejected.
_SAFE_RELPATH_RE = re.compile(r"[A-Za-z0-9._/-]+")


def _validate_get_file_path(value: str) -> str:
    """Positive-allow-list SHAPE validation for a get_file path (§14 ingress, LESSON 10).

    Accepts a bounded RELATIVE ASCII path; REJECTS (raises — parse-don't-trust, §4): empty / blank,
    anything outside `[A-Za-z0-9._/-]` (so NUL/control chars, backslash, drive `:`, the fullwidth
    solidus U+FF0F and every other unicode separator/homoglyph, `~`/`$`/glob, whitespace, AND all
    non-ASCII), an absolute path (leading `/`), and any `..` traversal segment (incl. mid-path).

    Non-ASCII is DELIBERATELY rejected at this frozen external boundary — the strictest allow-list
    is the smallest attack surface (eliminates the unicode-normalization / homoglyph / bidi residual
    class). Widening to international filenames is a Phase-8 ADDITIVE option (NFC-normalize +
    re-validate before the runtime containment check) — loosening a frozen allow-list is safe;
    tightening it is breaking. The canonicalize-against-the-REAL-root CONTAINMENT is deferred to
    Phase 8.2 (it needs the resolved root, unavailable at this frozen-contract layer).
    """
    if not value or _SAFE_RELPATH_RE.fullmatch(value) is None:
        raise ValueError("get_file path must be a bounded relative ASCII path ([A-Za-z0-9._/-])")
    if value.startswith("/"):
        raise ValueError("get_file path must be relative, not absolute")
    if ".." in value.split("/"):
        raise ValueError("get_file path must not contain '..' traversal segments")
    return value


_GetFilePath = Annotated[str, AfterValidator(_validate_get_file_path)]


class RetrievalScope(StrEnum):
    """The closed retrieval-BREADTH alphabet (§14) — single project vs federated portfolio.

    A NAMED domain alphabet (LESSON 6, membership snapshot). `project_id` is a SEPARATE scoping
    param, not a member here. Our call (not externally owned); wideable additively (StrEnum ⊂ str).
    """

    PROJECT = "project"
    PORTFOLIO = "portfolio"


class SearchParams(BaseModel):
    """`search` tool params — bounded query + breadth scope + capped top_k (§14)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    query: _BoundedQuery
    scope: RetrievalScope
    top_k: Annotated[int, Field(ge=1, le=MAX_TOP_K)] = 10
    project_id: _StrippedStr | None = None


class GetFileParams(BaseModel):
    """`get_file` tool params — the LESSON-10 path allow-list + required project scope (§14)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    path: _GetFilePath
    project_id: _StrippedStr


class GraphParams(BaseModel):
    """`graph` tool params — bounded query + optional bounded kind + required project scope (§14).

    `kind` is a bounded opaque string, NOT a `ports.CodeGraphQueryKind` (model/ must not import
    ports/ — §2.5 DAG); Phase-8.1 maps it to `CodeGraphQueryKind`. Default `None` ⇒ Phase-8
    picks the default query kind.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    query: _BoundedQuery
    kind: _StrippedStr | None = None
    project_id: _StrippedStr


class ListProjectsParams(BaseModel):
    """`list_projects` tool params — none (lists the registry); extra="forbid" rejects any (§14)."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class StatusParams(BaseModel):
    """`status` tool params — optional project scope (global or per-project status) (§14)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    project_id: _StrippedStr | None = None
