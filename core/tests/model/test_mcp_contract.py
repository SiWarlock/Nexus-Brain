"""Unit tests for the §14 MCP tool contract — INGRESS half (ARCHITECTURE.md §14, Appendix A).

★ Freeze-before-fork trust-boundary contract. Slice 1.5c1 freezes the `RetrievalScope` alphabet +
the 5 tool PARAM models (search/get_file/graph/list_projects/status) with positive-allow-list
ingress validation (LESSON 10): the `get_file` path SHAPE allow-list (the security pin), bounded
query/top_k via named constants, opaque project_id. The result/chip/provenance shapes + the
policy-denied marker + streaming are 1.5c2. Runtime canonicalize-against-the-real-root containment +
registry-scope authz + egress redaction + loopback transport are the Phase-8 boundary, NOT here.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from model.mcp_contract import (
    MAX_QUERY_LEN,
    MAX_TOP_K,
    GetFileParams,
    GraphParams,
    ListProjectsParams,
    RetrievalScope,
    SearchParams,
    StatusParams,
)

pytestmark = pytest.mark.unit


def test_retrieval_scope_values() -> None:
    # spec(§14): closed BREADTH alphabet (single project vs federated portfolio); project_id is a
    # SEPARATE scoping param. LESSON 6 membership snapshot — drift is a cross-track Finding.
    assert {s.value for s in RetrievalScope} == {"project", "portfolio"}


def test_param_field_name_snapshots() -> None:
    # spec(§14): §2.5-seam freeze — each tool's param field-name set.
    assert set(SearchParams.model_fields) == {"query", "scope", "top_k", "project_id"}
    assert set(GetFileParams.model_fields) == {"path", "project_id"}
    assert set(GraphParams.model_fields) == {"query", "kind", "project_id"}
    assert set(ListProjectsParams.model_fields) == set()
    assert set(StatusParams.model_fields) == {"project_id"}


def test_get_file_path_allowlist() -> None:
    # THE LESSON 10 security pin (§14 ingress): a strict ASCII POSITIVE allow-list on the get_file
    # path SHAPE + a bypass corpus (mirrors 1.4c resolve_codegraph_dir). Accepts a bounded relative
    # ASCII path; rejects absolute, drive, `..` traversal (incl. mid-path), the fullwidth-solidus
    # homoglyph (U+FF0F), NON-ASCII (deliberately — smallest attack surface; widening to intl
    # filenames is a Phase-8 additive option w/ NFC-normalize), NUL/control, backslash, `~`/`$`,
    # whitespace, empty. Canonicalize-against-real-root CONTAINMENT is deferred to Phase-8.2.
    rejected = (
        "/etc/passwd",  # absolute
        "/leading",  # leading slash
        "../x",  # traversal
        "a/../../b",  # traversal
        "a/../b",  # mid-path traversal
        "..",  # bare traversal
        "C:\\x",  # drive + backslash
        "C:foo",  # drive colon
        "a\\b",  # backslash separator
        "x\x00y",  # NUL
        "\x01\x02bad",  # control chars
        "a／b",  # U+FF0F fullwidth-solidus homoglyph
        "пример.txt",  # non-ASCII — deliberately rejected at the frozen boundary (Phase-8 widens)
        "~/secrets",  # tilde expansion
        "$HOME/x",  # env-var expansion
        "a b.py",  # whitespace
        "",  # empty
        "   ",  # whitespace-only
    )
    for bad in rejected:
        with pytest.raises(ValidationError):
            GetFileParams(path=bad, project_id="proj-1")
    for good in ("src/app.py", "a/b/c.py", "module_name/file-1.py"):
        assert GetFileParams(path=good, project_id="proj-1").path == good
    # Non-canonical but shape-valid forms are ACCEPTED here (not traversal vectors) and are
    # normalized + contained at Phase-8.2 (realpath-contain on the resolved path). Pinned so a
    # future shape-layer tightening is a visible, test-breaking change, not a silent semantic drift.
    for noncanonical in ("a/./b", "a//b", "a/", ".", "...."):
        assert GetFileParams(path=noncanonical, project_id="proj-1").path == noncanonical


def test_search_params_bounds() -> None:
    # §14 "bound query/k sizes": valid in-range constructs; empty/over-len query + 0/neg/over-cap
    # top_k raise (no silent clamp); scope is required; project_id optional.
    ok = SearchParams(query="auth flow", scope=RetrievalScope.PROJECT, top_k=5)
    assert ok.top_k == 5 and ok.project_id is None
    with pytest.raises(ValidationError):
        SearchParams(query="", scope=RetrievalScope.PROJECT)  # empty query
    with pytest.raises(ValidationError):  # over-cap query
        SearchParams(query="x" * (MAX_QUERY_LEN + 1), scope=RetrievalScope.PROJECT)
    for bad_k in (0, -1, MAX_TOP_K + 1):
        with pytest.raises(ValidationError):
            SearchParams(query="q", scope=RetrievalScope.PROJECT, top_k=bad_k)
    assert SearchParams(query="q", scope=RetrievalScope.PROJECT, top_k=MAX_TOP_K).top_k == MAX_TOP_K
    with pytest.raises(ValidationError):
        SearchParams.model_validate({"query": "q"})  # scope required
    with pytest.raises(ValidationError):
        SearchParams.model_validate({"scope": "project"})  # query required (LESSON 3 omit-each)


def test_get_file_requires_project_id() -> None:
    # get_file is project-scoped — project_id required (omitting raises).
    with pytest.raises(ValidationError):
        GetFileParams.model_validate({"path": "src/app.py"})
    assert GetFileParams(path="src/app.py", project_id="proj-1").project_id == "proj-1"


def test_graph_params() -> None:
    # §14 graph tool: bounded query; kind optional bounded str (Phase-8 maps to CodeGraphQueryKind —
    # model/ must NOT import ports/); project_id required.
    g = GraphParams(query="MyClass", kind="callers", project_id="proj-1")
    assert g.kind == "callers"
    assert GraphParams(query="MyClass", project_id="proj-1").kind is None  # kind optional
    with pytest.raises(ValidationError):
        GraphParams(query="", project_id="proj-1")  # query bounded non-empty
    with pytest.raises(ValidationError):
        GraphParams.model_validate({"query": "x"})  # project_id required
    with pytest.raises(ValidationError):
        GraphParams.model_validate({"project_id": "p"})  # query required (LESSON 3 omit-each)


def test_list_projects_and_status_params() -> None:
    # §14 tool-set completeness: list_projects takes no params; status.project_id optional.
    assert isinstance(ListProjectsParams(), ListProjectsParams)  # no required params
    assert StatusParams().project_id is None
    assert StatusParams(project_id="proj-1").project_id == "proj-1"


def test_frozen_and_extra_forbid() -> None:
    # parse-don't-trust §4: every param model frozen (mutation raises) + an unknown key rejected by
    # extra="forbid". The extra-key payloads are otherwise VALID (all required present) so the
    # rejection is the extra key itself — NOT a missing-required-field error masquerading as it.
    s = SearchParams(query="q", scope=RetrievalScope.PROJECT)
    with pytest.raises(ValidationError):
        s.query = "other"  # frozen
    models_with_valid_plus_extra = (
        (SearchParams, {"query": "q", "scope": "project", "x": 1}),
        (GetFileParams, {"path": "src/app.py", "project_id": "p", "x": 1}),
        (GraphParams, {"query": "q", "project_id": "p", "x": 1}),
        (ListProjectsParams, {"x": 1}),  # no required fields — the extra key is the only trigger
        (StatusParams, {"x": 1}),
    )
    for model, payload in models_with_valid_plus_extra:
        with pytest.raises(ValidationError):
            model.model_validate(payload)


def test_bounds_constants() -> None:
    # LESSON 10 spirit: a future loosening of an ingress bound must be a visible, breaking change.
    assert MAX_TOP_K == 100
    assert MAX_QUERY_LEN == 4096
