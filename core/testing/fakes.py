"""Deterministic test doubles for the determinism-seam ports (ARCHITECTURE.md §7, C-15).

The canonical `Fake*` home for the whole engine — 1.4 extends this file with the
provider / CodeGraph fakes + cassette record/replay. Each fake satisfies its port
structurally (DI-substitutable) and is fully reproducible so golden-set tests are stable.
"""

from __future__ import annotations

import hashlib
import random
import re
from collections.abc import Callable, Iterable, Sequence
from datetime import datetime, timedelta

from model.redactor_iface import Sink
from ports.codegraph import CodeGraphQueryKind, CodeGraphResult
from ports.events import Event
from ports.host import HostAction, HostCapability, HostDenied, HostIntent, HostResult
from ports.observability import ObsEvent
from ports.providers import Citation, GenerateResult, RerankResult
from ports.secrets import SecretNotFoundError, SecretRef


class FakeClock:
    """Deterministic `Clock` — time only moves when you `advance()` it forward.

    Enforces the same contract the real `SystemClock` upholds (parse-don't-trust):
    `start` must be timezone-aware (a naive datetime is rejected), and `advance`
    is forward-only so `now()`/`monotonic()` stay non-decreasing.
    """

    def __init__(self, start: datetime) -> None:
        if start.utcoffset() is None:
            raise ValueError("FakeClock start must be timezone-aware (UTC), not naive")
        self._now = start
        self._monotonic = 0.0

    def now(self) -> datetime:
        return self._now

    def monotonic(self) -> float:
        return self._monotonic

    def advance(self, delta: timedelta) -> None:
        """Move both the wall and monotonic clocks forward by `delta` (must be >= 0)."""
        if delta < timedelta(0):
            raise ValueError("FakeClock.advance delta must be non-negative (forward-only)")
        self._now += delta
        self._monotonic += delta.total_seconds()


class FakeIdGen:
    """Deterministic `IdGen` — reproducible per-kind sequence, distinct kinds never collide.

    Ids are opaque: `kind` separates the internal counters but is not recoverable from
    the emitted token (honors the opaque-id convention).
    """

    def __init__(self) -> None:
        self._counters: dict[str, int] = {}

    def new_id(self, kind: str) -> str:
        n = self._counters.get(kind, 0)
        self._counters[kind] = n + 1
        digest = hashlib.sha256(f"{kind}\x00{n}".encode()).hexdigest()
        return f"fakeid-{digest[:24]}"


class FakeSeed:
    """Deterministic `Seed` — the same seed yields the same draw sequence."""

    def __init__(self, seed: int) -> None:
        self._seed = seed

    def rng(self) -> random.Random:
        """Return a FRESH seeded `random.Random` at position 0 (parallel to `SystemSeed`).

        Hold the returned generator and draw from it repeatedly within a context;
        each `rng()` call restarts the same sequence, so don't call `rng()` expecting
        a continuing stream.
        """
        return random.Random(self._seed)


class FakeHost:
    """Deterministic, fail-closed `HostPort` double — the safety-seam fake every track injects.

    Upholds the SAME fail-closed allowlist contract a real host must (LESSON 1 fidelity — no looser
    fake on a safety seam, Key safety rule #4): `authorize` denies any capability outside the
    configured allowlist with `HostDenied`; `perform` executes ONLY an authorized action AND
    re-validates the capability allowlist (so a forged `authorized=True` for a non-allowlisted
    capability is still denied), recording performed actions for test assertions.
    """

    def __init__(self, capabilities: Iterable[HostCapability] = ()) -> None:
        self._capabilities = frozenset(capabilities)
        self.performed: list[HostAction] = []

    def capabilities(self) -> frozenset[HostCapability]:
        return self._capabilities

    def authorize(self, intent: HostIntent) -> HostAction:
        if intent.capability not in self._capabilities:
            raise HostDenied(f"capability {intent.capability.value!r} not in host allowlist")
        return HostAction(capability=intent.capability, summary=intent.summary, authorized=True)

    def perform(self, action: HostAction) -> HostResult:
        if not action.authorized:
            raise HostDenied("perform requires an action produced by authorize (forged rejected)")
        # defense in depth: never run a non-allowlisted capability even if `authorized` is forged.
        if action.capability not in self._capabilities:
            raise HostDenied(f"capability {action.capability.value!r} not in host allowlist")
        self.performed.append(action)
        return HostResult(ok=True, detail=f"performed {action.capability.value}")


class FakeEmbeddingProvider:
    """Deterministic `EmbeddingProvider` — a stable vector per text (no wall-clock/RNG)."""

    def __init__(self, dimension: int = 8, model_version: str = "fake-embed-v1") -> None:
        # Enforce the §5 dimension floor — a 0/negative-dim fake emits [] vectors that pass shape
        # assertions trivially and could mask a real dim-mismatch (LESSON 1: no looser fake).
        if dimension < 1:
            raise ValueError("FakeEmbeddingProvider dimension must be >= 1")
        self._dimension = dimension
        self._model_version = model_version

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_version(self) -> str:
        return self._model_version

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    def _vector(self, text: str) -> list[float]:
        # Deterministic per-text vector: expand a sha256 digest to `dimension` floats in [0, 1].
        digest = hashlib.sha256(text.encode()).digest()
        return [digest[i % len(digest)] / 255.0 for i in range(self._dimension)]


