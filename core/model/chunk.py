"""The frozen Chunk data contract — the per-project LanceDB row (ARCHITECTURE.md §5, Appendix A).

★ Freeze-before-fork contract. A Chunk is the semantic+lexical memory unit persisted to the
per-project LanceDB dataset. The field set is pinned by a spec(§5) schema-snapshot test; any
add/remove/rename must ride an atomic Appendix-A edit (a silent drift is a cross-track Finding).
FTS/BM25 is a native LanceDB index on `text`, not a stored field. The LanceDB `Vector(dim)` /
`LanceModel` binding + FTS config are derived from this model in Phase 3.1.
"""

from __future__ import annotations

import warnings
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StrictBool

from _types import IdentityStr, TextStr

# `register` (a canonical Appendix-A / DATA_MODEL field name) collides with BaseModel's
# metaclass attribute ABCMeta.register. Left implicit, Pydantic adopts that bound method as the
# field's default — silently making `register` optional + un-JSON-serializable. We pin it
# required via Field(...) below; the shadow is then benign, so we scope-suppress the (otherwise
# import-time) UserWarning to the class definition, keeping `python -W error` imports working.
with warnings.catch_warnings():
    warnings.filterwarnings(
        "ignore",
        message=r'Field name "register" .* shadows an attribute in parent "BaseModel"',
        category=UserWarning,
    )

    class Chunk(BaseModel):
        """One persisted chunk row. Immutable (`frozen`) + closed (`extra="forbid"`).

        `chunk_id` and `created_at` are REQUIRED with no default — the constructing caller
        (Phase-2 ingest) injects them via the `IdGen` / `Clock` seams (forbidden-rule 4 /
        LESSONS §1), never minted inline here.
        """

        model_config = ConfigDict(frozen=True, extra="forbid")

        chunk_id: IdentityStr
        project_id: IdentityStr
        source_path: IdentityStr
        doc_or_code: Literal["doc", "code"]
        producer: IdentityStr  # open-ended (classifier may grow): gstack | CE | human | ...
        doc_type: IdentityStr  # open-ended (classifier may grow): architecture | guide | adr | ...
        ownership: Literal["owned", "foreign", "supplemental"]
        register: Literal["plain", "deep"] = Field(...)  # required; Field(...) defeats the shadow
        text: TextStr
        vector: list[float]  # list→tuple (LESSON 8) deferred to Phase 3.1 (Vector(dim) owns repr)
        anchor: IdentityStr  # file:line[-line] span; the 1.3 Anchor references this, not embedded
        content_hash: IdentityStr
        last_resolved_sha: IdentityStr
        ingested_from_sha: IdentityStr
        embedding_model_version: IdentityStr
        context_blurb: TextStr | None = None  # Contextual-Retrieval prefix (code chunks); optional
        generation: int
        tombstone: StrictBool
        created_at: AwareDatetime
