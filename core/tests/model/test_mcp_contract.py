"""Unit tests for the §14 MCP tool contract — INGRESS half (ARCHITECTURE.md §14, Appendix A).

★ Freeze-before-fork trust-boundary contract. Slice 1.5c1 freezes the `RetrievalScope` alphabet +
the 5 tool PARAM models (search/get_file/graph/list_projects/status) with positive-allow-list
ingress validation (LESSON 10): the `get_file` path SHAPE allow-list (the security pin), bounded
query/top_k via named constants, opaque project_id. The result/chip/provenance shapes + the
policy-denied marker + streaming are 1.5c2. Runtime canonicalize-against-the-real-root containment +
registry-scope authz + egress redaction + loopback transport are the Phase-8 boundary, NOT here.
"""

from __future__ import annotations

from typing import Any, get_args

import pytest
from pydantic import ValidationError

from model.evidence import EvidenceRef
from model.mcp_contract import (
    MAX_QUERY_LEN,
    MAX_RESPONSE_ITEMS,
    MAX_TOP_K,
    GetFileParams,
    GraphParams,
    ListProjectsParams,
    McpResult,
    McpResultItem,
    McpToolResult,
    PolicyDenied,
    RetrievalScope,
    SearchParams,
    StatusParams,
)
from model.provenance import ProvenancePacket

pytestmark = pytest.mark.unit


def _evidence_ref_kwargs() -> dict[str, Any]:
    # A valid EvidenceRef payload (the §10 chip the MCP result composes).
    return {"type": "code", "label": "auth handler", "resource_ref": "chunk-1", "confidence": 0.9}


def _provenance_kwargs() -> dict[str, Any]:
    # A valid ProvenancePacket payload (the §10 grounding record on every answer).
    return {
        "project_ids": ["proj-1"],
        "source_ids": ["src-1"],
        "citations": ["src/auth.py:10-20"],
        "commit_shas": ["deadbeef"],
        "session_ids": ["sess-1"],
        "index_freshness": "fresh",
        "confidence": 0.8,
        "drift_markers": [],
        "evidence": [_evidence_ref_kwargs()],
    }


def _result_item_kwargs() -> dict[str, Any]:
    # A valid McpResultItem payload (chip + file:line + ids).
    return {"chip": _evidence_ref_kwargs(), "file_line": "src/auth.py:10-20", "ids": ["chunk-1"]}


def _result_kwargs() -> dict[str, Any]:
    # A valid McpResult payload (one item + a provenance packet).
    return {"items": [_result_item_kwargs()], "provenance": _provenance_kwargs()}


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


# ── 1.5c2 — the result half (McpResultItem / McpResult / PolicyDenied) ──────────────────────────


def test_mcp_result_item_composes_evidence_ref() -> None:
    # spec(§14): chip + file:line + ids result element; composes the 1.3c EvidenceRef (LESSON 8
    # nested coercion from a dict); file_line/ids elements strip + reject empty (LESSON 7).
    assert set(McpResultItem.model_fields) == {"chip", "file_line", "ids"}
    item = McpResultItem.model_validate(_result_item_kwargs())
    assert isinstance(item.chip, EvidenceRef)
    assert item.chip.label == "auth handler"
    assert item.file_line == "src/auth.py:10-20"
    assert item.ids == ("chunk-1",)  # coerced to a tuple (LESSON 8)
    stripped = McpResultItem.model_validate(
        {**_result_item_kwargs(), "file_line": "  f:1  ", "ids": ["  c1  "]}
    )
    assert stripped.file_line == "f:1" and stripped.ids == ("c1",)  # LESSON 7 strip
    bad_payloads = (
        {**_result_item_kwargs(), "file_line": ""},
        {**_result_item_kwargs(), "file_line": "   "},  # whitespace-only (LESSON 7)
        {**_result_item_kwargs(), "ids": [""]},
        {**_result_item_kwargs(), "ids": ["   "]},  # whitespace-only id element
    )
    for bad in bad_payloads:
        with pytest.raises(ValidationError):
            McpResultItem.model_validate(bad)


def test_mcp_result_envelope() -> None:
    # spec(§14): result envelope = items tuple (empty-valid) + composed ProvenancePacket + a
    # truncated flag (default False). §10 composition; LESSON 8 nested coercion.
    assert set(McpResult.model_fields) == {"items", "provenance", "truncated"}
    r = McpResult.model_validate(_result_kwargs())
    assert isinstance(r.items, tuple) and isinstance(r.items[0], McpResultItem)
    assert isinstance(r.provenance, ProvenancePacket)
    assert r.truncated is False  # fail-safe default
    empty = McpResult.model_validate({"items": [], "provenance": _provenance_kwargs()})
    assert empty.items == ()  # empty-valid (an ungrounded/zero-hit answer)


