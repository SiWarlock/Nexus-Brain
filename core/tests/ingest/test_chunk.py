"""Unit tests for the docs chunk stage (ARCHITECTURE.md §8; closed-set/subset guards §5).

`chunk_docs(text, classification, source_path)` splits a doc by heading into anchored `ChunkDraft`s
— the intermediate chunk-stage record the redactor (2.3) / pipeline (2.4) / embed (Phase 3) consume.
`ChunkDraft` carries the chunk-derivable subset of the frozen `Chunk` contract + the anchor span
data the frozen `Anchor` needs; both frozen models are assembled at 2.4 with ingest context (ids /
SHA / vector). A get_args drift test pins the draft's closed sets byte-identical to `Chunk`'s
(extends LESSON 19); a subset test pins that every chunk-mirroring field folds into `Chunk`.
"""

from __future__ import annotations

from typing import Any, get_args

import pytest
from pydantic import ValidationError

from _types import IDENTITY_MAX_LEN, TEXT_MAX_LEN
from ingest.chunk import ANCHOR_SPAN_FIELDS, ChunkDraft, chunk_docs
from ingest.classify import FileClassification
from model.chunk import Chunk

pytestmark = pytest.mark.unit


def _doc_cls(**overrides: str) -> FileClassification:
    kwargs: dict[str, str] = {
        "doc_or_code": "doc",
        "producer": "human",
        "doc_type": "guide",
        "ownership": "owned",
    }
    kwargs.update(overrides)
    return FileClassification(**kwargs)  # type: ignore[arg-type]


def _valid_draft_kwargs() -> dict[str, Any]:
    # Any: heterogeneous kwargs unpacked into ChunkDraft(...); negative tests override fields.
    return {
        "source_path": "docs/x.md",
        "doc_or_code": "doc",
        "producer": "human",
        "doc_type": "guide",
        "ownership": "owned",
        "register": "plain",
        "text": "# A\nbody",
        "anchor": "1-2",
        "target_line_start": 1,
        "target_line_end": 2,
        "target_symbol": "A",
    }


def test_chunk_docs_splits_by_heading() -> None:
    # spec(§8): a 3-heading doc → 3 drafts, each text scoped to its section.
    text = "# A\nalpha\n# B\nbeta\n# C\ngamma\n"
    drafts = chunk_docs(text, _doc_cls(), "docs/x.md")
    assert len(drafts) == 3
    assert drafts[0].target_symbol == "A" and "alpha" in drafts[0].text
    assert drafts[1].target_symbol == "B" and "beta" in drafts[1].text
    assert drafts[2].target_symbol == "C" and "gamma" in drafts[2].text


def test_chunk_docs_section_line_span() -> None:
    # spec(§8): each draft's 1-based target span bounds its section; anchor == the span string.
    text = "# A\nalpha\nbeta\n# B\ngamma\n"
    drafts = chunk_docs(text, _doc_cls(), "docs/x.md")
    assert (drafts[0].target_line_start, drafts[0].target_line_end) == (1, 3)
    assert drafts[0].anchor == "1-3"
    assert (drafts[1].target_line_start, drafts[1].target_line_end) == (4, 5)
    assert drafts[1].anchor == "4-5"


def test_chunk_docs_no_headings_single_draft() -> None:
    # spec(§8): R-PARTIAL — a heading-less doc → exactly one whole-file draft spanning all lines.
    text = "just\nsome\nlines\n"
    drafts = chunk_docs(text, _doc_cls(), "notes.txt")
    assert len(drafts) == 1
    assert (drafts[0].target_line_start, drafts[0].target_line_end) == (1, 3)
    assert drafts[0].anchor == "1-3"
    assert drafts[0].target_symbol is None
    assert "just" in drafts[0].text and "lines" in drafts[0].text


def test_chunk_docs_empty_section_kept() -> None:
    # spec(§8): a heading with no body still yields a draft (no drop); single-line span → "N".
    text = "# A\n# B\nbody\n"
    drafts = chunk_docs(text, _doc_cls(), "docs/x.md")
    assert len(drafts) == 2
    assert drafts[0].target_symbol == "A"
    assert (drafts[0].target_line_start, drafts[0].target_line_end) == (1, 1)
    assert drafts[0].anchor == "1"  # single-line span is the bare-N form
    assert drafts[1].target_symbol == "B"


def test_chunk_docs_preamble_before_first_heading_kept() -> None:
    # spec(§8): R-PARTIAL — content before the first heading is its own draft (symbol None).
    text = "intro line\n# A\nbody\n"
    drafts = chunk_docs(text, _doc_cls(), "docs/x.md")
    assert len(drafts) == 2
    assert drafts[0].target_symbol is None and "intro line" in drafts[0].text
    assert (drafts[0].target_line_start, drafts[0].target_line_end) == (1, 1)
    assert drafts[1].target_symbol == "A"


