"""Anchor-aware docs chunking — the §8 chunk stage (ARCHITECTURE.md §8; closed sets §5).

`chunk_docs(text, classification, source_path)` splits a markdown/doc file by heading into
`ChunkDraft`s — the intermediate chunk-stage record the redactor (2.3), the `add` pipeline (2.4),
and embed (Phase 3) consume. A `ChunkDraft` carries the chunk-derivable subset of the frozen `Chunk`
contract plus the file:line span data the frozen `Anchor` needs; BOTH frozen models are assembled
at 2.4 with ingest context (ids / SHA / vector / project_id) that does not exist at chunk-time.

Span syntax (owned by this Phase-2 producer, mirroring `Chunk.anchor` / `Anchor.source_span`): v0 is
line-only — `"start-end"` for a multi-line span, `"N"` for a single line, 1-based.

Cap discipline: `Chunk.text` / `ChunkDraft.text` are `TextStr`, capped at `TEXT_MAX_LEN` (frozen).
Raising that cap is a cross-track Finding, so the chunker SUB-SPLITS instead: any section (incl. the
heading-less whole-file fallback and the preamble) over the cap is tiled at line boundaries into
cap-bounded drafts that cover all CONTENT lines (blank lines between content spans belong to no
draft, since TextStr strips edge whitespace — spans are contiguous on content, not on blanks); a
single line longer than the cap is hard-split at char boundaries as a last resort. Guarantee: no
draft ever exceeds the cap, for any input, dropping no content. v0 heading detection is ATX
(`#`..`######`) with fenced-code-block immunity; setext / `.rst` / `.adoc` heading syntax falls
through to the (cap-safe) whole-file path — a Step-9 TODO.
"""

from __future__ import annotations

import re
import warnings
from pathlib import Path
from typing import Any, Literal, NamedTuple, Self

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, model_validator

from _types import IDENTITY_MAX_LEN, TEXT_MAX_LEN, IdentityStr, TextStr
from ingest.classify import FileClassification

# ATX heading: 1–6 leading '#', then ≥1 space/tab, then the (possibly empty) title. 7+ '#' or a
# missing space is NOT a heading (it falls through to body) — matches CommonMark.
_HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.*)$")

# A line whose lstrip starts with one of these toggles a fenced code block; `#` lines inside a fence
# are body, never split points.
_FENCE_PREFIXES = ("```", "~~~")

# Anchor-span fields — they fold into the frozen Anchor at 2.4, NOT into Chunk; excluded from the
# chunk-derivable-subset drift test.
ANCHOR_SPAN_FIELDS = frozenset({"target_line_start", "target_line_end", "target_symbol"})


# `register` (a canonical Chunk field name) collides with BaseModel's metaclass attribute
# ABCMeta.register; left implicit, Pydantic would adopt that bound method as the field's default,
# silently making it optional. We pin it required via Field(...) and scope-suppress the otherwise
# import-time UserWarning, exactly as the frozen `model.chunk.Chunk` does (keeps `-W error` clean).
with warnings.catch_warnings():
    warnings.filterwarnings(
        "ignore",
        message=r'Field name "register" .* shadows an attribute in parent "BaseModel"',
        category=UserWarning,
    )

    class ChunkDraft(BaseModel):
        """A chunk-stage record. Immutable + closed; closed sets mirror the frozen `Chunk` contract.

        Carries the chunk-derivable subset of `Chunk` (`source_path`/`doc_or_code`/`producer`/
        `doc_type`/`ownership`/`register`/`text`/`anchor`) plus the `Anchor` span data
        (`target_line_*`/`target_symbol`). The frozen `Chunk` + `Anchor` are assembled at 2.4.
        """

        model_config = ConfigDict(frozen=True, extra="forbid")

        source_path: IdentityStr
        doc_or_code: Literal["doc", "code"]
        producer: IdentityStr
        doc_type: IdentityStr
        ownership: Literal["owned", "foreign", "supplemental"]
        register: Literal["plain", "deep"] = Field(...)  # required; Field(...) defeats the shadow
        text: TextStr
        anchor: IdentityStr  # "N" / "start-end" span string (owned by this producer)
        target_line_start: PositiveInt
        target_line_end: PositiveInt
        # the heading title; None for a whole-file / preamble span
        target_symbol: IdentityStr | None = None

        @model_validator(mode="after")
        def _span_ordered(self) -> Self:
            # A backwards span is never valid; single-line ⇒ start == end (mirrors Anchor).
            if self.target_line_end < self.target_line_start:
                raise ValueError("target_line_end must be >= target_line_start (backwards span)")
            return self


