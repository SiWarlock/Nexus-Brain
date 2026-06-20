"""The 4 pluggable, version-stamped provider ports (ARCHITECTURE.md §7, §16, Appendix A:219).

Behavioral ports (LESSON 1): a `@runtime_checkable Protocol` + a faithful, DETERMINISTIC `Fake*`
double in `core/testing/fakes.py`. The REAL adapters (local Ollama / cloud Voyage·Anthropic) are
non-deterministic surfaces — eval-tested, never `/tdd`-ed; this slice freezes the interfaces, the
Fakes, and the frozen result types.

Providers are version-stamped (§16). Only `EmbeddingProvider.model_version` is on the Protocol: it
is the §5 generation-identity that gates "one embedding model per index generation" (Key safety
rule #5) + the StoreVersionStamp. Reranker/ModelProvider versions are adapter-config / eval /
observability concerns — additive later if a core consumer needs them.

The Protocols carry no field-snapshot (behavioral); their frozen RESULT types DO — pinned by
spec(§7) snapshots (they cross into retrieval/grounding). The rich per-provider Citations payload
(full Anthropic Citations → file:line + recorded_sha) is DEFERRED to §10 grounding (Phase-4); the
minimal `Citation` shape here narrows additively.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, NonNegativeInt

from _types import TextStr


class RerankResult(BaseModel):
    """One reranked result — references the input `documents` by index + a score. Frozen.

    `allow_inf_nan=False`: a NaN/±inf score would poison the score-desc sort + the RRF fusion math
    (NaN compares false, silently corrupting rank) — rejected at the parse boundary (§4).
    """

    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    index: NonNegativeInt
    score: float


class Citation(BaseModel):
    """A minimal cited-span record — what text was cited from which source. Frozen.

    The rich shape (file:line + recorded_sha, the full Anthropic Citations mapping) is the §10
    grounding gate's concern (Phase-4); this minimal shape narrows additively.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    cited_text: TextStr
    source_index: NonNegativeInt


class GenerateResult(BaseModel):
    """A model generation — the answer `text` + the `citations` it is grounded on. Frozen."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    text: TextStr
    citations: tuple[Citation, ...]  # LESSON 8: a frozen-contract collection is a tuple (immutable)


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Embeds text into vectors (§7/§16) — version-stamped (dimension + model_version)."""

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed a batch → one vector per input, each of length `dimension`."""
        ...

    @property
    def dimension(self) -> int:
        """The embedding dimension (must agree with the §5 StoreVersionStamp.dimension)."""
        ...

    @property
    def model_version(self) -> str:
        """The version-stamp identity — a model switch is a new generation (§16 / Key safety #5)."""
        ...


@runtime_checkable
class Reranker(Protocol):
    """Reranks documents against a query (§7) — returns index+score, sorted score-desc."""

    def rerank(self, query: str, documents: Sequence[str]) -> list[RerankResult]:
        """Score `documents` against `query` → RerankResults (by index), sorted score-desc."""
        ...


@runtime_checkable
class ContextStrategy(Protocol):
    """Augments a chunk with document context (§7) — the Contextual-Retrieval prefix."""

    def augment(self, chunk_text: str, document_context: str) -> str:
        """Return the augmented text (the `document_context` blurb prepended to `chunk_text`)."""
        ...


@runtime_checkable
class ModelProvider(Protocol):
    """Generates an answer + Citations (§7/§10)."""

    def generate(self, prompt: str) -> GenerateResult:
        """Generate a `GenerateResult` (answer text + citations) for `prompt`."""
        ...
