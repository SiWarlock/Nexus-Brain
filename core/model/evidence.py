"""The frozen EvidenceRef trust contract — a user-visible evidence record (ARCHITECTURE.md §10).

★ Freeze-before-fork contract. An `EvidenceRef` is one piece of evidence backing an answer:
`{type, label, resource_ref?, confidence?}` — the chip the §10 grounding layer surfaces. Aggregated
by the 1.3b `ProvenancePacket`; serialized at the NexusOps seam (P2).

The 4-field SHAPE is pinned by a spec(§10) schema-snapshot; drift is a cross-track Finding. Per lead
decision D-A11 (Option B), the field shape is frozen NOW while the `EvidenceType` membership is
DEFERRED — see the EvidenceType marker below.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from _types import IdentityStr

# ─── DEFERRED MEMBERSHIP (lead decision D-A11, Option B) ──────────────────────────────────────
# `EvidenceType` is the closed set of evidence kinds — but its canonical 11 values are OWNED
# externally (NexusOps `MAIN_PLATFORM_INTERFACE.md` v0.2), not in this repo. We freeze the
# EvidenceRef *shape* now and DEFER the membership: `EvidenceType` is a constrained `str` (NOT an
# instantiated enum), so any non-empty kind is accepted until the set is pinned. The membership
# MUST be narrowed to the canonical 11 at Phase-4 grounding (first consumption), BEFORE the
# post-spine fork wave (constraint C-15; the NexusOps integration seam; D-A11).
#
# ADDITIVE-NARROWING SAFETY (D-A11 guardrail 2): narrowing `EvidenceType` → a `StrEnum`/`Literal`
# of the canonical 11 is non-breaking — the field declaration `type: EvidenceType` and the field
# NAME stay unchanged (so the spec(§10) shape snapshot is stable), and `StrEnum ⊂ str` keeps every
# prior string value valid. There is deliberately NO EvidenceType value-membership snapshot (it
# would lock a set we are explicitly deferring — LESSON 6 corollary).
EvidenceType = IdentityStr


class EvidenceRef(BaseModel):
    """One user-visible evidence chip backing an answer — frozen + closed (`extra="forbid"`).

    `type` is the kind discriminator (deferred `EvidenceType` — see marker above). `resource_ref`
    is an OPAQUE locator of the underlying resource (a chunk_id / anchor_id / commit SHA / card id /
    task id) — the kind is carried by `type`, never parsed back out of the id (LESSON 2). Immutable:
    a re-scored evidence ref is a new instance, never an in-place mutation.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    type: EvidenceType
    label: IdentityStr
    resource_ref: IdentityStr | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