def _anchor(start: int, end: int) -> str:
    """v0 span string: bare "N" for a single line, "start-end" for a range."""
    return str(start) if start == end else f"{start}-{end}"


class _Section(NamedTuple):
    start_idx: int  # 0-based, inclusive
    end_idx: int  # 0-based, inclusive
    symbol: str | None  # the heading title; None for a preamble / whole-file section


class _Spec(NamedTuple):
    start: int  # 1-based line, inclusive
    end: int  # 1-based line, inclusive
    text: str
    symbol: str | None


def _heading_indices(lines: list[str]) -> list[int]:
    """0-based indices of ATX heading lines, skipping any inside a fenced code block.

    A fence is opened/closed by the SAME marker char (CommonMark §4.5): a ``` block is not closed by
    a ~~~ line and vice-versa — so a `#` line inside a backtick fence that contains a tilde line is
    still treated as body, not a split point.
    """
    out: list[int] = []
    open_fence: str | None = None
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        marker = next((p for p in _FENCE_PREFIXES if stripped.startswith(p)), None)
        if marker is not None:
            if open_fence is None:
                open_fence = marker  # opening fence
            elif marker == open_fence:
                open_fence = None  # matching closing fence
            continue  # a fence line is never a heading
        if open_fence is None and _HEADING_RE.match(line):
            out.append(i)
    return out


def _sections(lines: list[str]) -> list[_Section]:
    """Partition lines into sections in source order.

    Content before the first heading is a preamble section (symbol None); a heading-less file is one
    whole-file section (symbol None). Each heading owns from its line through the line before the
    next heading of any level (flat split — nested subsections become adjacent sections). An
    over-`IDENTITY_MAX_LEN` heading title is truncated (the symbol is a bounded `IdentityStr`).
    """
    n = len(lines)
    if n == 0:
        return []
    heads = _heading_indices(lines)
    if not heads:
        return [_Section(0, n - 1, None)]
    sections: list[_Section] = []
    if heads[0] > 0:
        sections.append(_Section(0, heads[0] - 1, None))  # preamble
    for k, h in enumerate(heads):
        end = heads[k + 1] - 1 if k + 1 < len(heads) else n - 1
        m = _HEADING_RE.match(lines[h])
        title = m.group(2).strip()[:IDENTITY_MAX_LEN] if m else ""
        sections.append(_Section(h, end, title or None))
    return sections


def _raw_specs(lines: list[str], section: _Section) -> list[_Spec]:
    """Tile a section's line range into cap-bounded specs in source order.

    Greedy: pack consecutive lines until the next would push the joined length over TEXT_MAX_LEN,
    then flush. A single line longer than the cap is flushed-around and hard-split at char
    boundaries (pieces on that one line). Each flushed spec is TRIMMED to its content extent — edge
    blank lines are dropped from BOTH its span and text, and an all-blank buffer yields no spec — so
    `spec.text == "\\n".join(lines[start-1:end])` holds exactly (TextStr strips surrounding
    whitespace, so a span that included edge blanks could never match its stored text). Internal
    blank lines are preserved (content). Blank lines between content thus belong to no spec.
    """
    specs: list[_Spec] = []
    buf: list[str] = []
    buf_start: int | None = None
    buf_len = 0

    def flush() -> None:
        nonlocal buf, buf_start, buf_len
        if buf_start is not None:
            lo, hi = 0, len(buf)
            while lo < hi and not buf[lo].strip():
                lo += 1
            while hi > lo and not buf[hi - 1].strip():
                hi -= 1
            if lo < hi:  # has content — emit the trimmed (content-only) span + text
                specs.append(
                    _Spec(buf_start + lo, buf_start + hi - 1, "\n".join(buf[lo:hi]), section.symbol)
                )
        buf, buf_start, buf_len = [], None, 0

    for idx in range(section.start_idx, section.end_idx + 1):
        lineno = idx + 1
        ltext = lines[idx]
        length = len(ltext)
        if length > TEXT_MAX_LEN:
            flush()
            for j in range(0, length, TEXT_MAX_LEN):
                specs.append(_Spec(lineno, lineno, ltext[j : j + TEXT_MAX_LEN], section.symbol))
            continue
        added = length + (1 if buf else 0)  # +1 for the joining newline
        if buf and buf_len + added > TEXT_MAX_LEN:
            flush()
            added = length
        if buf_start is None:
            buf_start = lineno
        buf.append(ltext)
        buf_len += added
    flush()
    return specs