def test_chunk_docs_target_symbol_is_heading() -> None:
    # spec(§8): target_symbol == the heading title; a whole-file draft has no symbol.
    drafts = chunk_docs("# Hello World\nbody\n", _doc_cls(), "docs/x.md")
    assert drafts[0].target_symbol == "Hello World"
    whole = chunk_docs("no heading here\n", _doc_cls(), "notes.txt")
    assert whole[0].target_symbol is None


def test_chunk_docs_ignores_headings_in_fenced_code_block() -> None:
    # spec(§8): a `#` line inside a ``` fenced code block is body, not a heading split point.
    text = "# Real\n```\n# not a heading\ncode\n```\nafter\n"
    drafts = chunk_docs(text, _doc_cls(), "docs/x.md")
    assert len(drafts) == 1
    assert drafts[0].target_symbol == "Real"
    assert "# not a heading" in drafts[0].text


def test_chunk_docs_fence_closes_only_on_matching_marker() -> None:
    # spec(§8): a ``` fence is not closed by a ~~~ line (CommonMark §4.5) — the `#` between the
    # mismatched markers stays body, so the whole block is one section under the real heading.
    text = "# Real\n```\n~~~\n# still code\n~~~\n```\nafter\n"
    drafts = chunk_docs(text, _doc_cls(), "docs/x.md")
    assert len(drafts) == 1
    assert drafts[0].target_symbol == "Real"
    assert "# still code" in drafts[0].text


def test_chunk_docs_overlong_heading_title_truncated() -> None:
    # spec(§8): a heading title longer than IDENTITY_MAX_LEN is truncated, never crashes
    # ChunkDraft construction (target_symbol is a bounded IdentityStr).
    title = "t" * (IDENTITY_MAX_LEN + 50)
    drafts = chunk_docs(f"# {title}\nbody\n", _doc_cls(), "docs/x.md")
    assert len(drafts) == 1
    assert drafts[0].target_symbol is not None
    assert len(drafts[0].target_symbol) == IDENTITY_MAX_LEN


def test_chunk_docs_carries_classification() -> None:
    # spec(§8): the classify→chunk hand-off — each draft mirrors the four axes + source_path.
    cls = _doc_cls(producer="gstack", doc_type="readme", ownership="foreign")
    d = chunk_docs("# A\nx\n", cls, "vendor/p.md")[0]
    assert (d.doc_or_code, d.producer, d.doc_type, d.ownership) == (
        "doc",
        "gstack",
        "readme",
        "foreign",
    )
    assert d.source_path == "vendor/p.md"


def test_chunk_docs_register_value() -> None:
    # spec(§5): register closed-set field is populated with the v0 default (design Q3).
    assert chunk_docs("# A\nx\n", _doc_cls(), "docs/x.md")[0].register == "plain"


def test_chunk_docs_deterministic() -> None:
    # determinism posture: same input → identical draft tuple in source order.
    text = "# A\na\n# B\nb\n"
    assert chunk_docs(text, _doc_cls(), "docs/x.md") == chunk_docs(text, _doc_cls(), "docs/x.md")


def test_chunk_docs_empty_file_returns_empty() -> None:
    # spec(§8): a degenerate empty / whitespace-only file has no content → no drafts (nothing
    # dropped). Refines "no headings → one draft" for the zero-content case (TextStr is non-empty).
    assert chunk_docs("", _doc_cls(), "docs/x.md") == ()
    assert chunk_docs("   \n\n", _doc_cls(), "docs/x.md") == ()


def _spans(drafts: tuple[ChunkDraft, ...]) -> list[tuple[int, int]]:
    return [(d.target_line_start, d.target_line_end) for d in drafts]


def test_chunk_docs_subsplits_oversized_section() -> None:
    # spec(§8): a heading section over TEXT_MAX_LEN is sub-split at line boundaries into contiguous
    # cap-bounded drafts that tile the section with no gaps/overlaps (respects the frozen cap).
    body_lines = [f"line {i} " + "x" * 20 for i in range(800)]  # ~ >8KB of body
    text = "# Big\n" + "\n".join(body_lines) + "\n"
    n_lines = len(text.splitlines())  # 1 heading + 800 body
    drafts = chunk_docs(text, _doc_cls(), "docs/x.md")
    assert len(drafts) >= 2
    assert all(len(d.text) <= TEXT_MAX_LEN for d in drafts)
    spans = _spans(drafts)
    assert spans[0][0] == 1  # covers from the first line
    assert spans[-1][1] == n_lines  # ...through the last
    for (_, e1), (s2, _) in zip(spans, spans[1:], strict=False):
        assert s2 == e1 + 1  # contiguous: no gaps, no overlaps


