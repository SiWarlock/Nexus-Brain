"""The frozen Anchor trust contract — the §10 north-star grounding primitive (ARCHITECTURE.md §10).

★ Freeze-before-fork contract. An `Anchor` is the typed file:line[-range] edge from a prose/answer
span (`source_file` + `source_span`) to a code target (`target_path` + `target_line_start..end`,
optionally a `target_symbol`), carrying its revalidation `state`, the `last_resolved_sha` it was
last grounded against, and a `[0, 1]` `confidence`. The grounding gate (§10) serves a citation only
when its anchor's `state == live`; a stale/unknown anchor flags the claim as unsupported.

The 11-field set is pinned by a spec(§10) schema-snapshot test and the `AnchorState` alphabet by a
membership snapshot; either drift is a cross-track Finding. `source_span` + the `target_*` span are
a TYPING seam — the file:line span *syntax* is owned/parsed by the Phase-2 anchor producer, not
validated here (mirroring Chunk's bare `anchor`/`*_sha`). `anchor_id` is caller-injected via IdGen.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PositiveInt,
    StringConstraints,
    model_validator,
)

# Every §5/§10 identity/path string field strips surrounding whitespace and rejects empty /
# whitespace-only (the before-fork sweep). A whitespace-loose identity in a frozen cross-track
# contract is a Finding.
IdentityStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class AnchorState(StrEnum):
    """The closed 5-value anchor revalidation alphabet (Appendix-A line 216).

    A NAMED state-machine alphabet (reused by the Phase-2+ revalidation transitions) — hence a
    StrEnum, not an inline `Literal`. `deleted` is NOT a member: removal of the anchor row is a
    record-lifecycle event, distinct from a value of the live `state` field (§5↔Appendix-A).
    """

    LIVE = "live"
    STALE = "stale"
    MOVED = "moved"
    UNKNOWN = "unknown"
    ORPHANED = "orphaned"


class Anchor(BaseModel):
    """One immutable file:line[-range] grounding edge — frozen + closed (`extra="forbid"`).

    `anchor_id` is REQUIRED with no default — the Phase-2 producer injects it via the `IdGen` seam
    (forbidden-rule 4 / LESSONS §1), never minted inline. Revalidation produces a NEW instance with
    an updated `state`/`last_resolved_sha`, never an in-place mutation.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    anchor_id: IdentityStr
    project_id: IdentityStr
    source_file: IdentityStr
    source_span: IdentityStr  # "10" / "10-20" / "10:5-12:8" — span syntax owned by Phase-2
    target_path: IdentityStr
    target_line_start: PositiveInt
    target_line_end: PositiveInt
    target_symbol: IdentityStr | None = None  # a bare line-range anchor needn't name a symbol
    state: AnchorState
    last_resolved_sha: IdentityStr  # the SHA the anchor was last grounded against (§10)
    confidence: float = Field(..., ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _span_ordered(self) -> Self:
        # A backwards span is never valid; single-line ⇒ start == end (§10 line-range semantics).
        if self.target_line_end < self.target_line_start:
            raise ValueError("target_line_end must be >= target_line_start (backwards span)")
        return self
