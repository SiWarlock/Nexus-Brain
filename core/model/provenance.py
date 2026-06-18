"""The frozen ProvenancePacket trust contract — the §10 grounding record (ARCHITECTURE.md §10).

★ Freeze-before-fork contract. A `ProvenancePacket` is the evidence + freshness + confidence record
attached to EVERY answer — the audit of trust: the cited file:line spans, the SHAs they are grounded
at, the contributing project/source/session ids, index freshness, overall confidence, drift markers,
and the aggregated `EvidenceRef`s. Composes the frozen 1.3c `EvidenceRef` by value.

The 10-field set is pinned by a spec(§10) schema-snapshot; drift is a cross-track Finding.
`citations` are file:line TOKENS (strings the gate post-validates against live anchors), NOT
embedded `Anchor` objects (§10 says file:line[]). The freshness vocab + file:line token format are
producer-owned (Phase-4) — bare strip+min_length strings here, like the anchor-span deferral.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from model.evidence import EvidenceRef

# LESSON 7: every §5/§10 identity/path/token string strips surrounding whitespace + rejects empty /
# whitespace-only (a whitespace-loose token in a frozen cross-track contract is a Finding).
_StrippedStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ProvenancePacket(BaseModel):
    """The per-answer grounding/trust record — frozen + closed (`extra="forbid"`).

    List fields are REQUIRED with no default (a trust record is constructed deliberately), but an
    empty list is valid — an ungrounded/flagged answer carries `citations=[]` + `evidence=[]`.
    `evidence` composes the frozen `EvidenceRef` by value (parse-don't-trust extends to each nested
    element). Immutable: a re-grounded answer mints a new packet, never an in-place mutation.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    project_ids: list[_StrippedStr]
    source_ids: list[_StrippedStr]
    citations: list[_StrippedStr]  # file:line[-range] TOKENS; span format producer-owned (Phase-4)
    commit_shas: list[_StrippedStr]  # the SHAs the citations are grounded at
    session_ids: list[_StrippedStr]
    recorded_sha: _StrippedStr | None = None  # the recorded-Citations SHA (optional)
    index_freshness: _StrippedStr  # freshness marker; vocab owned by the Phase-4 subsystem
    confidence: float = Field(..., ge=0.0, le=1.0)  # the answer's overall confidence
    drift_markers: list[_StrippedStr]
    evidence: list[EvidenceRef]  # §10 evidence chips, composed by value (Appendix-A:217)
