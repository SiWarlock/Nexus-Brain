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
contiguous, gap-free, cap-bounded drafts; a single line longer than the cap is hard-split at char
boundaries as a last resort. Guarantee: no draft ever exceeds the cap, for any input, dropping no
content. v0 heading detection is ATX (`#`..`######`) with fenced-code-block immunity; setext /
`.rst` / `.adoc` heading syntax falls through to the (cap-safe) whole-file path — a Step-9 TODO.
"""

from __future__ import annotations

import re
import warnings
from typing import Literal, NamedTuple, Self

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
    boundaries (pieces on that one line). Every line lands in exactly one spec → contiguous tiling.
    """
    specs: list[_Spec] = []
    buf: list[str] = []
    buf_start: int | None = None
    buf_len = 0

    def flush() -> None:
        nonlocal buf, buf_start, buf_len
        if buf_start is None:
            return
        specs.append(_Spec(buf_start, buf_start + len(buf) - 1, "\n".join(buf), section.symbol))
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


def _merge_blanks(specs: list[_Spec]) -> list[_Spec]:
    """Fold blank (whitespace-only) specs into a neighbour's span so coverage stays gap-free.

    TextStr forbids an empty draft, so a buffer that is all blank lines is never emitted; instead
    its line span is absorbed by the previous emitted draft (end extended) — or, for leading blanks
    with no predecessor, prepended to the next emitted draft's start. A section that is wholly blank
    yields no drafts (the empty-file / blank-section case).
    """
    merged: list[_Spec] = []
    pending_start: int | None = None
    for spec in specs:
        if not spec.text.strip():
            if merged:
                merged[-1] = merged[-1]._replace(end=spec.end)  # extend over the blank lines
            elif pending_start is None:
                pending_start = spec.start
            continue
        if pending_start is not None:
            spec = spec._replace(start=pending_start)
            pending_start = None
        merged.append(spec)
    return merged


def chunk_docs(
    text: str, classification: FileClassification, source_path: str
) -> tuple[ChunkDraft, ...]:
    """Split a doc into anchored, cap-bounded `ChunkDraft`s (heading sections, source order).

    Pure + deterministic. `register` is the v0 docs default `"plain"` (`"deep"` is reserved for
    later context-augmented chunks). The four classification axes pass through from the input.
    """
    lines = text.splitlines()
    drafts: list[ChunkDraft] = []
    for section in _sections(lines):
        for spec in _merge_blanks(_raw_specs(lines, section)):
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