def test_policy_denied_marker() -> None:
    # spec(§14): policy-denied is a returned VALUE marker, NOT a raised exception (a raise would
    # look like a tool failure, not a policy outcome). denied=Literal[True] can't pose as non-deny;
    # a tool's contract return is the union McpResult | PolicyDenied.
    assert set(PolicyDenied.model_fields) == {"denied", "reason"}
    d = PolicyDenied(reason="cloud egress blocked by policy")
    assert d.denied is True
    assert d.reason == "cloud egress blocked by policy"
    with pytest.raises(ValidationError):
        PolicyDenied.model_validate({"denied": False, "reason": "x"})  # Literal[True] rejects False
    with pytest.raises(ValidationError):
        PolicyDenied.model_validate({})  # reason required (LESSON 3 omit-each; denied defaults)
    assert set(get_args(McpToolResult)) == {McpResult, PolicyDenied}


def test_result_deep_immutable() -> None:
    # LESSON 8: deep immutability + nested parse-don't-trust. Mutating items / a nested chip field /
    # provenance raises; a bad nested element (EvidenceRef with an extra key) is rejected at parse.
    r = McpResult.model_validate(_result_kwargs())
    with pytest.raises(ValidationError):
        r.items = ()  # frozen container
    with pytest.raises(ValidationError):
        r.items[0].chip.label = "x"  # deep-frozen nested chip
    with pytest.raises(ValidationError):
        r.provenance.confidence = 0.1  # deep-frozen nested provenance
    bad_chip = {**_result_item_kwargs(), "chip": {"type": "c", "label": "l", "extra_bad": 1}}
    with pytest.raises(ValidationError):
        McpResultItem.model_validate(bad_chip)  # nested EvidenceRef extra="forbid"
    # nested ProvenancePacket parse-don't-trust: a malformed provenance (a required field omitted)
    # is rejected at parse — the §10 grounding record can't slip in half-formed (LESSON 8).
    bad_prov = {k: v for k, v in _provenance_kwargs().items() if k != "index_freshness"}
    with pytest.raises(ValidationError):
        McpResult.model_validate({"items": [_result_item_kwargs()], "provenance": bad_prov})


def test_result_json_roundtrip() -> None:
    # LESSON 8: dict + JSON-string round-trips preserve equality (the egress/persistence path —
    # tuple → array → tuple, nested models coerce back).
    r = McpResult.model_validate(
        {"items": [_result_item_kwargs()], "provenance": _provenance_kwargs(), "truncated": True}
    )
    assert McpResult.model_validate(r.model_dump()) == r
    assert McpResult.model_validate_json(r.model_dump_json()) == r


def test_response_bound_constant() -> None:
    # §14 "bound response sizes": MAX_RESPONSE_ITEMS named constant (a future loosening is a
    # visible, test-breaking change — LESSON 10 spirit). The contract ENFORCES the cap (over-bound
    # raises — defense-in-depth, like MAX_TOP_K); Phase-8.2 owns the truncation LOGIC + truncated.
    assert MAX_RESPONSE_ITEMS == 500
    over = [_result_item_kwargs()] * (MAX_RESPONSE_ITEMS + 1)
    with pytest.raises(ValidationError):
        McpResult.model_validate({"items": over, "provenance": _provenance_kwargs()})


def test_result_models_frozen_extra_forbid() -> None:
    # parse-don't-trust §4: the 3 new models frozen + extra="forbid" (tested with a VALID base
    # payload + an extra key, so the rejection is the extra key — not a missing-required error).
    d = PolicyDenied(reason="r")
    with pytest.raises(ValidationError):
        d.reason = "other"  # frozen
    payloads = (
        (McpResultItem, {**_result_item_kwargs(), "x": 1}),
        (McpResult, {"items": [], "provenance": _provenance_kwargs(), "x": 1}),
        (PolicyDenied, {"denied": True, "reason": "r", "x": 1}),
    )
    for model, payload in payloads:
        with pytest.raises(ValidationError):
            model.model_validate(payload)


def test_composed_mcpresult_provenance_immutable() -> None:
    # LESSON 8 (1.6b) — the END-TO-END closure of the 1.5c2 catch: a composed McpResult's
    # provenance.evidence is a tuple, so it can no longer be .append-mutated through the result
    # envelope (it was list[EvidenceRef] when 1.5c2 landed; 1.6b tuple-ifies ProvenancePacket).
    r = McpResult.model_validate(_result_kwargs())
    assert isinstance(r.provenance.evidence, tuple)
    with pytest.raises(AttributeError):
        r.provenance.evidence.append(object())  # type: ignore[attr-defined]  # tuple has no .append


def test_mcp_truncated_strict() -> None:
    # §14 (1.6c, Q1 uniformity): truncated is StrictBool — a lax 1/"yes"/"true"/"on" can't coerce to
    # True; a real bool is accepted. A system-set output flag, hardened uniformly (like host.ok).
    for lax in (1, 0, "yes", "true", "on", "false"):
        with pytest.raises(ValidationError):
            McpResult.model_validate({**_result_kwargs(), "truncated": lax})
    assert McpResult.model_validate({**_result_kwargs(), "truncated": True}).truncated is True
