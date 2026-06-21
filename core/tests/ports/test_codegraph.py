"""Unit tests for the CodeGraphPort read-only seam (ARCHITECTURE.md §7, Appendix A:220).

★ Freeze-before-fork behavioral port over the external CodeGraph (=1.0.1). Bakes the Phase-0
spike-0.2 / D-A4 corrections: schema_versions >= 5 (NOT =1); the `search` kind → CLI `query`;
CODEGRAPH_DIR single-segment containment. Freezes the Protocol + enum + helpers + FakeCodeGraph;
the real CLI shell-out adapter is Phase-3 (spike Risk-3/4). Collection fields use tuple (LESSON 8).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from ports.codegraph import (
    CodeGraphPort,
    CodeGraphQueryKind,
    CodeGraphResult,
    CodeGraphSchemaError,
    assert_schema_compatible,
    resolve_codegraph_dir,
)
from testing.fakes import FakeCodeGraph

pytestmark = pytest.mark.unit


def test_codegraph_protocol_conformance() -> None:
    # LESSON 1: the Fake structurally satisfies the port (runtime_checkable).
    assert isinstance(FakeCodeGraph(), CodeGraphPort)


def test_query_kind_values() -> None:
    # LESSON 6: the closed query-kind set is a frozen contract (§7/Appendix-A:220).
    assert {k.value for k in CodeGraphQueryKind} == {
        "explore",
        "node",
        "callers",
        "callees",
        "search",
    }


def test_query_kind_cli_mapping() -> None:
    # spike-0.2 Risk-2: `search` → the 1.0.1 CLI `query` verb (no `codegraph search` exists);
    # the other four map to their own verb.
    assert CodeGraphQueryKind.SEARCH.cli_command == "query"
    assert CodeGraphQueryKind.EXPLORE.cli_command == "explore"
    assert CodeGraphQueryKind.NODE.cli_command == "node"
    assert CodeGraphQueryKind.CALLERS.cli_command == "callers"
    assert CodeGraphQueryKind.CALLEES.cli_command == "callees"


def test_schema_gate() -> None:
    # spike-0.2 Risk-1: assert MAX(schema_versions.version) >= 5 — forward-safe (6+ ok), NOT = 1.
    assert_schema_compatible(5)
    assert_schema_compatible(6)
    for bad in (4, 1, 0):
        with pytest.raises(CodeGraphSchemaError):
            assert_schema_compatible(bad)


def test_codegraph_dir_default() -> None:
    # spike §5: no/empty CODEGRAPH_DIR → the `.codegraph` default.
    assert resolve_codegraph_dir(None) == ".codegraph"
    assert resolve_codegraph_dir("") == ".codegraph"
    assert resolve_codegraph_dir("   ") == ".codegraph"


def test_codegraph_dir_valid_override() -> None:
    # spike §5: a valid single path segment is accepted (surrounding whitespace stripped).
    assert resolve_codegraph_dir("cg_index") == "cg_index"
    assert resolve_codegraph_dir("  cg_index  ") == "cg_index"


def test_codegraph_dir_invalid_fallback() -> None:
    # spike §5 + §14 allow-list: anything that isn't a single SAFE path segment falls back to the
    # default — separators, `.`/`..`, absolute/drive paths, leading-dash (CLI-flag injection), null
    # byte, unicode separator (U+FF0F), `~`/`$`/glob, and whitespace.
    bad_values = (
        "a/b",
        "a\\b",
        ".",
        "..",
        "/abs/path",
        "../escape",
        "./rel",
        "-rf",
        "--output=x",
        "a\x00b",
        "C:",
        "C:foo",
        "a／b",
        "~",
        "$HOME",
        "*",
        "a b",
        "a\nb",
    )
    for bad in bad_values:
        assert resolve_codegraph_dir(bad) == ".codegraph"


def test_codegraph_result_snapshot() -> None:
    # spec(§7): §2.5-seam ★ freeze — CodeGraphResult shape; collection field is a tuple (LESSON 8);
    # the structured per-kind parse is Phase-3-deferred (spike Risk-4).
    assert set(CodeGraphResult.model_fields) == {"kind", "symbols"}
    r = CodeGraphResult(kind=CodeGraphQueryKind.NODE, symbols=("Foo", "Bar"))
    assert isinstance(r.symbols, tuple)
    # an empty result (no symbols found — the empty-index case) is valid.
    assert CodeGraphResult(kind=CodeGraphQueryKind.NODE, symbols=()).symbols == ()
    # extra kwarg rejected (extra="forbid") — non-empty symbols so the ONLY trigger is `extra`.
    bad_extra: dict[str, Any] = {"kind": CodeGraphQueryKind.NODE, "symbols": ("Foo",), "extra": 1}
    with pytest.raises(ValidationError):
        CodeGraphResult(**bad_extra)
    with pytest.raises(ValidationError):
        r.symbols = ()  # frozen


def test_query_contract() -> None:
    # spec(§7): query(kind, sym) → a CodeGraphResult tagged with the kind.
    result = FakeCodeGraph().query(CodeGraphQueryKind.CALLERS, "MyFunc")
    assert isinstance(result, CodeGraphResult)
    assert result.kind is CodeGraphQueryKind.CALLERS


def test_fakecodegraph_fidelity() -> None:
    # LESSON 1: deterministic canned results (same input → same result); configurable per kind.
    fcg = FakeCodeGraph()
    assert fcg.query(CodeGraphQueryKind.NODE, "Foo") == fcg.query(CodeGraphQueryKind.NODE, "Foo")
    # the echo-default tags the result with the requested kind, for every kind.
    for kind in CodeGraphQueryKind:
        assert fcg.query(kind, "Sym").kind is kind
    canned = CodeGraphResult(kind=CodeGraphQueryKind.SEARCH, symbols=("A", "B"))
    fcg2 = FakeCodeGraph(results={CodeGraphQueryKind.SEARCH: canned})
    assert fcg2.query(CodeGraphQueryKind.SEARCH, "anything") == canned


def test_no_hardcoded_codegraph_path() -> None:
    # forbidden-rule 5 / D-27: resolve via CODEGRAPH_DIR (no hardcoded `.codegraph/` literal); no
    # references to the deleted MCP tools (the trace/context graph tools).
    src = Path(__file__).resolve().parents[2].joinpath("ports", "codegraph.py").read_text()
    assert ".codegraph/" not in src
    assert "codegraph_trace" not in src
    assert "codegraph_context" not in src


def test_codegraph_result_strip_identity() -> None:
    # LESSON 7: symbol tuple elements strip + reject empty/whitespace.
    for bad in ("", "   "):
        with pytest.raises(ValidationError):
            CodeGraphResult(kind=CodeGraphQueryKind.NODE, symbols=(bad,))
    stripped = CodeGraphResult(kind=CodeGraphQueryKind.NODE, symbols=("  Foo  ",))
    assert stripped.symbols == ("Foo",)