def _drafts_from_sections(
    lines: list[str],
    sections: list[_Section],
    classification: FileClassification,
    source_path: str,
) -> tuple[ChunkDraft, ...]:
    """Tile each section's source lines into cap-bounded `ChunkDraft`s, in source order.

    The single draft-building path for BOTH chunk_docs (heading sections) and chunk_code (leaf +
    complement sections). Draft text is always `"\\n".join(lines[start-1:end])` — the real source at
    the draft's span — so a draft's text verbatim-occupies its anchor (the §10 north-star accuracy
    invariant), by construction, for docs and code alike (modulo TextStr's edge-whitespace strip).

    v0: `register` is always `"plain"`; add a `register` parameter here when chunk_code needs
    `"deep"` for context-augmented code scopes.
    """
    drafts: list[ChunkDraft] = []
    for section in sorted(sections, key=lambda s: s.start_idx):
        for spec in _raw_specs(lines, section):
            drafts.append(
                ChunkDraft(
                    source_path=source_path,
                    doc_or_code=classification.doc_or_code,
                    producer=classification.producer,
                    doc_type=classification.doc_type,
                    ownership=classification.ownership,
                    register="plain",
                    text=spec.text,
                    anchor=_anchor(spec.start, spec.end),
                    target_line_start=spec.start,
                    target_line_end=spec.end,
                    target_symbol=spec.symbol,
                )
            )
    return tuple(drafts)


def chunk_docs(
    text: str, classification: FileClassification, source_path: str
) -> tuple[ChunkDraft, ...]:
    """Split a doc into anchored, cap-bounded `ChunkDraft`s (heading sections, source order).

    Pure + deterministic. `register` is the v0 docs default `"plain"` (`"deep"` is reserved for
    later context-augmented chunks). The four classification axes pass through from the input.
    """
    lines = text.splitlines()
    return _drafts_from_sections(lines, _sections(lines), classification, source_path)


# --- code chunking (2.2b): AST-aware via the vendored CodeHierarchyNodeParser -------------------
# File extension -> the parser language name (also the .scm tag-file stem). Only the languages the
# vendored parser ships built-in config for are mapped; every other extension routes to the
# whole-file line-tiling fallback (R-PARTIAL). Adding a language = wire its grammar in
# `_code_hierarchy._GRAMMAR_MODULES` + a parser config entry + a row here.
_EXT_LANGUAGE: dict[str, str] = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".hh": "cpp",
    ".hxx": "cpp",
    ".php": "php",
}

# Files larger than this skip the AST parser (→ line-tiling fallback): tree-sitter builds the whole
# file's tree in memory, so a giant generated/minified file is a memory-pressure surface, and AST
# hierarchy on it has no value. Real source files sit far below this.
_MAX_PARSE_BYTES = 2_000_000  # 2 MB


def _detect_language(source_path: str) -> str | None:
    """The parser language for `source_path`'s extension, or None → line-tiling fallback."""
    return _EXT_LANGUAGE.get(Path(source_path).suffix.lower())


def _parse_code(text: str, language: str) -> list[Any]:
    """The parser seam (mockable; the fallback boundary). Returns the parser's flat node list.

    Isolated so tests can force the fallback (monkeypatch this to raise) and so the heavy vendored
    parser import is lazy. The vendored module is excluded from strict typing (see pyproject).
    """
    from llama_index.core.schema import Document

    from ingest._code_hierarchy import (  # type: ignore[attr-defined]  # vendored, untyped
        CodeHierarchyNodeParser,
    )

    parser_cls: Any = CodeHierarchyNodeParser
    nodes: list[Any] = parser_cls(language=language).get_nodes_from_documents([Document(text=text)])
    return nodes


def _leaf_nodes(nodes: list[Any], text: str) -> list[Any]:
    """The full-content leaf nodes: a real char span whose text VERBATIM occupies it.

    A skeleton/parent node (elided text — child scopes replaced by "Code replaced for brevity"
    placeholders, or no char span) fails the verbatim check and is skipped; its real content rides
    its own leaf node + the complement, so nothing is lost and no draft claims a span its text
    doesn't occupy (the §10 anchor-accuracy invariant).
    """
    leaves: list[Any] = []
    for n in nodes:
        sc, ec = n.start_char_idx, n.end_char_idx
        if sc is not None and ec is not None and n.text == text[sc:ec]:
            leaves.append(n)
    return leaves


