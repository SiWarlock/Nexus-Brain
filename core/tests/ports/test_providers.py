"""Unit tests for the 4 provider ports (ARCHITECTURE.md §7, §16, Appendix A:219).

★ Freeze-before-fork behavioral ports (LESSON 1): `@runtime_checkable` Protocols + deterministic
`Fake*` doubles. The Protocols carry no field-snapshot (behavioral); the frozen RESULT types
(`RerankResult`/`GenerateResult`/`Citation`) DO — they cross into retrieval/grounding (spec(§7)).
Real adapters are non-deterministic → eval-tested, never here; this slice freezes the seam + Fakes.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from ports.providers import (
    Citation,
    ContextStrategy,
    EmbeddingProvider,
    GenerateResult,
    ModelProvider,
    Reranker,
    RerankResult,
)
from testing.fakes import (
    FakeContextStrategy,
    FakeEmbeddingProvider,
    FakeModelProvider,
    FakeReranker,
)

pytestmark = pytest.mark.unit


def test_provider_protocol_conformance() -> None:
    # LESSON 1: each Fake structurally satisfies its Protocol (runtime_checkable). NOTE:
    # runtime_checkable verifies attribute/method PRESENCE only — not signatures or descriptor type
    # (a @property and a plain attr both pass) — so the full behavioral contract is pinned by the
    # per-port tests below, not by isinstance alone.
    assert isinstance(FakeEmbeddingProvider(), EmbeddingProvider)
    assert isinstance(FakeReranker(), Reranker)
    assert isinstance(FakeContextStrategy(), ContextStrategy)
    assert isinstance(FakeModelProvider(), ModelProvider)


def test_embedding_provider_contract() -> None:
    # spec(§7/§16): embed(batch) → one vector per input, each of length `dimension`; the
    # dimension/model_version identity is exposed (dimension must agree with StoreVersionStamp).
    emb = FakeEmbeddingProvider(dimension=8)
    texts = ["alpha", "beta", "gamma"]
    vectors = emb.embed(texts)
    assert len(vectors) == len(texts)
    assert all(len(v) == emb.dimension for v in vectors)
    assert all(isinstance(x, float) for v in vectors for x in v)
    assert isinstance(emb.dimension, int)
    assert isinstance(emb.model_version, str) and emb.model_version != ""


def test_fake_embedding_deterministic() -> None:
    # LESSON 1: a non-deterministic fake breaks the eval/test seam — same input → identical vector.
    emb = FakeEmbeddingProvider(dimension=8)
    assert emb.embed(["x"]) == emb.embed(["x"])
    assert FakeEmbeddingProvider(dimension=8).embed(["x", "y"]) == emb.embed(["x", "y"])


def test_reranker_contract() -> None:
    # spec(§7): rerank → list[RerankResult] by index, scored, sorted desc, len ≤ input.
    rr = FakeReranker()
    docs = ["doc a", "doc b", "doc c", "doc d"]
    results = rr.rerank("query", docs)
    assert all(isinstance(r, RerankResult) for r in results)
    assert len(results) <= len(docs)
    assert {r.index for r in results} <= set(range(len(docs)))
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)


def test_rerank_result_snapshot() -> None:
    # spec(§7): §2.5-seam ★ freeze — RerankResult shape + frozen/extra-forbid.
    assert set(RerankResult.model_fields) == {"index", "score"}
    bad: dict[str, Any] = {"index": 0, "score": 1.0, "extra": 1}
    with pytest.raises(ValidationError):
        RerankResult(**bad)
    r = RerankResult(index=0, score=1.0)
    with pytest.raises(ValidationError):
        r.score = 2.0
    # a NaN/±inf score is rejected at parse (allow_inf_nan=False) — it would poison the desc sort.
    for bad_score in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValidationError):
            RerankResult(index=0, score=bad_score)


def test_context_strategy_contract() -> None:
    # spec(§7): augment → a non-empty augmented string (the document-context blurb + the chunk).
    cs = FakeContextStrategy()
    out = cs.augment("chunk body", "doc summary")
    assert isinstance(out, str) and out != ""
    assert "chunk body" in out and "doc summary" in out


def test_model_provider_contract() -> None:
    # spec(§7/§10): generate → GenerateResult{text, citations}; citations is a list[Citation] (≥0).
    mp = FakeModelProvider()
    result = mp.generate("a prompt")
    assert isinstance(result, GenerateResult)
    assert isinstance(result.text, str) and result.text != ""
    assert isinstance(result.citations, list)
    assert all(isinstance(c, Citation) for c in result.citations)
    assert FakeModelProvider(citations=[]).generate("p").citations == []
    # nested Citation is frozen too — deep immutability (ProvenancePacket-consistent, LESSON 8).
    gr = FakeModelProvider(citations=[Citation(cited_text="c", source_index=0)]).generate("p")
    with pytest.raises(ValidationError):
        gr.citations[0].cited_text = "z"


def test_generate_result_and_citation_snapshot() -> None:
    # spec(§7): §2.5-seam ★ freeze — GenerateResult + Citation shapes; rich payload deferred (Q6).
    assert set(GenerateResult.model_fields) == {"text", "citations"}
    assert set(Citation.model_fields) == {"cited_text", "source_index"}
    bad_gen: dict[str, Any] = {"text": "x", "citations": [], "extra": 1}
    bad_cit: dict[str, Any] = {"cited_text": "x", "source_index": 0, "extra": 1}
    with pytest.raises(ValidationError):
        GenerateResult(**bad_gen)
    with pytest.raises(ValidationError):
        Citation(**bad_cit)
    g = GenerateResult(text="x", citations=[])
    with pytest.raises(ValidationError):
        g.text = "y"


def test_fakes_fidelity() -> None:
    # LESSON 1: each Fake enforces the real contract shape — typed results, dimension agreement,
    # deterministic generation. No looser fake.
    emb = FakeEmbeddingProvider(dimension=16)
    assert all(len(v) == 16 for v in emb.embed(["a", "b"]))
    rr = FakeReranker()
    assert all(isinstance(r, RerankResult) for r in rr.rerank("q", ["a", "b"]))
    mp = FakeModelProvider(text="ans", citations=[Citation(cited_text="c", source_index=0)])
    res = mp.generate("p")
    assert res.text == "ans" and res.citations[0].cited_text == "c"
    assert mp.generate("p") == mp.generate("p")
    # the fake enforces the §5 dimension floor (no looser fake): dimension >= 1.
    with pytest.raises(ValueError):
        FakeEmbeddingProvider(dimension=0)
    # a post-construction mutation of the caller's citations list does NOT bleed into generate().
    cites = [Citation(cited_text="c", source_index=0)]
    aliased = FakeModelProvider(citations=cites)
    cites.append(Citation(cited_text="leak", source_index=1))
    assert len(aliased.generate("p").citations) == 1


def test_result_types_required_fields() -> None:
    # LESSON 3: every field on the frozen result types is required (omit-each-field guard).
    rerank: dict[str, Any] = {"index": 0, "score": 1.0}
    citation: dict[str, Any] = {"cited_text": "c", "source_index": 0}
    generate: dict[str, Any] = {"text": "t", "citations": []}
    for field in rerank:
        with pytest.raises(ValidationError):
            RerankResult(**{k: v for k, v in rerank.items() if k != field})
    for field in citation:
        with pytest.raises(ValidationError):
            Citation(**{k: v for k, v in citation.items() if k != field})
    for field in generate:
        with pytest.raises(ValidationError):
            GenerateResult(**{k: v for k, v in generate.items() if k != field})


def test_provider_result_strip_identity() -> None:
    # LESSON 7: result-type string fields (GenerateResult.text, Citation.cited_text) strip + reject
    # empty/whitespace.
    for bad in ("", "   "):
        with pytest.raises(ValidationError):
            GenerateResult(text=bad, citations=[])
        with pytest.raises(ValidationError):
            Citation(cited_text=bad, source_index=0)
    assert GenerateResult(text="  hi  ", citations=[]).text == "hi"
    assert Citation(cited_text="  c  ", source_index=0).cited_text == "c"