class FakeReranker:
    """Deterministic `Reranker` — a stable per-(query, doc) score, sorted score-desc."""

    def rerank(self, query: str, documents: Sequence[str]) -> list[RerankResult]:
        scored = [
            RerankResult(index=i, score=self._score(query, d)) for i, d in enumerate(documents)
        ]
        return sorted(scored, key=lambda r: r.score, reverse=True)

    def _score(self, query: str, doc: str) -> float:
        digest = hashlib.sha256(f"{query}\x00{doc}".encode()).hexdigest()
        return int(digest[:8], 16) / 0xFFFFFFFF


class FakeContextStrategy:
    """Deterministic `ContextStrategy` — prepends the document-context blurb to the chunk."""

    def augment(self, chunk_text: str, document_context: str) -> str:
        return f"{document_context}\n\n{chunk_text}"


class FakeModelProvider:
    """Deterministic `ModelProvider` — canned answer text + citations (no live generation)."""

    def __init__(
        self, text: str = "fake generated answer", citations: list[Citation] | None = None
    ) -> None:
        self._text = text
        default = [Citation(cited_text="fake cite", source_index=0)]
        # copy: don't alias the caller's list (post-construction mutation must not bleed in).
        self._citations = list(default if citations is None else citations)

    def generate(self, prompt: str) -> GenerateResult:
        return GenerateResult(text=self._text, citations=list(self._citations))


class FakeCodeGraph:
    """Deterministic `CodeGraphPort` double — canned per-kind results (configurable).

    Same (kind, sym) → same result (no wall-clock/RNG). A `results` map supplies a canned
    `CodeGraphResult` per kind; for kinds with no canned result, `query` echoes the requested
    symbol back as the single result (a stable, contract-shaped default).
    """

    def __init__(self, results: dict[CodeGraphQueryKind, CodeGraphResult] | None = None) -> None:
        self._results = dict(results) if results is not None else {}

    def query(self, kind: CodeGraphQueryKind, sym: str) -> CodeGraphResult:
        if kind in self._results:
            return self._results[kind]
        return CodeGraphResult(kind=kind, symbols=(sym,))


class FakeEventSource:
    """Deterministic `EventSource` — `poll` and `subscribe` consume the SAME pending queue.

    Both paths deliver-and-drain the queue, so they share one consistent view-of-world (poll then
    subscribe on the same instance correctly sees zero events the second time).
    """

    def __init__(self, events: Sequence[Event] = ()) -> None:
        self._queue: list[Event] = list(events)

    def poll(self) -> tuple[Event, ...]:
        drained = tuple(self._queue)
        self._queue.clear()
        return drained

    def subscribe(self, handler: Callable[[Event], None]) -> None:
        drained = tuple(self._queue)
        self._queue.clear()
        for event in drained:
            handler(event)


class FakeSecretStore:
    """Deterministic `SecretStore` double — in-memory test secrets resolved by ref.

    Secrets live OUT-OF-BAND in a private dict (never on the `SecretRef`, never in `repr`).
    `get_ref` returns coordinates; `resolve` returns the transient plaintext (Key safety rule #3)
    and fails closed with `SecretNotFoundError` on an unknown ref (never a silent empty string).
    """

    def __init__(
        self, secrets: dict[str, str] | None = None, service: str = "nexus-brain-test"
    ) -> None:
        self._service = service
        self._secrets = dict(secrets) if secrets is not None else {}

    def get_ref(self, name: str) -> SecretRef:
        return SecretRef(service=self._service, account=name)

    def resolve(self, ref: SecretRef) -> str:
        if ref.account not in self._secrets:
            raise SecretNotFoundError(f"no secret for account={ref.account!r}")
        return self._secrets[ref.account]


class FakeRedactor:
    """Deterministic `Redactor` double — observably strips obvious prefix-tokened credentials.

    A TEST DOUBLE, NOT the catchable-set engine (that is Phase-2.3 + its fuzz gate) — it makes NO
    recall/FP claim and intentionally misses the entropy/JSON/env classes. Its job is to be a
    contract-faithful stand-in (LESSON 1 fidelity — no looser fake on a safety seam): it upholds
    every behavioral invariant the real engine must —
      - idempotent — replaces matched tokens with a fixed marker that the pattern can't re-match;
      - never raises — `re.sub` tolerates any input string (empty / NUL+control / long / non-ASCII);
      - git-SHA passthrough — the credential prefixes (`ghp_`, `github_pat_`, `sk-`, `xoxb-`) cannot
        occur inside bare hex, so a 40/64-char SHA always survives (§18 / D-14 zero-tolerance);
      - pure — in-memory string substitution, no network / no file I/O (safety rule #6).
    `sink` is accepted but applies NO per-sink strictness (D-A5/D-A6 owner-deferred — the param is
    here so the signature accommodates a future cloud-stricter engine, not to branch on it now).
    """

    # Prefix-tokened credential shapes only — deliberately narrow; entropy/JSON/env classes are the
    # real engine's job. Anchored on the canonical (lowercase) credential prefixes, matched
    # case-sensitively: real PATs/keys are lowercase-prefixed, and each prefix carries a `-`/`_`
    # that can never occur in bare hex, so git SHAs (any case) are passthrough-safe by construction.
    # A deliberately upper-cased prefix is not a real token and is (correctly) left untouched.
    _TOKEN_RE = re.compile(r"(?:github_pat_|ghp_|sk-|xoxb-)[A-Za-z0-9_-]+")
    _MARKER = "[REDACTED]"

    def redact(self, payload: str, sink: Sink) -> str:
        return self._TOKEN_RE.sub(self._MARKER, payload)


class FakeObservabilitySink:
    """`ObservabilitySink` double — records emitted events LOCALLY (never network)."""

    def __init__(self) -> None:
        self.emitted: list[ObsEvent] = []

    def emit(self, event: ObsEvent) -> None:
        self.emitted.append(event)