def _qualified_symbol(node: Any) -> str | None:
    """The dotted scope path (e.g. `Class.method`) from the node's inclusive scopes, capped.

    The IDENTITY_MAX_LEN cap may truncate a very deep path mid-segment (cosmetic only — the symbol
    is advisory; the anchor span carries the load-bearing location). v0 accepts that.
    """
    names = [s.get("name") for s in node.metadata.get("inclusive_scopes", []) if s.get("name")]
    return ".".join(names)[:IDENTITY_MAX_LEN] or None


def _line_range(text: str, start_char: int, end_char: int) -> tuple[int, int]:
    """1-based [start_line, end_line] (inclusive) for a char span's CONTENT extent.

    `end_line` is the last line with content: trailing newlines/blank lines in the char span are
    dropped (`rstrip("\\n")`), so any trailing blanks fall to the complement rather than the leaf —
    keeping the span aligned with the draft's (edge-stripped) text. `start_char` is assumed to sit
    at a line start (the parser's scope nodes begin at the indentation).
    """
    start_line = text.count("\n", 0, start_char) + 1
    end_line = start_line + text[start_char:end_char].rstrip("\n").count("\n")
    return start_line, end_line


def _whole_file_drafts(
    lines: list[str], classification: FileClassification, source_path: str
) -> tuple[ChunkDraft, ...]:
    """The fallback: line-tile the whole file (symbol None). R-PARTIAL — never drops a file."""
    if not lines:
        return ()
    return _drafts_from_sections(
        lines, [_Section(0, len(lines) - 1, None)], classification, source_path
    )


def chunk_code(
    text: str, classification: FileClassification, source_path: str
) -> tuple[ChunkDraft, ...]:
    """Split source code into anchored, cap-bounded `ChunkDraft`s (AST scopes + complement).

    AST-aware via the vendored CodeHierarchyNodeParser: emit the full-content LEAF scope nodes (each
    a draft with a qualified `target_symbol` + an accurate span) and line-tile the COMPLEMENT (every
    line no leaf covers — signatures, top-level stmts, small inline scopes; symbol None). Leaves
    ∪ complement tile the whole file disjointly, so coverage is total (R-PARTIAL) and every draft's
    text verbatim-occupies its span. Unsupported language / parse error / no leaves → the whole-file
    line-tiling fallback. Pure + deterministic; `register` is the v0 default `"plain"`.
    """
    if not text.strip():
        return ()
    lines = text.splitlines()
    n_lines = len(lines)

    language = _detect_language(source_path)
    # Route an oversized file straight to the line-tiling fallback: tree-sitter parses the whole
    # buffer into an in-memory tree, so a huge (e.g. generated/minified) file is a memory-pressure
    # surface — and AST hierarchy on such a file is not worth it. The fallback still covers it
    # (R-PARTIAL). Deeply-nested source that trips RecursionError is caught below (see the except).
    if language is None or len(text) > _MAX_PARSE_BYTES:
        return _whole_file_drafts(lines, classification, source_path)
    try:
        nodes = _parse_code(text, language)
    except Exception:
        # Broad by design — MUST keep catching RecursionError (deep nesting) + MemoryError so a
        # hostile/pathological source degrades to the line-tiling fallback, never crashes the
        # ingest pipeline. Narrowing this is a safety regression.
        return _whole_file_drafts(lines, classification, source_path)
    leaves = _leaf_nodes(nodes, text)
    if not leaves:
        return _whole_file_drafts(lines, classification, source_path)

    sections: list[_Section] = []
    covered: set[int] = set()
    leaf_ranges: list[tuple[int, int, str | None]] = []
    for node in leaves:
        sl, el = _line_range(text, node.start_char_idx, node.end_char_idx)
        sl = max(1, min(sl, n_lines))
        el = max(sl, min(el, n_lines))
        leaf_ranges.append((sl, el, _qualified_symbol(node)))

    prev_end = 0
    for sl, el, symbol in sorted(leaf_ranges, key=lambda r: r[0]):
        sl = max(sl, prev_end + 1)  # clip any overlap so the partition stays disjoint
        if sl > el:
            continue
        sections.append(_Section(sl - 1, el - 1, symbol))
        covered.update(range(sl, el + 1))
        prev_end = el

    run_start: int | None = None  # contiguous runs of complement (uncovered) lines
    for ln in range(1, n_lines + 1):
        if ln not in covered:
            if run_start is None:
                run_start = ln
        elif run_start is not None:
            sections.append(_Section(run_start - 1, ln - 2, None))
            run_start = None
    if run_start is not None:
        sections.append(_Section(run_start - 1, n_lines - 1, None))

    return _drafts_from_sections(lines, sections, classification, source_path)