def test_chunk_docs_subsplits_oversized_whole_file_fallback() -> None:
    # spec(§8): the heading-less / .rst / .adoc whole-file fallback is also cap-bounded (R-PARTIAL).
    text = "\n".join("z" * 80 for _ in range(200))  # ~16KB, no headings
    drafts = chunk_docs(text, _doc_cls(), "big.rst")
    assert len(drafts) >= 2
    assert all(len(d.text) <= TEXT_MAX_LEN for d in drafts)
    assert all(d.target_symbol is None for d in drafts)
    spans = _spans(drafts)
    assert spans[0][0] == 1 and spans[-1][1] == 200
    for (_, e1), (s2, _) in zip(spans, spans[1:], strict=False):
        assert s2 == e1 + 1


def test_chunk_docs_hard_splits_oversized_single_line() -> None:
    # spec(§8): a single line longer than the cap is hard-split at char boundaries (last resort);
    # every piece is on that one line and ≤ cap. Guarantee: NO draft ever exceeds the cap.
    huge = "z" * (TEXT_MAX_LEN * 2 + 5)
    text = "# H\n" + huge + "\n"
    drafts = chunk_docs(text, _doc_cls(), "docs/x.md")
    assert all(len(d.text) <= TEXT_MAX_LEN for d in drafts)
    pieces = [d for d in drafts if d.target_line_start == 2]
    assert len(pieces) >= 2
    assert all(d.target_line_start == d.target_line_end == 2 for d in pieces)
    assert all(d.anchor == "2" for d in pieces)


def test_chunkdraft_closed_sets_match_chunk_contract() -> None:
    # spec(§5): frozen-Chunk alignment — the draft's closed sets are byte-identical to Chunk's
    # (extends LESSON 19; mirrors the 2.1 classifier vocab guard).
    for field in ("doc_or_code", "ownership", "register"):
        assert get_args(ChunkDraft.model_fields[field].annotation) == get_args(
            Chunk.model_fields[field].annotation
        )


def test_chunkdraft_fields_subset_of_chunk() -> None:
    # spec(§5): every chunk-mirroring draft field folds into Chunk — no orphan field that can't
    # become a Chunk attribute at 2.4 (anchor span fields fold into Anchor, excluded here).
    chunk_mirror = set(ChunkDraft.model_fields) - ANCHOR_SPAN_FIELDS
    assert chunk_mirror <= set(Chunk.model_fields)


def test_chunkdraft_rejects_unknown_closed_set() -> None:
    # spec(§5): closed-set integrity / parse-don't-trust — an out-of-set register raises.
    kwargs = _valid_draft_kwargs()
    kwargs["register"] = "loud"
    with pytest.raises(ValidationError):
        ChunkDraft(**kwargs)


def test_chunkdraft_rejects_backwards_span() -> None:
    # spec(§5): span integrity — end < start is never valid (mirrors Anchor._span_ordered).
    kwargs = _valid_draft_kwargs()
    kwargs["target_line_start"] = 10
    kwargs["target_line_end"] = 5
    with pytest.raises(ValidationError):
        ChunkDraft(**kwargs)


def test_chunkdraft_is_frozen() -> None:
    # spec(§5): the draft is immutable (extra="forbid" + frozen), like the contracts it feeds.
    d = ChunkDraft(**_valid_draft_kwargs())
    with pytest.raises(ValidationError):
        d.text = "mutated"


def test_chunkdraft_all_required_fields_omittable() -> None:
    # spec(§5): every field except target_symbol is required (no default) — generalizes the freeze
    # pin and catches the metaclass-shadow default trap on `register` (LESSON 3 / mirrors Chunk).
    optional = {"target_symbol"}
    for name in set(_valid_draft_kwargs()) - optional:
        kwargs = _valid_draft_kwargs()
        del kwargs[name]
        with pytest.raises(ValidationError):
            ChunkDraft(**kwargs)


def test_chunk_docs_nul_byte_raises_at_boundary() -> None:
    # spec(§5): parse-don't-trust — a NUL/control byte in pre-redaction content hard-rejects at the
    # TextStr boundary (intentional; file-level malformed-content resilience is a 2.3/2.4 item,
    # LESSON 14). Pinned so the harsh fail-mode is deliberate, not incidental.
    with pytest.raises(ValidationError):
        chunk_docs("# A\nb\x00d\n", _doc_cls(), "docs/x.md")
